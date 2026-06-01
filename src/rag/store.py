import pickle
import re
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from src.rag.chunking import load_chunks_from_json, normalize_model_label


class VinFastRAGStore:
    """TF-IDF vector search over VinFast knowledge chunks."""

    def __init__(self) -> None:
        self.chunks: list[dict[str, Any]] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None

    @property
    def is_ready(self) -> bool:
        return self._matrix is not None and len(self.chunks) > 0

    def build_from_json(self, data_path: Path) -> int:
        self.chunks = load_chunks_from_json(data_path)
        texts = [c["text"] for c in self.chunks]
        self._vectorizer = TfidfVectorizer(
            max_features=20000,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self._matrix = self._vectorizer.fit_transform(texts)
        return len(self.chunks)

    def save(self, index_path: Path) -> None:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunks": self.chunks,
            "vectorizer": self._vectorizer,
            "matrix": self._matrix,
        }
        index_path.write_bytes(pickle.dumps(payload))

    def load(self, index_path: Path) -> bool:
        if not index_path.exists():
            return False
        payload = pickle.loads(index_path.read_bytes())
        self.chunks = payload["chunks"]
        self._vectorizer = payload["vectorizer"]
        self._matrix = payload["matrix"]
        return True

    def _model_boost(self, chunk: dict[str, Any], query_models: list[str]) -> float:
        if not query_models:
            return 0.0
        chunk_models = {m.upper().replace(" ", "") for m in chunk.get("models", [])}
        q_models = {m.upper().replace(" ", "") for m in query_models}
        overlap = chunk_models & q_models
        if overlap:
            return 0.15
        for q in q_models:
            for c in chunk_models:
                if q in c or c in q:
                    return 0.08
        return 0.0

    def search(
        self,
        query: str,
        top_k: int = 4,
        model_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.is_ready:
            raise RuntimeError("RAG index is not built. Run ingest first.")

        assert self._vectorizer is not None
        assert self._matrix is not None

        query_vec = self._vectorizer.transform([query])
        scores = linear_kernel(query_vec, self._matrix).flatten()
        query_models = normalize_model_label(query)
        if model_filter:
            query_models.extend(normalize_model_label(model_filter))

        ranked = []
        for idx, score in enumerate(scores):
            chunk = self.chunks[idx]
            boosted = float(score) + self._model_boost(chunk, query_models)
            ranked.append((boosted, idx))

        ranked.sort(key=lambda x: x[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, idx in ranked[:top_k]:
            if score <= 0:
                continue
            c = self.chunks[idx]
            snippet = c["text"][:500] + ("..." if len(c["text"]) > 500 else "")
            results.append(
                {
                    "score": round(score, 4),
                    "title": c.get("title", ""),
                    "url": c.get("url", ""),
                    "models": c.get("models", []),
                    "category": c.get("category", ""),
                    "snippet": snippet,
                    "text": c.get("text", ""),
                    "chunk_index": c.get("chunk_index"),
                    "keywords": c.get("keywords", []),
                    "short": c.get("short", False),
                }
            )
        return results

    def compare_models(self, models: list[str], top_k_per_model: int = 2) -> dict[str, Any]:
        comparison: dict[str, Any] = {"models": {}, "sources": []}
        for model in models:
            hits = self.search(
                f"giá lăn bánh thông số kỹ thuật {model}",
                top_k=top_k_per_model,
                model_filter=model,
            )
            comparison["models"][model] = {
                "highlights": _extract_highlights(hits),
                "chunks": hits,
            }
            for h in hits:
                if h.get("url"):
                    comparison["sources"].append({"model": model, "url": h["url"]})
        return comparison


def _extract_highlights(hits: list[dict[str, Any]]) -> dict[str, str | None]:
    text = " ".join(h["snippet"] for h in hits)
    price = _first_match(
        text,
        [
            r"giá\s*(?:niêm yết|lăn bánh)?[^.\n]{0,40}?(\d[\d.,\s]*(?:triệu|tỷ|VNĐ|đồng))",
            r"(\d[\d.,]*\s*triệu)",
            r"(\d{1,3}(?:\.\d{3}){2,}\s*(?:VNĐ|đồng)?)",
        ],
    )
    dimensions = _first_match(
        text,
        [r"(\d{3,4}\s*x\s*\d{3,4}\s*x\s*\d{3,4}\s*(?:\(mm\))?)"],
    )
    range_km = _first_match(text, [r"(~?\d{2,3}\s*[-–]?\s*\d{0,3}\s*km)"])
    seats = _first_match(text, [r"(\d+\s*chỗ)"])
    return {
        "price_hint": price,
        "dimensions": dimensions,
        "range_hint": range_km,
        "seats": seats,
    }


def _first_match(text: str, patterns: list[str]) -> str | None:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None
