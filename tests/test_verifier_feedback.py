from ragiac.evaluation.intent import IntentResult
from ragiac.generation import verifier_feedback as vf
from ragiac.generation.verifier_feedback import RefinementResult
from ragiac.validation.opa_validator import PolicyResult
from ragiac.validation.report import ValidationReport
from ragiac.validation.terraform_validator import TerraformResult


class RecordingLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


def test_refine_skips_the_retry_when_the_first_attempt_already_passes(monkeypatch):
    monkeypatch.setattr(vf, "validate_terraform", lambda hcl, settings, run_plan: [TerraformResult(True, "validate", "", "")])
    monkeypatch.setattr(vf, "check_policies", lambda hcl, settings: PolicyResult(True, [], "", ""))
    llm = RecordingLLM("should not be used")

    result = vf.refine("hcl", "a bucket", llm, settings=object(), run_plan=False)

    assert result.attempts == 1
    assert result.hcl == "hcl"
    assert result.final_report is None
    assert llm.calls == []


def test_refine_retries_once_with_diagnostics_and_returns_the_fixed_hcl(monkeypatch):
    calls = {"n": 0}

    def fake_validate(hcl, settings, run_plan):
        calls["n"] += 1
        passed = calls["n"] > 1  # first validation (of the original hcl) fails, second (of the fix) passes
        return [TerraformResult(passed, "validate", "", "" if passed else "Error: Missing required argument")]

    monkeypatch.setattr(vf, "validate_terraform", fake_validate)
    monkeypatch.setattr(vf, "check_policies", lambda hcl, settings: PolicyResult(True, [], "", ""))
    llm = RecordingLLM("fixed hcl")

    result = vf.refine("broken hcl", "a bucket", llm, settings=object(), run_plan=False)

    assert result.attempts == 2
    assert result.hcl == "fixed hcl"
    assert result.first_attempt_report.overall_passed is False
    assert result.final_report.overall_passed is True
    (system_prompt, user_prompt), = llm.calls
    assert "broken hcl" in user_prompt
    assert "Missing required argument" in user_prompt
    assert "a bucket" in user_prompt


def test_refine_includes_policy_violations_in_the_feedback_prompt(monkeypatch):
    monkeypatch.setattr(vf, "validate_terraform", lambda hcl, settings, run_plan: [TerraformResult(True, "validate", "", "")])
    monkeypatch.setattr(
        vf, "check_policies", lambda hcl, settings: PolicyResult(False, ["bucket.x is missing labels.environment"], "", "")
    )
    llm = RecordingLLM("fixed hcl")

    vf.refine("hcl", "a bucket", llm, settings=object(), run_plan=False)

    (_, user_prompt), = llm.calls
    assert "missing labels.environment" in user_prompt


def test_refine_triggers_and_gives_feedback_on_an_intent_mismatch_too(monkeypatch):
    # terraform and policy both pass, but the intent spec is not satisfied; this must still
    # trigger a retry and the feedback prompt must mention the intent failure, not just
    # terraform/policy diagnostics (a real gap found by checking a verifier-feedback sample that
    # had both a policy violation and an unrelated intent mismatch: fixing the policy violation
    # alone silently left the intent mismatch in place, because it was never surfaced).
    monkeypatch.setattr(vf, "validate_terraform", lambda hcl, settings, run_plan: [TerraformResult(True, "validate", "", "")])
    monkeypatch.setattr(vf, "check_policies", lambda hcl, settings: PolicyResult(True, [], "", ""))
    llm = RecordingLLM("fixed hcl")
    hcl = 'resource "google_container_node_pool" "p" {\n node_count = 2\n}'
    intent = {"attributes": [{"resource": "google_container_node_pool", "path": "node_count", "equals": 3}]}

    result = vf.refine(hcl, "a cluster with 3 nodes", llm, settings=object(), intent=intent, run_plan=False)

    assert result.attempts == 2
    assert result.first_attempt_intent.passed is False
    (_, user_prompt), = llm.calls
    assert "node_count" in user_prompt


def test_passed_reflects_the_last_attempt_made():
    report = ValidationReport([TerraformResult(True, "validate", "", "")], None)
    passing_intent = IntentResult(True)
    failing_intent = IntentResult(False, ["still wrong"])
    assert RefinementResult("hcl", 1, report, passing_intent, None, None).passed is True
    assert RefinementResult("hcl", 2, report, failing_intent, report, failing_intent).passed is False
    assert RefinementResult("hcl", 2, report, failing_intent, report, passing_intent).passed is True
