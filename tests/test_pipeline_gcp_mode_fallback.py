"""RAGIAC_MODE=gcp should still fall back to the local in-memory vector store until Vertex AI
Vector Search index/endpoint IDs are actually configured, since that's a separate, slower
provisioning step -- real embeddings/generation shouldn't be blocked on it."""

from ragiac.config import Settings
from ragiac.pipeline import build_vector_store
from ragiac.vectorstore.in_memory import InMemoryVectorStore


def test_gcp_mode_without_vector_search_ids_falls_back_to_in_memory(tmp_path):
    settings = Settings(
        ragiac_mode="gcp",
        google_cloud_project="some-project",
        index_cache_dir=tmp_path,
        vertex_vector_index_id="",
        vertex_vector_endpoint_id="",
    )

    store = build_vector_store(settings)

    assert isinstance(store, InMemoryVectorStore)
