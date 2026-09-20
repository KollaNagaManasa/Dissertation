"""Builds the mid-semester report (.docx) from the repository and a stored benchmark run.

Usage: py report/build_report.py [run_id] [output.docx]
Numbers and tables in Section 6 are computed from results/<run_id>/; the interpretive text is in
report/commentary.py. Run report/make_figures.py first to refresh the charts.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

from docx_helpers import Report  # noqa: E402
import results_section  # noqa: E402
import sections_a  # noqa: E402
import sections_b  # noqa: E402
import sections_c  # noqa: E402


def load_run(run_id: str):
    run_dir = ROOT / "results" / run_id
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8")) if (run_dir / "summary.json").exists() else None
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8")) if (run_dir / "manifest.json").exists() else None
    samples = run_dir / "samples.jsonl"
    records = [json.loads(line) for line in samples.read_text(encoding="utf-8").splitlines() if line.strip()] if samples.exists() else []
    return summary, manifest, records


EXTRA_RUNS = ("abl-topk3", "abl-nocap", "lowtemp")


def load_extra() -> dict:
    """Summaries of the follow-up runs (retrieval ablations, near-greedy run), if they exist."""
    out = {}
    for rid in EXTRA_RUNS:
        path = ROOT / "results" / rid / "summary.json"
        if path.exists():
            out[rid] = json.loads(path.read_text(encoding="utf-8"))
    return out


def build(run_id: str, out_path: Path) -> Path:
    summary, manifest, records = load_run(run_id)
    extra = load_extra()
    R = Report()

    R.title_page(
        [
            ("BIRLA INSTITUTE OF TECHNOLOGY & SCIENCE, PILANI", 14, True, 2),
            ("WORK INTEGRATED LEARNING PROGRAMMES (WILP) DIVISION", 11, True, 2),
            ("Second Semester of Academic Year 2026-2027", 11, False, 26),
            ("SEZG628T : Dissertation / Project / Project Work", 12, True, 4),
            ("MID-SEMESTER REPORT", 12, True, 30),
            ("RAG-Powered Assistant for Infrastructure as Code Generation", 22, True, 34),
            ("Student Name: KOLLA NAGA MANASA", 12, True, 4),
            ("BITS ID: 2024TM93519", 12, True, 4),
            ("Degree Program: M.Tech (Software Engineering)", 12, False, 4),
            ("Research Area: Artificial Intelligence", 12, False, 24),
            ("Dissertation carried out at", 11, False, 2),
            ("Caprus IT Private Limited, Hyderabad", 12, True, 22),
            ("Supervisor: Karthik Reddy Charla, Technical Manager, Caprus IT Private Limited", 11, False, 3),
            ("Additional Examiner: Devoleena Das, Accenture Private Limited", 11, False, 30),
            ("September 2026", 11, False, 0),
        ]
    )
    R.footer_page_numbers()
    results_section.abstract(R, summary, manifest)  # abstract + sign-off page precede the contents, as in the BITS format
    R.contents()
    sections_a.introduction(R)
    sections_a.literature(R)
    sections_b.design(R)
    sections_b.implementation(R)
    sections_c.methodology(R)
    results_section.results(R, summary, manifest, records, extra)
    results_section.discussion(R, summary, manifest)
    sections_c.remaining_work(R)
    results_section.conclusion(R)
    sections_c.references(R)
    sections_c.abbreviations(R)
    sections_c.appendices(R, manifest)
    R.update_fields_on_open()
    R.save(out_path)
    return out_path


if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else "main-01"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Mid_Semester_Report.docx"
    print("wrote", build(run, out))
