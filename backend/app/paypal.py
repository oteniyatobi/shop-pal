"""PayPal REST API integration (Orders v2), sandbox by default.

Flow:
  1. Frontend PayPal button calls our /api/paypal/orders -> create_order()
     The order total is computed server-side from the cart, never trusted from the browser.
  2. User approves the payment in the PayPal popup.
  3. Frontend calls /api/paypal/orders/{id}/capture -> capture_order() moves the money.

Mock mode: if PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET aren't set, orders are simulated
locally (IDs start with "MOCK-") so the rest of the app can be developed without keys.
Mock mode switches off automatically as soon as real credentials are configured.
"""

import os
import time
import uuid

import httpx

from .tools import Cart

_token: dict = {"value": None, "expires_at": 0.0}

MOCK_PREFIX = "MOCK-"


def base_url() -> str:
    return os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")


def is_configured() -> bool:
    """True when real PayPal credentials are present (otherwise we run in mock mode)."""
    return bool(os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET"))


def _get_access_token() -> str:
    """Fetch an OAuth2 token with client credentials, cached until shortly before it expires."""
    if _token["value"] and time.time() < _token["expires_at"]:
        return _token["value"]

    client_id = os.getenv("PAYPAL_CLIENT_ID")
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be set.")

    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{base_url()}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
        )
        resp.raise_for_status()
        data = resp.json()

    _token["value"] = data["access_token"]
    _token["expires_at"] = time.time() + data.get("expires_in", 3600) - 60
    return _token["value"]


def _request(method: str, path: str, json_body: dict | None = None) -> dict:
    token = _get_access_token()
    with httpx.Client(timeout=20) as client:
        resp = client.request(
            method,
            f"{base_url()}{path}",
            json=json_body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


def create_order(cart: Cart) -> dict:
    """Create a PayPal order with itemized line items so the buyer sees what they're paying for."""
    if not is_configured():
        return {"id": f"{MOCK_PREFIX}{uuid.uuid4().hex[:16].upper()}", "status": "CREATED"}

    snapshot = cart.snapshot()
    total = snapshot["total"]
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "description": "ShopPal order",
                "amount": {
                    "currency_code": "USD",
                    "value": total,
                    # PayPal requires item_total to equal the sum of unit_amount * quantity.
                    "breakdown": {"item_total": {"currency_code": "USD", "value": total}},
                },
                "items": [
                    {
                        "name": item["title"][:127],  # PayPal max length
                        "unit_amount": {"currency_code": "USD", "value": item["unit_price"]},
                        "quantity": str(item["quantity"]),
                        "category": "PHYSICAL_GOODS",
                    }
                    for item in snapshot["items"]
                ],
            }
        ],
    }
    return _request("POST", "/v2/checkout/orders", body)


def capture_order(order_id: str) -> dict:
    """Capture an approved order. Returns PayPal's response (status == 'COMPLETED' on success)."""
    if not is_configured() and order_id.startswith(MOCK_PREFIX):
        # Mimic the fields of PayPal's capture response that main.py reads.
        return {"id": order_id, "status": "COMPLETED", "payer": {"name": {"given_name": "Demo"}}}

    return _request("POST", f"/v2/checkout/orders/{order_id}/capture")
