"""End-to-end smoke test of the local (RAGIAC_MODE=local) pipeline: real ingestion of the
sample knowledge base, real TF-IDF embedding + in-memory retrieval, stub generation."""

from pathlib import Path

from ragiac.config import Settings
from ragiac.pipeline import build_pipeline

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_ingest_and_retrieve_over_sample_knowledge_base(tmp_path):
    settings = Settings(
        ragiac_mode="local",
        knowledge_base_dir=REPO_ROOT / "data" / "knowledge_base",
        index_cache_dir=tmp_path,
    )
    pipeline = build_pipeline(settings)

    n_chunks = pipeline.ingest()
    assert n_chunks > 0

    results = pipeline.retriever.retrieve("versioned storage bucket with lifecycle rule")
    assert len(results) > 0
    assert any("gcs_bucket.md" in r.chunk.doc_id for r in results)


def test_generate_rag_returns_stub_output_in_local_mode(tmp_path):
    settings = Settings(
        ragiac_mode="local",
        knowledge_base_dir=REPO_ROOT / "data" / "knowledge_base",
        index_cache_dir=tmp_path,
    )
    pipeline = build_pipeline(settings)
    pipeline.ingest()

    output = pipeline.generate_rag("a versioned gcs bucket")
    assert "STUB OUTPUT" in output
