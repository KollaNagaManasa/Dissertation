from ragiac.ingestion.chunker import Chunk
from ragiac.vectorstore.in_memory import InMemoryVectorStore


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(chunk_id=chunk_id, doc_id=chunk_id, source=chunk_id, text=text)


def test_search_returns_most_similar_first():
    store = InMemoryVectorStore()
    store.upsert(
        [_chunk("a", "bucket"), _chunk("b", "cluster"), _chunk("c", "database")],
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    )

    results = store.search([0.9, 0.1, 0.0], top_k=2)

    assert [r.chunk.chunk_id for r in results] == ["a", "b"]
    assert results[0].score > results[1].score


def test_search_on_empty_store_returns_empty_list():
    store = InMemoryVectorStore()
    assert store.search([1.0, 0.0], top_k=5) == []


def test_save_and_load_roundtrip(tmp_path):
    cache_path = tmp_path / "index.json"
    store = InMemoryVectorStore(cache_path=cache_path)
    store.upsert([_chunk("a", "bucket")], [[1.0, 2.0, 3.0]])
    store.save()

    reloaded = InMemoryVectorStore(cache_path=cache_path)
    assert reloaded.load() is True
    results = reloaded.search([1.0, 2.0, 3.0], top_k=1)
    assert results[0].chunk.chunk_id == "a"


def test_upsert_is_idempotent_by_chunk_id():
    store = InMemoryVectorStore()
    store.upsert([_chunk("a", "old")], [[1.0, 0.0]])
    store.upsert([_chunk("a", "new"), _chunk("b", "other")], [[0.0, 1.0], [1.0, 1.0]])

    assert len(store) == 2
    results = store.search([0.0, 1.0], top_k=1)
    assert results[0].chunk.text == "new"


def test_clear_empties_the_store():
    store = InMemoryVectorStore()
    store.upsert([_chunk("a", "x")], [[1.0, 0.0]])
    store.clear()
    assert len(store) == 0
    assert store.search([1.0, 0.0], top_k=1) == []
