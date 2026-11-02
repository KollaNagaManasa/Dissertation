"""Builds the mid-semester review presentation (.pptx).

Usage: py report/build_slides.py [output.pptx]      (needs `pip install python-pptx`)

Content mirrors report/sections_*.py and report/commentary.py; every number is taken from the
stored benchmark runs under results/ (main-01, abl-topk3, abl-nocap, lowtemp). Keep the two in
step: if the report text changes, change the matching slide here.
"""

import sys
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- palette ---
# Deep navy dominates; teal is the system's colour, amber the control arm,
# brick a failure, slate anything neutral. Mint is fill-only (too light for text).
NAVY = "111A3A"
NAVY2 = "1D2A52"
INK = "16203C"
TEAL = "027A8A"
TEAL_D = "015C68"
MINT = "06B894"
AMBER = "D9933B"
AMBER_D = "A06A18"
BRICK = "BC4B4B"
SLATE = "626E85"
SLATE_L = "93A0B4"
MIST = "F1F5F9"
MIST2 = "DFE7EF"
WHITE = "FFFFFF"

HEAD = "Cambria"
BODY = "Calibri"

W, H = 13.333, 7.5
M = 0.7                 # side margin
CW = W - 2 * M          # content width, 11.933
TITLE_Y = 0.40
TOP = 1.34              # first line of content
BOT = 6.78              # content must end here; footer sits below
FOOTER = "RAG-Powered Assistant for Infrastructure as Code Generation  ·  Mid-Semester Review"

NO_GRID = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"


# ---------------------------------------------------------------- helpers ---
def _rgb(h):
    return RGBColor.from_string(h)


def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def para(tf, text="", size=14, bold=False, color=INK, font=BODY, align=None, italic=False,
         before=0, after=0, line=None, first=False, runs=None):
    """One paragraph. Runs are (text, overrides) pairs when a line needs mixed styling."""
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    if align is not None:
        p.alignment = align
    if line is not None:
        p.line_spacing = line
    p.space_before = Pt(before)
    p.space_after = Pt(after)
    for t, o in (runs if runs is not None else [(text, {})]):
        r = p.add_run()
        r.text = t
        f = r.font
        f.size = Pt(o.get("size", size))
        f.bold = o.get("bold", bold)
        f.italic = o.get("italic", italic)
        f.name = o.get("font", font)
        f.color.rgb = _rgb(o.get("color", color))
    return p


def bullet(p, char="•", color=SLATE, indent=0.20):
    """Real DrawingML bullet, so PowerPoint keeps the hanging indent."""
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(Emu(Inches(indent))))
    pPr.set("indent", str(-Emu(Inches(indent))))
    pPr.append(parse_xml('<a:buClr %s><a:srgbClr val="%s"/></a:buClr>' % (nsdecls("a"), color)))
    pPr.append(parse_xml('<a:buFont %s typeface="Arial"/>' % nsdecls("a")))
    pPr.append(parse_xml('<a:buChar %s char="%s"/>' % (nsdecls("a"), char)))
    return p


def shape(slide, kind, x, y, w, h, fill=None, line=None, radius=None, lw=1.0):
    shp = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = _rgb(fill)
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = _rgb(line)
        shp.line.width = Pt(lw)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    if radius is not None:
        shp.adjustments[0] = radius
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return shp


def card(slide, x, y, w, h, fill=MIST, line=None, radius=0.06):
    return shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=fill, line=line, radius=radius)


def chip(slide, x, y, w, h, text, fill, color=WHITE, size=10, bold=True):
    shp = shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=fill, radius=0.5)
    tf = shp.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(tf, text, size=size, bold=bold, color=color, align=PP_ALIGN.CENTER, first=True)
    return shp


def disc(slide, x, y, d, text, fill=TEAL, color=WHITE, size=15):
    shp = shape(slide, MSO_SHAPE.OVAL, x, y, d, d, fill=fill)
    tf = shp.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(tf, text, size=size, bold=True, color=color, font=HEAD, align=PP_ALIGN.CENTER, first=True)
    return shp


def arrow(slide, x, y, w=0.30, h=0.20, color=SLATE_L):
    return shape(slide, MSO_SHAPE.RIGHT_ARROW, x, y, w, h, fill=color)


# ------------------------------------------------------------ slide kinds ---
def _blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _bg(slide, prs, color):
    shp = shape(slide, MSO_SHAPE.RECTANGLE, 0, 0, W, H, fill=color)
    slide.shapes._spTree.remove(shp._element)
    slide.shapes._spTree.insert(2, shp._element)
    return shp


def content_slide(prs, title, number):
    """Light slide; title always at the same place, footer and slide number below."""
    slide = _blank(prs)
    tf = textbox(slide, M, TITLE_Y, CW, 0.78)
    para(tf, title, size=36, bold=True, color=INK, font=HEAD, first=True)
    f = textbox(slide, M, 6.97, CW - 1.0, 0.3)
    para(f, FOOTER, size=9, color=SLATE_L, first=True)
    n = textbox(slide, W - M - 0.8, 6.97, 0.8, 0.3)
    para(n, str(number), size=9, color=SLATE_L, align=PP_ALIGN.RIGHT, first=True)
    return slide


def divider_slide(prs, num, title, blurb):
    slide = _blank(prs)
    _bg(slide, prs, NAVY)
    disc(slide, M, 2.62, 0.95, num, fill=TEAL, size=30)
    tf = textbox(slide, M + 1.35, 2.52, 9.4, 1.3)
    para(tf, title, size=42, bold=True, color=WHITE, font=HEAD, first=True)
    para(tf, blurb, size=15, color=SLATE_L, before=8)
    return slide


# ------------------------------------------------------------------ table ---
def table(slide, x, y, w, col_w, headers, rows, head_h=0.46, row_h=0.42,
          size=11, head_size=11, align_centre=()):
    n_rows = len(rows) + 1
    shp = slide.shapes.add_table(n_rows, len(headers), Inches(x), Inches(y),
                                 Inches(w), Inches(head_h + row_h * len(rows)))
    tbl = shp.table
    tblPr = tbl._tbl.tblPr
    for e in tblPr.findall(qn("a:tableStyleId")):
        tblPr.remove(e)
    tblPr.append(parse_xml("<a:tableStyleId %s>%s</a:tableStyleId>" % (nsdecls("a"), NO_GRID)))
    tbl.first_row = False
    tbl.horz_banding = False
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    tbl.rows[0].height = Inches(head_h)
    for i in range(1, n_rows):
        tbl.rows[i].height = Inches(row_h)

    def fill_cell(cell, content, bold, colour, fsize, bg, centre):
        cell.fill.solid()
        cell.fill.fore_color.rgb = _rgb(bg)
        cell.margin_left = cell.margin_right = Inches(0.12)
        cell.margin_top = cell.margin_bottom = Inches(0.07)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.word_wrap = True
        al = PP_ALIGN.CENTER if centre else PP_ALIGN.LEFT
        if isinstance(content, list):
            para(tf, size=fsize, color=colour, align=al, line=1.0, first=True, runs=content)
        else:
            para(tf, content, size=fsize, bold=bold, color=colour, align=al, line=1.0, first=True)

    for c, head in enumerate(headers):
        fill_cell(tbl.cell(0, c), head, True, WHITE, head_size, INK, c in align_centre)
    for r, row in enumerate(rows, start=1):
        bg = WHITE if r % 2 else MIST
        for c, val in enumerate(row):
            fill_cell(tbl.cell(r, c), val, False, INK, size, bg, c in align_centre)
    return tbl


# ------------------------------------------------------------------ chart ---
def _style_axes(ch, maxv, vfmt='0"%"'):
    ch.font.size = Pt(11)
    ch.font.name = BODY
    ch.font.color.rgb = _rgb(SLATE)
    va = ch.value_axis
    va.minimum_scale = 0
    if maxv is not None:
        va.maximum_scale = maxv
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = _rgb(MIST2)
    va.major_gridlines.format.line.width = Pt(0.75)
    va.tick_labels.font.size = Pt(10)
    va.tick_labels.font.name = BODY
    va.tick_labels.font.color.rgb = _rgb(SLATE)
    va.tick_labels.number_format = vfmt
    va.tick_labels.number_format_is_linked = False
    va.format.line.fill.background()
    ca = ch.category_axis
    ca.has_major_gridlines = False
    ca.tick_labels.font.size = Pt(11)
    ca.tick_labels.font.name = BODY
    ca.tick_labels.font.color.rgb = _rgb(INK)
    ca.format.line.color.rgb = _rgb(MIST2)
    ca.format.line.width = Pt(0.75)


def bar_chart(slide, x, y, w, h, categories, series, colors, kind="col", maxv=100,
              fmt='0.0"%"', vfmt='0"%"', inside=False, gap=70, overlap=-18, legend=True,
              label_size=10, label_color=INK):
    cd = CategoryChartData()
    cd.categories = categories
    for name, vals in series:
        cd.add_series(name, vals, number_format=fmt)
    ctype = XL_CHART_TYPE.COLUMN_CLUSTERED if kind == "col" else XL_CHART_TYPE.BAR_CLUSTERED
    ch = slide.shapes.add_chart(ctype, Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    ch.has_title = False
    ch.has_legend = legend and len(series) > 1
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.TOP
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(11)
        ch.legend.font.name = BODY
        ch.legend.font.color.rgb = _rgb(INK)
    plot = ch.plots[0]
    plot.gap_width = gap
    plot.overlap = overlap
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = fmt
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.INSIDE_END if inside else XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(label_size)
    dl.font.bold = True
    dl.font.name = BODY
    dl.font.color.rgb = _rgb(label_color)
    for s, c in zip(ch.series, colors):
        s.format.fill.solid()
        s.format.fill.fore_color.rgb = _rgb(c)
        s.format.line.fill.background()
    _style_axes(ch, maxv, vfmt)
    return ch


# =================================================================== deck ===
def build(out_path: Path) -> Path:
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    prs.core_properties.title = "RAG-Powered Assistant for Infrastructure as Code Generation"
    prs.core_properties.author = "Kolla Naga Manasa (2024TM93519)"
    prs.core_properties.subject = "BITS SEZG628T Dissertation - Mid-Semester Review"

    cover(prs)
    agenda(prs, 2)
    divider_slide(prs, "1", "Introduction", "The problem, the objectives and the questions this dissertation asks")
    why_hard(prs, 4)
    problem_and_rqs(prs, 5)
    objectives(prs, 6)
    divider_slide(prs, "2", "Literature Review", "What is already established, and the gap this work addresses")
    literature(prs, 8)
    gap(prs, 9)
    divider_slide(prs, "3", "Research Methodology", "Architecture, technology decisions, experimental arms and metrics")
    architecture(prs, 11)
    tech_choices(prs, 12)
    arms(prs, 13)
    validation(prs, 14)
    divider_slide(prs, "4", "Data Collection", "The knowledge base, the benchmark task set and what every run records")
    knowledge_base(prs, 16)
    task_set(prs, 17)
    divider_slide(prs, "5", "Results So Far", "First full benchmark: 35 tasks, three arms, five samples per task")
    headline(prs, 19)
    failures(prs, 20)
    central_finding(prs, 21)
    robustness(prs, 22)
    feedback(prs, 23)
    plan(prs, 24)
    conclusion(prs)
    closing(prs)

    prs.save(str(out_path))
    return out_path


# ------------------------------------------------------------------ 1 cover
def cover(prs):
    slide = _blank(prs)
    _bg(slide, prs, NAVY)
    logo = HERE / "assets" / "bits_logo.png"
    if logo.exists():
        card(slide, M, 0.72, 1.02, 1.02, fill=WHITE, radius=0.10)
        slide.shapes.add_picture(str(logo), Inches(M + 0.09), Inches(0.81), Inches(0.84), Inches(0.82))

    tf = textbox(slide, M, 2.22, 11.4, 2.1)
    para(tf, "RAG-Powered Assistant for", size=46, bold=True, color=WHITE, font=HEAD, line=1.05, first=True)
    para(tf, "Infrastructure as Code Generation", size=46, bold=True, color=WHITE, font=HEAD, line=1.05)

    tf = textbox(slide, M, 4.32, 11.4, 0.4)
    para(tf, "Mid-Semester Dissertation Review  ·  BITS SEZG628T", size=17, color=MINT, first=True)

    meta = [
        ("Student", "Kolla Naga Manasa  ·  2024TM93519  ·  M.Tech (Software Engineering)"),
        ("Supervisor", "Karthik Reddy Charla  ·  Caprus IT Private Limited, Hyderabad"),
        ("Submitted", "October 2026"),
    ]
    y = 5.18
    for label, value in meta:
        t = textbox(slide, M, y, 1.5, 0.3)
        para(t, label, size=11, bold=True, color=SLATE_L, first=True)
        t = textbox(slide, M + 1.55, y, 9.8, 0.3)
        para(t, value, size=13, color=WHITE, first=True)
        y += 0.46


# ----------------------------------------------------------------- 2 agenda
def agenda(prs, n):
    slide = content_slide(prs, "What this review covers", n)
    items = [
        ("1", "Introduction", "Why IaC generation is hard, the problem statement, objectives and research questions"),
        ("2", "Literature Review", "What is established about LLM-generated IaC, and the gap this work addresses"),
        ("3", "Research Methodology", "Architecture, settled technology choices, three experimental arms, metrics fixed in advance"),
        ("4", "Data Collection", "Knowledge base, the 35-task GCP benchmark, and what every run records"),
        ("5", "Results So Far", "First full benchmark across three arms, plus ablations and a near-greedy run"),
        ("6", "Feedback and Plan", "Supervisor remarks and actions taken, remaining work and the schedule"),
    ]
    cw, gap = 3.73, 0.36
    for i, (num, title, body) in enumerate(items):
        col, row = i % 3, i // 3
        x = M + col * (cw + gap)
        y = TOP + 0.20 + row * (2.26 + 0.34)
        card(slide, x, y, cw, 2.26, fill=MIST, radius=0.05)
        disc(slide, x + 0.28, y + 0.28, 0.5, num, fill=TEAL, size=15)
        tf = textbox(slide, x + 0.28, y + 0.92, cw - 0.56, 0.4)
        para(tf, title, size=17, bold=True, color=INK, font=HEAD, first=True)
        tf = textbox(slide, x + 0.28, y + 1.36, cw - 0.56, 0.78)
        para(tf, body, size=11.5, color=SLATE, line=1.15, first=True)


# ------------------------------------------------------------- 4 why it is hard
def why_hard(prs, n):
    slide = content_slide(prs, "Why generating IaC is hard", n)
    rows = [
        ("1", "The schema is large and it moves",
         "The google provider was at major version 8 while this work was done. Arguments are renamed, "
         "removed and newly required between releases, and resources depend on one another in ways the "
         "documentation describes only indirectly."),
        ("2", "The model's knowledge is frozen",
         "An LLM produces arguments that have since been renamed or removed, omits arguments that have "
         "become required, and cannot know a release published after its training cut-off."),
        ("3", "Organisational policy is never in the request",
         "Mandatory labels, private-by-default, backups, deletion protection and the default region are "
         "assumed by the organisation and absent from the sentence a developer types."),
    ]
    y = TOP + 0.10
    for num, head, body in rows:
        disc(slide, M, y - 0.02, 0.50, num, fill=TEAL, size=15)
        tf = textbox(slide, M + 0.74, y, 7.3, 0.36)
        para(tf, head, size=17, bold=True, color=INK, font=HEAD, first=True)
        tf = textbox(slide, M + 0.74, y + 0.40, 7.3, 0.92)
        para(tf, body, size=12.5, color=SLATE, line=1.18, first=True)
        y += 1.62

    x = M + 8.42
    card(slide, x, TOP + 0.10, 3.51, 2.34, fill=NAVY, radius=0.05)
    tf = textbox(slide, x + 0.30, TOP + 0.38, 2.91, 1.8)
    para(tf, "Plausible is not correct", size=19, bold=True, color=WHITE, font=HEAD, first=True)
    para(tf, "A configuration can be syntactically valid, pass terraform plan, and still be wrong for "
             "the organisation that has to run it.", size=12.5, color=SLATE_L, line=1.2, before=10)

    card(slide, x, TOP + 2.64, 3.51, 2.34, fill=MIST, radius=0.05)
    tf = textbox(slide, x + 0.30, TOP + 2.92, 2.91, 1.8)
    para(tf, "Why it matters here", size=13, bold=True, color=TEAL_D, first=True)
    para(tf, "Caprus IT provisions delivery work largely through Terraform. Misconfiguration and the "
             "slow onboarding of new engineers both cost time.", size=12, color=SLATE, line=1.2, before=6)


# --------------------------------------------------- 5 problem statement + RQs
def problem_and_rqs(prs, n):
    slide = content_slide(prs, "Problem statement and research questions", n)
    card(slide, M, TOP, CW, 1.62, fill=NAVY, radius=0.045)
    tf = textbox(slide, M + 0.36, TOP + 0.24, CW - 0.72, 1.16)
    para(tf, "Given a natural-language infrastructure requirement, generate Terraform for Google Cloud that is "
             "well-formed and consistent with the provider schema, actually implements what was asked, and "
             "complies with organisational policy.", size=16, color=WHITE, line=1.22, first=True)
    para(tf, runs=[("Central question:  ", {"bold": True, "color": MINT, "size": 13}),
                   ("does retrieval over provider documentation and organisational conventions improve these "
                    "outcomes compared with the same model used without retrieval — and where it does not, "
                    "what kinds of errors remain?", {"color": SLATE_L, "size": 13})],
         line=1.2, before=8)

    rqs = [
        ("RQ1", "Technical correctness", "Does retrieval increase the share of configurations that validate, plan and satisfy the stated intent?", TEAL),
        ("RQ2", "Organisational policy", "Does retrieval increase policy conformance — and is any gain due to retrieval, or just to the conventions being available?", AMBER_D),
        ("RQ3", "Error distribution", "Which error categories dominate, and how does retrieval change their distribution?", BRICK),
        ("RQ4", "Retrieval quality", "How often does retrieval surface documentation for the resources a task needs, and is that linked to success?", SLATE),
    ]
    cw, gap = 2.81, 0.35
    y = TOP + 1.94
    for i, (tag, head, body, colour) in enumerate(rqs):
        x = M + i * (cw + gap)
        card(slide, x, y, cw, 2.56, fill=MIST, radius=0.05)
        chip(slide, x + 0.26, y + 0.26, 0.74, 0.3, tag, fill=colour, size=11)
        tf = textbox(slide, x + 0.26, y + 0.70, cw - 0.52, 0.66)
        para(tf, head, size=15.5, bold=True, color=INK, font=HEAD, line=1.1, first=True)
        tf = textbox(slide, x + 0.26, y + 1.26, cw - 0.52, 1.12)
        para(tf, body, size=11.5, color=SLATE, line=1.18, first=True)


# ----------------------------------------------------------- 6 objectives
def objectives(prs, n):
    slide = content_slide(prs, "Objectives and status at mid-semester", n)
    rows = [
        ("O1", "Study the state of the art in LLM code generation and RAG for IaC",
         [("DONE  ", {"bold": True, "color": TEAL_D}), ("for this report; continues to the final report", {"color": SLATE})]),
        ("O2", "Identify common LLM error categories and the knowledge gaps retrieval must close",
         [("DONE  ", {"bold": True, "color": TEAL_D}), ("taxonomy implemented and applied to every benchmark sample", {"color": SLATE})]),
        ("O3", "Design a RAG architecture: ingestion, chunking, embedding, vector store, retrieval, generation",
         [("DONE  ", {"bold": True, "color": TEAL_D}), ("design and rationale recorded per decision", {"color": SLATE})]),
        ("O4", "Build a working prototype that generates IaC from natural-language prompts",
         [("DONE  ", {"bold": True, "color": TEAL_D}), ("runs end to end on real Google Cloud services; 105 automated tests", {"color": SLATE})]),
        ("O5", "Validate output with automated tooling and benchmark against a non-RAG baseline",
         [("DONE  ", {"bold": True, "color": TEAL_D}), ("plus a control arm, two retrieval ablations and a near-greedy run. ", {"color": SLATE}),
          ("Chunk size ablation pending", {"color": AMBER_D, "bold": True})]),
        ("O6", "User evaluation of usability and developer trust",
         [("PROPOSED  ", {"bold": True, "color": AMBER_D}), ("design complete and awaiting approval; to run in Phase 6", {"color": SLATE})]),
    ]
    table(slide, M, TOP + 0.08, CW, [0.78, 5.5, 5.655],
          ["#", "Objective (from the approved outline)", "Status"],
          rows, head_h=0.46, row_h=0.72, size=12, head_size=12, align_centre=(0,))
    tf = textbox(slide, M, 6.26, CW, 0.4)
    para(tf, "Five of the six objectives are complete and the sixth is designed. The work is a phase ahead of the "
             "approved schedule.", size=12, italic=True, color=SLATE, first=True)


# ----------------------------------------------------------- 8 literature
def literature(prs, n):
    slide = content_slide(prs, "What the literature establishes", n)
    cards = [
        ("[1]", "Lewis et al., NeurIPS 2020",
         "RAG pairs a generator's parametric memory with a dense document index queried at inference time. "
         "The knowledge source updates without retraining, and output gains traceable provenance.",
         "Provider schemas change every few weeks — retraining is not an option.", TEAL),
        ("[2]", "IaC-Eval, NeurIPS 2024",
         "458 human-curated Terraform scenarios, scored against explicit intent specifications rather than "
         "syntax alone. Released tooling targets AWS.",
         "The model for the machine-checkable intent specs used here.", TEAL),
        ("[3]", "Nekrasov et al., 2025",
         "Error taxonomy for LLM-generated Terraform plus knowledge injection: overall success rises from "
         "27.1% to 62.6% (technical validation 75.3%).",
         "Names a “Correctness–Congruence Gap”: proficient coders, limited architects.", AMBER_D),
        ("[4]", "Jouini, 2026",
         "Verifier-first evaluation over 186 tasks using validate, plan and OPA. Active retrieval lifted one "
         "small model from 14.0% to 45.7% pass@1.",
         "79% of residual OPA failures were information gaps — so put policy where the model can see it.", AMBER_D),
    ]
    cw, gap = 5.79, 0.355
    for i, (tag, head, body, note, colour) in enumerate(cards):
        x = M + (i % 2) * (cw + gap)
        y = TOP + 0.04 + (i // 2) * (1.86 + 0.18)
        card(slide, x, y, cw, 1.86, fill=MIST, radius=0.05)
        tf = textbox(slide, x + 0.28, y + 0.22, 0.5, 0.28)
        para(tf, tag, size=12, bold=True, color=colour, first=True)
        tf = textbox(slide, x + 0.80, y + 0.20, cw - 1.08, 0.3)
        para(tf, head, size=15, bold=True, color=INK, font=HEAD, first=True)
        tf = textbox(slide, x + 0.28, y + 0.60, cw - 0.56, 0.78)
        para(tf, body, size=11.5, color=SLATE, line=1.15, first=True)
        tf = textbox(slide, x + 0.28, y + 1.34, cw - 0.56, 0.44)
        para(tf, note, size=11.5, bold=True, italic=True, color=colour, line=1.12, first=True)

    y = TOP + 4.18
    card(slide, M, y, CW, 1.26, fill=NAVY, radius=0.04)
    tf = textbox(slide, M + 0.32, y + 0.18, CW - 0.64, 0.86)
    para(tf, runs=[("[5] Multi-IaC-Eval  ", {"bold": True, "color": MINT, "size": 12}),
                   ("modern LLMs exceed 95% syntactic validity across IaC formats — syntax is close to saturated.   ",
                    {"color": WHITE, "size": 12}),
                   ("[6] Vargas et al.  ", {"bold": True, "color": MINT, "size": 12}),
                   ("validity and security are largely orthogonal; automated scanning stays necessary.",
                    {"color": WHITE, "size": 12})], line=1.2, first=True)
    para(tf, runs=[("[7] ImportSnare  ", {"bold": True, "color": AMBER, "size": 12}),
                   ("poisoned documentation steers retrieval-augmented code generators to malicious dependencies — "
                    "over 50% attack success at a 0.01% poisoning ratio. The corpus is a trust boundary.",
                    {"color": WHITE, "size": 12})], line=1.2, before=6)


# ----------------------------------------------------------------- 9 the gap
def gap(prs, n):
    slide = content_slide(prs, "The gap this work addresses", n)
    cw = 5.79
    x2 = M + cw + 0.355

    card(slide, M, TOP, cw, 4.0, fill=MIST, radius=0.05)
    tf = textbox(slide, M + 0.32, TOP + 0.26, cw - 0.64, 0.34)
    para(tf, "What the reviewed literature does", size=17, bold=True, color=SLATE, font=HEAD, first=True)
    tf = textbox(slide, M + 0.32, TOP + 0.76, cw - 0.64, 3.1)
    for i, t in enumerate([
        "Concentrates on AWS. No GCP-specific benchmark for LLM-generated Terraform was found.",
        "Tends to report one success figure per system, which hides whether a failure was malformed code or an unmet convention.",
        "Studies knowledge injection in aggregate, without separating retrieval of provider documentation from retrieval of organisational policy.",
    ]):
        bullet(para(tf, t, size=13, color=SLATE, line=1.2, before=0 if i == 0 else 11, first=(i == 0)))

    card(slide, x2, TOP, cw, 4.0, fill=NAVY, radius=0.05)
    tf = textbox(slide, x2 + 0.32, TOP + 0.26, cw - 0.64, 0.34)
    para(tf, "What this work adds", size=17, bold=True, color=MINT, font=HEAD, first=True)
    tf = textbox(slide, x2 + 0.32, TOP + 0.76, cw - 0.64, 3.1)
    for i, t in enumerate([
        "A GCP-specific task set of 35 requirements with machine-checkable intent specifications.",
        "Technical correctness, intent satisfaction and organisational policy reported as three separate quantities.",
        "A per-sample error taxonomy derived from validator output, applied to every generated configuration.",
        "A paired RAG-versus-no-retrieval comparison on the same model, prompt and sampling settings.",
        "A conventions-in-prompt control arm that separates retrieving the conventions from merely knowing them.",
    ]):
        bullet(para(tf, t, size=13, color=WHITE, line=1.2, before=0 if i == 0 else 9, first=(i == 0)), color=MINT)

    tf = textbox(slide, M, TOP + 4.26, CW, 0.5)
    para(tf, "The task set follows IaC-Eval's intent-specification approach but is new and GCP-specific, so its "
             "results are not directly comparable to published AWS figures.", size=12.5, italic=True,
         color=SLATE, first=True)


# ------------------------------------------------------------ 11 architecture
def architecture(prs, n):
    slide = content_slide(prs, "System architecture", n)
    bands = [
        ("OFFLINE  ·  KNOWLEDGE-BASE CONSTRUCTION", TEAL, [
            ("Source documents", "47 pages of public google-provider docs (v8.3.0) + 4 convention documents"),
            ("Markdown-aware chunker", "Fenced HCL kept whole; every chunk prefixed with its heading path"),
            ("Vertex AI embeddings", "text-embedding-005, 768-dim, document task type; cached on disk"),
            ("Vector index", "1,034 chunks, exact cosine search, persisted to disk"),
        ]),
        ("ONLINE  ·  GENERATION", AMBER_D, [
            ("Natural-language requirement", "“A Cloud Storage bucket in asia-south1 with versioning enabled”"),
            ("Arm selects the context", "RAG: top-8 (≤3 per doc) · Control: conventions pasted in · Baseline: none"),
            ("Gemini 3.8 Flash on Vertex AI", "Same prompt template, provider ~> 8.0 and temperature in every arm"),
            ("Generated Terraform", "Extracted from the reply; retried with backoff on quota errors"),
        ]),
        ("VALIDATION  ·  IDENTICAL FOR ALL THREE ARMS", SLATE, [
            ("terraform init / validate / plan", "Read-only; runs only against the experimentation project"),
            ("OPA policy via Conftest", "Required labels, public IAM grants, Cloud SQL exposure, open ingress"),
            ("Functional-intent checks", "Did it build the resources and attributes that were asked for?"),
            ("Error taxonomy + stored record", "Every sample: HCL, retrieved chunks, diagnostics, categories"),
        ]),
    ]
    bw, bgap = 2.78, 0.30
    y = TOP - 0.02
    for label, colour, boxes in bands:
        tf = textbox(slide, M, y, 8.0, 0.24)
        para(tf, label, size=10.5, bold=True, color=colour, first=True)
        by = y + 0.26
        for i, (head, body) in enumerate(boxes):
            x = M + i * (bw + bgap)
            card(slide, x, by, bw, 1.22, fill=MIST, radius=0.07)
            tf = textbox(slide, x + 0.18, by + 0.14, bw - 0.36, 0.48)
            para(tf, head, size=12, bold=True, color=INK, line=1.08, first=True)
            tf = textbox(slide, x + 0.18, by + 0.62, bw - 0.36, 0.52)
            para(tf, body, size=10, color=SLATE, line=1.1, first=True)
            if i < 3:
                arrow(slide, x + bw + 0.02, by + 0.51, 0.26, 0.2, colour)
        y += 1.70

    tf = textbox(slide, M, 6.34, CW, 0.42)
    para(tf, runs=[("Every external call sits behind a small interface  ", {"bold": True, "color": INK, "size": 12}),
                   ("(Vertex AI, GCS, terraform, conftest), so the pipeline runs offline for development and "
                    "testing, and the vector store can move to Vertex AI Vector Search by configuration alone. "
                    "105 automated tests, including integration tests that run the real policy engine.",
                    {"color": SLATE, "size": 12})], line=1.18, first=True)


# ----------------------------------------------------------- 12 tech choices
def tech_choices(prs, n):
    slide = content_slide(prs, "Technology choices, settled and justified", n)
    tf = textbox(slide, M, TOP - 0.08, CW, 0.32)
    para(tf, "The four choices the supervisor asked to be settled at this stage are fixed, with the reasoning "
             "recorded for each.", size=12.5, color=SLATE, first=True)
    rows = [
        ("Cloud and IaC tool", "Google Cloud Platform; Terraform with the google provider, constrained to ~> 8.0",
         "Terraform is the delivery team's tool and GCP is the cloud used for all experimentation."),
        ("Region", "asia-south1 (Mumbai) for storage, embeddings and the index",
         "Google Cloud has no Hyderabad region; Mumbai is roughly 600 km away against roughly 1,350 km for Delhi."),
        ("Generation model", "Gemini 3.8 Flash on Vertex AI, global endpoint",
         "The current GA Flash model: 2.0-flash no longer exists and 2.5-flash shuts down on 20 Oct 2026, inside this timeline."),
        ("Embeddings", "Vertex AI text-embedding-005 (768 dimensions)",
         "Supports separate document and query task types, which the model is trained to expect for asymmetric retrieval."),
        ("Vector store", "In-memory exact cosine search, persisted; Vertex AI Vector Search implemented but not provisioned",
         "At 1,034 chunks exact search is instantaneous; an ANN service would add cost and operations without improving retrieval."),
        ("Validation and policy", "Terraform 1.16.2 (init / validate / plan); Conftest 0.70.0 on OPA 1.20.2",
         "The policy-as-code checks named in the outline; plan is read-only and never applies."),
    ]
    table(slide, M, TOP + 0.36, CW, [2.3, 4.3, 5.333],
          ["Concern", "Choice", "Why"], rows, head_h=0.42, row_h=0.76, size=11, head_size=11)


# ------------------------------------------------------------------ 13 arms
def arms(prs, n):
    slide = content_slide(prs, "Three experimental arms", n)
    cols = [
        ("RAG", TEAL, "The system as built",
         ["Requirement plus the eight most similar chunks, at most three from any one document.",
          "Corpus is provider documentation and the organisational conventions.",
          "Measures retrieval as actually implemented."]),
        ("BASELINE", SLATE, "The model alone",
         ["Same model, same prompt template, same target provider constraint, same temperature.",
          "No retrieved context at all.",
          "Differs from RAG in exactly one respect, so any difference is attributable to retrieval."]),
        ("CONVENTIONS IN PROMPT", AMBER_D, "The control",
         ["RAG prompt with the four convention documents pasted in whole.",
          "No retrieval and no provider documentation.",
          "Measures the value of knowing the conventions, separately from retrieving them."]),
    ]
    cw, gapx = 3.86, 0.19
    for i, (tag, colour, sub, points) in enumerate(cols):
        x = M + i * (cw + gapx)
        card(slide, x, TOP, cw, 3.28, fill=MIST, radius=0.05)
        chip(slide, x + 0.28, TOP + 0.26, min(2.9, 0.16 * len(tag) + 0.5), 0.34, tag, fill=colour, size=11)
        tf = textbox(slide, x + 0.28, TOP + 0.72, cw - 0.56, 0.34)
        para(tf, sub, size=16, bold=True, color=INK, font=HEAD, first=True)
        tf = textbox(slide, x + 0.28, TOP + 1.16, cw - 0.56, 1.95)
        for j, p in enumerate(points):
            bullet(para(tf, p, size=12, color=SLATE, line=1.16, before=0 if j == 0 else 9, first=(j == 0)),
                   color=colour)

    y = TOP + 3.52
    card(slide, M, y, CW, 1.46, fill=NAVY, radius=0.045)
    tf = textbox(slide, M + 0.34, y + 0.22, CW - 0.68, 1.1)
    para(tf, "Why the control arm exists", size=15, bold=True, color=MINT, font=HEAD, first=True)
    para(tf, "The organisational conventions are stated only in the retrieval corpus, so the baseline cannot know "
             "them. Without a control, any policy advantage of RAG over the baseline could simply be the model "
             "being told the conventions rather than retrieval working. RAG against the control isolates the value "
             "of retrieving provider documentation; the control against the baseline isolates the value of knowing "
             "the conventions.", size=12.5, color=WHITE, line=1.2, before=6)

    tf = textbox(slide, M, y + 1.60, CW, 0.32)
    para(tf, "Sampling: five samples per task per arm at temperature 0.8, so that samples differ and pass@k is "
             "meaningful.", size=11.5, italic=True, color=SLATE, first=True)


# ------------------------------------------------------------ 14 validation
def validation(prs, n):
    slide = content_slide(prs, "Validation stack and metrics", n)
    levels = [
        ("1", "Well-formed", "terraform init + validate", "Is it valid and consistent with the provider schema?", TEAL),
        ("2", "Plannable", "terraform plan (read-only)", "Can Terraform build an execution plan against the real API?", TEAL),
        ("3", "Policy-compliant", "OPA through Conftest", "Does it obey organisational policy that the request never stated?", AMBER_D),
        ("4", "Intent-satisfying", "Task-specific intent checks", "Did it build what was actually asked for?", BRICK),
    ]
    lw = 6.9
    y = TOP - 0.02
    for num, name, tool, question, colour in levels:
        card(slide, M, y, lw, 1.00, fill=MIST, radius=0.07)
        disc(slide, M + 0.22, y + 0.25, 0.50, num, fill=colour, size=14)
        tf = textbox(slide, M + 0.90, y + 0.16, lw - 1.12, 0.3)
        para(tf, runs=[(name, {"bold": True, "size": 14.5, "color": INK, "font": HEAD}),
                       ("   " + tool, {"size": 11.5, "color": colour, "bold": True})], first=True)
        tf = textbox(slide, M + 0.90, y + 0.50, lw - 1.12, 0.4)
        para(tf, question, size=12, color=SLATE, line=1.1, first=True)
        y += 1.12

    x = M + lw + 0.34
    rw = CW - lw - 0.34
    card(slide, x, TOP - 0.02, rw, 5.04, fill=NAVY, radius=0.045)
    tf = textbox(slide, x + 0.32, TOP + 0.24, rw - 0.64, 4.5)
    para(tf, "Metrics fixed before the run", size=17, bold=True, color=WHITE, font=HEAD, first=True)
    para(tf, "SPECIFIED BY THE SUPERVISOR", size=10, bold=True, color=MINT, before=14)
    for t in ["Validate pass rate and plan pass rate",
              "OPA policy-violation rate, over samples the engine could parse",
              "pass@k, unbiased estimator, for k = 1, 3 and 5"]:
        bullet(para(tf, t, size=12, color=WHITE, line=1.14, before=6), color=MINT)
    para(tf, "ADDED IN THIS WORK", size=10, bold=True, color=AMBER, before=14)
    for t in ["Functional pass: validates, plans and satisfies intent",
              "Overall pass: functional pass with no policy violation",
              "Retrieval hit rate: were the needed resources' docs retrieved?"]:
        bullet(para(tf, t, size=12, color=WHITE, line=1.14, before=6), color=AMBER)
    para(tf, "ANALYSIS", size=10, bold=True, color=SLATE_L, before=14)
    para(tf, "95% Wilson score intervals on every proportion, and a paired per-task comparison tested with an "
             "exact two-sided sign test.", size=12, color=WHITE, line=1.14, before=6)

    tf = textbox(slide, M, TOP + 4.56, lw, 0.9)
    para(tf, "Three decisions that protect the numbers", size=12.5, bold=True, color=INK, first=True)
    para(tf, "Plan failures caused by missing credentials or an undefaulted variable are never scored  ·  HCL the "
             "policy engine cannot parse is a syntax failure, not a policy violation  ·  the Rego rules were "
             "themselves tested against known-violating and known-compliant configurations.",
         size=11, color=SLATE, line=1.14, before=3)


# -------------------------------------------------------- 16 knowledge base
def knowledge_base(prs, n):
    slide = content_slide(prs, "The knowledge base", n)
    stats = [("47", "provider doc pages"), ("1,034", "indexed chunks"), ("4", "convention documents"),
             ("1,500", "character chunk target"), ("8", "chunks retrieved per query")]
    sw, sgap = 2.26, 0.17
    for i, (value, label) in enumerate(stats):
        x = M + i * (sw + sgap)
        card(slide, x, TOP - 0.04, sw, 1.14, fill=NAVY, radius=0.06)
        tf = textbox(slide, x + 0.16, TOP + 0.10, sw - 0.32, 0.56)
        para(tf, value, size=30, bold=True, color=MINT, font=HEAD, align=PP_ALIGN.CENTER, first=True)
        tf = textbox(slide, x + 0.16, TOP + 0.70, sw - 0.32, 0.3)
        para(tf, label, size=10.5, color=SLATE_L, align=PP_ALIGN.CENTER, first=True)

    items = [
        ("Source and provenance",
         "Public documentation for the google Terraform provider from release v8.3.0 (MPL-2.0), fetched over "
         "HTTPS at a pinned tag by a script and never hand-edited."),
        ("Cleaning",
         "Generated front matter and the import and timeout sections are removed. A comment recording the "
         "source URL, release and licence is added to every page."),
        ("Chunking",
         "Fenced HCL blocks are kept whole, and every chunk is prefixed with its heading path, so a chunk from "
         "the middle of an argument list still names its resource."),
        ("Organisational conventions",
         "Four short documents: default region, a mandatory environment label, no public exposure unless "
         "requested, deletion protection and backups, regional over zonal."),
    ]
    y = TOP + 1.26
    for head, bodytext in items:
        tf = textbox(slide, M, y, 7.55, 0.26)
        para(tf, head, size=13.5, bold=True, color=TEAL_D, first=True)
        tf = textbox(slide, M, y + 0.30, 7.55, 0.68)
        para(tf, bodytext, size=11.5, color=SLATE, line=1.16, first=True)
        y += 1.06

    x = M + 7.88
    rw = CW - 7.88
    card(slide, x, TOP + 1.26, rw, 1.96, fill=MIST, radius=0.05)
    tf = textbox(slide, x + 0.28, TOP + 1.48, rw - 0.56, 1.6)
    para(tf, "The corpus is a trust boundary", size=14.5, bold=True, color=INK, font=HEAD, first=True)
    para(tf, "Whatever enters the knowledge base shapes the generated code [7]. The corpus therefore holds only a "
             "pinned release of official documentation and reviewed conventions — no user-contributed content, and "
             "no customer or production data.", size=11.5, color=SLATE, line=1.16, before=6)

    card(slide, x, TOP + 3.42, rw, 1.96, fill=MIST, radius=0.05)
    tf = textbox(slide, x + 0.28, TOP + 3.64, rw - 0.56, 1.6)
    para(tf, "Why a cap of three chunks per document", size=14.5, bold=True, color=INK, font=HEAD, first=True)
    para(tf, "For a requirement asking for a VPC with subnets and Cloud NAT, the top eight results came entirely "
             "from the NAT and subnetwork pages — none described the network resource itself. The cap was added "
             "after that inspection.", size=11.5, color=SLATE, line=1.16, before=6)


# -------------------------------------------------------------- 17 task set
def task_set(prs, n):
    slide = content_slide(prs, "Task set and what every run records", n)
    tf = textbox(slide, M, TOP - 0.06, 6.7, 0.3)
    para(tf, "35 natural-language requirements: 33 headline tasks and 2 that deliberately conflict with policy.",
         size=12.5, color=SLATE, first=True)

    cats = [("Platform", 1), ("Compute", 2), ("Messaging", 2), ("Analytics", 2), ("Security", 2),
            ("Policy conflict", 2), ("Serverless", 3), ("Kubernetes", 4), ("Database", 5),
            ("Network", 6), ("Storage", 6)]
    bar_chart(slide, M - 0.12, TOP + 0.30, 6.5, 4.5,
              [c for c, _ in cats], [("Tasks", [v for _, v in cats])], [TEAL],
              kind="bar", maxv=7, fmt='0', vfmt='0', gap=50, overlap=-10, legend=False,
              label_size=10, label_color=INK)

    x = M + 6.62
    rw = CW - 6.62
    tf = textbox(slide, x, TOP + 0.28, rw, 0.3)
    para(tf, "How the tasks are specified", size=14.5, bold=True, color=INK, font=HEAD, first=True)
    tf = textbox(slide, x, TOP + 0.64, rw, 1.5)
    for i, t in enumerate([
        "Difficulty 1 to 3: 10 single-resource tasks, 12 with several interacting constraints, 13 spanning several related resources.",
        "Each task carries a machine-checkable intent specification — required resource types plus assertions on their attributes.",
        "Specifications allow legitimate alternatives (an IAM member or an IAM binding; node_count or initial_node_count) and evaluate constant arithmetic.",
    ]):
        bullet(para(tf, t, size=11.5, color=SLATE, line=1.15, before=0 if i == 0 else 8, first=(i == 0)))

    card(slide, x, TOP + 2.36, rw, 2.44, fill=NAVY, radius=0.05)
    tf = textbox(slide, x + 0.3, TOP + 2.58, rw - 0.6, 2.0)
    para(tf, "What every run records", size=14.5, bold=True, color=MINT, font=HEAD, first=True)
    para(tf, runs=[("Manifest  ", {"bold": True, "color": AMBER, "size": 11.5}),
                   ("git commit, model, temperature, embedding model, chunking and retrieval settings, index size, "
                    "provider-doc release, target provider constraint, Terraform and Conftest versions, and hashes "
                    "of the task file and policies.", {"color": WHITE, "size": 11.5})], line=1.15, before=8)
    para(tf, runs=[("Per sample  ", {"bold": True, "color": AMBER, "size": 11.5}),
                   ("the generated HCL, the retrieved chunks, full validator diagnostics and the assigned error "
                    "categories. Every summary statistic is computed from those records, so any table can be "
                    "regenerated or audited.", {"color": WHITE, "size": 11.5})], line=1.15, before=8)

    tf = textbox(slide, M, 6.26, CW, 0.4)
    para(tf, runs=[("Main run:  ", {"bold": True, "color": INK, "size": 12}),
                   ("35 tasks × 3 arms × 5 samples = 525 stored samples (165 headline + 10 policy-conflict scored "
                    "per arm), plus three follow-up runs. No customer or production information is used anywhere "
                    "in the study.", {"color": SLATE, "size": 12})], line=1.16, first=True)


# ------------------------------------------------------------- 19 headline
def headline(prs, n):
    slide = content_slide(prs, "Headline results", n)
    bar_chart(slide, M - 0.14, TOP - 0.06, 7.6, 4.05,
              ["Validate pass", "Functional pass", "Overall pass\n(incl. org policy)"],
              [("Baseline", [99.4, 97.0, 57.0]),
               ("Conventions in prompt", [97.6, 95.2, 95.2]),
               ("RAG", [98.8, 98.8, 78.8])],
              [SLATE, AMBER, TEAL], maxv=100, inside=True, label_color=WHITE, label_size=10)

    x = M + 7.62
    rw = CW - 7.62
    tf = textbox(slide, x, TOP - 0.02, rw, 0.32)
    para(tf, "What it shows", size=17, bold=True, color=INK, font=HEAD, first=True)
    points = [
        ("Technical correctness is at ceiling.", "Validate and functional pass rates sit within a few points of "
         "each other and the intervals overlap almost completely — no evidence that retrieval improves "
         "correctness (RQ1).", TEAL),
        ("Policy is where the arms separate.", "Overall pass — functional correctness with no policy violation — "
         "rises from 57.0% without retrieval to 78.8% with it (RQ2).", AMBER_D),
        ("The control does better still.", "Pasting the four convention documents into the prompt reaches 95.2% "
         "with no retrieval at all, so retrieval recovers about half of the available policy gain.", BRICK),
    ]
    y = TOP + 0.38
    for head, body, colour in points:
        tf = textbox(slide, x, y, rw, 0.32)
        para(tf, head, size=13, bold=True, color=colour, line=1.12, first=True)
        tf = textbox(slide, x, y + 0.34, rw, 0.80)
        para(tf, body, size=11.5, color=SLATE, line=1.16, first=True)
        y += 1.24

    y = TOP + 4.18
    card(slide, M, y, CW, 1.08, fill=NAVY, radius=0.045)
    tf = textbox(slide, M + 0.32, y + 0.18, CW - 0.64, 0.78)
    para(tf, runs=[("Paired by task, so the result does not depend on the number of samples:  ",
                    {"bold": True, "color": MINT, "size": 12.5}),
                   ("across 33 headline tasks RAG beats the baseline on 10 and is worse on none — a mean gain of "
                    "21.8 percentage points, exact sign test p = 0.002. Against the control, RAG loses on 10 tasks "
                    "and wins on 3 (p = 0.092).", {"color": WHITE, "size": 12.5})], line=1.2, first=True)
    para(tf, "n = 165 per arm; 95% Wilson intervals for every proportion are in the report.",
         size=10.5, italic=True, color=SLATE_L, before=5)


# ------------------------------------------------------------- 20 failures
def failures(prs, n):
    slide = content_slide(prs, "Where the failures actually are", n)
    bar_chart(slide, M - 0.14, TOP - 0.06, 7.0, 4.3,
              ["Missing environment label", "Public access (allUsers)"],
              [("Baseline", [42.0, 12.0]),
               ("Conventions in prompt", [0.0, 0.0]),
               ("RAG", [20.0, 0.0])],
              [SLATE, AMBER, TEAL], maxv=50, fmt='0"%"', inside=False,
              label_color=INK, label_size=10)
    tf = textbox(slide, M, TOP + 4.30, 7.0, 0.3)
    para(tf, "Share of samples containing the error category, by arm.", size=10.5, italic=True,
         color=SLATE, first=True)

    x = M + 7.1
    rw = CW - 7.1
    card(slide, x, TOP - 0.06, rw, 2.22, fill=MIST, radius=0.05)
    tf = textbox(slide, x + 0.3, TOP + 0.18, rw - 0.6, 1.8)
    para(tf, "Almost nothing is a coding error", size=16, bold=True, color=INK, font=HEAD, first=True)
    para(tf, "Every technical category — HCL syntax, invalid reference, plan error, provider initialisation, "
             "intent mismatch — appears in at most 2% of samples in every arm, on counts of between zero and four "
             "samples. That is far too few to separate the arms (RQ3).", size=12, color=SLATE, line=1.18, before=8)

    card(slide, x, TOP + 2.38, rw, 2.22, fill=NAVY, radius=0.05)
    tf = textbox(slide, x + 0.3, TOP + 2.62, rw - 0.6, 1.8)
    para(tf, "The gap is concentrated", size=16, bold=True, color=MINT, font=HEAD, first=True)
    para(tf, "Compute, network, platform, serverless, messaging and security tasks pass at 90% or more in every "
             "arm, baseline included. The differences sit entirely in the three resource types the label rule "
             "covers — storage (0% / 70% / 100%), database (0% / 16% / 80%) and Kubernetes (25% / 75% / 95%), "
             "baseline / RAG / control.", size=12, color=WHITE, line=1.18, before=8)

    tf = textbox(slide, M, 6.22, CW, 0.46)
    para(tf, runs=[("Requirements that deliberately conflict with policy:  ", {"bold": True, "color": BRICK, "size": 12}),
                   ("all three arms did exactly what was asked — 100% intent pass and 100% policy violation. No arm "
                    "refused, adapted or warned. The validation layer is the only thing that stops a conflicting "
                    "request, which is why it exists.", {"color": SLATE, "size": 12})], line=1.16, first=True)


# ------------------------------------------------------- 21 central finding
def central_finding(prs, n):
    slide = content_slide(prs, "The central finding", n)
    cw = 5.79
    x2 = M + cw + 0.355

    card(slide, M, TOP, cw, 2.26, fill=MIST, radius=0.05)
    tf = textbox(slide, M + 0.32, TOP + 0.22, cw - 0.64, 0.66)
    para(tf, "97.0%", size=38, bold=True, color=TEAL, font=HEAD, first=True)
    tf = textbox(slide, M + 0.32, TOP + 0.94, cw - 0.64, 1.2)
    para(tf, "Retrieval of provider documentation works", size=15.5, bold=True, color=INK, font=HEAD, first=True)
    para(tf, "Nearly every RAG sample was given the documentation for the resources it had to build. The hit rate "
             "is the share of needed resource types whose documentation appears in the retrieved chunks.",
         size=12, color=SLATE, line=1.16, before=6)

    card(slide, x2, TOP, cw, 2.26, fill=NAVY, radius=0.05)
    tf = textbox(slide, x2 + 0.32, TOP + 0.22, cw - 0.64, 0.66)
    para(tf, "12%", size=38, bold=True, color=AMBER, font=HEAD, first=True)
    tf = textbox(slide, x2 + 0.32, TOP + 0.94, cw - 0.64, 1.2)
    para(tf, "Retrieval of cross-cutting policy does not", size=15.5, bold=True, color=WHITE, font=HEAD, first=True)
    para(tf, "The organisational conventions reached the model in only 12% of samples — and the policy failures "
             "fall exactly where they were absent (RQ4).", size=12, color=SLATE_L, line=1.16, before=6)

    y = TOP + 2.50
    tf = textbox(slide, M, y, CW, 0.3)
    para(tf, "Why", size=17, bold=True, color=INK, font=HEAD, first=True)
    tf = textbox(slide, M, y + 0.36, CW, 0.84)
    para(tf, "Policy is cross-cutting: it applies to a resource without ever being mentioned in the request. Ranking "
             "documents by similarity to the request therefore ranks resource documentation first, and the "
             "conventions rarely make the top eight. The gap between RAG and the control is a retrieval-design "
             "problem, not evidence that retrieval is unhelpful.", size=13, color=SLATE, line=1.18, first=True)

    y = TOP + 3.82
    remedies = [("Inject a short policy summary into every prompt, unconditionally", TEAL),
                ("Expand the query with the resource types it names before retrieving", TEAL),
                ("Index the conventions per resource type rather than as whole documents", TEAL)]
    tf = textbox(slide, M, y, 7.3, 0.3)
    para(tf, "Remedies to test — none tested yet", size=14, bold=True, color=TEAL_D, first=True)
    tf = textbox(slide, M, y + 0.34, 7.3, 1.1)
    for i, (t, c) in enumerate(remedies):
        bullet(para(tf, t, size=12.5, color=SLATE, line=1.15, before=0 if i == 0 else 7, first=(i == 0)), color=c)

    card(slide, M + 7.6, y - 0.08, CW - 7.6, 1.62, fill=MIST, radius=0.05)
    tf = textbox(slide, M + 7.88, y + 0.14, CW - 8.16, 1.3)
    para(tf, "The control is a ceiling, not an alternative", size=13.5, bold=True, color=AMBER_D, first=True)
    para(tf, "Four short documents fit in a prompt. A real organisation's conventions may not — at which point "
             "retrieval, done well, becomes necessary.", size=11.5, color=SLATE, line=1.16, before=6)


# ---------------------------------------------------------- 22 robustness
def robustness(prs, n):
    slide = content_slide(prs, "Robustness and limitations", n)
    cw = 5.79
    x2 = M + cw + 0.355

    card(slide, M, TOP, cw, 4.14, fill=MIST, radius=0.05)
    tf = textbox(slide, M + 0.32, TOP + 0.24, cw - 0.64, 0.32)
    para(tf, "Robustness checks", size=17, bold=True, color=TEAL_D, font=HEAD, first=True)
    checks = [
        (0.00, "Fewer retrieved chunks (top-8 → top-3)",
         "Overall pass 78.8% → 73.7%; retrieval hit rate 97.0% → 94.4%."),
        (0.76, "Per-document cap removed", "Overall pass unchanged at 78.8%."),
        (1.52, "Near-greedy run at temperature 0", "Same ordering and similar gaps: 57.6% baseline, 78.8% RAG, "
         "97.0% control; RAG functional pass 100%. Paired, RAG beats the baseline on 7 tasks and loses on none "
         "(p = 0.016)."),
    ]
    for dy, head, body in checks:
        y = TOP + 0.68 + dy
        tf = textbox(slide, M + 0.32, y, cw - 0.64, 0.28)
        para(tf, head, size=12.5, bold=True, color=INK, first=True)
        tf = textbox(slide, M + 0.32, y + 0.30, cw - 0.64, 0.84)
        para(tf, body, size=11.5, color=SLATE, line=1.16, first=True)
    tf = textbox(slide, M + 0.32, TOP + 3.24, cw - 0.64, 0.68)
    para(tf, "The intervals overlap heavily throughout, so neither retrieval setting is shown to matter — and the "
             "findings are not an artefact of sampling at temperature 0.8.", size=11.5, italic=True,
         color=TEAL_D, line=1.16, first=True)

    card(slide, x2, TOP, cw, 4.14, fill=NAVY, radius=0.05)
    tf = textbox(slide, x2 + 0.32, TOP + 0.24, cw - 0.64, 0.32)
    para(tf, "Limitations stated openly", size=17, bold=True, color=AMBER, font=HEAD, first=True)
    tf = textbox(slide, x2 + 0.32, TOP + 0.68, cw - 0.64, 3.3)
    for i, t in enumerate([
        "The task set, the organisational conventions and the OPA policies were all written by the author, so compliance partly measures whether the model follows a short, clearly written document.",
        "The policy surface is narrow: four rules, and the label rule touches only three resource types.",
        "Intent is checked statically on parsed HCL, so values produced through variables or for_each cannot be resolved.",
        "33 headline tasks and one model at one temperature: intervals are wide and category-level results are indicative, not conclusive.",
        "11 samples in the main run failed for reasons unrelated to the generated code. Each was flagged, excluded and generated again — none was ever scored.",
    ]):
        bullet(para(tf, t, size=11.5, color=WHITE, line=1.16, before=0 if i == 0 else 9, first=(i == 0)), color=AMBER)

    tf = textbox(slide, M, TOP + 4.34, CW, 0.3)
    para(tf, "Every figure on these slides is computed from stored per-sample records and can be regenerated from "
             "the repository.", size=11.5, italic=True, color=SLATE, first=True)


# ------------------------------------------------------------ 23 feedback
def feedback(prs, n):
    slide = content_slide(prs, "Supervisor feedback and actions taken", n)
    rows = [
        ("Settle the cloud provider, LLM, embedding model and vector store",
         "All four are fixed with the reasoning recorded per decision: GCP and Terraform ~> 8.0, Gemini 3.8 Flash "
         "on Vertex AI, text-embedding-005, and an in-memory exact store with a documented migration path to "
         "Vertex AI Vector Search.", "DONE", TEAL),
        ("Fix the evaluation metrics before collecting any results",
         "Validate and plan pass rates, OPA violation rate and pass@k were fixed in advance and are recorded in "
         "every run manifest. Functional pass, overall pass and retrieval hit rate were added on top, not in "
         "place of them.", "DONE", TEAL),
        ("Use sanitised internal templates — no customer or production data",
         "The corpus is a pinned public provider release plus four hand-written convention documents. No "
         "customer, production or credential data is used anywhere. Replacing the hand-written conventions with "
         "reviewed internal templates is scheduled in Phase 5.", "IN PROGRESS", AMBER_D),
        ("State the participant count, task set and instrument for the user evaluation",
         "8 engineers (4 with under a year of Terraform, 4 with two or more), within-subjects and counterbalanced, "
         "4 matched tasks each. Measures: task success, time, edit count, the System Usability Scale, a "
         "trust-in-automation scale and five interview questions. Awaiting approval.", "PROPOSED", BRICK),
    ]
    y = TOP - 0.02
    for ask, done, status, colour in rows:
        card(slide, M, y, CW, 1.16, fill=MIST, radius=0.055)
        tf = textbox(slide, M + 0.3, y + 0.17, 3.5, 0.86)
        para(tf, ask, size=12.5, bold=True, color=INK, line=1.14, first=True)
        tf = textbox(slide, M + 4.0, y + 0.17, 6.35, 0.86)
        para(tf, done, size=11.5, color=SLATE, line=1.16, first=True)
        chip(slide, M + 10.58, y + 0.41, 1.15, 0.34, status, fill=colour, size=9.5)
        y += 1.30

    tf = textbox(slide, M, y + 0.08, CW, 0.3)
    para(tf, "The metric set, the arms and the statistical treatment were all written down before the benchmark "
             "was run, as required.", size=11.5, italic=True, color=SLATE, first=True)


# ---------------------------------------------------------------- 24 plan
def plan(prs, n):
    slide = content_slide(prs, "Remaining work and plan", n)
    phases = [
        ("1", "Literature review", "25 Jul – 14 Aug", "DONE", TEAL),
        ("2", "Outline submission", "15 Aug – 04 Sep", "DONE", TEAL),
        ("3", "RAG and KB design", "05 – 25 Sep", "DONE", TEAL),
        ("4", "Prototype + mid-sem", "26 Sep – 16 Oct", "DONE", TEAL),
        ("5", "Full implementation", "17 Oct – 06 Nov", "ACTIVE", AMBER_D),
        ("6", "Benchmark + user study", "07 – 30 Nov", "PENDING", SLATE),
    ]
    pw, pgap = 1.76, 0.277
    for i, (num, name, dates, status, colour) in enumerate(phases):
        x = M + i * (pw + pgap)
        dark = status != "PENDING"
        card(slide, x, TOP - 0.02, pw, 1.72, fill=(NAVY if status == "ACTIVE" else MIST), radius=0.07)
        disc(slide, x + (pw - 0.44) / 2, TOP + 0.14, 0.44, num, fill=colour, size=13)
        tf = textbox(slide, x + 0.12, TOP + 0.66, pw - 0.24, 0.46)
        para(tf, name, size=11.5, bold=True, color=(WHITE if status == "ACTIVE" else INK),
             align=PP_ALIGN.CENTER, line=1.08, first=True)
        tf = textbox(slide, x + 0.12, TOP + 1.14, pw - 0.24, 0.24)
        para(tf, dates, size=9.5, color=(SLATE_L if status == "ACTIVE" else SLATE),
             align=PP_ALIGN.CENTER, first=True)
        tf = textbox(slide, x + 0.12, TOP + 1.40, pw - 0.24, 0.24)
        para(tf, status, size=9, bold=True, color=(AMBER if status == "ACTIVE" else colour),
             align=PP_ALIGN.CENTER, first=True)
        if i < 5:
            arrow(slide, x + pw + 0.01, TOP + 0.76, 0.26, 0.18, SLATE_L)

    y = TOP + 1.96
    tf = textbox(slide, M, y, CW, 0.3)
    para(tf, "What is left to do", size=17, bold=True, color=INK, font=HEAD, first=True)
    work = [
        ("Chunk-size ablation", "The only ablation not yet run; it needs the index rebuilt and re-embedded, into a "
         "separate index so the reported run stays reproducible. Its effect is related back to retrieval hit rate (RQ4)."),
        ("Query and corpus design for policy", "The targeted test of the remedies on the previous slide. This is where "
         "the measurable gap lies, so it is the most useful next step."),
        ("Reviewed internal templates", "Replace the hand-written conventions with sanitised internal templates, to test "
         "whether the result survives messier real-world text."),
        ("Deeper error analysis", "Manually review a sample of failures per category, refine the taxonomy, and map it "
         "onto the published taxonomy of Nekrasov et al. [3]."),
        ("User evaluation", "Run the 8-participant study in Phase 6, once the design is approved."),
        ("Optional extensions", "Verifier-feedback refinement in the style of [4], and a corpus poisoning-robustness "
         "check in the spirit of [7]."),
    ]
    cw, gapx = 5.79, 0.355
    for i, (head, body) in enumerate(work):
        x = M + (i % 2) * (cw + gapx)
        yy = y + 0.40 + (i // 2) * 1.12
        disc(slide, x, yy + 0.02, 0.3, "→", fill=TEAL, size=11)
        tf = textbox(slide, x + 0.44, yy, cw - 0.44, 0.26)
        para(tf, head, size=12.5, bold=True, color=INK, first=True)
        tf = textbox(slide, x + 0.44, yy + 0.28, cw - 0.44, 0.76)
        para(tf, body, size=11, color=SLATE, line=1.14, first=True)


# ----------------------------------------------------------- 25 conclusion
def conclusion(prs):
    slide = _blank(prs)
    _bg(slide, prs, NAVY)
    tf = textbox(slide, M, 0.52, CW, 0.7)
    para(tf, "Conclusion", size=38, bold=True, color=WHITE, font=HEAD, first=True)

    findings = [
        ("1", "The model writes correct Terraform with or without retrieval",
         "Validate and functional pass rates are near ceiling in every arm, so retrieval brings no measurable gain "
         "in technical correctness on this task set."),
        ("2", "Retrieval does improve organisational policy compliance",
         "Overall pass rises from 57.0% to 78.8%, and retrieval never made a task worse than the baseline — better "
         "on 10 of 33 tasks, worse on none (p = 0.002)."),
        ("3", "But stating the conventions in the prompt does better still",
         "The control reaches 95.2%. The stored records give the reason: the conventions were retrieved in only 12% "
         "of samples, and the policy failures fall exactly where they were absent."),
    ]
    y = 1.46
    for num, head, body in findings:
        disc(slide, M, y + 0.04, 0.52, num, fill=TEAL, size=15)
        tf = textbox(slide, M + 0.76, y, 11.1, 0.34)
        para(tf, head, size=17, bold=True, color=WHITE, font=HEAD, first=True)
        tf = textbox(slide, M + 0.76, y + 0.40, 11.1, 0.62)
        para(tf, body, size=12.5, color=SLATE_L, line=1.18, first=True)
        y += 1.30

    card(slide, M, 5.46, CW, 1.36, fill=NAVY2, radius=0.045)
    tf = textbox(slide, M + 0.34, 5.70, CW - 0.68, 0.94)
    para(tf, "The practical lesson", size=14, bold=True, color=MINT, font=HEAD, first=True)
    para(tf, "The value of a RAG assistant for IaC depends less on retrieving more documentation than on making "
             "sure policy reaches the model — and automated policy validation remains essential either way, since "
             "every arm violated policy when the request itself asked it to.",
         size=12.5, color=WHITE, line=1.18, before=5)


# -------------------------------------------------------------- 26 closing
def closing(prs):
    slide = _blank(prs)
    _bg(slide, prs, NAVY)
    tf = textbox(slide, M, 2.52, 11.4, 1.0)
    para(tf, "Thank you", size=52, bold=True, color=WHITE, font=HEAD, first=True)
    tf = textbox(slide, M, 3.66, 9.4, 0.4)
    para(tf, "Questions and feedback welcome", size=18, color=MINT, first=True)
    tf = textbox(slide, M, 4.42, 10.4, 0.9)
    para(tf, "The prototype, the benchmark harness and all 525 stored samples are in the repository; every table "
             "and figure in the mid-semester report regenerates from them.", size=12.5, color=SLATE_L,
         line=1.2, first=True)
    tf = textbox(slide, M, 5.72, 11.4, 0.7)
    para(tf, "Kolla Naga Manasa  ·  2024TM93519  ·  M.Tech (Software Engineering)", size=12.5,
         color=WHITE, first=True)
    para(tf, "Supervisor: Karthik Reddy Charla  ·  Caprus IT Private Limited, Hyderabad", size=12.5,
         color=SLATE_L, before=4)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Mid_Semester_Presentation.pptx"
    print("wrote", build(out))
