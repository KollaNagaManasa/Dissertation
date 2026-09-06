from ragiac.validation.opa_validator import PolicyResult
from ragiac.validation.report import ValidationReport
from ragiac.validation.terraform_validator import TerraformResult


def test_overall_passed_requires_terraform_and_policy():
    ok_terraform = [
        TerraformResult(True, "init", "", ""),
        TerraformResult(True, "validate", "", ""),
        TerraformResult(True, "plan", "", ""),
    ]
    ok_policy = PolicyResult(True, [], "", "")

    assert ValidationReport(ok_terraform, ok_policy).overall_passed is True

    failing_policy = PolicyResult(False, ["public bucket"], "", "")
    assert ValidationReport(ok_terraform, failing_policy).overall_passed is False

    failing_terraform = [TerraformResult(True, "init", "", ""), TerraformResult(False, "validate", "", "err")]
    assert ValidationReport(failing_terraform, ok_policy).overall_passed is False


def test_policy_passed_defaults_true_when_not_checked():
    ok_terraform = [TerraformResult(True, "init", "", "")]
    report = ValidationReport(ok_terraform, policy_result=None)
    assert report.policy_passed is True
    assert report.overall_passed is True
