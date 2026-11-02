"""End-to-end smoke test of the local (RAGIAC_MODE=local) pipeline: real ingestion of the
sample knowledge base, real TF-IDF embedding + in-memory retrieval, template-based generation."""

from pathlib import Path

from ragiac.config import Settings
from ragiac.generation import verifier_feedback as vf
from ragiac.pipeline import build_pipeline
from ragiac.validation.opa_validator import PolicyResult
from ragiac.validation.terraform_validator import TerraformResult

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


def test_generate_rag_returns_real_hcl_in_local_mode(tmp_path):
    settings = Settings(
        ragiac_mode="local",
        knowledge_base_dir=REPO_ROOT / "data" / "knowledge_base",
        index_cache_dir=tmp_path,
    )
    pipeline = build_pipeline(settings)
    pipeline.ingest()

    output = pipeline.generate_rag("a versioned gcs bucket")
    assert 'resource "google_storage_bucket"' in output
    assert "enabled = true" in output  # versioning block, since "versioned" was in the requirement


def test_generate_templates_returns_real_hcl_in_local_mode(tmp_path):
    settings = Settings(
        ragiac_mode="local",
        knowledge_base_dir=REPO_ROOT / "data" / "knowledge_base",
        internal_templates_dir=REPO_ROOT / "data" / "internal_templates",
        index_cache_dir=tmp_path,
    )
    pipeline = build_pipeline(settings)

    assert "asia-south1" in pipeline.templates_generator.conventions_text  # loaded the messier docs, not the hand-written ones
    output = pipeline.generate_templates("a versioned gcs bucket")
    assert 'resource "google_storage_bucket"' in output


def test_generate_rag_with_feedback_skips_retry_when_first_attempt_passes(tmp_path, monkeypatch):
    settings = Settings(
        ragiac_mode="local",
        knowledge_base_dir=REPO_ROOT / "data" / "knowledge_base",
        index_cache_dir=tmp_path,
    )
    pipeline = build_pipeline(settings)
    pipeline.ingest()
    monkeypatch.setattr(vf, "validate_terraform", lambda hcl, settings, run_plan: [TerraformResult(True, "validate", "", "")])
    monkeypatch.setattr(vf, "check_policies", lambda hcl, settings: PolicyResult(True, [], "", ""))

    result, retrieved = pipeline.generate_rag_with_feedback("a versioned gcs bucket", run_plan=False)

    assert result.attempts == 1
    assert result.passed is True
    assert 'resource "google_storage_bucket"' in result.hcl
    assert len(retrieved) > 0
