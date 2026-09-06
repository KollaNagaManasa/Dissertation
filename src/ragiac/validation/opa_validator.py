"""Policy-as-code checks via `conftest` (Open Policy Agent) against data/policies/*.rego."""

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ragiac.config import Settings


@dataclass(frozen=True)
class PolicyResult:
    passed: bool
    violations: list[str]
    raw_stdout: str
    raw_stderr: str


def check_policies(hcl: str, settings: Settings) -> PolicyResult:
    binary = settings.conftest_binary
    if shutil.which(binary) is None:
        raise FileNotFoundError(
            f"'{binary}' was not found on PATH. Install conftest to run policy checks "
            "(https://www.conftest.dev/install/)."
        )

    with tempfile.TemporaryDirectory(prefix="ragiac_opa_") as tmpdir:
        workdir = Path(tmpdir)
        tf_file = workdir / "main.tf"
        tf_file.write_text(hcl, encoding="utf-8")

        result = subprocess.run(
            [binary, "test", "--parser", "hcl2", "--policy", str(settings.policy_dir), "-o", "json", str(tf_file)],
            capture_output=True,
            text=True,
            timeout=120,
        )

    violations: list[str] = []
    try:
        report = json.loads(result.stdout) if result.stdout else []
        for file_result in report:
            for failure in file_result.get("failures", []):
                violations.append(failure.get("msg", str(failure)))
    except json.JSONDecodeError:
        if result.returncode != 0:
            violations.append(result.stderr or result.stdout)

    return PolicyResult(
        passed=result.returncode == 0,
        violations=violations,
        raw_stdout=result.stdout,
        raw_stderr=result.stderr,
    )
