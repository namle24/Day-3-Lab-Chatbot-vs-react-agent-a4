import argparse
from pathlib import Path

from src.rag.store import VinFastRAGStore

DEFAULT_DATA = Path(__file__).resolve().parents[2] / "vinfast_rag_data.json"
DEFAULT_INDEX = Path(__file__).resolve().parents[2] / "data" / "rag_index.pkl"


def ingest(data_path: Path = DEFAULT_DATA, index_path: Path = DEFAULT_INDEX) -> int:
    store = VinFastRAGStore()
    count = store.build_from_json(data_path)
    store.save(index_path)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Build VinFast RAG TF-IDF index")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    args = parser.parse_args()
    n = ingest(args.data, args.index)
    print(f"Indexed {n} chunks -> {args.index}")


if __name__ == "__main__":
    main()
