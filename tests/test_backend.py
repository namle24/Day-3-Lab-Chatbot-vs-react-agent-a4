import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.tools.calculator import calculate, down_payment, sanitize_expression
from src.rag.ingest import ingest
from src.rag.store import VinFastRAGStore


def test_calculator_safe():
    assert calculate("1090000000 * 0.3")["ok"] is True
    assert calculate("import os")["ok"] is False
    assert down_payment(1_000_000_000, 30)["down_payment"] == 300_000_000


def test_sanitize_strips_bad_chars():
    assert "1090" in sanitize_expression("1090 * 0.3; drop table")


@pytest.fixture(scope="module")
def rag_index(tmp_path_factory):
    index = tmp_path_factory.mktemp("rag") / "index.pkl"
    data = ROOT / "vinfast_rag_data.json"
    n = ingest(data, index)
    assert n > 0
    return index


def test_rag_search(rag_index):
    store = VinFastRAGStore()
    assert store.load(rag_index)
    hits = store.search("VF5 giá lăn bánh", top_k=2)
    assert len(hits) >= 1
    assert "snippet" in hits[0]


def test_compare_models(rag_index):
    store = VinFastRAGStore()
    store.load(rag_index)
    cmp = store.compare_models(["VF5", "VF6"])
    assert "VF5" in cmp["models"] or "vf5" in str(cmp).lower()
