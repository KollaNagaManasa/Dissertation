from dataclasses import dataclass
from typing import Protocol

from ragiac.ingestion.chunker import Chunk


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


class VectorStore(Protocol):
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    def search(self, query_vector: list[float], top_k: int) -> list[ScoredChunk]: ...
