"""Dependency-light TF-IDF embedder for offline dev/tests (RAGIAC_MODE=local).

Not a substitute for Vertex AI embeddings in the real experiments — it exists so
the ingestion -> retrieval -> generation pipeline can be exercised end-to-end
without GCP credentials, e.g. in CI or while iterating on prompts/validation.
"""

import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

_TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class LocalTfidfEmbedder:
    def __init__(self, max_features: int = 4096):
        self.max_features = max_features
        self.dimension = max_features
        self._vocabulary: dict[str, int] = {}
        self._idf: np.ndarray | None = None

    def fit(self, corpus: list[str]) -> None:
        doc_freq: Counter[str] = Counter()
        term_freq_total: Counter[str] = Counter()
        for text in corpus:
            tokens = set(_tokenize(text))
            doc_freq.update(tokens)
            term_freq_total.update(_tokenize(text))

        vocab_terms = [term for term, _ in term_freq_total.most_common(self.max_features)]
        self._vocabulary = {term: i for i, term in enumerate(vocab_terms)}
        self.dimension = len(self._vocabulary)

        n_docs = max(len(corpus), 1)
        idf = np.zeros(self.dimension, dtype=np.float32)
        for term, idx in self._vocabulary.items():
            idf[idx] = math.log((1 + n_docs) / (1 + doc_freq[term])) + 1.0
        self._idf = idf

    def _vectorize(self, text: str) -> np.ndarray:
        if self._idf is None:
            raise RuntimeError("LocalTfidfEmbedder.fit() must be called before embed()")

        vec = np.zeros(self.dimension, dtype=np.float32)
        counts = Counter(_tokenize(text))
        for term, count in counts.items():
            idx = self._vocabulary.get(term)
            if idx is not None:
                vec[idx] = count * self._idf[idx]

        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(t).tolist() for t in texts]

    def save(self, path: Path) -> None:
        if self._idf is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"vocabulary": self._vocabulary, "idf": self._idf.tolist(), "max_features": self.max_features}
        path.write_text(json.dumps(payload), encoding="utf-8")

    def load(self, path: Path) -> bool:
        if not path.exists():
            return False
        payload = json.loads(path.read_text(encoding="utf-8"))
        self._vocabulary = payload["vocabulary"]
        self._idf = np.array(payload["idf"], dtype=np.float32)
        self.max_features = payload["max_features"]
        self.dimension = len(self._vocabulary)
        return True
