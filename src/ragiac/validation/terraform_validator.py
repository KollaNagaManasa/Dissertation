"""Runs `terraform init/validate/plan` against generated HCL, using the google provider.

Requires the `terraform` CLI on PATH. Never applies — only init/validate/plan, so it is
safe to run against generated code without provisioning real GCP resources (a `plan`
still needs valid credentials/project to resolve data sources, so run this against a
sandbox/experimentation GCP project, per the supervisor's remark on cloud accounts for
experimentation).
"""

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ragiac.config import Settings


@dataclass(frozen=True)
class TerraformResult:
    passed: bool
    stage: str  # "init" | "validate" | "plan"
    stdout: str
    stderr: str


def _run(binary: str, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([binary, *args], cwd=cwd, capture_output=True, text=True, timeout=180)


def validate_terraform(hcl: str, settings: Settings, run_plan: bool = True) -> list[TerraformResult]:
    binary = settings.terraform_binary
    if shutil.which(binary) is None:
        raise FileNotFoundError(
            f"'{binary}' was not found on PATH. Install Terraform to run validation "
            "(https://developer.hashicorp.com/terraform/install)."
        )

    results: list[TerraformResult] = []
    with tempfile.TemporaryDirectory(prefix="ragiac_tf_") as tmpdir:
        workdir = Path(tmpdir)
        (workdir / "main.tf").write_text(hcl, encoding="utf-8")

        init = _run(binary, ["init", "-input=false", "-backend=false"], workdir)
        results.append(TerraformResult(init.returncode == 0, "init", init.stdout, init.stderr))
        if init.returncode != 0:
            return results

        validate = _run(binary, ["validate", "-json"], workdir)
        results.append(TerraformResult(validate.returncode == 0, "validate", validate.stdout, validate.stderr))
        if validate.returncode != 0 or not run_plan:
            return results

        plan = _run(binary, ["plan", "-input=false", "-lock=false"], workdir)
        results.append(TerraformResult(plan.returncode == 0, "plan", plan.stdout, plan.stderr))

    return results
