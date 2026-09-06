#!/usr/bin/env python
"""Natural-language requirement -> generated Terraform, then validated.

Usage: py scripts/ask.py "A GCS bucket for invoice PDFs, versioned, 30 day Nearline lifecycle rule"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ragiac.pipeline import build_pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirement", help="Natural-language infrastructure requirement")
    parser.add_argument("--baseline", action="store_true", help="Use the non-RAG baseline instead")
    parser.add_argument("--no-validate", action="store_true", help="Skip terraform/OPA validation")
    parser.add_argument("--no-plan", action="store_true", help="Run terraform validate but skip plan")
    args = parser.parse_args()

    pipeline = build_pipeline()
    hcl = pipeline.generate_baseline(args.requirement) if args.baseline else pipeline.generate_rag(args.requirement)

    print("=" * 80)
    print(hcl)
    print("=" * 80)

    if args.no_validate:
        return

    try:
        report = pipeline.validate(hcl, run_plan=not args.no_plan)
        print(report.summary())
    except FileNotFoundError as e:
        print(f"[validation skipped] {e}")


if __name__ == "__main__":
    main()
