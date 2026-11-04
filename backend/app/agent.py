"""The ShopPal agent: a function-calling loop over the shopping tools, powered by Google Gemini.

We talk to Gemini through its OpenAI-compatible endpoint, so we can use the
standard `openai` SDK and OpenAI-style tool definitions unchanged.

Flow for each user message:
  1. Append the message to the session's conversation history.
  2. Ask the model for a reply. If it requests tool calls, run them, append the
     results, and ask again — up to MAX_TOOL_ROUNDS times.
  3. Return the final text reply plus any UI data (products, cart, checkout)
     the tools produced along the way.
"""

import json
import os

from openai import APIConnectionError, InternalServerError, OpenAI, RateLimitError

from .tools import TOOL_DEFINITIONS, Cart, execute_tool

# Flash-Lite is fast (~3s) and has far more free-tier headroom than Flash, which
# rate-limits after a request or two; each chat turn makes 2-3 model calls.
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
# Lighter model tried when the main one is overloaded (503), rate-limited (429) or slow.
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.1-flash-lite")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
REQUEST_TIMEOUT_SECONDS = 30
MAX_TOOL_ROUNDS = 6


class AgentBusyError(RuntimeError):
    """Gemini is overloaded, rate-limited or timing out. Safe for the user to retry."""

SYSTEM_PROMPT = """You are ShopPal, a friendly and concise AI shopping assistant.

How to help:
- Always use search_products to find items. Never invent products, prices, or IDs.
- The catalog is small and has four categories: electronics, jewelery, men's clothing, women's clothing.
  Translate vague requests (e.g. "a gift for my mom") into sensible keywords, categories and price filters.
- Product cards are shown to the user automatically, numbered 1, 2, 3 in the order search results return them.
  Mention products in that same order so "the first one" is unambiguous, and don't repeat full descriptions.
  Briefly say why each option fits (one short line each).
- When the user says "the first one", "the cheaper one", etc., map it to the IDs from your most recent results.
- Confirm every cart change with the item name and new cart total.
- When the user is ready to pay, call checkout. A PayPal button appears right below your message — tell them to use it.
- Never ask for card numbers or personal payment details; PayPal handles payment securely.
- All prices are in USD. Keep replies short and conversational."""

_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Create the client lazily so the app can boot without a key (e.g. for health checks)."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        # No silent SDK retries: the fallback model below is our retry, and the user
        # gets an answer (or a clear error) within about a minute at worst.
        _client = OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=0)
    return _client


def _complete(messages: list[dict]):
    """Call Gemini, falling back to a lighter model when the main one is busy."""
    for model in dict.fromkeys([MODEL, FALLBACK_MODEL]):  # de-duplicated, order kept
        try:
            return get_client().chat.completions.create(model=model, messages=messages, tools=TOOL_DEFINITIONS)
        except (APIConnectionError, RateLimitError, InternalServerError):  # timeouts, 429s and 5xx
            continue
    raise AgentBusyError("ShopPal is a little busy right now. Please try again in a moment.")


class Session:
    """Everything we remember about one shopper. Stored in memory (fine for a demo)."""

    def __init__(self):
        self.history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.cart = Cart()
        self.pending_order_id: str | None = None  # PayPal order awaiting capture
        self.orders: list[dict] = []


_sessions: dict[str, Session] = {}


def get_session(session_id: str) -> Session:
    if session_id not in _sessions:
        _sessions[session_id] = Session()
    return _sessions[session_id]


def run_agent(session: Session, user_message: str | None = None, system_note: str | None = None) -> dict:
    """Run one agent turn. Pass `system_note` to inform the agent of an app event
    (like a completed payment) without it appearing as something the user said."""
    turn_start = len(session.history)
    if user_message:
        session.history.append({"role": "user", "content": user_message})
    if system_note:
        # Sent as a tagged user turn: Gemini only accepts system messages at the start of a chat.
        session.history.append({"role": "user", "content": f"[App event, not typed by the shopper] {system_note}"})

    try:
        return _run_tool_loop(session)
    except Exception:
        # Drop the failed turn so the history stays valid and a retry starts clean.
        del session.history[turn_start:]
        raise


def _run_tool_loop(session: Session) -> dict:
    """Ask the model, run any tools it requests, and repeat until it replies with text."""
    ui: dict = {"products": None, "cart": None, "checkout": False}

    for _ in range(MAX_TOOL_ROUNDS):
        message = _complete(session.history).choices[0].message

        # Store the assistant turn (including any tool calls) in plain-dict form.
        # Tool calls are dumped as-is so Gemini's extra fields (e.g. thought signatures,
        # which Gemini 3 models require on the next request) are sent back intact.
        entry: dict = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            entry["tool_calls"] = [call.model_dump(exclude_none=True) for call in message.tool_calls]
        session.history.append(entry)

        if not message.tool_calls:
            return {"reply": message.content or "", **ui}

        # Execute each requested tool and feed the results back to the model.
        for call in message.tool_calls:
            try:
                args = json.loads(call.function.arguments or "{}")
                result, ui_update = execute_tool(call.function.name, args, session.cart)
            except json.JSONDecodeError:
                result, ui_update = {"error": "Tool arguments were not valid JSON."}, {}

            # Later tool calls win, e.g. a second search replaces the first one's cards.
            for key, value in ui_update.items():
                ui[key] = value

            session.history.append(
                {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)}
            )

    return {"reply": "Sorry, I got a bit tangled up there. Could you rephrase that?", **ui}
