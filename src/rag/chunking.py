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

    for line in raw.get("general_overview", []):
        line = line.strip()
        if not line:
            continue
        models = normalize_model_label(line) or ["overview"]
        chunks.append(
            {
                "text": line,
                "title": "Tổng quan dòng xe VinFast",
                "url": "",
                "models": models,
                "category": "overview",
            }
        )

    for product in raw.get("detailed_products", []):
        title = product.get("title", "")
        url = product.get("url", "")
        content = product.get("content", "")
        
        # Strip noisy related articles footer and product list block to prevent search contamination
        for noise_marker in [
            "Xem thêm các bài viết liên quan khác:",
            "Xem thêm các bài viết liên quan khác",
            "Sản Phẩm VinFast VF3 Eco",
            "Sản Phẩm VinFast"
        ]:
            if noise_marker in content:
                content = content.split(noise_marker)[0].strip()

        models = normalize_model_label(title + " " + content[:500])
        if not models:
            models = ["unknown"]
        for i, piece in enumerate(_split_content(content)):
            chunks.append(
                {
                    "text": piece,
                    "title": title,
                    "url": url,
                    "models": models,
                    "category": "product",
                    "chunk_index": i,
                }
            )

    return chunks
