"""Builds the final dissertation report (.docx) in the WILP project-report layout.

Usage: py report/build_final_report.py [run_id] [output.docx]
Layout per the WILP "Guidelines for the preparation of a project report": 9 x 11 inch pages, 1 inch
margins, double spacing; cover and title page unnumbered, the matter before the Introduction numbered
in small Roman numerals and the rest in Arabic numerals. Chapters follow the structure the mid-semester
review asked for. Run report/make_figures.py <run_id> first to draw the result charts, and
report/export_pdf.ps1 afterwards to produce the PDF with every field updated.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import final_front_matter as F  # noqa: E402
import final_results  # noqa: E402
import final_sections  # noqa: E402
import sections_a  # noqa: E402
import sections_b  # noqa: E402
import sections_c  # noqa: E402
from docx_helpers import Report  # noqa: E402


def build(run_id: str, out_path: Path) -> Path:
    _, manifest, _ = final_results.load_run(run_id)
    R = Report(page="wilp", line_spacing=2.0, chapter_headings=True)

    R.number_first_section(None)
    F.cover(R)
    F.title_page(R)

    R.start_section("lowerRoman")
    F.acknowledgements(R)
    F.abstract_sheet(R, final_sections.ABSTRACT)
    R.contents("Table of Contents")

    R.start_section("decimal")
    final_sections.introduction(R)
    sections_a.literature(R, final=True)
    final_sections.problem_statement(R)

    R.h1("4. Methodology Used")
    R.p(
        "This chapter covers the system design and the reasons for each technology choice (4.1), the "
        "implementation and the engineering problems found and fixed along the way (4.2), and the evaluation "
        "methodology (4.3)."
    )
    sections_b.design(R, final=True)
    sections_b.implementation(R)
    final_sections.methodology(R)

    final_results.results(R, run_id)
    final_sections.conclusion(R)

    sections_c.appendices(R, manifest, final=True)
    sections_c.references(R)
    F.glossary(R)
    sections_c.abbreviations(R)
    R.update_fields_on_open()
    R.save(out_path)
    return out_path


if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else "final-01"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Final_Report.docx"
    print("wrote", build(run, out))
