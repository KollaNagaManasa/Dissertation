from types import SimpleNamespace

import pytest

from ragiac.config import Settings
from ragiac.evaluation import runner
from ragiac.evaluation.runner import Task, evaluate_sample, load_tasks, read_records, run_benchmark
from ragiac.generation.rag_generator import Generation
from ragiac.ingestion.chunker import Chunk
from ragiac.validation.opa_validator import PolicyResult
from ragiac.validation.terraform_validator import TerraformResult
from ragiac.vectorstore.base import ScoredChunk

GOOD_HCL = """
resource "google_storage_bucket" "b" {
  name     = "x"
  location = "asia-south1"
  versioning {
    enabled = true
  }
}
"""

TASK = Task(
    id="t1",
    category="storage",
    difficulty=1,
    requirement="A versioned bucket",
    intent={
        "resources": ["google_storage_bucket"],
        "attributes": [{"resource": "google_storage_bucket", "path": "versioning.enabled", "equals": True}],
    },
)


class FakePipeline:
    def __init__(self, hcl=GOOD_HCL, fail_generation=False):
        self.settings = Settings(ragiac_mode="gcp")
        self.hcl = hcl
        self.fail_generation = fail_generation
        self.calls = 0

    def generate_rag_detailed(self, requirement):
        self.calls += 1
        if self.fail_generation:
            raise RuntimeError("quota")
        text = '[google_storage_bucket > Example]\nresource "google_storage_bucket" "x" {}'
        chunk = Chunk("c", "gcs_bucket.md", "s", text)
        return Generation(self.hcl, [ScoredChunk(chunk, 0.9)])

    def generate_baseline(self, requirement):
        self.calls += 1
        return self.hcl


def _tf_ok(hcl, settings, run_plan=True):
    results = [TerraformResult(True, "init", "", ""), TerraformResult(True, "validate", '{"valid": true}', "")]
    if run_plan:
        results.append(TerraformResult(True, "plan", "", ""))
    return results


@pytest.fixture
def fake_validators(monkeypatch):
    monkeypatch.setattr(runner, "validate_terraform", _tf_ok)
    monkeypatch.setattr(runner, "check_policies", lambda hcl, settings: PolicyResult(True, [], "", ""))


def test_rag_sample_record_has_everything_needed_for_analysis(fake_validators):
    record = evaluate_sample(FakePipeline(), TASK, "rag", 0, run_plan=True)

    assert record["overall_pass"] is True
    assert record["validate_pass"] and record["plan_pass"] and record["policy_pass"] and record["intent_pass"]
    assert record["retrieval_hit"] == 1.0
    assert record["retrieved"] == [
        {"doc_id": "gcs_bucket.md", "score": 0.9, "resource_types": ["google_storage_bucket"]}
    ]
    assert record["hcl"] == GOOD_HCL
    assert record["errors"] == []


def test_baseline_has_no_retrieval_fields(fake_validators):
    record = evaluate_sample(FakePipeline(), TASK, "baseline", 0, run_plan=False)
    assert record["retrieved"] == [] and record["retrieval_hit"] is None
    assert record["plan_pass"] is None


def test_intent_failure_fails_overall_even_when_terraform_and_policy_pass(fake_validators):
    wrong = GOOD_HCL.replace("enabled = true", "enabled = false")
    record = evaluate_sample(FakePipeline(hcl=wrong), TASK, "rag", 0, run_plan=False)
    assert record["validate_pass"] and record["policy_pass"]
    assert not record["intent_pass"] and not record["overall_pass"]
    assert "INTENT_ATTRIBUTE_MISMATCH" in record["errors"]


def test_generation_failure_is_recorded_not_raised(fake_validators):
    record = evaluate_sample(FakePipeline(fail_generation=True), TASK, "rag", 0, run_plan=False)
    assert record["generation_error"].startswith("RuntimeError")
    assert record["errors"] == ["GENERATION_FAILED"]
    assert not record["overall_pass"]


def test_plan_credential_failure_is_not_held_against_the_model(monkeypatch):
    def tf(hcl, settings, run_plan=True):
        return [
            TerraformResult(True, "init", "", ""),
            TerraformResult(True, "validate", '{"valid": true}', ""),
            TerraformResult(False, "plan", "", "Error: Attempted to load application default credentials"),
        ]

    monkeypatch.setattr(runner, "validate_terraform", tf)
    monkeypatch.setattr(runner, "check_policies", lambda hcl, settings: PolicyResult(True, [], "", ""))
    record = evaluate_sample(FakePipeline(), TASK, "rag", 0, run_plan=True)

    assert record["plan_pass"] is None
    assert record["overall_pass"] is True
    assert "PLAN_ENVIRONMENT" in record["errors"]  # recorded, but excluded from model-error counts in summary


def test_unparseable_hcl_is_a_syntax_failure_not_a_policy_violation(monkeypatch):
    broken = 'resource "google_storage_bucket" "b" {'

    def tf(hcl, settings, run_plan=True):
        return [
            TerraformResult(False, "init", "", "Error: Unclosed configuration block"),
        ]

    monkeypatch.setattr(runner, "validate_terraform", tf)
    monkeypatch.setattr(
        runner, "check_policies", lambda hcl, settings: PolicyResult(False, ["conftest failed"], "", "", evaluated=False)
    )
    record = evaluate_sample(FakePipeline(hcl=broken), TASK, "rag", 0, run_plan=False)

    assert record["policy_evaluated"] is False
    assert "HCL_SYNTAX" in record["errors"]
    assert not any(e.startswith("POLICY") for e in record["errors"])


def test_run_benchmark_writes_records_and_resumes(fake_validators, tmp_path):
    pipeline = FakePipeline()
    tasks = [TASK, Task("t2", "storage", 1, "Another", None)]

    records = run_benchmark(pipeline, tasks, ["rag", "baseline"], n_samples=2, run_plan=False, run_dir=tmp_path)
    assert len(records) == 8
    assert pipeline.calls == 8
    assert len(read_records(tmp_path / "samples.jsonl")) == 8

    again = run_benchmark(pipeline, tasks, ["rag", "baseline"], n_samples=2, run_plan=False, run_dir=tmp_path)
    assert len(again) == 8
    assert pipeline.calls == 8  # nothing regenerated on resume


def test_run_benchmark_resumes_a_partial_run(fake_validators, tmp_path):
    pipeline = FakePipeline()
    run_benchmark(pipeline, [TASK], ["rag"], n_samples=1, run_plan=False, run_dir=tmp_path)
    assert pipeline.calls == 1

    run_benchmark(pipeline, [TASK], ["rag", "baseline"], n_samples=2, run_plan=False, run_dir=tmp_path)
    assert pipeline.calls == 1 + 3  # only the 3 missing (task, arm, sample) combinations


def test_shipped_task_file_is_well_formed():
    tasks = load_tasks(SimpleNamespace(read_text=lambda encoding: open("data/eval/gcp_tasks.jsonl", encoding=encoding).read()))
    assert len(tasks) >= 30
    assert len({t.id for t in tasks}) == len(tasks)
    assert all(t.intent and t.intent.get("resources") for t in tasks)
    assert {t.difficulty for t in tasks} == {1, 2, 3}
    assert sum(1 for t in tasks if t.category == "policy_conflict") == 2


def test_required_variable_without_default_is_not_held_against_the_model(monkeypatch):
    def tf(hcl, settings, run_plan=True):
        return [
            TerraformResult(True, "init", "", ""),
            TerraformResult(True, "validate", '{"valid": true}', ""),
            TerraformResult(False, "plan", "", "Error: No value for required variable"),
        ]

    monkeypatch.setattr(runner, "validate_terraform", tf)
    monkeypatch.setattr(runner, "check_policies", lambda hcl, settings: PolicyResult(True, [], "", ""))
    record = evaluate_sample(FakePipeline(), TASK, "rag", 0, run_plan=True)

    assert record["plan_pass"] is None and record["overall_pass"] is True
    assert "PLAN_NEEDS_INPUT" in record["errors"]


def test_real_plan_errors_still_fail_the_sample(monkeypatch):
    def tf(hcl, settings, run_plan=True):
        return [
            TerraformResult(True, "init", "", ""),
            TerraformResult(True, "validate", '{"valid": true}', ""),
            TerraformResult(False, "plan", "", "Error: Invalid bucket name"),
        ]

    monkeypatch.setattr(runner, "validate_terraform", tf)
    monkeypatch.setattr(runner, "check_policies", lambda hcl, settings: PolicyResult(True, [], "", ""))
    record = evaluate_sample(FakePipeline(), TASK, "rag", 0, run_plan=True)

    assert record["plan_pass"] is False and record["overall_pass"] is False
    assert "PLAN_ERROR" in record["errors"]


def test_parallel_run_matches_sequential_and_has_no_duplicate_samples(fake_validators, tmp_path):
    tasks = [TASK, Task("t2", "storage", 1, "Another", None), Task("t3", "storage", 1, "Third", None)]

    records = run_benchmark(FakePipeline(), tasks, ["rag", "baseline"], n_samples=3, run_plan=False, run_dir=tmp_path, workers=4)

    keys = [(r["task_id"], r["arm"], r["sample_idx"]) for r in records]
    assert len(keys) == len(set(keys)) == 18
    stored = read_records(tmp_path / "samples.jsonl")
    assert sorted((r["task_id"], r["arm"], r["sample_idx"]) for r in stored) == sorted(keys)


def test_validator_crash_is_recorded_and_does_not_abort_the_run(monkeypatch, tmp_path):
    import subprocess

    def boom(hcl, settings, run_plan=True):
        raise subprocess.TimeoutExpired("terraform", 300)

    monkeypatch.setattr(runner, "validate_terraform", boom)
    monkeypatch.setattr(runner, "check_policies", lambda hcl, settings: PolicyResult(True, [], "", ""))

    records = run_benchmark(FakePipeline(), [TASK], ["rag"], n_samples=2, run_plan=False, run_dir=tmp_path)

    assert len(records) == 2
    assert all("VALIDATION_TOOL_ERROR" in r["errors"] and not r["overall_pass"] for r in records)
    assert records[0]["validation_error"].startswith("TimeoutExpired")


def test_missing_binary_aborts_instead_of_recording_a_sample(monkeypatch):
    def missing(hcl, settings, run_plan=True):
        raise FileNotFoundError("terraform not found")

    monkeypatch.setattr(runner, "validate_terraform", missing)
    with pytest.raises(FileNotFoundError):
        evaluate_sample(FakePipeline(), TASK, "rag", 0, run_plan=False)


def test_conventions_arm_uses_no_retrieval_and_is_generated_separately(fake_validators):
    class WithConventions(FakePipeline):
        def generate_conventions(self, requirement):
            self.calls += 1
            return self.hcl

    pipeline = WithConventions()
    record = evaluate_sample(pipeline, TASK, "conventions", 0, run_plan=False)

    assert record["arm"] == "conventions"
    assert record["retrieved"] == [] and record["retrieval_hit"] is None
    assert record["overall_pass"] is True
    assert pipeline.calls == 1


def test_terraform_tool_failure_is_flagged_as_infrastructure_not_a_model_error(monkeypatch):
    from ragiac.evaluation.runner import is_infrastructure_failure

    def tf(hcl, settings, run_plan=True):
        return [
            TerraformResult(True, "init", "", ""),
            TerraformResult(False, "validate", "", "Error: Failed to load plugin schemas"),
        ]

    monkeypatch.setattr(runner, "validate_terraform", tf)
    monkeypatch.setattr(runner, "check_policies", lambda hcl, settings: PolicyResult(True, [], "", ""))
    record = evaluate_sample(FakePipeline(), TASK, "rag", 0, run_plan=False)

    assert "TOOL_FAILURE" in record["errors"]
    assert record["validation_error"] and is_infrastructure_failure(record)
    assert not is_infrastructure_failure({"errors": [], "diagnostics": ["validate: Unsupported argument"]})
    assert is_infrastructure_failure({"errors": [], "diagnostics": ["validate: Failed to load plugin schemas"]})  # old records


def test_tool_failures_are_excluded_from_model_error_counts():
    from ragiac.evaluation.summary import summarize

    rec = {
        "task_id": "t", "arm": "rag", "category": "storage", "difficulty": 1, "validate_pass": False, "plan_pass": None,
        "policy_evaluated": True, "policy_pass": True, "intent_pass": False, "overall_pass": False,
        "errors": ["TOOL_FAILURE", "UNSUPPORTED_ARGUMENT"], "flags": [], "retrieval_hit": None,
        "latency_gen_s": 1.0, "deprecation_warnings": 0,
    }
    assert summarize([rec])["headline"]["rag"]["error_counts"] == {"UNSUPPORTED_ARGUMENT": 1}
