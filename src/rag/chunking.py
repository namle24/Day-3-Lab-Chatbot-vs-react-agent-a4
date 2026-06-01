import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, List

MODEL_PATTERN = re.compile(r"VF\s*(\d+)", re.IGNORECASE)
VARIANT_PATTERN = re.compile(r"VF\s*(\d+)\s*(Eco|Plus|MPV)?", re.IGNORECASE)


def normalize_model_label(text: str) -> list[str]:
    """Extract model tags like VF5, VF6 Plus from text."""
    found: list[str] = []
    for match in VARIANT_PATTERN.finditer(text):
        num = match.group(1)
        variant = (match.group(2) or "").strip()
        label = f"VF{num}"
        if variant:
            label = f"{label} {variant.title()}"
        if label not in found:
            found.append(label)
    return found


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.!?。؟]|\n)\s+")


def sentence_tokenize(text: str) -> list[str]:
    """Very small sentence tokenizer that preserves short sentences."""
    if not text:
        return []
    parts = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    # fallback: split by newline if nothing found
    if not parts:
        parts = [p.strip() for p in text.split("\n") if p.strip()]
    return parts


def _sliding_window_chunks(sentences: Iterable[str], max_chars: int = 900, overlap_chars: int = 200) -> list[str]:
    """Create overlapping chunks from sentence list to help short queries match precise spans.

    This reduces hallucination by keeping chunks focused and including overlap to preserve context.
    """
    chunks: List[str] = []
    current: List[str] = []
    size = 0
    sentences = list(sentences)
    i = 0
    while i < len(sentences):
        s = sentences[i]
        if size + len(s) <= max_chars or not current:
            current.append(s)
            size += len(s)
            i += 1
        else:
            chunks.append(" ".join(current))
            # step back to create overlap
            overlap = []
            if overlap_chars > 0:
                # add sentences from the end until overlap_chars reached
                acc = 0
                for sent in reversed(current):
                    if acc >= overlap_chars:
                        break
                    overlap.insert(0, sent)
                    acc += len(sent)
            current = overlap.copy()
            size = sum(len(x) for x in current)
    if current:
        chunks.append(" ".join(current))
    return chunks


_SIMPLE_STOPWORDS = {
    # a small mix of English + Vietnamese stopwords for lightweight keyword extraction
    "và",
    "là",
    "của",
    "the",
    "is",
    "a",
    "an",
    "in",
    "on",
    "for",
    "with",
    "by",
}


def extract_keywords(text: str, top_n: int = 5) -> list[str]:
    words = re.findall(r"\w+", text.lower())
    words = [w for w in words if w not in _SIMPLE_STOPWORDS and len(w) > 1]
    ctr = Counter(words)
    return [w for w, _ in ctr.most_common(top_n)]


def load_chunks_from_json(data_path: Path) -> list[dict[str, Any]]:
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    chunks: list[dict[str, Any]] = []

    # general overview: keep as-is but add keywords and short sentence chunks
    for line in raw.get("general_overview", []):
        line = line.strip()
        if not line:
            continue
        models = normalize_model_label(line) or ["overview"]
        overview_chunk = {
            "text": line,
            "title": "Tổng quan dòng xe VinFast",
            "url": "",
            "models": models,
            "category": "overview",
            "keywords": extract_keywords(line),
            "short": len(line) < 250,
        }
        chunks.append(overview_chunk)
        # also add smaller sentence chunks for better matching to short queries
        for si, sent in enumerate(sentence_tokenize(line)):
            if len(sent) < 300:
                chunks.append(
                    {
                        "text": sent,
                        "title": "Tổng quan dòng xe VinFast",
                        "url": "",
                        "models": models,
                        "category": "overview_sentence",
                        "keywords": extract_keywords(sent),
                        "short": True,
                        "sentence_index": si,
                    }
                )

    for product in raw.get("detailed_products", []):
        title = product.get("title", "")
        url = product.get("url", "")
        content = product.get("content", "")
        models = normalize_model_label(title + " " + content[:500])
        if not models:
            models = ["unknown"]

        # prefer overlapping sentence-window chunks to make answers precise
        sentences = sentence_tokenize(content)
        if sentences:
            window_chunks = _sliding_window_chunks(sentences, max_chars=900, overlap_chars=200)
            for i, piece in enumerate(window_chunks):
                chunks.append(
                    {
                        "text": piece,
                        "title": title,
                        "url": url,
                        "models": models,
                        "category": "product",
                        "chunk_index": i,
                        "keywords": extract_keywords(piece),
                        "short": len(piece) < 300,
                    }
                )
            # additionally, include very short sentence-level chunks to help tiny queries
            for si, sent in enumerate(sentences):
                if len(sent) <= 220:
                    chunks.append(
                        {
                            "text": sent,
                            "title": title,
                            "url": url,
                            "models": models,
                            "category": "product_sentence",
                            "sentence_index": si,
                            "keywords": extract_keywords(sent),
                            "short": True,
                        }
                    )
        else:
            # fallback to paragraph splitting when sentence tokenizer fails
            paras = [p.strip() for p in re.split(r"\n+", content) if p.strip()]
            for i, piece in enumerate(paras):
                chunks.append(
                    {
                        "text": piece,
                        "title": title,
                        "url": url,
                        "models": models,
                        "category": "product",
                        "chunk_index": i,
                        "keywords": extract_keywords(piece),
                        "short": len(piece) < 300,
                    }
                )

    return chunks
