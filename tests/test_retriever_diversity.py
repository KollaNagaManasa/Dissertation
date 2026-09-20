from ragiac.ingestion.chunker import Chunk
from ragiac.retrieval.retriever import Retriever
from ragiac.vectorstore.in_memory import InMemoryVectorStore


class FixedEmbedder:
    dimension = 2

    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


def _store() -> InMemoryVectorStore:
    store = InMemoryVectorStore()
    chunks = [Chunk(f"big::{i}", "big.md", "big.md", f"big {i}") for i in range(6)]
    chunks.append(Chunk("small::0", "small.md", "small.md", "small"))
    vectors = [[1.0, 0.01 * i] for i in range(6)] + [[0.9, 0.5]]  # small.md is the weakest match
    store.upsert(chunks, vectors)
    return store


def test_without_cap_one_doc_can_fill_every_slot():
    results = Retriever(FixedEmbedder(), _store(), top_k=4, max_per_doc=0).retrieve("q")
    assert {r.chunk.doc_id for r in results} == {"big.md"}


def test_per_doc_cap_lets_other_docs_in():
    results = Retriever(FixedEmbedder(), _store(), top_k=4, max_per_doc=2).retrieve("q")
    docs = [r.chunk.doc_id for r in results]
    assert docs.count("big.md") == 2
    assert "small.md" in docs
