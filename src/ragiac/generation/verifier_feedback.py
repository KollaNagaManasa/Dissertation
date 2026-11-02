"""Verifier-feedback refinement in the style of Jouini (2026, arXiv:2607.20478): one retry round
that feeds the validator's own diagnostics back to the model, rather than open-ended refinement.
That paper reports binary convergence on this kind of feedback - tasks resolve on the first retry
or not at all - so a single round captures most of the available benefit without the cost and
complexity of an unbounded refinement loop.
"""

from dataclasses import dataclass

from ragiac.config import Settings
from ragiac.evaluation.intent import IntentResult, check_intent
from ragiac.evaluation.taxonomy import error_summaries
from ragiac.generation.rag_generator import LLM
from ragiac.validation.opa_validator import check_policies
from ragiac.validation.report import ValidationReport
from ragiac.validation.terraform_validator import validate_terraform

FEEDBACK_SYSTEM_PROMPT = (
    "You are an infrastructure engineer fixing a Terraform configuration for Google Cloud "
    "Platform (the `google`/`google-beta` providers only) that failed validation. Make the "
    "minimal change that resolves the diagnostics given; do not rewrite parts of the "
    "configuration the diagnostics do not mention. Output a single, complete Terraform "
    "configuration (HCL) with no prose outside of HCL comments."
)

FEEDBACK_USER_TEMPLATE = """This configuration was generated for the requirement below but failed validation:

{hcl}

Validation diagnostics:
{diagnostics}

Fix the configuration so it passes validation.

Requirement:
{requirement}"""


def _validate(hcl: str, requirement_intent: dict | None, settings: Settings, run_plan: bool, check_opa: bool) -> tuple[ValidationReport, IntentResult]:
    report = ValidationReport(
        terraform_results=validate_terraform(hcl, settings, run_plan=run_plan),
        policy_result=check_policies(hcl, settings) if check_opa else None,
    )
    return report, check_intent(hcl, requirement_intent)


def _passed(report: ValidationReport, intent_result: IntentResult) -> bool:
    return report.overall_passed and intent_result.passed


def _diagnostics_text(report: ValidationReport, intent_result: IntentResult) -> str:
    # Without this, a sample whose terraform/policy issues get fixed but which also had a
    # pre-existing intent mismatch (e.g. a wrong attribute value) stays broken after the retry,
    # because the model was never told the intent check failed - see test for the case this fixes.
    lines = [s for r in report.terraform_results if not r.passed for s in error_summaries(r)]
    if report.policy_result is not None and not report.policy_result.passed:
        lines += [f"org policy: {v}" for v in report.policy_result.violations]
    lines += [f"intent: {f}" for f in intent_result.failures]
    return "\n".join(f"- {line}" for line in lines) or "(validation failed with no diagnostic text)"


@dataclass(frozen=True)
class RefinementResult:
    hcl: str
    attempts: int  # 1 if the first attempt already passed, 2 if one retry was used
    first_attempt_report: ValidationReport
    first_attempt_intent: IntentResult
    final_report: ValidationReport | None  # None when no retry was needed
    final_intent: IntentResult | None

    @property
    def passed(self) -> bool:
        report, intent = (self.final_report, self.final_intent) if self.attempts > 1 else (self.first_attempt_report, self.first_attempt_intent)
        return _passed(report, intent)


def refine(
    hcl: str,
    requirement: str,
    llm: LLM,
    settings: Settings,
    intent: dict | None = None,
    run_plan: bool = True,
    check_opa: bool = True,
) -> RefinementResult:
    first_report, first_intent = _validate(hcl, intent, settings, run_plan, check_opa)
    if _passed(first_report, first_intent):
        return RefinementResult(hcl, 1, first_report, first_intent, None, None)

    user_prompt = FEEDBACK_USER_TEMPLATE.format(
        hcl=hcl, diagnostics=_diagnostics_text(first_report, first_intent), requirement=requirement
    )
    fixed_hcl = llm.generate(FEEDBACK_SYSTEM_PROMPT, user_prompt)
    final_report, final_intent = _validate(fixed_hcl, intent, settings, run_plan, check_opa)
    return RefinementResult(fixed_hcl, 2, first_report, first_intent, final_report, final_intent)
