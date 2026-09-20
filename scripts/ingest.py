#!/usr/bin/env python
"""Builds (or refreshes) the vector index from data/knowledge_base.

Usage: py scripts/ingest.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ragiac.pipeline import build_pipeline  # noqa: E402


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    pipeline = build_pipeline()
    n_chunks = pipeline.ingest()
    mode = pipeline.settings.ragiac_mode
    print(f"Ingested {n_chunks} chunks into the vector store (mode={mode}).")
    if n_chunks == 0:
        print(f"No documents found under {pipeline.settings.knowledge_base_dir}. Add .md/.txt/.tf files there.")


if __name__ == "__main__":
    main()
