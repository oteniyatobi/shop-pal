"""Wrapper around the Fake Store API (https://fakestoreapi.com).

The catalog is small (~20 items), so we fetch it once, cache it in memory,
and do filtering/keyword matching locally. That keeps search fast and avoids
hammering the free API.
"""

import time

import httpx

FAKE_STORE_URL = "https://fakestoreapi.com"
CACHE_TTL_SECONDS = 600

# Categories exposed by the Fake Store API. Also used as an enum in the tool schema.
CATEGORIES = ["electronics", "jewelery", "men's clothing", "women's clothing"]

# Filler words that shouldn't count as search keywords.
STOPWORDS = {"the", "for", "and", "with", "under", "over", "some", "any", "something", "want", "need"}

_cache: dict = {"products": None, "fetched_at": 0.0}


def get_all_products() -> list[dict]:
    """Return the full catalog, refreshing the cache when it goes stale."""
    now = time.time()
    if _cache["products"] is None or now - _cache["fetched_at"] > CACHE_TTL_SECONDS:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{FAKE_STORE_URL}/products")
            resp.raise_for_status()
            _cache["products"] = resp.json()
            _cache["fetched_at"] = now
    return _cache["products"]


def get_product(product_id: int) -> dict | None:
    """Look up a single product by ID (from the cached catalog)."""
    products = get_all_products()
    return next((p for p in products if p["id"] == product_id), None)


def summarize(product: dict, description_chars: int = 160) -> dict:
    """Trim a raw product down to the fields the LLM and UI actually need."""
    description = product.get("description", "")
    if len(description) > description_chars:
        description = description[:description_chars].rstrip() + "…"
    rating = product.get("rating") or {}
    return {
        "id": product["id"],
        "title": product["title"],
        "price": product["price"],
        "category": product["category"],
        "image": product["image"],
        "description": description,
        "rating": rating.get("rate"),
        "rating_count": rating.get("count"),
    }


def search_products(
    query: str = "",
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 5,
) -> dict:
    """Filter by category/price, then rank by keyword overlap with the query.

    If no product matches the keywords, we fall back to the price/category
    matches so the agent still has something sensible to recommend
    (e.g. "a gift for my mom" has no literal keyword hits).
    """
    products = get_all_products()
    terms = [t for t in query.lower().split() if len(t) > 2 and t not in STOPWORDS]

    def keyword_score(p: dict) -> int:
        text = f"{p['title']} {p['description']} {p['category']}".lower()
        return sum(1 for t in terms if t in text)

    filtered = [
        p
        for p in products
        if (not category or p["category"].lower() == category.lower())
        and (min_price is None or p["price"] >= min_price)
        and (max_price is None or p["price"] <= max_price)
    ]

    scored = [(keyword_score(p), p) for p in filtered]
    keyword_hits = [(s, p) for s, p in scored if s > 0]
    exact_match = bool(keyword_hits) or not terms
    candidates = keyword_hits if keyword_hits else scored

    # Best keyword match first, then highest rated.
    candidates.sort(key=lambda sp: (-sp[0], -(sp[1].get("rating") or {}).get("rate", 0)))
    return {
        "keyword_match": exact_match,
        "results": [summarize(p) for _, p in candidates[:limit]],
    }
