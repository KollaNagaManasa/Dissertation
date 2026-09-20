#!/usr/bin/env python
"""Downloads public google-provider docs into data/knowledge_base/provider_docs/.

Usage: py scripts/fetch_provider_docs.py [--tag v8.3.0]
Then re-run: py scripts/ingest.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ragiac.ingestion.provider_docs import DEFAULT_TAG, fetch_all  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=DEFAULT_TAG, help="terraform-provider-google release tag")
    parser.add_argument("--out", default="data/knowledge_base/provider_docs")
    args = parser.parse_args()

    results = fetch_all(Path(args.out), args.tag)
    for r in results:
        print(f"{'ok     ' if r.ok else 'MISSING'} {r.name} {r.detail}")
    ok = sum(r.ok for r in results)
    print(f"\n{ok}/{len(results)} pages written to {args.out} (tag {args.tag})")
    if ok < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
