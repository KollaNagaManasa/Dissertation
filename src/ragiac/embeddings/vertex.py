"""Vertex AI embeddings (text-embedding-005 by default).

Requires `google-cloud-aiplatform` and a GCP project with the Vertex AI API
enabled; authenticate with `gcloud auth application-default login`.

Documents and queries are embedded with different task types (RETRIEVAL_DOCUMENT /
RETRIEVAL_QUERY), which the model is trained to expect for asymmetric retrieval.

A fresh project has a very low per-minute embedding quota, so vectors are cached on disk
(append-only JSONL keyed by model + task type + text hash): a run that dies part-way keeps its
progress, and re-ingesting or re-asking the same prompt costs no API calls.
"""

import hashlib
import json
import logging
import threading
from pathlib import Path

from ragiac.config import Settings
from ragiac.retry import call_with_backoff, vertex_retryable_errors

log = logging.getLogger(__name__)


class VertexEmbedder:
    dimension = 768  # text-embedding-005 output size

    def __init__(self, settings: Settings, model=None, cache_path: Path | None = None):
        if model is None:
            from vertexai.language_models import TextEmbeddingModel
            import vertexai

            vertexai.init(project=settings.google_cloud_project, location=settings.google_cloud_region)
            model = TextEmbeddingModel.from_pretrained(settings.vertex_embedding_model)
        self._model = model
        self._model_name = settings.vertex_embedding_model
        self._batch_size = settings.embedding_batch_size
        self._max_retries = settings.api_max_retries
        self._cache_path = cache_path if cache_path is not None else settings.cache_dir / "embedding_cache.jsonl"
        self._cache: dict[str, list[float]] = {}
        self._cache_lock = threading.Lock()
        self._load_cache()

    def _key(self, text: str, task_type: str) -> str:
        return hashlib.sha256(f"{self._model_name}|{task_type}|{text}".encode("utf-8")).hexdigest()

    def _load_cache(self) -> None:
        if not self._cache_path.exists():
            return
        with self._cache_path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    self._cache[entry["k"]] = entry["v"]

    def _append_cache(self, entries: dict[str, list[float]]) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self._cache_path.open("a", encoding="utf-8") as f:
            for k, v in entries.items():
                f.write(json.dumps({"k": k, "v": v}) + "\n")

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        from vertexai.language_models import TextEmbeddingInput

        keys = [self._key(t, task_type) for t in texts]
        missing = [i for i, k in enumerate(keys) if k not in self._cache]
        if missing:
            log.info("embedding %d/%d texts (%d cached)", len(missing), len(texts), len(texts) - len(missing))

        for start in range(0, len(missing), self._batch_size):
            idx = missing[start : start + self._batch_size]
            batch = [TextEmbeddingInput(texts[i], task_type) for i in idx]
            embeddings = call_with_backoff(
                lambda b=batch: self._model.get_embeddings(b),
                retryable=vertex_retryable_errors(),
                max_retries=self._max_retries,
            )
            new = {keys[i]: list(e.values) for i, e in zip(idx, embeddings)}
            with self._cache_lock:
                self._cache.update(new)
                self._append_cache(new)
            log.info("embedded %d/%d", min(start + self._batch_size, len(missing)), len(missing))

        return [self._cache[k] for k in keys]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]
