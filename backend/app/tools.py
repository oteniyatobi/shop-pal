"""Tools the shopping agent can call, plus the per-session cart they operate on.

Each tool returns two things:
  - `result`: JSON sent back to the LLM so it can reason about what happened
  - `ui`:     structured data the frontend renders (product cards, cart, checkout button)
"""

from decimal import ROUND_HALF_UP, Decimal

from . import products

CENTS = Decimal("0.01")
MAX_QUANTITY = 10


def to_money(value) -> Decimal:
    """Convert a float/str price to a 2-decimal Decimal (avoids float rounding bugs)."""
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


class Cart:
    """In-memory cart keyed by product ID."""

    def __init__(self):
        self.items: dict[int, dict] = {}

    def add(self, product: dict, quantity: int) -> None:
        line = self.items.get(product["id"])
        if line:
            line["quantity"] = min(line["quantity"] + quantity, MAX_QUANTITY)
        else:
            self.items[product["id"]] = {
                "id": product["id"],
                "title": product["title"],
                "image": product["image"],
                "unit_price": to_money(product["price"]),
                "quantity": quantity,
            }

    def remove(self, product_id: int, quantity: int | None = None) -> bool:
        """Remove `quantity` units (or the whole line if None). Returns False if not in cart."""
        line = self.items.get(product_id)
        if not line:
            return False
        if quantity is None or quantity >= line["quantity"]:
            del self.items[product_id]
        else:
            line["quantity"] -= quantity
        return True

    def clear(self) -> None:
        self.items.clear()

    def is_empty(self) -> bool:
        return not self.items

    def total(self) -> Decimal:
        return sum((line["unit_price"] * line["quantity"] for line in self.items.values()), Decimal("0.00"))

    def snapshot(self) -> dict:
        """JSON-friendly view of the cart. Money is formatted as strings like "12.99"."""
        return {
            "items": [
                {
                    "id": line["id"],
                    "title": line["title"],
                    "image": line["image"],
                    "unit_price": f"{line['unit_price']:.2f}",
                    "quantity": line["quantity"],
                    "line_total": f"{line['unit_price'] * line['quantity']:.2f}",
                }
                for line in self.items.values()
            ],
            "item_count": sum(line["quantity"] for line in self.items.values()),
            "total": f"{self.total():.2f}",
            "currency": "USD",
        }


# --- Function-calling schemas (OpenAI format, accepted by Gemini's compatible API) -------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Search the store catalog. Use short keywords (e.g. 'backpack', 'jacket', 'ring') "
                "and the category/price filters to narrow results. Results are shown to the user as cards."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keywords describing the product."},
                    "category": {"type": "string", "enum": products.CATEGORIES},
                    "min_price": {"type": "number", "description": "Minimum price in USD."},
                    "max_price": {"type": "number", "description": "Maximum price in USD."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get the full details (description, rating) of one product.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "integer"}},
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add a product to the user's cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer"},
                    "quantity": {"type": "integer", "description": f"1 to {MAX_QUANTITY}. Defaults to 1."},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_cart",
            "description": "Show the current contents and total of the user's cart.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_cart",
            "description": "Remove a product from the cart. Omit quantity to remove it entirely.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer"},
                    "quantity": {"type": "integer", "description": "How many units to remove."},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checkout",
            "description": (
                "Start checkout when the user is ready to pay. Displays a PayPal payment button "
                "in the chat for the current cart."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# --- Tool implementations --------------------------------------------------------------

def _search_products(cart: Cart, query: str = "", category=None, min_price=None, max_price=None):
    found = products.search_products(query, category, min_price, max_price)
    # Label each result with the number shown on its card, so "the first one" means the same
    # thing to the model as to the user.
    numbered = [{"card_number": i + 1, **p} for i, p in enumerate(found["results"])]
    result = {
        **found,
        "results": numbered,
        "note": "Each result's card_number is the number shown on its card. Present them in card_number order.",
    }
    return result, {"products": found["results"]}


def _get_product_details(cart: Cart, product_id: int):
    product = products.get_product(product_id)
    if not product:
        return {"error": f"No product with id {product_id}."}, {}
    details = products.summarize(product, description_chars=600)
    return details, {"products": [details]}


def _add_to_cart(cart: Cart, product_id: int, quantity: int = 1):
    product = products.get_product(product_id)
    if not product:
        return {"error": f"No product with id {product_id}."}, {}
    quantity = max(1, min(int(quantity), MAX_QUANTITY))
    cart.add(product, quantity)
    snapshot = cart.snapshot()
    return {"added": product["title"], "quantity": quantity, "cart": snapshot}, {"cart": snapshot}


def _view_cart(cart: Cart):
    snapshot = cart.snapshot()
    return snapshot, {"cart": snapshot}


def _remove_from_cart(cart: Cart, product_id: int, quantity: int | None = None):
    if not cart.remove(product_id, quantity):
        return {"error": f"Product {product_id} is not in the cart."}, {}
    snapshot = cart.snapshot()
    return {"removed": product_id, "cart": snapshot}, {"cart": snapshot}


def _checkout(cart: Cart):
    if cart.is_empty():
        return {"error": "The cart is empty. Help the user find something first."}, {}
    snapshot = cart.snapshot()
    return (
        {"status": "payment_button_displayed", "cart": snapshot},
        {"cart": snapshot, "checkout": True},
    )


_HANDLERS = {
    "search_products": _search_products,
    "get_product_details": _get_product_details,
    "add_to_cart": _add_to_cart,
    "view_cart": _view_cart,
    "remove_from_cart": _remove_from_cart,
    "checkout": _checkout,
}


def execute_tool(name: str, args: dict, cart: Cart) -> tuple[dict, dict]:
    """Run a tool by name. Errors are returned to the LLM rather than raised,
    so the agent can recover (e.g. apologize or retry with different args)."""
    handler = _HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool '{name}'."}, {}
    try:
        return handler(cart, **args)
    except TypeError as exc:  # bad/missing arguments from the model
        return {"error": f"Invalid arguments for {name}: {exc}"}, {}
    except Exception as exc:  # e.g. Fake Store API is down
        return {"error": f"{name} failed: {exc}"}, {}
