"""Error taxonomy for LLM-generated Terraform (dissertation objective 2).

Every failed sample is mapped onto a small set of categories derived from what the validators
actually report, so failures can be counted per arm (RAG vs baseline) instead of read one by one.
Unrecognised messages fall into *_OTHER buckets and their raw text is kept in the run records, so
the taxonomy can be refined against real data (and mapped onto the published taxonomy in
arXiv:2512.14792) rather than guessed up front.

Categories, grouped by the stage that catches them:
  generation : GENERATION_FAILED, EMPTY_OUTPUT
  init       : PROVIDER_INIT
  syntax     : HCL_SYNTAX
  schema     : UNSUPPORTED_ARGUMENT, UNSUPPORTED_BLOCK, MISSING_REQUIRED, INVALID_VALUE,
               CONFLICTING_ARGUMENTS, INVALID_REFERENCE, EXPRESSION_ERROR, VALIDATE_OTHER
  plan       : PLAN_ERROR (PLAN_ENVIRONMENT / PLAN_NEEDS_INPUT are not model errors: missing
               credentials, or a variable declared without a default that plan cannot fill in)
  tooling    : TOOL_FAILURE (terraform itself failed; not a model error, and the sample is re-run)
  policy     : POLICY_MISSING_LABELS, POLICY_PUBLIC_ACCESS, POLICY_OTHER
  intent     : INTENT_MISSING_RESOURCE, INTENT_ATTRIBUTE_MISMATCH
Informational flags (not failures): DEPRECATED_USAGE, PROVIDER_VERSION_MISMATCH
"""

import json
import re
from dataclasses import dataclass, field

from ragiac.evaluation.intent import IntentResult
from ragiac.validation.opa_validator import PolicyResult
from ragiac.validation.terraform_validator import TerraformResult

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_ERROR_LINE_RE = re.compile(r"Error:\s*(.+)")

# Ordered: first match wins. Patterns are matched case-insensitively against the diagnostic summary.
_SUMMARY_RULES: list[tuple[str, str]] = [
    (r"unsupported argument", "UNSUPPORTED_ARGUMENT"),
    (r"unsupported block type", "UNSUPPORTED_BLOCK"),
    (r"missing required argument|insufficient .* blocks?|too many .* blocks?", "MISSING_REQUIRED"),
    (r"conflicting configuration|invalid combination of arguments|conflicts with", "CONFLICTING_ARGUMENTS"),
    (r"undeclared|unsupported attribute|invalid reference|reference to", "INVALID_REFERENCE"),
    (r"invalid function argument|call to unknown function|invalid operand|inconsistent conditional", "EXPRESSION_ERROR"),
    (
        r"incorrect attribute value type|invalid value|expected .* to be|must be|is not a valid|"
        r"invalid .* value|value must|unsuitable value",
        "INVALID_VALUE",
    ),
    (
        r"argument or block definition required|unclosed|unterminated|invalid character|missing newline|"
        r"missing item separator|invalid expression|invalid multi-line|missing key/value|invalid block definition|"
        r"unbalanced|extra characters|attribute redefined|duplicate .*(argument|attribute)",
        "HCL_SYNTAX",
    ),
    (r"failed to query available provider|no available releases|invalid provider|provider .* not found", "PROVIDER_INIT"),
]

_PLAN_ENV_RE = re.compile(
    r"default credentials|application default credentials|requires explicit configuration|"
    r"required field is not set|could not find default|project.*not set|permission denied|"
    r"has not been used in project|accessnotconfigured|api .* not enabled|403",
    re.I,
)


# Terraform itself failing (provider plugin would not load, timed out, crashed) says nothing about
# the generated code, whichever stage it happens in; such samples are re-run, not scored.
TOOL_FAILURE_RE = re.compile(
    r"failed to load plugin schemas|plugin did not respond|unrecognized remote plugin message|"
    r"plugin exited before we could connect|context deadline exceeded|connection reset by peer|"
    r"failed to instantiate provider|could not load plugin",
    re.I,
)

# Failures that say nothing about the generated code's quality.
NON_MODEL_ERRORS = {"PLAN_ENVIRONMENT", "PLAN_NEEDS_INPUT", "TOOL_FAILURE"}
NON_MODEL_PLAN_ERRORS = NON_MODEL_ERRORS  # older name, kept for the plan-evaluability check


@dataclass(frozen=True)
class Classification:
    errors: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    raw_summaries: list[str] = field(default_factory=list)
    deprecation_warnings: int = 0


def _clean(text: str) -> str:
    return _ANSI_RE.sub("", text).replace("│", " ")


def error_summaries(result: TerraformResult) -> list[str]:
    """Diagnostic summaries for a failed terraform stage (JSON for validate, text otherwise)."""
    if result.stage == "validate" and result.stdout.strip().startswith("{"):
        try:
            diagnostics = json.loads(result.stdout).get("diagnostics", [])
            return [d["summary"] for d in diagnostics if d.get("severity") == "error"]
        except (json.JSONDecodeError, KeyError):
            pass
    return [m.group(1).strip() for m in _ERROR_LINE_RE.finditer(_clean(result.stdout + "\n" + result.stderr))]


def deprecation_warning_count(results: list[TerraformResult]) -> int:
    for r in results:
        if r.stage == "validate" and r.stdout.strip().startswith("{"):
            try:
                diagnostics = json.loads(r.stdout).get("diagnostics", [])
            except json.JSONDecodeError:
                return 0
            return sum(1 for d in diagnostics if d.get("severity") == "warning" and "deprecat" in d.get("summary", "").lower())
    return 0


def classify_summary(summary: str, stage: str) -> str:
    if TOOL_FAILURE_RE.search(summary):
        return "TOOL_FAILURE"
    if stage == "plan":
        if re.search(r"no value for required variable", summary, re.I):
            return "PLAN_NEEDS_INPUT"
        return "PLAN_ENVIRONMENT" if _PLAN_ENV_RE.search(summary) else "PLAN_ERROR"
    for pattern, code in _SUMMARY_RULES:
        if re.search(pattern, summary, re.I):
            return code
    return "PROVIDER_INIT" if stage == "init" else "VALIDATE_OTHER"


def classify_policy(violation: str) -> str:
    lowered = violation.lower()
    if "label" in lowered:
        return "POLICY_MISSING_LABELS"
    if "allusers" in lowered or "allauthenticatedusers" in lowered or "public ip" in lowered:
        return "POLICY_PUBLIC_ACCESS"
    return "POLICY_OTHER"


def provider_version_flag(hcl: str, target_major: int) -> str | None:
    match = re.search(r"hashicorp/google[^}]*?version\s*=\s*\"[^\d\"]*(\d+)", hcl, re.S)
    if match and int(match.group(1)) != target_major:
        return "PROVIDER_VERSION_MISMATCH"
    return None


def classify(
    hcl: str | None,
    terraform_results: list[TerraformResult],
    policy_result: PolicyResult | None,
    intent_result: IntentResult | None,
    generation_error: str | None = None,
    target_provider_major: int = 8,
) -> Classification:
    if generation_error:
        return Classification(errors=["GENERATION_FAILED"], raw_summaries=[generation_error])
    if not hcl or not hcl.strip():
        return Classification(errors=["EMPTY_OUTPUT"])

    errors: list[str] = []
    raw: list[str] = []

    for r in terraform_results:
        if r.passed:
            continue
        for summary in error_summaries(r) or [f"{r.stage} failed (no diagnostic parsed)"]:
            errors.append(classify_summary(summary, r.stage))
            raw.append(f"{r.stage}: {summary}")

    if policy_result is not None and getattr(policy_result, "evaluated", True) and not policy_result.passed:
        for violation in policy_result.violations:
            errors.append(classify_policy(violation))
            raw.append(f"policy: {violation}")

    if intent_result is not None and not intent_result.passed:
        for failure in intent_result.failures:
            errors.append("INTENT_MISSING_RESOURCE" if failure.startswith("missing resource") else "INTENT_ATTRIBUTE_MISMATCH")
            raw.append(f"intent: {failure}")

    flags: list[str] = []
    if provider_version_flag(hcl, target_provider_major):
        flags.append("PROVIDER_VERSION_MISMATCH")
    n_deprecated = deprecation_warning_count(terraform_results)
    if n_deprecated:
        flags.append("DEPRECATED_USAGE")

    return Classification(errors=sorted(set(errors)), flags=flags, raw_summaries=raw, deprecation_warnings=n_deprecated)
