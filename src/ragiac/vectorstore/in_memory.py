"""In-memory cosine-similarity vector store for local dev/tests.

Persists its index to a JSON file under data/index/ so `scripts/ask.py` can run
in a separate process from `scripts/ingest.py` without re-embedding every time.
"""

import json
from pathlib import Path

import numpy as np

from ragiac.ingestion.chunker import Chunk
from ragiac.vectorstore.base import ScoredChunk


class InMemoryVectorStore:
    def __init__(self, cache_path: Path | None = None):
        self._cache_path = cache_path
        self._chunks: list[Chunk] = []
        self._vectors: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self._chunks)

    def clear(self) -> None:
        self._chunks = []
        self._vectors = None

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must be the same length")
        # Replace by chunk_id so re-ingesting an already-loaded index doesn't duplicate chunks.
        incoming = {c.chunk_id for c in chunks}
        if self._chunks and self._vectors is not None:
            keep = [i for i, c in enumerate(self._chunks) if c.chunk_id not in incoming]
            self._chunks = [self._chunks[i] for i in keep]
            self._vectors = self._vectors[keep] if keep else None
        self._chunks.extend(chunks)
        new_vectors = np.array(vectors, dtype=np.float32)
        self._vectors = new_vectors if self._vectors is None else np.vstack([self._vectors, new_vectors])

    def search(self, query_vector: list[float], top_k: int) -> list[ScoredChunk]:
        if self._vectors is None or len(self._chunks) == 0:
            return []

        query = np.array(query_vector, dtype=np.float32)
        query_norm = np.linalg.norm(query)
        store_norms = np.linalg.norm(self._vectors, axis=1)
        denom = store_norms * query_norm
        denom[denom == 0] = 1e-9
        similarities = (self._vectors @ query) / denom

        top_indices = np.argsort(-similarities)[:top_k]
        return [ScoredChunk(chunk=self._chunks[i], score=float(similarities[i])) for i in top_indices]

    def save(self) -> None:
        if self._cache_path is None or self._vectors is None:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunks": [
                {"chunk_id": c.chunk_id, "doc_id": c.doc_id, "source": c.source, "text": c.text}
                for c in self._chunks
            ],
            "vectors": self._vectors.tolist(),
        }
        self._cache_path.write_text(json.dumps(payload), encoding="utf-8")

    def load(self) -> bool:
        if self._cache_path is None or not self._cache_path.exists():
            return False
        payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
        self._chunks = [Chunk(**c) for c in payload["chunks"]]
        self._vectors = np.array(payload["vectors"], dtype=np.float32)
        return True
