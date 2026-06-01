import json
from pathlib import Path
from typing import Any

from src.rag.store import VinFastRAGStore

DEFAULT_INDEX = Path(__file__).resolve().parents[2] / "data" / "rag_index.pkl"

_store: VinFastRAGStore | None = None


def get_rag_store() -> VinFastRAGStore:
    global _store
    if _store is None:
        _store = VinFastRAGStore()
        if not _store.load(DEFAULT_INDEX):
            data_path = Path(__file__).resolve().parents[2] / "vinfast_rag_data.json"
            _store.build_from_json(data_path)
            _store.save(DEFAULT_INDEX)
    return _store


def lookup_vehicle(query: str, top_k: int = 4) -> dict[str, Any]:
    store = get_rag_store()
    hits = store.search(query, top_k=top_k)
    return {
        "ok": True,
        "query": query,
        "count": len(hits),
        "results": hits,
    }


def compare_vehicles(model_a: str, model_b: str) -> dict[str, Any]:
    store = get_rag_store()
    data = store.compare_models([model_a, model_b])
    return {"ok": True, "comparison": data}


def get_vehicle_specs(model: str) -> dict[str, Any]:
    """Retrieve structured specifications for a specific vehicle model."""
    store = get_rag_store()
    hits = store.search(f"thông số kỹ thuật động cơ pin kích thước {model}", top_k=4, model_filter=model)
    
    from src.rag.store import _extract_highlights
    highlights = _extract_highlights(hits)
    text_snippet = " ".join(h.get("snippet", "") for h in hits)
    
    return {
        "ok": True,
        "model": model,
        "specs": highlights,
        "details": text_snippet,
        "sources": [h.get("url") for h in hits if h.get("url")]
    }


def format_lookup_for_agent(payload: dict[str, Any]) -> str:
    results = payload.get("results", [])
    if not results:
        return "Không tìm thấy thông tin xe phù hợp trong cơ sở dữ liệu."
    
    formatted = []
    for idx, r in enumerate(results, 1):
        formatted.append(
            f"=== TÀI LIỆU KHẢO SÁT [{idx}] ===\n"
            f"• Tiêu đề: {r.get('title', 'N/A')}\n"
            f"• Dòng xe liên quan: {', '.join(r.get('models', []))}\n"
            f"• Nội dung chi tiết:\n{r.get('snippet', '').strip()}\n"
        )
    return "\n".join(formatted)


def format_comparison_for_agent(payload: dict[str, Any]) -> str:
    comparison = payload.get("comparison", {})
    models_data = comparison.get("models", {})
    if not models_data:
        return "Không có dữ liệu so sánh phù hợp trong cơ sở dữ liệu."
    
    formatted = []
    formatted.append("=== KẾT QUẢ SO SÁNH XE ===")
    for model, data in models_data.items():
        highlights = data.get("highlights", {})
        formatted.append(f"\n--- THÔNG TIN DÒNG XE: {model} ---")
        formatted.append(f"• Giá lăn bánh/niêm yết dự kiến: {highlights.get('price_hint') or 'Chưa rõ'}")
        formatted.append(f"• Kích thước tổng thể: {highlights.get('dimensions') or 'Chưa rõ'}")
        formatted.append(f"• Quãng đường di chuyển (WLTP): {highlights.get('range_hint') or 'Chưa rõ'}")
        formatted.append(f"• Số chỗ ngồi: {highlights.get('seats') or 'Chưa rõ'}")
        
        formatted.append("\nTài liệu chi tiết đính kèm:")
        for idx, chunk in enumerate(data.get("chunks", []), 1):
            formatted.append(f"  [{idx}] {chunk.get('title')}:\n  {chunk.get('snippet').strip()}\n")
            
    return "\n".join(formatted)

