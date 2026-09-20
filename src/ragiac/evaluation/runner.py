"""Benchmark runner: task set x arms x samples -> per-sample records + reproducibility manifest.

Every sample is appended to samples.jsonl the moment it finishes, so a crash or quota stall loses
nothing and `resume` can continue. Records are the single source of truth: summary.json/md are
pure functions of them (see summary.py) and can be regenerated after the taxonomy changes.
"""

import hashlib
import json
import platform
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ragiac.evaluation.intent import check_intent
from ragiac.evaluation.metrics import retrieval_hit
from ragiac.evaluation.taxonomy import NON_MODEL_PLAN_ERRORS, TOOL_FAILURE_RE, Classification, classify
from ragiac.generation.prompts import TARGET_PROVIDER_CONSTRAINT
from ragiac.ingestion.provider_docs import DEFAULT_TAG
from ragiac.validation.opa_validator import check_policies
from ragiac.validation.terraform_validator import terraform_version, validate_terraform

ARMS = ("rag", "baseline", "conventions")


@dataclass(frozen=True)
class Task:
    id: str
    category: str
    difficulty: int
    requirement: str
    intent: dict | None


def load_tasks(path: Path) -> list[Task]:
    tasks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            tasks.append(Task(d["id"], d.get("category", "uncategorised"), d.get("difficulty", 0), d["requirement"], d.get("intent")))
    return tasks


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=20)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _conftest_version(binary: str) -> str | None:
    try:
        out = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=20)
        return out.stdout.strip().splitlines()[0] if out.returncode == 0 and out.stdout.strip() else None
    except (OSError, subprocess.SubprocessError):
        return None


def build_manifest(pipeline, run_id: str, task_file: Path, arms: list[str], n_samples: int, run_plan: bool, label: str) -> dict:
    s = pipeline.settings
    policy_hash = hashlib.sha256(
        b"".join(p.read_bytes() for p in sorted(s.policy_dir.glob("*.rego")))
    ).hexdigest()
    return {
        "run_id": run_id,
        "label": label,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "mode": s.ragiac_mode,
        "generation_model": s.vertex_generation_model,
        "generation_location": s.vertex_generation_location,
        "temperature": s.generation_temperature,
        "embedding_model": s.vertex_embedding_model,
        "chunk_size": s.chunk_size,
        "chunk_overlap": s.chunk_overlap,
        "top_k": s.top_k,
        "max_chunks_per_doc": s.max_chunks_per_doc,
        "index_chunks": len(pipeline.vector_store) if hasattr(pipeline.vector_store, "__len__") else None,
        "provider_docs_tag": DEFAULT_TAG,
        "target_provider_constraint": TARGET_PROVIDER_CONSTRAINT,
        "terraform_version": terraform_version(s),
        "conftest_version": _conftest_version(s.conftest_binary),
        "task_file": str(task_file),
        "task_file_sha256": _sha256(task_file),
        "policy_sha256": policy_hash,
        "arms": arms,
        "samples_per_task": n_samples,
        "terraform_plan_run": run_plan,
        "python": platform.python_version(),
    }


def evaluate_sample(pipeline, task: Task, arm: str, sample_idx: int, run_plan: bool) -> dict:
    record: dict = {
        "task_id": task.id,
        "category": task.category,
        "difficulty": task.difficulty,
        "arm": arm,
        "sample_idx": sample_idx,
        "requirement": task.requirement,
        "hcl": None,
        "retrieved": [],
        "retrieval_hit": None,
        "generation_error": None,
    }

    started = time.monotonic()
    hcl: str | None = None
    try:
        if arm == "rag":
            generation = pipeline.generate_rag_detailed(task.requirement)
            hcl = generation.hcl
            record["retrieved"] = [
                {"doc_id": r.chunk.doc_id, "score": round(r.score, 4), "resource_types": _resource_types(r.chunk.text)}
                for r in generation.retrieved
            ]
            record["retrieval_hit"] = retrieval_hit(
                _expected_resources(task.intent), [t for r in record["retrieved"] for t in r["resource_types"]]
            )
        elif arm == "conventions":
            hcl = pipeline.generate_conventions(task.requirement)
        else:
            hcl = pipeline.generate_baseline(task.requirement)
    except Exception as e:  # noqa: BLE001 - a failed generation is a data point, not a crash
        record["generation_error"] = f"{type(e).__name__}: {str(e)[:300]}"
    record["latency_gen_s"] = round(time.monotonic() - started, 2)
    record["hcl"] = hcl

    terraform_results, policy_result, intent_result = [], None, None
    validation_error: str | None = None
    if hcl and hcl.strip():
        started = time.monotonic()
        try:
            terraform_results = validate_terraform(hcl, pipeline.settings, run_plan=run_plan)
            policy_result = check_policies(hcl, pipeline.settings)
            intent_result = check_intent(hcl, task.intent)
        except FileNotFoundError:
            raise  # a missing terraform/conftest binary invalidates the whole run - don't record it as a sample
        except Exception as e:  # noqa: BLE001 - e.g. a terraform timeout: keep the run alive, record the failure
            validation_error = f"{type(e).__name__}: {str(e)[:300]}"
        record["latency_validate_s"] = round(time.monotonic() - started, 2)
    classification = classify(hcl, terraform_results, policy_result, intent_result, record["generation_error"])
    if not validation_error and "TOOL_FAILURE" in classification.errors:
        validation_error = "terraform tool failure (not a defect in the generated code)"
    record["validation_error"] = validation_error
    if validation_error:
        classification = Classification(
            errors=sorted({*classification.errors, "VALIDATION_TOOL_ERROR"}),
            flags=classification.flags,
            raw_summaries=[*classification.raw_summaries, f"validation: {validation_error}"],
            deprecation_warnings=classification.deprecation_warnings,
        )

    stages = {r.stage: r.passed for r in terraform_results}
    plan_failed = any(r.stage == "plan" and not r.passed for r in terraform_results)
    plan_failed_for_env = (
        plan_failed
        and bool(NON_MODEL_PLAN_ERRORS & set(classification.errors))
        and "PLAN_ERROR" not in classification.errors
    )
    validate_ok = bool(stages.get("init")) and bool(stages.get("validate"))
    plan_ok = None if ("plan" not in stages or plan_failed_for_env) else stages["plan"]
    policy_evaluated = policy_result is not None and getattr(policy_result, "evaluated", True)
    policy_ok = bool(policy_result and policy_result.passed) if policy_evaluated else False
    intent_ok = bool(intent_result and intent_result.passed)

    record.update(
        {
            "terraform_stages": stages,
            "validate_pass": validate_ok,
            "plan_pass": plan_ok,
            "policy_evaluated": bool(policy_evaluated),
            "policy_pass": policy_ok,
            "policy_violations": list(policy_result.violations) if policy_result else [],
            "intent_pass": intent_ok,
            "intent_failures": list(intent_result.failures) if intent_result else [],
            "errors": classification.errors,
            "flags": classification.flags,
            "diagnostics": classification.raw_summaries,
            "deprecation_warnings": classification.deprecation_warnings,
            "overall_pass": bool(validate_ok and plan_ok is not False and policy_ok and intent_ok),
        }
    )
    return record


_RESOURCE_TYPE_RE = re.compile(r"(?<![A-Za-z0-9_])google_[a-z0-9_]+")


def _resource_types(text: str) -> list[str]:
    return sorted(set(_RESOURCE_TYPE_RE.findall(text)))


def _expected_resources(intent: dict | None) -> list:
    """Resource types the task needs; each entry is a type or a list of acceptable alternatives."""
    return list(intent.get("resources", [])) if intent else []


def is_infrastructure_failure(record: dict) -> bool:
    """True when the sample was lost to the environment (API/quota failure, terraform crashing)
    rather than to anything the model wrote; such samples are dropped and re-run by --redo-errors."""
    return bool(
        record.get("generation_error")
        or record.get("validation_error")
        or any(TOOL_FAILURE_RE.search(d) for d in record.get("diagnostics", []))
    )


def read_records(samples_path: Path) -> list[dict]:
    if not samples_path.exists():
        return []
    return [json.loads(line) for line in samples_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_benchmark(
    pipeline,
    tasks: list[Task],
    arms: list[str],
    n_samples: int,
    run_plan: bool,
    run_dir: Path,
    on_record: Callable[[dict, int, int], None] | None = None,
    workers: int = 1,
) -> list[dict]:
    run_dir.mkdir(parents=True, exist_ok=True)
    samples_path = run_dir / "samples.jsonl"
    existing = read_records(samples_path)
    done = {(r["task_id"], r["arm"], r["sample_idx"]) for r in existing}

    plan = [(t, a, i) for i in range(n_samples) for t in tasks for a in arms]
    total = len(plan)
    pending = [(pos, t, a, i) for pos, (t, a, i) in enumerate(plan, start=1) if (t.id, a, i) not in done]
    records = list(existing)
    lock = threading.Lock()

    def work(item) -> None:
        position, task, arm, idx = item
        record = evaluate_sample(pipeline, task, arm, idx, run_plan)
        with lock:
            with samples_path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            records.append(record)
            if on_record:
                on_record(record, position, total)

    if workers <= 1:
        for item in pending:
            work(item)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(work, pending))  # re-raises the first worker exception
    return records
