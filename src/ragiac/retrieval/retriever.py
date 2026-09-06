from dataclasses import dataclass

from ragiac.embeddings.base import Embedder
from ragiac.vectorstore.base import ScoredChunk, VectorStore


@dataclass
class Retriever:
    embedder: Embedder
    vector_store: VectorStore
    top_k: int = 5

    def retrieve(self, query: str) -> list[ScoredChunk]:
        [query_vector] = self.embedder.embed([query])
        return self.vector_store.search(query_vector, self.top_k)

    def assemble_context(self, query: str) -> str:
        results = self.retrieve(query)
        blocks = [f"[Source: {r.chunk.source}]\n{r.chunk.text}" for r in results]
        return "\n\n---\n\n".join(blocks)
