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


def _split_content(text: str, max_chars: int = 900) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for para in paragraphs:
        if size + len(para) > max_chars and current:
            chunks.append("\n".join(current))
            current = [para]
            size = len(para)
        else:
            current.append(para)
            size += len(para)
    if current:
        chunks.append("\n".join(current))
    return chunks


def _make_chunk(
    text: str,
    title: str,
    url: str = "",
    models: list[str] | None = None,
    category: str = "",
    chunk_index: int | None = None,
    sentence_index: int | None = None,
) -> dict[str, Any]:
    chunk = {
        "text": text.strip(),
        "title": title,
        "url": url,
        "models": models or [],
        "category": category,
        "keywords": extract_keywords(text),
        "short": len(text) < 300,
    }
    if chunk_index is not None:
        chunk["chunk_index"] = chunk_index
    if sentence_index is not None:
        chunk["sentence_index"] = sentence_index
    return chunk


def _parse_number(value: Any) -> str:
    if value in (None, ""):
        return "N/A"
    return str(value)


def _add_vehicle_chunks(chunks: list[dict[str, Any]], raw: dict[str, Any]) -> None:
    for vehicle in raw.get("vehicles", []):
        model = vehicle.get("model", "").strip()
        category = vehicle.get("category", "").strip()
        description = vehicle.get("description", "").strip()
        specs = vehicle.get("specs", {}) or {}
        variants = vehicle.get("variants", []) or []
        highlights = vehicle.get("highlights", []) or []
        reviews = vehicle.get("reviews", []) or []

        spec_text = [f"Dòng xe {model} - {category}".strip()]
        if description:
            spec_text.append(f"Mô tả: {description}")
        spec_text.append(
            "Kích thước: "
            f"{_parse_number(specs.get('length_mm'))} x {_parse_number(specs.get('width_mm'))} x {_parse_number(specs.get('height_mm'))} mm"
        )
        spec_text.append(f"Số chỗ ngồi: {_parse_number(specs.get('seats'))}")
        spec_text.append(f"Công suất: {_parse_number(specs.get('power_kw'))} kW")
        spec_text.append(f"Quãng đường di chuyển: {_parse_number(specs.get('range_km'))} km")
        spec_text.append(f"Dung lượng pin: {_parse_number(specs.get('battery_kwh'))} kWh")
        chunks.append(
            _make_chunk(
                "\n".join(spec_text),
                title=f"Thông số kỹ thuật {model}",
                models=[model] if model else [],
                category="specifications",
            )
        )

        for variant_index, variant in enumerate(variants):
            variant_name = variant.get("name", "").strip()
            price = variant.get("price_vnd", 0)
            price_rolling = variant.get("price_rolling_vnd", 0)
            notes = variant.get("notes", "").strip()
            quarter = variant.get("price_quarter", "").strip()
            quarter_text = f" Áp dụng: {quarter}." if quarter else ""
            price_text = f"{variant_name}: Giá niêm yết {price:,} VNĐ, Giá lăn bánh {price_rolling:,} VNĐ.{quarter_text} {notes}".strip()
            chunks.append(
                _make_chunk(
                    price_text,
                    title=f"Giá {variant_name or model}",
                    models=[model] if model else [],
                    category="pricing",
                    chunk_index=variant_index,
                )
            )

        if highlights:
            highlights_text = f"Các tính năng nổi bật của {model}:\n" + "\n".join(f"- {h}" for h in highlights)
            chunks.append(
                _make_chunk(
                    highlights_text,
                    title=f"Tính năng {model}",
                    models=[model] if model else [],
                    category="features",
                )
            )

        if reviews:
            reviews_text = f"Đánh giá về {model}:\n" + "\n".join(f"- {r}" for r in reviews)
            chunks.append(
                _make_chunk(
                    reviews_text,
                    title=f"Đánh giá {model}",
                    models=[model] if model else [],
                    category="reviews",
                )
            )


def _add_text_chunks(
    chunks: list[dict[str, Any]],
    title: str,
    url: str,
    content: str,
    category: str,
    models: list[str] | None = None,
) -> None:
    sentences = sentence_tokenize(content)
    if sentences:
        window_chunks = _sliding_window_chunks(sentences, max_chars=900, overlap_chars=200)
        for chunk_index, piece in enumerate(window_chunks):
            chunks.append(
                _make_chunk(
                    piece,
                    title=title,
                    url=url,
                    models=models,
                    category=category,
                    chunk_index=chunk_index,
                )
            )
        for sentence_index, sentence in enumerate(sentences):
            if len(sentence) <= 220:
                chunks.append(
                    _make_chunk(
                        sentence,
                        title=title,
                        url=url,
                        models=models,
                        category=f"{category}_sentence",
                        sentence_index=sentence_index,
                    )
                )
        return

    for chunk_index, piece in enumerate(_split_content(content)):
        chunks.append(
            _make_chunk(
                piece,
                title=title,
                url=url,
                models=models,
                category=category,
                chunk_index=chunk_index,
            )
        )


def load_chunks_from_json(data_path: Path) -> list[dict[str, Any]]:
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    chunks: list[dict[str, Any]] = []

    for line in raw.get("general_overview", []):
        line = line.strip()
        if not line:
            continue
        models = normalize_model_label(line) or ["overview"]
        chunks.append(
            _make_chunk(
                line,
                title="Tổng quan dòng xe VinFast",
                models=models,
                category="overview",
            )
        )
        for sentence_index, sentence in enumerate(sentence_tokenize(line)):
            if len(sentence) < 300:
                chunks.append(
                    _make_chunk(
                        sentence,
                        title="Tổng quan dòng xe VinFast",
                        models=models,
                        category="overview_sentence",
                        sentence_index=sentence_index,
                    )
                )

    for product in raw.get("detailed_products", []):
        title = product.get("title", "")
        url = product.get("url", "")
        content = product.get("content", "")
        models = normalize_model_label(title + " " + content[:500]) or ["unknown"]
        _add_text_chunks(chunks, title, url, content, category="product", models=models)

    _add_vehicle_chunks(chunks, raw)

    for promo in raw.get("promotions", []):
        title = promo.get("title", "").strip()
        desc = promo.get("description", "").strip()
        promo_text = f"{title}: {desc}".strip(": ")
        chunks.append(
            _make_chunk(
                promo_text,
                title=title,
                category="promotions",
                models=normalize_model_label(title + " " + desc),
            )
        )

    financing = raw.get("financing", {}) or {}
    if financing:
        fin_text = ["Thông tin tài chính:"]
        down_payments = financing.get("down_payment_options", []) or []
        for opt in down_payments:
            fin_text.append(f"- Trả trước {opt.get('percent', 0)}%: {opt.get('description', '')}")

        loan_terms = financing.get("loan_terms", []) or []
        fin_text.append(f"Thời hạn vay: {', '.join(str(t) for t in loan_terms)} tháng")

        rates = financing.get("interest_rates", {}) or {}
        fin_text.append(f"Lãi suất: Năm 1: {rates.get('year1', 'N/A')}, Sau năm 4: {rates.get('after_year4', 'N/A')}")

        chunks.append(
            _make_chunk(
                "\n".join(fin_text),
                title="Thông tin tài chính và trả góp",
                category="financing",
            )
        )

    for doc in raw.get("documents", []):
        title = doc.get("title", "").strip()
        content = doc.get("content", "").strip()
        category = (doc.get("category", "") or "").strip().lower()
        chunks.append(
            _make_chunk(
                f"{title}\n{content}".strip(),
                title=title,
                category=category,
                models=normalize_model_label(title + " " + content),
            )
        )

    return chunks
