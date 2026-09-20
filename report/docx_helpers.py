"""Small python-docx helper layer: styled headings, inline **bold**/*italic*/`code`, tables with
shaded headers, captioned figures, page numbers and a contents field."""

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BODY_FONT = "Times New Roman"
CODE_FONT = "Consolas"
ACCENT = RGBColor(0x1F, 0x3A, 0x5F)
_INLINE = re.compile(r"(\*\*.+?\*\*|`.+?`|\*.+?\*)")
_INLINE_MARKUP = re.compile(r"\*\*.+?\*\*|`.+?`|\*.+?\*")


def _set_font(run, name=BODY_FONT, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color


def _shade(cell, hex_fill):
    tc_pr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def _field(paragraph, instruction, placeholder=""):
    """Insert a complex field (PAGE, TOC ...). Word fills it in on open/update."""
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for el in (begin, instr, sep, text, end):
        run._r.append(el)
    return run


class Report:
    def __init__(self):
        self.doc = Document()
        self._table_no = 0
        self._figure_no = 0
        self._captions = {"Table": [], "Figure": []}
        self._list_fields = {}
        self._setup_page()
        self._setup_styles()

    # ---- setup ---------------------------------------------------------------------------------
    def _setup_page(self):
        section = self.doc.sections[0]
        section.page_height, section.page_width = Cm(29.7), Cm(21.0)  # A4
        section.left_margin = section.right_margin = Cm(2.5)
        section.top_margin = section.bottom_margin = Cm(2.4)

    def _setup_styles(self):
        normal = self.doc.styles["Normal"]
        normal.font.name = BODY_FONT
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
        normal.font.size = Pt(11.5)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.15
        caption = self.doc.styles["Caption"]
        caption.font.name = BODY_FONT
        caption.font.color.rgb = RGBColor(0, 0, 0)
        caption.font.size = Pt(10)
        for name, size, before, after in (("Heading 1", 16, 18, 8), ("Heading 2", 13.5, 12, 4), ("Heading 3", 12, 8, 3)):
            style = self.doc.styles[name]
            style.font.name = BODY_FONT
            style.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
            style.element.rPr.rFonts.set(qn("w:ascii"), BODY_FONT)
            style.element.rPr.rFonts.set(qn("w:hAnsi"), BODY_FONT)
            # Word's built-in heading styles reference theme fonts, which override the names above.
            for theme_attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                style.element.rPr.rFonts.attrib.pop(qn(theme_attr), None)
            style.font.size = Pt(size)
            style.font.bold = True
            style.font.color.rgb = ACCENT
            style.paragraph_format.space_before = Pt(before)
            style.paragraph_format.space_after = Pt(after)
            style.paragraph_format.keep_with_next = True

    # ---- inline text -----------------------------------------------------------------------------
    def _runs(self, paragraph, text, size=None, italic=None, bold=None):
        for part in _INLINE.split(text):
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                _set_font(paragraph.add_run(part[2:-2]), size=size, bold=True, italic=italic)
            elif part.startswith("`") and part.endswith("`"):
                _set_font(paragraph.add_run(part[1:-1]), name=CODE_FONT, size=(size or 11.5) - 1.5)
            elif part.startswith("*") and part.endswith("*") and len(part) > 2:
                _set_font(paragraph.add_run(part[1:-1]), size=size, italic=True, bold=bold)
            else:
                _set_font(paragraph.add_run(part), size=size, italic=italic, bold=bold)

    # ---- blocks ------------------------------------------------------------------------------------
    def h1(self, text, page_break=True):
        if page_break:
            self.page_break()
        self.doc.add_heading(text, level=1)

    def h2(self, text):
        self.doc.add_heading(text, level=2)

    def h3(self, text):
        self.doc.add_heading(text, level=3)

    def p(self, text, align="justify", italic=None, size=None, space_after=None):
        para = self.doc.add_paragraph()
        para.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER}[align]
        if space_after is not None:
            para.paragraph_format.space_after = Pt(space_after)
        self._runs(para, text, size=size, italic=italic)
        return para

    def bullets(self, items, style="List Bullet"):
        for item in items:
            para = self.doc.add_paragraph(style=style)
            para.paragraph_format.space_after = Pt(2)
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            self._runs(para, item)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def numbered(self, items):
        self.bullets(items, style="List Number")

    def code(self, text, size=8.5):
        for line in text.strip("\n").split("\n"):
            para = self.doc.add_paragraph()
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.line_spacing = 1.0
            para.paragraph_format.left_indent = Cm(0.5)
            _set_font(para.add_run(line if line else " "), name=CODE_FONT, size=size)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def _caption(self, kind, number, text, align):
        """Word caption: 'Table <SEQ>. text' in the Caption style, so a TOC caption field can list it."""
        para = self.doc.add_paragraph(style="Caption")
        para.alignment = align
        para.paragraph_format.space_after = Pt(6)
        para.paragraph_format.keep_with_next = align == WD_ALIGN_PARAGRAPH.LEFT
        _set_font(para.add_run(f"{kind} "), size=10, bold=True, italic=False)
        _set_font(_field(para, f"SEQ {kind} \\* ARABIC", str(number)), size=10, bold=True, italic=False)
        _set_font(para.add_run(". "), size=10, bold=True, italic=False)
        self._runs(para, text, size=10, italic=True)
        self._captions[kind].append(f"{kind} {number}. " + _INLINE_MARKUP.sub(lambda m: m.group(0).strip("*`"), text))

    def table(self, headers, rows, widths_cm, caption, font_size=9.5, header_fill="D9E2F3", align_right_from=None):
        self._table_no += 1
        self._caption("Table", self._table_no, caption, WD_ALIGN_PARAGRAPH.LEFT)
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.width = Cm(widths_cm[i])
            _shade(cell, header_fill)
            para = cell.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            self._runs(para, f"**{header}**", size=font_size)
        for row in rows:
            cells = table.add_row().cells
            for i, value in enumerate(row):
                cells[i].width = Cm(widths_cm[i])
                para = cells[i].paragraphs[0]
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.line_spacing = 1.0
                if align_right_from is not None and i >= align_right_from:
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                self._runs(para, str(value), size=font_size)
        # repeat header row across pages
        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        header_flag = OxmlElement("w:tblHeader")
        header_flag.set(qn("w:val"), "true")
        tr_pr.append(header_flag)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def signature_block(self, left: list[str], right: list[str]):
        """Two side-by-side sign-off blocks (student / supervisor), as on the BITS abstract page."""
        for _ in range(3):
            self.doc.add_paragraph()
        table = self.doc.add_table(rows=len(left), cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for r, (a, b) in enumerate(zip(left, right)):
            for c, text in enumerate((a, b)):
                para = table.rows[r].cells[c].paragraphs[0]
                para.paragraph_format.space_after = Pt(10)
                if r == 0:  # top rule above the signature caption
                    ppr = para._p.get_or_add_pPr()
                    border = OxmlElement("w:pBdr")
                    top = OxmlElement("w:top")
                    for k, v in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", "000000")):
                        top.set(qn(f"w:{k}"), v)
                    border.append(top)
                    ppr.append(border)
                self._runs(para, f"**{text}**" if r == 0 else text, size=10.5)

    def figure(self, path: Path, width_cm: float, caption: str):
        self._figure_no += 1
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.keep_with_next = True
        para.add_run().add_picture(str(path), width=Cm(width_cm))
        self._caption("Figure", self._figure_no, caption, WD_ALIGN_PARAGRAPH.CENTER)

    # ---- front matter / furniture ---------------------------------------------------------------
    def title_page(self, lines):
        """lines: list of (text, size, bold, space_after)."""
        for _ in range(3):
            self.doc.add_paragraph()
        for text, size, bold, after in lines:
            para = self.doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.space_after = Pt(after)
            _set_font(para.add_run(text), size=size, bold=bold, color=ACCENT if size >= 18 else None)

    def contents(self, title="Contents"):
        self.page_break()
        heading = self.doc.add_paragraph()
        _set_font(heading.add_run(title), size=16, bold=True, color=ACCENT)
        para = self.doc.add_paragraph()
        _field(para, 'TOC \\o "1-2" \\h \\z \\u',"Right-click here and choose Update Field to build the table of contents.")
        for kind, title_text in (("Figure", "List of Figures"), ("Table", "List of Tables")):
            head = self.doc.add_paragraph()
            head.paragraph_format.space_before = Pt(18)
            head.paragraph_format.keep_with_next = True
            _set_font(head.add_run(title_text), size=14, bold=True, color=ACCENT)
            body = self.doc.add_paragraph()
            _field(body, f'TOC \\h \\z \\c "{kind}"', "")
            self._list_fields[kind] = body  # prefilled with the captions in save(), once they are known

    def _prefill_lists(self):
        """Word rebuilds these lists (with page numbers) on open; until then show the captions so the
        lists are never blank in viewers that do not update fields."""
        for kind, body in self._list_fields.items():
            text_el = body._p.xpath(".//w:t")[-1]
            lines = self._captions[kind]
            text_el.text = lines[0] if lines else ""
            run = text_el.getparent()
            anchor = text_el
            for line in lines[1:]:
                br = OxmlElement("w:br")
                anchor.addnext(br)
                nxt = OxmlElement("w:t")
                nxt.text = line
                nxt.set(qn("xml:space"), "preserve")
                br.addnext(nxt)
                anchor = nxt

    def footer_page_numbers(self):
        section = self.doc.sections[0]
        section.different_first_page_header_footer = True  # no footer on the title page
        para = section.footer.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_font(para.add_run("RAG-Powered Assistant for Infrastructure as Code Generation  |  Page "), size=9)
        _field(para, "PAGE", "1")

    def update_fields_on_open(self):
        settings = self.doc.settings.element
        flag = OxmlElement("w:updateFields")
        flag.set(qn("w:val"), "true")
        settings.append(flag)

    def save(self, path: Path):
        self._prefill_lists()
        self.doc.save(str(path))
