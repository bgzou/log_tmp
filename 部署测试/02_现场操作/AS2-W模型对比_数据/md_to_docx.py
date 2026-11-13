"""Convert the AS2-W comparison report from Markdown to DOCX."""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

SRC = Path(sys.argv[1])
DST = Path(sys.argv[2])

CJK = "微软雅黑"
LATIN = "Segoe UI"
MONO = "Consolas"
ACCENT = RGBColor(0x1F, 0x3B, 0x57)


def set_run_font(run, size=10.5, bold=None, mono=False, color=None):
    run.font.name = MONO if mono else LATIN
    run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), MONO if mono else CJK)
    rfonts.set(qn("w:ascii"), MONO if mono else LATIN)
    rfonts.set(qn("w:hAnsi"), MONO if mono else LATIN)


def add_runs(par, text, size=10.5, base_bold=False):
    """Inline: **bold**, `code`, *italic*."""
    for tok in re.split(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)", text):
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
            set_run_font(par.add_run(tok[2:-2].replace("`", "")), size, bold=True)
        elif tok.startswith("`") and tok.endswith("`") and len(tok) > 2:
            set_run_font(par.add_run(tok[1:-1]), size - 0.5, mono=True)
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            r = par.add_run(tok[1:-1])
            set_run_font(r, size)
            r.font.italic = True
        else:
            set_run_font(par.add_run(tok), size, bold=base_bold)


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def set_cell_margins(table, top=30, bottom=30, left=60, right=60):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)


def add_page_number(section):
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._element.addnext(fld)
    set_run_font(run, 8)


def build():
    md = SRC.read_text(encoding="utf-8").splitlines()
    doc = Document()

    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(1.8)
    sec.left_margin = Cm(2.0)
    sec.right_margin = Cm(2.0)
    add_page_number(sec)

    style = doc.styles["Normal"]
    style.font.name = LATIN
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), CJK)
    style.paragraph_format.space_after = Pt(3)
    style.paragraph_format.line_spacing = 1.15

    usable = sec.page_width - sec.left_margin - sec.right_margin

    i = 0
    n = len(md)
    in_code = False
    code_lines = []

    while i < n:
        line = md[i].rstrip()

        # fenced code
        if line.strip().startswith("```"):
            if in_code:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.3)
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(4)
                pPr = p._p.get_or_add_pPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "F2F2F2")
                pPr.append(shd)
                for k, cl in enumerate(code_lines):
                    r = p.add_run(cl)
                    set_run_font(r, 8.5, mono=True)
                    if k < len(code_lines) - 1:
                        r.add_break()
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if not line.strip():
            i += 1
            continue

        # horizontal rule
        if re.fullmatch(r"-{3,}", line.strip()):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            pPr = p._p.get_or_add_pPr()
            pbdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "4")
            bottom.set(qn("w:color"), "BFBFBF")
            pbdr.append(bottom)
            pPr.append(pbdr)
            i += 1
            continue

        # table
        if line.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:|-]+\|\s*$", md[i + 1]):
            rows = []
            while i < n and md[i].lstrip().startswith("|"):
                cells = [c.strip() for c in md[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            header = rows[0]
            body = [r for r in rows[2:]]
            cols = len(header)
            table = doc.add_table(rows=1, cols=cols)
            table.style = "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = True
            set_cell_margins(table)

            # column widths from content length
            weights = []
            for c in range(cols):
                lens = [len(r[c]) if c < len(r) else 0 for r in rows]
                w = max(6, min(60, sorted(lens)[int(len(lens) * 0.8)]))
                weights.append(w ** 0.85)
            total = sum(weights)
            widths = [int(usable * w / total) for w in weights]

            hdr = table.rows[0]
            for c, text in enumerate(header):
                cell = hdr.cells[c]
                cell.width = widths[c]
                cell.text = ""
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                add_runs(p, text, size=8.3, base_bold=True)
                shade(cell, "DCE6F1")

            for r in body:
                row = table.add_row()
                for c in range(cols):
                    cell = row.cells[c]
                    cell.width = widths[c]
                    cell.text = ""
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_after = Pt(0)
                    add_runs(p, r[c] if c < len(r) else "", size=8.0)

            doc.add_paragraph().paragraph_format.space_after = Pt(0)
            continue

        # headings
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            if level == 1:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(10)
                set_run_font(p.add_run(text), 20, bold=True, color=ACCENT)
            elif level == 2:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(14)
                p.paragraph_format.space_after = Pt(5)
                pPr = p._p.get_or_add_pPr()
                pbdr = OxmlElement("w:pBdr")
                bottom = OxmlElement("w:bottom")
                bottom.set(qn("w:val"), "single")
                bottom.set(qn("w:sz"), "8")
                bottom.set(qn("w:color"), "1F3B57")
                pbdr.append(bottom)
                pPr.append(pbdr)
                set_run_font(p.add_run(text), 14, bold=True, color=ACCENT)
            elif level == 3:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(9)
                p.paragraph_format.space_after = Pt(3)
                set_run_font(p.add_run(text), 11.5, bold=True, color=ACCENT)
            else:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(2)
                set_run_font(p.add_run(text), 10.5, bold=True)
            i += 1
            continue

        # bullets
        m = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if m:
            indent = len(m.group(1)) // 2
            p = doc.add_paragraph(style="List Bullet" if indent == 0 else "List Bullet 2")
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.left_indent = Cm(0.6 + 0.6 * indent)
            add_runs(p, m.group(2), size=10.5)
            i += 1
            continue

        # numbered
        m = re.match(r"^(\s*)(\d+)\.\s+(.*)$", line)
        if m:
            indent = len(m.group(1)) // 2
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.left_indent = Cm(0.6 + 0.6 * indent)
            add_runs(p, m.group(3), size=10.5)
            i += 1
            continue

        # blockquote
        if line.lstrip().startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            add_runs(p, line.lstrip("> ").strip(), size=10)
            for r in p.runs:
                r.font.italic = True
            i += 1
            continue

        # normal paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        add_runs(p, line, size=10.5)
        i += 1

    doc.save(DST)
    print(f"saved {DST}")


if __name__ == "__main__":
    build()
