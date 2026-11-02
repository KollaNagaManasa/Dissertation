from ragiac.config import Settings
from ragiac.generation.local_template_llm import LocalTemplateLLM, _extract_requirement
from ragiac.generation.prompts import build_baseline_prompt, build_rag_prompt
from ragiac.generation.verifier_feedback import FEEDBACK_SYSTEM_PROMPT, FEEDBACK_USER_TEMPLATE


def _llm() -> LocalTemplateLLM:
    return LocalTemplateLLM(Settings(google_cloud_region="asia-south1"))


def test_rag_gcs_bucket_applies_grounded_defaults():
    system, user = build_rag_prompt(
        "A GCS bucket for invoice PDFs, versioned, with a 30 day lifecycle rule to Nearline, prod",
        context="[Source: gcs_bucket.md]\nuniform_bucket_level_access recommended",
    )
    hcl = _llm().generate(system, user)

    assert 'resource "google_storage_bucket"' in hcl
    assert 'location                    = "asia-south1"' in hcl
    assert "uniform_bucket_level_access = true" in hcl
    assert "enabled = true" in hcl  # versioning
    assert "age = 30" in hcl
    assert 'storage_class = "NEARLINE"' in hcl
    assert 'environment = "prod"' in hcl


def test_extract_requirement_finds_the_real_requirement_in_a_verifier_feedback_prompt():
    # regression: FEEDBACK_USER_TEMPLATE used to have nothing after {requirement}, so the regex
    # (which needs a trailing "\n\nGenerate") never matched and _extract_requirement fell back to
    # returning the *entire* prompt (failed HCL + diagnostics included) as "the requirement".
    user_prompt = FEEDBACK_USER_TEMPLATE.format(
        hcl='resource "google_storage_bucket" "x" {}', diagnostics="- missing required argument", requirement="A versioned GCS bucket, prod"
    )
    assert _extract_requirement(user_prompt) == "A versioned GCS bucket, prod"


def test_local_llm_handles_a_verifier_feedback_retry_prompt_end_to_end():
    # integration-level check that the full retry path a user would hit via the Streamlit
    # "retry with verifier feedback" checkbox or the rag_feedback arm (in local mode) composes
    # correctly: the right resource type for the real requirement, not a crash or garbage output.
    user_prompt = FEEDBACK_USER_TEMPLATE.format(
        hcl='resource "google_storage_bucket" "x" {}',
        diagnostics="- missing required argument: location",
        requirement="A Cloud SQL instance for prod, 3 nodes",
    )
    hcl = _llm().generate(FEEDBACK_SYSTEM_PROMPT, user_prompt)

    assert 'resource "google_sql_database_instance"' in hcl


def test_baseline_gcs_bucket_omits_grounded_defaults():
    system, user = build_baseline_prompt("A GCS bucket for invoice PDFs, versioned")
    hcl = _llm().generate(system, user)

    assert 'resource "google_storage_bucket"' in hcl
    assert 'location = "US"' in hcl
    assert "uniform_bucket_level_access" not in hcl
    assert "labels" not in hcl


def test_public_bucket_gets_iam_member():
    system, user = build_rag_prompt("A GCS bucket for a public static website", context="")
    hcl = _llm().generate(system, user)

    assert 'resource "google_storage_bucket_iam_member" "public_read"' in hcl
    assert 'member = "allUsers"' in hcl


def test_cloud_sql_detected_and_grounded():
    system, user = build_rag_prompt(
        "A production PostgreSQL Cloud SQL instance, regional, with backups, no public IP",
        context="",
    )
    hcl = _llm().generate(system, user)

    assert 'resource "google_sql_database_instance"' in hcl
    assert 'database_version = "POSTGRES_15"' in hcl
    assert 'availability_type = "REGIONAL"' in hcl
    assert "deletion_protection = true" in hcl
    assert "ipv4_enabled = false" in hcl


def test_gke_detected_with_node_count_and_machine_type():
    system, user = build_rag_prompt(
        "A production regional GKE cluster with private nodes, workload identity, 3 e2-medium nodes",
        context="",
    )
    hcl = _llm().generate(system, user)

    assert 'resource "google_container_cluster"' in hcl
    assert "enable_private_nodes = true" in hcl
    assert "workload_identity_config" in hcl
    assert "node_count = 3" in hcl
    assert 'machine_type = "e2-medium"' in hcl
    assert "resource_labels" in hcl
    assert 'environment = "prod"' in hcl
