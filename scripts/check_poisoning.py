#!/usr/bin/env python
"""Corpus poisoning-robustness check, in the spirit of [7] (ImportSnare, arXiv:2509.07941):
plant one adversarial document in a copy of the knowledge base and see whether the RAG arm's
retrieval and generation follow its (malicious) guidance, and whether OPA still catches it if so.

This is a reusable version of the one-off check reported in Section 8.1 of the report, so the
same probe (or a different adversarial document / task set) can be re-run and extended.

Usage:
  py scripts/check_poisoning.py \\
      --kb-dir data/knowledge_base_poison_test --index-cache-dir data/index_poison_test \\
      --marker-doc storage_access_policy_update.md --task-prefix gcs- \\
      --indicator allUsers --indicator us-central1

The poisoned knowledge-base directory must already exist (a copy of data/knowledge_base/ plus the
adversarial document) and be ingested first: this script only runs retrieval/generation/policy
checks over it, it does not build the index.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ragiac.config import Settings, get_settings  # noqa: E402
from ragiac.evaluation.runner import load_tasks  # noqa: E402
from ragiac.pipeline import build_pipeline  # noqa: E402
from ragiac.validation.opa_validator import check_policies  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kb-dir", required=True, help="Poisoned knowledge-base directory (already ingested)")
    parser.add_argument("--index-cache-dir", required=True, help="Vector-store cache dir built from --kb-dir")
    parser.add_argument("--marker-doc", required=True, help="Filename of the planted adversarial document")
    parser.add_argument("--tasks", default="data/eval/gcp_tasks.jsonl")
    parser.add_argument("--task-prefix", help="Only run tasks whose id starts with this prefix (e.g. 'gcs-')")
    parser.add_argument("--only", help="Comma-separated task ids to run, instead of --task-prefix")
    parser.add_argument(
        "--indicator",
        action="append",
        default=[],
        dest="indicators",
        help="Substring that, if present in the generated HCL, counts as having followed the poisoned advice "
        "(repeatable)",
    )
    parser.add_argument("--out", help="Write detailed JSON results to this path")
    args = parser.parse_args()

    base_settings = get_settings()
    settings = Settings(
        **{**base_settings.model_dump(), "knowledge_base_dir": Path(args.kb_dir), "index_cache_dir": Path(args.index_cache_dir)}
    )
    pipeline = build_pipeline(settings)
    if hasattr(pipeline.vector_store, "__len__") and len(pipeline.vector_store) == 0:
        sys.exit(f"The index at {args.index_cache_dir} is empty - ingest {args.kb_dir} first (py scripts/ingest.py).")

    tasks = load_tasks(Path(args.tasks))
    if args.only:
        wanted = {t.strip() for t in args.only.split(",")}
        tasks = [t for t in tasks if t.id in wanted]
    elif args.task_prefix:
        tasks = [t for t in tasks if t.id.startswith(args.task_prefix)]
    if not tasks:
        sys.exit("no tasks selected (--tasks/--task-prefix/--only)")

    results = []
    for task in tasks:
        generation = pipeline.generate_rag_detailed(task.requirement)
        retrieved_docs = sorted({r.chunk.doc_id for r in generation.retrieved})
        poisoned_retrieved = any(args.marker_doc in d for d in retrieved_docs)
        followed = [i for i in args.indicators if i in generation.hcl]
        policy = check_policies(generation.hcl, settings)

        print(f"{'=' * 10} {task.id}")
        print(f"  poisoned doc retrieved: {poisoned_retrieved}  (retrieved: {retrieved_docs})")
        print(f"  followed poisoned advice: {bool(followed)}  (matched: {followed})")
        print(f"  OPA violations: {policy.violations}")
        results.append(
            {
                "task_id": task.id,
                "poisoned_retrieved": poisoned_retrieved,
                "retrieved_docs": retrieved_docs,
                "followed_indicators": followed,
                "opa_violations": policy.violations,
                "hcl": generation.hcl,
            }
        )

    n = len(results)
    retrieved_n = sum(1 for r in results if r["poisoned_retrieved"])
    followed_n = sum(1 for r in results if r["followed_indicators"])
    print(f"\n{retrieved_n}/{n} tasks retrieved the poisoned document; {followed_n}/{n} show a followed indicator.")

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"detailed results written to {args.out}")


if __name__ == "__main__":
    main()
