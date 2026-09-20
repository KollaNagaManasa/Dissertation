import json

from ragiac.evaluation.intent import IntentResult
from ragiac.evaluation.summary import render_markdown, summarize
from ragiac.evaluation.taxonomy import (
    classify,
    classify_policy,
    classify_summary,
    deprecation_warning_count,
    error_summaries,
    provider_version_flag,
)
from ragiac.validation.opa_validator import PolicyResult
from ragiac.validation.terraform_validator import TerraformResult


def _validate(diagnostics: list[dict], passed: bool = False) -> TerraformResult:
    return TerraformResult(passed, "validate", json.dumps({"valid": passed, "diagnostics": diagnostics}), "")


def test_classify_summary_maps_common_terraform_errors():
    assert classify_summary("Unsupported argument", "validate") == "UNSUPPORTED_ARGUMENT"
    assert classify_summary("Unsupported block type", "validate") == "UNSUPPORTED_BLOCK"
    assert classify_summary("Missing required argument", "validate") == "MISSING_REQUIRED"
    assert classify_summary("Reference to undeclared resource", "validate") == "INVALID_REFERENCE"
    assert classify_summary("Argument or block definition required", "validate") == "HCL_SYNTAX"
    assert classify_summary("Invalid combination of arguments", "validate") == "CONFLICTING_ARGUMENTS"
    assert classify_summary('expected location to be one of ["US"], got X', "validate") == "INVALID_VALUE"
    assert classify_summary("something novel", "validate") == "VALIDATE_OTHER"
    assert classify_summary("Failed to query available provider packages", "init") == "PROVIDER_INIT"


def test_plan_credential_errors_are_environment_not_model_errors():
    msg = "Attempted to load application default credentials since neither `credentials` nor `access_token` was set"
    assert classify_summary(msg, "plan") == "PLAN_ENVIRONMENT"
    assert classify_summary("Error creating bucket: name already taken", "plan") == "PLAN_ERROR"
    assert classify_summary("No value for required variable", "plan") == "PLAN_NEEDS_INPUT"


def test_classify_policy_violations():
    assert classify_policy("google_storage_bucket.x is missing labels.environment") == "POLICY_MISSING_LABELS"
    assert classify_policy("x grants access to allUsers") == "POLICY_PUBLIC_ACCESS"
    assert classify_policy("has a public IP (ipv4_enabled = true)") == "POLICY_PUBLIC_ACCESS"
    assert classify_policy("something else") == "POLICY_OTHER"


def test_error_summaries_read_validate_json_and_plain_text():
    result = _validate([{"severity": "error", "summary": "Unsupported argument"}, {"severity": "warning", "summary": "w"}])
    assert error_summaries(result) == ["Unsupported argument"]

    init = TerraformResult(False, "init", "", "\x1b[31mError: Failed to query available provider packages\x1b[0m")
    assert error_summaries(init) == ["Failed to query available provider packages"]


def test_deprecation_warnings_counted_from_validate_output():
    result = _validate([{"severity": "warning", "summary": "Deprecated attribute"}, {"severity": "warning", "summary": "other"}], passed=True)
    assert deprecation_warning_count([result]) == 1


def test_provider_version_flag():
    assert provider_version_flag('required_providers {\n google = {\n source = "hashicorp/google"\n version = "~> 5.0"\n }\n}', 8) == "PROVIDER_VERSION_MISMATCH"
    assert provider_version_flag('google = {\n source = "hashicorp/google"\n version = "~> 8.0"\n}', 8) is None
    assert provider_version_flag("resource {}", 8) is None


def test_classify_combines_stages_and_flags():
    hcl = 'google = {\n source = "hashicorp/google"\n version = "~> 5.0"\n}'
    c = classify(
        hcl,
        [TerraformResult(True, "init", "", ""), _validate([{"severity": "error", "summary": "Unsupported argument"}])],
        PolicyResult(False, ["b is missing labels.environment"], "", ""),
        IntentResult(False, ["missing resource type google_sql_user", "x.y does not satisfy {}"]),
    )
    assert c.errors == sorted(
        ["UNSUPPORTED_ARGUMENT", "POLICY_MISSING_LABELS", "INTENT_MISSING_RESOURCE", "INTENT_ATTRIBUTE_MISMATCH"]
    )
    assert c.flags == ["PROVIDER_VERSION_MISMATCH"]


def test_generation_failure_and_empty_output():
    assert classify(None, [], None, None, generation_error="TooManyRequests").errors == ["GENERATION_FAILED"]
    assert classify("   ", [], None, None).errors == ["EMPTY_OUTPUT"]


def test_unevaluated_policy_is_not_counted_as_violation():
    not_evaluated = PolicyResult(False, ["conftest failed"], "", "", evaluated=False)
    assert classify("x", [], not_evaluated, None).errors == []


def _record(task, arm, overall, category="storage", validate=True, policy_ok=True, evaluated=True, errors=(), hit=None):
    return {
        "task_id": task,
        "arm": arm,
        "category": category,
        "difficulty": 1,
        "validate_pass": validate,
        "plan_pass": None,
        "policy_evaluated": evaluated,
        "policy_pass": policy_ok,
        "intent_pass": overall,
        "overall_pass": overall,
        "errors": list(errors),
        "flags": [],
        "retrieval_hit": hit,
        "latency_gen_s": 2.0,
        "deprecation_warnings": 0,
    }


def test_summarize_headline_paired_and_conflict_sections():
    records = [
        _record("t1", "rag", True, hit=1.0),
        _record("t1", "baseline", False, policy_ok=False, errors=["POLICY_MISSING_LABELS"]),
        _record("t2", "rag", True, hit=0.5),
        _record("t2", "baseline", True),
        _record("t3", "rag", True, hit=1.0),
        _record("t3", "baseline", False, errors=["PLAN_ENVIRONMENT", "PLAN_NEEDS_INPUT", "UNSUPPORTED_ARGUMENT"]),
        _record("c1", "rag", False, category="policy_conflict", policy_ok=False),
        _record("c1", "baseline", False, category="policy_conflict", policy_ok=False),
    ]
    s = summarize(records, ks=[1])

    assert s["headline"]["rag"]["overall_pass_rate"]["rate"] == 1.0
    assert s["headline"]["baseline"]["overall_pass_rate"]["rate"] == 1 / 3
    assert s["headline"]["rag"]["retrieval_hit_rate"] == (1.0 + 0.5 + 1.0) / 3
    assert s["headline"]["baseline"]["error_counts"] == {"POLICY_MISSING_LABELS": 1, "UNSUPPORTED_ARGUMENT": 1}
    assert s["headline"]["rag"]["pass_at_k_overall"]["1"] == 1.0

    assert s["paired_overall_pass"]["rag_better"] == 2
    assert s["paired_overall_pass"]["tied"] == 1
    assert s["paired_overall_pass"]["baseline_better"] == 0
    assert s["paired_overall_pass"]["sign_test_p"] == 0.5  # 2 wins, 0 losses: exact two-sided p

    assert "c1" not in json.dumps(s["by_category"])  # conflict tasks excluded from headline
    assert set(s["policy_conflict_tasks"]) == {"rag", "baseline"}


def test_opa_violation_rate_excludes_unevaluable_samples():
    records = [
        _record("t1", "rag", False, policy_ok=False, evaluated=True),
        _record("t2", "rag", False, policy_ok=False, evaluated=False),  # unparseable: syntax error, not a violation
        _record("t3", "rag", True),
    ]
    metric = summarize(records)["headline"]["rag"]["opa_violation_rate"]
    assert metric["n"] == 2
    assert metric["rate"] == 0.5


def test_render_markdown_contains_key_sections():
    records = [_record("t1", "rag", True, hit=1.0), _record("t1", "baseline", False, errors=["HCL_SYNTAX"])]
    markdown = render_markdown(None, summarize(records))
    for expected in ("Headline metrics", "overall pass", "pass@1", "Error categories", "HCL_SYNTAX", "Paired comparison"):
        assert expected in markdown


def test_functional_pass_ignores_org_policy_but_not_intent_or_plan():
    def rec(**kw):
        base = _record("t", "rag", False, policy_ok=False)
        base.update(kw)
        return base

    records = [
        rec(task_id="a", validate_pass=True, plan_pass=None, intent_pass=True),  # policy-only failure -> functional
        rec(task_id="b", validate_pass=True, plan_pass=False, intent_pass=True),  # plan failed
        rec(task_id="c", validate_pass=True, plan_pass=True, intent_pass=False),  # wrong thing built
        rec(task_id="d", validate_pass=False, plan_pass=None, intent_pass=True),  # does not validate
    ]
    metric = summarize(records)["headline"]["rag"]["functional_pass_rate"]
    assert metric["rate"] == 0.25 and metric["n"] == 4


def test_three_arm_summary_adds_rag_vs_conventions_comparison():
    records = []
    for task, rag, conv, base in (("t1", True, False, False), ("t2", True, True, False), ("t3", False, False, False)):
        records += [_record(task, "rag", rag), _record(task, "conventions", conv), _record(task, "baseline", base)]
    s = summarize(records)

    assert set(s["headline"]) == {"baseline", "conventions", "rag"}
    assert s["paired_overall_pass"]["arm_b"] == "baseline"
    assert s["paired_rag_vs_conventions"]["arm_b"] == "conventions"
    assert s["paired_rag_vs_conventions"]["rag_better"] == 1
    assert "RAG vs conventions-in-prompt" in render_markdown(None, s)


def test_two_arm_summary_has_no_conventions_comparison():
    s = summarize([_record("t1", "rag", True), _record("t1", "baseline", False)])
    assert s["paired_rag_vs_conventions"] is None
