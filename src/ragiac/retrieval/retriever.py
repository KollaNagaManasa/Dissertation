from dataclasses import dataclass

from ragiac.embeddings.base import Embedder
from ragiac.vectorstore.base import ScoredChunk, VectorStore

_OVERFETCH = 5  # candidates fetched per slot when diversifying, so the per-doc cap has room to work


def format_context(results: list[ScoredChunk]) -> str:
    blocks = [f"[Source: {r.chunk.source}]\n{r.chunk.text}" for r in results]
    return "\n\n---\n\n".join(blocks)


@dataclass
class Retriever:
    embedder: Embedder
    vector_store: VectorStore
    top_k: int = 5
    # Cap on chunks taken from any single document (0 = no cap). Provider docs are long, so
    # without a cap one resource's page can fill every slot and crowd out the other resources a
    # multi-resource requirement needs (e.g. a VPC prompt retrieving only Cloud NAT pages).
    max_per_doc: int = 0

    def retrieve(self, query: str) -> list[ScoredChunk]:
        if hasattr(self.embedder, "embed_query"):
            query_vector = self.embedder.embed_query(query)
        else:
            [query_vector] = self.embedder.embed([query])

        if self.max_per_doc <= 0:
            return self.vector_store.search(query_vector, self.top_k)

        selected: list[ScoredChunk] = []
        per_doc: dict[str, int] = {}
        for candidate in self.vector_store.search(query_vector, self.top_k * _OVERFETCH):
            if per_doc.get(candidate.chunk.doc_id, 0) >= self.max_per_doc:
                continue
            per_doc[candidate.chunk.doc_id] = per_doc.get(candidate.chunk.doc_id, 0) + 1
            selected.append(candidate)
            if len(selected) == self.top_k:
                break
        return selected

    def assemble_context(self, query: str) -> str:
        return format_context(self.retrieve(query))
