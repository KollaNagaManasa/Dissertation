#!/usr/bin/env python
"""RAG vs. non-RAG baseline benchmark over a fixed prompt set.

Reports the metrics named in the outline's supervisor remarks: terraform
validate/plan pass rate and OPA policy-violation rate, for each arm.

Usage: py scripts/benchmark.py --prompts data/eval/prompts.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ragiac.pipeline import Pipeline, build_pipeline  # noqa: E402


def run_arm(pipeline: Pipeline, prompts: list[dict], use_baseline: bool, run_plan: bool) -> dict:
    n = len(prompts)
    terraform_passes = 0
    policy_passes = 0
    policy_checked = 0

    for item in prompts:
        requirement = item["requirement"]
        hcl = pipeline.generate_baseline(requirement) if use_baseline else pipeline.generate_rag(requirement)
        try:
            report = pipeline.validate(hcl, run_plan=run_plan, check_opa=True)
        except FileNotFoundError as e:
            print(f"[{item.get('id', '?')}] validation skipped: {e}")
            continue

        if report.terraform_passed:
            terraform_passes += 1
        if report.policy_result is not None:
            policy_checked += 1
            if report.policy_passed:
                policy_passes += 1

    return {
        "n": n,
        "terraform_pass_rate": terraform_passes / n if n else 0.0,
        "opa_pass_rate": (policy_passes / policy_checked) if policy_checked else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", default="data/eval/prompts.jsonl")
    parser.add_argument("--no-plan", action="store_true", help="Skip terraform plan (validate only)")
    args = parser.parse_args()

    prompts_path = Path(args.prompts)
    prompts = [json.loads(line) for line in prompts_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    pipeline = build_pipeline()
    run_plan = not args.no_plan

    print(f"Benchmarking {len(prompts)} prompts (mode={pipeline.settings.ragiac_mode})...\n")

    rag_metrics = run_arm(pipeline, prompts, use_baseline=False, run_plan=run_plan)
    baseline_metrics = run_arm(pipeline, prompts, use_baseline=True, run_plan=run_plan)

    print("RAG:     ", rag_metrics)
    print("Baseline:", baseline_metrics)


if __name__ == "__main__":
    main()
