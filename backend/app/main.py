"""ShopPal Flask app.

Routes:
  GET  /api/health                        - liveness check (used by Render)
  GET  /api/config                        - public config for the frontend (PayPal client ID)
  POST /api/chat                          - send a message to the shopping agent
  POST /api/paypal/orders                 - create a PayPal order from the session's cart
  POST /api/paypal/orders/<id>/capture    - capture payment, then have the agent confirm

In production, the built React app (frontend/dist) is served from "/" too,
so the whole project deploys as a single Render web service.
"""

from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")  # must run before modules that read env vars at import time

import os  # noqa: E402

import httpx  # noqa: E402
from flask import Flask, jsonify, request, send_from_directory  # noqa: E402
from flask_cors import CORS  # noqa: E402

from . import paypal  # noqa: E402
from .agent import AgentBusyError, get_session, run_agent  # noqa: E402

FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

# static_folder=None: we serve the React build ourselves (see the catch-all route below).
app = Flask(__name__, static_folder=None)

# Only needed if the frontend is served from a different origin than the API.
# In local dev, Vite proxies /api to this server, so CORS isn't involved.
frontend_origin = os.getenv("FRONTEND_ORIGIN")
if frontend_origin:
    CORS(app, origins=[frontend_origin])


def error(message: str, status: int):
    """JSON error response. The frontend reads the `detail` field."""
    return jsonify({"detail": message}), status


def session_from_request():
    """Parse the JSON body and look up the shopper's session.
    Returns (session, body), or (None, body) if session_id is missing/invalid."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    if not isinstance(session_id, str) or not 8 <= len(session_id) <= 64:
        return None, body
    return get_session(session_id), body


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    # The client ID is public by design; the secret never leaves the server.
    # An empty ID tells the frontend to use mock checkout (see paypal.is_configured).
    client_id = os.getenv("PAYPAL_CLIENT_ID", "") if paypal.is_configured() else ""
    return {"paypal_client_id": client_id}


@app.post("/api/chat")
def chat():
    session, body = session_from_request()
    if session is None:
        return error("Missing or invalid session_id.", 400)

    message = body.get("message")
    if not isinstance(message, str) or not 1 <= len(message.strip()) <= 2000:
        return error("Message must be 1-2000 characters.", 400)

    try:
        return run_agent(session, user_message=message)
    except AgentBusyError as exc:
        return error(str(exc), 503)
    except Exception as exc:
        app.logger.exception("Agent turn failed")
        return error(f"Sorry, something went wrong: {exc}", 502)


@app.post("/api/paypal/orders")
def create_paypal_order():
    session, _ = session_from_request()
    if session is None:
        return error("Missing or invalid session_id.", 400)
    if session.cart.is_empty():
        return error("Cart is empty.", 400)

    try:
        order = paypal.create_order(session.cart)
    except (httpx.HTTPError, RuntimeError) as exc:
        return error(f"PayPal error: {exc}", 502)

    session.pending_order_id = order["id"]
    return {"id": order["id"]}


@app.post("/api/paypal/orders/<order_id>/capture")
def capture_paypal_order(order_id: str):
    session, _ = session_from_request()
    if session is None:
        return error("Missing or invalid session_id.", 400)
    # Only capture orders this session actually created.
    if order_id != session.pending_order_id:
        return error("Unknown order for this session.", 400)

    try:
        result = paypal.capture_order(order_id)
    except (httpx.HTTPError, RuntimeError) as exc:
        return error(f"PayPal error: {exc}", 502)

    status = result.get("status")
    if status != "COMPLETED":
        return {"status": status, "reply": "The payment didn't go through. Want to try again?"}

    # Record the order and empty the cart.
    order = session.cart.snapshot()
    payer_name = result.get("payer", {}).get("name", {}).get("given_name", "")
    session.orders.append({"order_id": order_id, **order})
    session.cart.clear()
    session.pending_order_id = None

    # Let the agent write the confirmation so it stays in the conversation's voice.
    items = ", ".join(f"{i['quantity']} x {i['title']}" for i in order["items"])
    note = (
        f"APP EVENT: PayPal payment captured successfully. Order ID: {order_id}. "
        f"Payer first name: {payer_name or 'unknown'}. Items: {items}. Total: ${order['total']} USD. "
        "Thank the user and give a short order summary. Do not call checkout again."
    )
    try:
        reply = run_agent(session, system_note=note)["reply"]
    except Exception:
        reply = f"Payment complete! Order {order_id} for ${order['total']} is confirmed."

    return {"status": status, "order_id": order_id, "order": order, "reply": reply}


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def frontend(path: str):
    """Serve the built React app. Unknown paths fall back to index.html."""
    if path.startswith("api/"):
        return error("Not found.", 404)
    if not FRONTEND_DIST.exists():
        return error("Frontend not built. Use the Vite dev server, or run `npm run build` in frontend/.", 404)
    if path and (FRONTEND_DIST / path).is_file():
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")
