#!/usr/bin/env python3
"""Export vehicle comparison to a Markdown file.

Usage: python3 scripts/export_compare_md.py VF3 VF5 out.md
"""
import sys
import json
import re
from pathlib import Path

from src.tools import vehicle_lookup


def extract_price_and_quarter_from_chunks(chunks):
    quarter = None
    for c in chunks:
        snip = c.get("snippet") or c.get("text") or ""
        m = re.search(r"Giá lăn bánh\s*([0-9,]+)\s*VNĐ", snip, re.I)
        if m:
            q = re.search(r"Áp dụng:\s*([^\.\n]+)", snip, re.I)
            if q:
                quarter = q.group(1).strip()
            return int(m.group(1).replace(",", "")), quarter
    return None, quarter


def build_markdown(model_a, model_b, comparison):
    models = comparison.get("models", {})
    a = models.get(model_a, {})
    b = models.get(model_b, {})

    def price_hint(item):
        return (item.get("highlights") or {}).get("price_hint")

    ph_a = price_hint(a)
    ph_b = price_hint(b)
    roll_a, q_a = extract_price_and_quarter_from_chunks(a.get("chunks", []))
    roll_b, q_b = extract_price_and_quarter_from_chunks(b.get("chunks", []))

    lines = []
    lines.append(f"# So sánh {model_a} và {model_b}\n")

    lines.append(f"## {model_a}")
    if ph_a:
        lines.append(f"- Giá niêm yết: {ph_a}")
    if roll_a:
        qtext = f" (Áp dụng: {q_a})" if q_a else ""
        lines.append(f"- Giá lăn bánh{qtext}: {roll_a:,} VNĐ")

    lines.append(f"\n## {model_b}")
    if ph_b:
        lines.append(f"- Giá niêm yết: {ph_b}")
    if roll_b:
        qtext = f" (Áp dụng: {q_b})" if q_b else ""
        lines.append(f"- Giá lăn bánh{qtext}: {roll_b:,} VNĐ")

    if roll_a and roll_b:
        diff = abs(roll_a - roll_b)
        lines.append(f"\n## Chênh lệch\n- Chênh lệch lăn bánh (ước tính): {diff:,} VNĐ")

    # include raw JSON for reference
    lines.append("\n---\n")
    lines.append("<details><summary>Raw comparison JSON</summary>\n\n``json\n")
    lines.append(json.dumps(comparison, ensure_ascii=False, indent=2))
    lines.append("\n``\n</details>\n")

    return "\n".join(lines)


def main(argv):
    if len(argv) < 4:
        print("Usage: export_compare_md.py MODEL_A MODEL_B OUT.md")
        return 2
    model_a = argv[1].upper()
    model_b = argv[2].upper()
    out = Path(argv[3])

    cmp = vehicle_lookup.compare_vehicles(model_a, model_b)
    if not cmp.get("ok"):
        print("Compare failed or no data")
        return 1

    md = build_markdown(model_a, model_b, cmp.get("comparison", {}))
    out.write_text(md, encoding="utf-8")
    print(f"Wrote comparison to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
