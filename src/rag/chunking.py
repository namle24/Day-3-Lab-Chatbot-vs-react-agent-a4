import json
import re
from pathlib import Path
from typing import Any

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


def load_chunks_from_json(data_path: Path) -> list[dict[str, Any]]:
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    chunks: list[dict[str, Any]] = []

    # Process structured vehicle data
    for vehicle in raw.get("vehicles", []):
        model = vehicle.get("model", "")
        category = vehicle.get("category", "")
        description = vehicle.get("description", "")
        specs = vehicle.get("specs", {})
        variants = vehicle.get("variants", [])
        highlights = vehicle.get("highlights", [])
        reviews = vehicle.get("reviews", [])

        # Create spec chunk for each model
        spec_text = f"Dòng xe {model} - {category}\n"
        spec_text += f"Mô tả: {description}\n"
        spec_text += f"Kích thước: {specs.get('length_mm', 'N/A')} x {specs.get('width_mm', 'N/A')} x {specs.get('height_mm', 'N/A')} mm\n"
        spec_text += f"Số chỗ ngồi: {specs.get('seats', 'N/A')}\n"
        spec_text += f"Công suất: {specs.get('power_kw', 'N/A')} kW\n"
        spec_text += f"Quãng đường di chuyển: {specs.get('range_km', 'N/A')} km\n"
        spec_text += f"Dung lượng pin: {specs.get('battery_kwh', 'N/A')} kWh\n"

        chunks.append({
            "text": spec_text,
            "title": f"Thông số kỹ thuật {model}",
            "url": "",
            "models": [model],
            "category": "specifications",
        })

        # Create pricing chunks for each variant
        for variant in variants:
            variant_name = variant.get("name", "")
            price = variant.get("price_vnd", 0)
            price_rolling = variant.get("price_rolling_vnd", 0)
            notes = variant.get("notes", "")
            
            price_text = f"{variant_name}: Giá niêm yết {price:,} VNĐ, Giá lăn bánh {price_rolling:,} VNĐ. {notes}"
            chunks.append({
                "text": price_text,
                "title": f"Giá {variant_name}",
                "url": "",
                "models": [model],
                "category": "pricing",
            })

        # Create highlights chunk
        if highlights:
            highlights_text = f"Các tính năng nổi bật của {model}:\n" + "\n".join(f"- {h}" for h in highlights)
            chunks.append({
                "text": highlights_text,
                "title": f"Tính năng {model}",
                "url": "",
                "models": [model],
                "category": "features",
            })

        # Create reviews chunk
        if reviews:
            reviews_text = f"Đánh giá về {model}:\n" + "\n".join(f"- {r}" for r in reviews)
            chunks.append({
                "text": reviews_text,
                "title": f"Đánh giá {model}",
                "url": "",
                "models": [model],
                "category": "reviews",
            })

    # Process promotions
    for promo in raw.get("promotions", []):
        title = promo.get("title", "")
        desc = promo.get("description", "")
        promo_text = f"{title}: {desc}"
        chunks.append({
            "text": promo_text,
            "title": title,
            "url": "",
            "models": [],
            "category": "promotions",
        })

    # Process financing info
    financing = raw.get("financing", {})
    if financing:
        fin_text = "Thông tin tài chính:\n"
        down_payments = financing.get("down_payment_options", [])
        for opt in down_payments:
            fin_text += f"- Trả trước {opt.get('percent', 0)}%: {opt.get('description', '')}\n"
        
        loan_terms = financing.get("loan_terms", [])
        fin_text += f"Thời hạn vay: {', '.join(str(t) for t in loan_terms)} tháng\n"
        
        rates = financing.get("interest_rates", {})
        fin_text += f"Lãi suất: Năm 1: {rates.get('year1', 'N/A')}, Sau năm 4: {rates.get('after_year4', 'N/A')}"
        
        chunks.append({
            "text": fin_text,
            "title": "Thông tin tài chính và trả góp",
            "url": "",
            "models": [],
            "category": "financing",
        })

    # Process documents
    for doc in raw.get("documents", []):
        title = doc.get("title", "")
        content = doc.get("content", "")
        category = doc.get("category", "")
        
        chunks.append({
            "text": f"{title}\n{content}",
            "title": title,
            "url": "",
            "models": normalize_model_label(title + " " + content) or [],
            "category": category.lower(),
        })

    return chunks
