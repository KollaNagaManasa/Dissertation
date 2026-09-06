"""Aggregates terraform + OPA validation into the metrics named in the outline's
supervisor remarks: validate/plan pass rate and OPA policy-violation rate."""

from dataclasses import dataclass

from ragiac.validation.opa_validator import PolicyResult
from ragiac.validation.terraform_validator import TerraformResult


@dataclass(frozen=True)
class ValidationReport:
    terraform_results: list[TerraformResult]
    policy_result: PolicyResult | None

    @property
    def terraform_passed(self) -> bool:
        return bool(self.terraform_results) and all(r.passed for r in self.terraform_results)

    @property
    def policy_passed(self) -> bool:
        return self.policy_result is None or self.policy_result.passed

    @property
    def overall_passed(self) -> bool:
        return self.terraform_passed and self.policy_passed

    def summary(self) -> str:
        lines = [f"terraform: {'PASS' if self.terraform_passed else 'FAIL'}"]
        for r in self.terraform_results:
            lines.append(f"  {r.stage}: {'ok' if r.passed else 'FAILED'}")
        if self.policy_result is not None:
            lines.append(f"opa: {'PASS' if self.policy_result.passed else 'FAIL'}")
            for v in self.policy_result.violations:
                lines.append(f"  violation: {v}")
        return "\n".join(lines)
