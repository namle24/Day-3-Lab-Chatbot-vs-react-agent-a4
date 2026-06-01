from typing import Any

from src.tools.vehicle_lookup import get_rag_store


def search_reviews(query: str, car_model: str | None = None, top_k: int = 3) -> dict[str, Any]:
    """Search marketing/review-style content for a vehicle."""
    enriched = f"đánh giá review khách hàng ưu nhược điểm {car_model or ''} {query}".strip()
    store = get_rag_store()
    hits = store.search(enriched, top_k=top_k, model_filter=car_model)
    return {
        "ok": True,
        "query": query,
        "car_model": car_model,
        "reviews": hits,
    }
