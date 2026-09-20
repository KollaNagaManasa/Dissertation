"""Runs `terraform init/validate/plan` against generated HCL, using the google provider.

Requires the `terraform` CLI on PATH. Never applies — only init/validate/plan, so it is
safe to run against generated code without provisioning real GCP resources. `plan` needs
application-default credentials and a project (passed via GOOGLE_CLOUD_PROJECT, since generated
provider blocks don't set one), so run it against the experimentation project only.

A shared provider plugin cache keeps `init` from re-downloading the (large) google provider on
every sample — essential for benchmark runs with hundreds of validations.
"""

import json
import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from ragiac.config import Settings


# `init` populates the shared provider plugin cache; concurrent first-time installs into it can
# race, so init is serialised across threads (validate/plan stay parallel). Once a provider
# version is cached, init is a quick local link, so this costs little.
_INIT_LOCK = threading.Lock()


@dataclass(frozen=True)
class TerraformResult:
    passed: bool
    stage: str  # "init" | "validate" | "plan"
    stdout: str
    stderr: str


def _env(settings: Settings) -> dict[str, str]:
    cache_dir = settings.tf_plugin_cache_dir.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "TF_IN_AUTOMATION": "1", "TF_PLUGIN_CACHE_DIR": str(cache_dir)}
    if settings.google_cloud_project:
        env.setdefault("GOOGLE_CLOUD_PROJECT", settings.google_cloud_project)
    return env


def _run(binary: str, args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run([binary, *args], cwd=cwd, capture_output=True, text=True, timeout=300, env=env)


def terraform_version(settings: Settings) -> str | None:
    if shutil.which(settings.terraform_binary) is None:
        return None
    out = subprocess.run([settings.terraform_binary, "version", "-json"], capture_output=True, text=True)
    try:
        return json.loads(out.stdout).get("terraform_version")
    except json.JSONDecodeError:
        return None


def validate_terraform(hcl: str, settings: Settings, run_plan: bool = True) -> list[TerraformResult]:
    binary = settings.terraform_binary
    if shutil.which(binary) is None:
        raise FileNotFoundError(
            f"'{binary}' was not found on PATH. Install Terraform to run validation "
            "(https://developer.hashicorp.com/terraform/install)."
        )

    env = _env(settings)
    results: list[TerraformResult] = []
    with tempfile.TemporaryDirectory(prefix="ragiac_tf_") as tmpdir:
        workdir = Path(tmpdir)
        (workdir / "main.tf").write_text(hcl, encoding="utf-8")

        with _INIT_LOCK:
            init = _run(binary, ["init", "-input=false", "-backend=false", "-no-color"], workdir, env)
        results.append(TerraformResult(init.returncode == 0, "init", init.stdout, init.stderr))
        if init.returncode != 0:
            return results

        validate = _run(binary, ["validate", "-json", "-no-color"], workdir, env)
        results.append(TerraformResult(validate.returncode == 0, "validate", validate.stdout, validate.stderr))
        if validate.returncode != 0 or not run_plan:
            return results

        plan = _run(binary, ["plan", "-input=false", "-lock=false", "-no-color"], workdir, env)
        results.append(TerraformResult(plan.returncode == 0, "plan", plan.stdout, plan.stderr))

    return results
