#!/usr/bin/env python
"""RAG vs. non-RAG baseline benchmark over the GCP task set.

Every sample is written to results/<run_id>/samples.jsonl as it finishes; summary.json/md are
regenerated from those records. Metrics (fixed in advance per the supervisor's remarks):
validate/plan pass rate, OPA policy-violation rate, pass@k — plus functional-intent pass rate,
retrieval hit rate and an error-category breakdown.

Examples:
  py scripts/benchmark.py --samples 5 --k 1,3,5 --plan --workers 4 --label "main run"
  py scripts/benchmark.py --only gcs-01,sql-01 --samples 2          # quick smoke test
  py scripts/benchmark.py --resume 20260920-101500                   # continue an interrupted run
  py scripts/benchmark.py --resume <id> --redo-errors                # re-run samples lost to API/infra failures
  py scripts/benchmark.py --summarize 20260920-101500                # re-summarise stored records
  py scripts/benchmark.py --max-per-doc 0 --label "ablation: no per-doc cap"

Results are only meaningful with RAGIAC_MODE=gcp (the local template generator is not an LLM).
"""

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ragiac.config import get_settings  # noqa: E402
from ragiac.evaluation.runner import (  # noqa: E402
    ARMS,
    build_manifest,
    is_infrastructure_failure,
    load_tasks,
    read_records,
    run_benchmark,
)
from ragiac.evaluation.summary import render_markdown, summarize  # noqa: E402
from ragiac.pipeline import build_pipeline  # noqa: E402


def write_summary(run_dir: Path, ks: list[int]) -> str:
    records = read_records(run_dir / "samples.jsonl")
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    summary = summarize(records, ks)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    markdown = render_markdown(manifest, summary)
    (run_dir / "summary.md").write_text(markdown, encoding="utf-8")
    return markdown


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tasks", default="data/eval/gcp_tasks.jsonl")
    parser.add_argument("--samples", type=int, default=3, help="samples per task per arm (needed for pass@k)")
    parser.add_argument("--k", default="1", help="comma-separated k values for pass@k (each <= --samples)")
    parser.add_argument("--arms", default="rag,baseline", help="comma-separated: rag, baseline, conventions")
    parser.add_argument("--only", help="comma-separated task ids to run")
    parser.add_argument("--limit", type=int, help="run only the first N tasks")
    parser.add_argument("--workers", type=int, default=1, help="parallel samples (generation and validation are I/O-bound; 3-4 is reasonable)")
    parser.add_argument("--plan", action="store_true", help="also run terraform plan (uses ADC + the configured project; never applies)")
    parser.add_argument("--temperature", type=float, help="override GENERATION_TEMPERATURE")
    parser.add_argument("--top-k", type=int, help="override TOP_K (retrieval ablation)")
    parser.add_argument("--max-per-doc", type=int, help="override MAX_CHUNKS_PER_DOC; 0 disables the cap (retrieval ablation)")
    parser.add_argument("--label", default="", help="free-text label stored in the manifest")
    parser.add_argument("--run-id")
    parser.add_argument("--resume", metavar="RUN_ID")
    parser.add_argument(
        "--redo-errors",
        action="store_true",
        help="with --resume: drop samples whose generation or validation *infrastructure* failed "
        "(e.g. the machine slept, quota exhausted) and re-run them. Do this only after the run has finished.",
    )
    parser.add_argument("--summarize", metavar="RUN_ID", help="re-summarise an existing run and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    settings = get_settings()
    ks = [int(k) for k in args.k.split(",")]

    if args.summarize:
        print(write_summary(settings.results_dir / args.summarize, ks))
        return

    if not settings.is_gcp_mode:
        print("WARNING: RAGIAC_MODE is not 'gcp' - results come from the local template generator and are NOT valid benchmark data.\n")
    for binary in (settings.terraform_binary, settings.conftest_binary):
        if shutil.which(binary) is None:
            sys.exit(f"'{binary}' not found on PATH - required for validation.")
    if max(ks) > args.samples:
        sys.exit(f"--k {max(ks)} exceeds --samples {args.samples}; pass@k needs at least k samples per task.")

    if args.temperature is not None:
        settings.generation_temperature = args.temperature
    if args.top_k is not None:
        settings.top_k = args.top_k
    if args.max_per_doc is not None:
        settings.max_chunks_per_doc = args.max_per_doc

    arms = [a.strip() for a in args.arms.split(",")]
    unknown = set(arms) - set(ARMS)
    if unknown:
        sys.exit(f"unknown arm(s): {sorted(unknown)}; choose from {ARMS}")

    task_file = Path(args.tasks)
    tasks = load_tasks(task_file)
    if args.only:
        wanted = {t.strip() for t in args.only.split(",")}
        tasks = [t for t in tasks if t.id in wanted]
    if args.limit:
        tasks = tasks[: args.limit]
    if not tasks:
        sys.exit("no tasks selected")

    run_id = args.resume or args.run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = settings.results_dir / run_id
    pipeline = build_pipeline(settings)

    if "rag" in arms and hasattr(pipeline.vector_store, "__len__") and len(pipeline.vector_store) == 0:
        sys.exit("The vector index is empty - run `py scripts/ingest.py` first.")

    if args.redo_errors:
        if not args.resume:
            sys.exit("--redo-errors requires --resume RUN_ID")
        samples_path = run_dir / "samples.jsonl"
        records = read_records(samples_path)
        keep = [r for r in records if not is_infrastructure_failure(r)]
        dropped = len(records) - len(keep)
        if dropped:
            backup = run_dir / "samples.before-redo.jsonl"
            backup.write_text(samples_path.read_text(encoding="utf-8"), encoding="utf-8")
            samples_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep), encoding="utf-8")
        print(f"--redo-errors: dropped {dropped} infrastructure-failed sample(s) for re-run (backup kept)")

    manifest_path = run_dir / "manifest.json"
    if args.resume and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        added = [a for a in arms if a not in manifest.get("arms", [])]
        if added:  # an arm added to an existing run (e.g. the control arm) - record when it was run
            manifest["arms"] = [*manifest.get("arms", []), *added]
            manifest.setdefault("arms_added_later", {}).update({a: datetime.now().isoformat() for a in added})
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if not (args.resume and manifest_path.exists()):
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest = build_manifest(pipeline, run_id, task_file, arms, args.samples, args.plan, args.label)
        manifest["tasks_selected"] = [t.id for t in tasks]
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"run {run_id}: {len(tasks)} tasks x {len(arms)} arms x {args.samples} samples = {len(tasks) * len(arms) * args.samples} evaluations")
    print(f"model={settings.vertex_generation_model} temperature={settings.generation_temperature} top_k={settings.top_k} "
          f"max_per_doc={settings.max_chunks_per_doc} plan={args.plan} workers={args.workers}\n")

    def progress(record: dict, position: int, total: int) -> None:
        status = "PASS" if record["overall_pass"] else "fail"
        errors = ",".join(record["errors"]) or "-"
        print(f"[{position:>4}/{total}] {record['task_id']:<8} {record['arm']:<8} #{record['sample_idx']} {status}  {errors}", flush=True)

    run_benchmark(pipeline, tasks, arms, args.samples, args.plan, run_dir, on_record=progress, workers=args.workers)
    print("\n" + write_summary(run_dir, ks))
    print(f"records + summary written to {run_dir}")


if __name__ == "__main__":
    main()
