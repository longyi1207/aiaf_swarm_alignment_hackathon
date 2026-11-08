#!/usr/bin/env python3
"""Build the submission .docx from paper/draft.md on top of the official Apart template, then convert it to PDF.

    .venv/bin/python paper/scripts/build_docx.py      # -> paper/build/paper.docx, paper/build/paper.pdf, page PNGs

draft.md conventions: TITLE: / ABSTRACT: / AUTHORS: header fields; '## ' and '### ' headings; 'FIGURE: path | width_in | caption';
'TABLE: caption' followed by '| a | b |' rows (first row is the header); '1. ' numbered and '- ' bulleted items;
**bold** and *italic* inline. Placeholders in CAPS_WITH_UNDERSCORES are rendered as a highlighted note.
"""
from __future__ import annotations

import copy
import re
import subprocess
import sys
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
TEMPLATE = PAPER / "template/apart_template.docx"
BUILD = PAPER / "build"
FONT = "Old Standard TT"
BODY_PT = 10

INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")
PLACEHOLDER = re.compile(r"\b[A-Z][A-Z_]{6,}[A-Z]\b")


def set_font(run, size=BODY_PT, bold=None, italic=None, color=None):
    run.font.name = FONT
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts"); rpr.insert(0, fonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(a), FONT)
    run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def smart(text):
    """Typographic quotes and apostrophes."""
    text = re.sub(r'(^|[\s(\[—–-])"', lambda m: m.group(1) + "\u201c", text)
    text = text.replace('"', "\u201d")
    text = re.sub(r"(^|[\s(\[])'", lambda m: m.group(1) + "\u2018", text)
    return text.replace("'", "\u2019")


def add_inline(par, text, size=BODY_PT, base_bold=False, base_italic=False):
    text = smart(text)
    for piece in INLINE.split(text):
        if not piece:
            continue
        bold, italic = base_bold, base_italic
        if piece.startswith("**") and piece.endswith("**"):
            piece, bold = piece[2:-2], True
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            piece, italic = piece[1:-1], True
        for j, chunk in enumerate(PLACEHOLDER.split(piece)):
            if chunk:
                set_font(par.add_run(chunk), size, bold, italic)
            ph = PLACEHOLDER.findall(piece)
            if j < len(ph):
                r = par.add_run(f"[{ph[j]}: to be added]")
                set_font(r, size, True, False); r.font.highlight_color = WD_COLOR_INDEX.YELLOW


def para_format(par, after=4, before=0, line=1.08, align=None, keep_next=False, indent=None, first=None):
    pf = par.paragraph_format
    pf.space_after, pf.space_before, pf.line_spacing = Pt(after), Pt(before), line
    if align is not None:
        par.alignment = align
    if keep_next:
        pf.keep_with_next = True
    if indent is not None:
        pf.left_indent = Inches(indent)
    if first is not None:
        pf.first_line_indent = Inches(first)


class Builder:
    def __init__(self):
        self.doc = docx.Document(str(TEMPLATE))
        body = self.doc.element.body
        children = list(body.iterchildren())
        self.sect = children[-1]
        for el in children[2:-1]:          # keep the leading empty paragraph and the title block table
            body.remove(el)
        self.fig = 0
        self.tab = 0

    # ---- header block -------------------------------------------------------------------------------------------
    def header(self, title, authors, abstract):
        t = self.doc.tables[0]
        tp = t.rows[0].cells[0].paragraphs[1]
        runs = tp.runs
        runs[0].text = smart(title)
        runs[0].font.size = Pt(17)
        cell = t.rows[1].cells[0]
        # authors: replace the nested author grid (which LibreOffice renders too narrow) with centred paragraphs
        outer = cell.tables[0]._tbl
        def cpar(text, size, bold=False, italic=False, after=0):
            p = OxmlElement("w:p")
            outer.addprevious(p)
            par = docx.text.paragraph.Paragraph(p, cell)
            set_font(par.add_run(text), size, bold, italic)
            para_format(par, after=after, line=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
            return par
        cpar("", 6)
        affs = list(dict.fromkeys(a for _, a in authors))
        names = cpar("", 11.5)
        for k, (n, a) in enumerate(authors):
            if k:
                set_font(names.add_run(",   "), 11.5)
            set_font(names.add_run(n), 11.5)
            if len(affs) > 1:
                r = names.add_run(str(affs.index(a) + 1)); set_font(r, 11.5); r.font.superscript = True
        aff = cpar("", 10, italic=True, after=8)
        for k, a in enumerate(affs):
            if len(affs) > 1:
                r = aff.add_run(("      " if k else "") + str(k + 1)); set_font(r, 10, italic=True); r.font.superscript = True
            set_font(aff.add_run(a), 10, italic=True)
        cpar("With", 10.5, bold=True)
        cpar("Apart Research", 10.5, after=6)
        outer.getparent().remove(outer)
        # abstract: nested 1x1 table
        ab = cell.tables[0].rows[0].cells[0]
        p = ab.paragraphs[0]
        for r in p.runs:
            r.text = ""
        p.runs[0].text = smart(abstract)
        p.runs[0].font.italic = False
        for r in p.runs:
            r.font.underline = False
        for extra in ab.paragraphs[1:]:
            extra._element.getparent().remove(extra._element)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # ---- body -------------------------------------------------------------------------------------------------------
    def _new_par(self):
        p = self.doc.add_paragraph()
        self.sect.addprevious(p._element)
        return p

    def heading(self, text, level):
        p = self._new_par()
        p.style = self.doc.styles["Heading 2" if level == 2 else "Heading 3"]
        r = p.add_run(text)
        if level == 2:
            set_font(r, 13.5, True, False, "434343"); para_format(p, after=3, before=12, keep_next=True)
        else:
            set_font(r, 11.5, True, False, "555555"); para_format(p, after=2, before=8, keep_next=True)

    def paragraph(self, text, size=BODY_PT, after=6, align=None, indent=None, first=None):
        p = self._new_par()
        add_inline(p, text, size)
        para_format(p, after=after, align=align, indent=indent, first=first)
        return p

    def item(self, marker, text):
        p = self._new_par()
        add_inline(p, f"{marker}\t{text}")
        para_format(p, after=3, indent=0.3, first=-0.22)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(0.3))

    def figure(self, path, width, caption):
        p = self._new_par()
        p.add_run().add_picture(str(PAPER / path), width=Inches(width))
        para_format(p, after=3, before=6, align=WD_ALIGN_PARAGRAPH.CENTER, keep_next=True, line=1.0)
        c = self._new_par()
        add_inline(c, caption, 9.2)
        para_format(c, after=10, line=1.08)

    def table(self, caption, rows):
        c = self._new_par()
        add_inline(c, caption, 9.2)
        para_format(c, after=4, before=4, line=1.08, keep_next=True)
        header, data = rows[0], rows[1:]
        ncol = len(header)
        tbl = self.doc.add_table(rows=len(rows), cols=ncol)
        self.sect.addprevious(tbl._tbl)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        widths = [2.35] + [(6.3 - 2.35) / (ncol - 1)] * (ncol - 1)
        tblpr0 = tbl._tbl.tblPr
        lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblpr0.append(lay)
        tw = OxmlElement("w:tblW"); tw.set(qn("w:w"), str(int(6.3 * 1440))); tw.set(qn("w:type"), "dxa")
        old = tblpr0.find(qn("w:tblW"))
        if old is not None:
            tblpr0.remove(old)
        tblpr0.append(tw)
        grid = tbl._tbl.tblGrid
        for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(int(w * 1440)))
        for i, row in enumerate(rows):
            trpr = tbl.rows[i]._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit"); trpr.append(cs)
            for j, val in enumerate(row):
                cell = tbl.cell(i, j)
                cell.width = Inches(widths[j])
                p = cell.paragraphs[0]
                indent = j == 0 and i > 0 and val.startswith("Random")
                add_inline(p, val, 9.2, base_bold=(i == 0))
                para_format(p, after=1, before=1, line=1.0,
                            align=WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER,
                            indent=0.15 if indent else None, keep_next=(i < len(rows) - 1))
        # booktabs-style rules: top, below header, bottom
        tblpr = tbl._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge, val in (("top", "single"), ("bottom", "single"), ("insideH", "nil"), ("insideV", "nil"),
                          ("left", "nil"), ("right", "nil")):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), val)
            if val == "single":
                el.set(qn("w:sz"), "8"); el.set(qn("w:color"), "444444")
            borders.append(el)
        tblpr.append(borders)
        for cell in tbl.rows[0].cells:
            tcpr = cell._tc.get_or_add_tcPr()
            b = OxmlElement("w:tcBorders"); bot = OxmlElement("w:bottom")
            bot.set(qn("w:val"), "single"); bot.set(qn("w:sz"), "6"); bot.set(qn("w:color"), "444444")
            b.append(bot); tcpr.append(b)
        spacer = self._new_par(); para_format(spacer, after=4, line=1.0)

    def reference(self, text):
        p = self._new_par()
        add_inline(p, text, 9.2)
        para_format(p, after=2.5, line=1.05, indent=0.25, first=-0.25)

    def save(self, out):
        self.doc.save(str(out))


def parse(md: str):
    fields, body = {}, []
    lines = md.splitlines()
    i = 0
    while i < len(lines) and not lines[i].startswith("## "):
        m = re.match(r"^(TITLE|ABSTRACT|AUTHORS):\s*(.*)$", lines[i])
        if m:
            key, val = m.groups(); i += 1
            buf = [val] if val else []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(TITLE|ABSTRACT|AUTHORS):", lines[i]) and not lines[i].startswith("## "):
                buf.append(lines[i]); i += 1
            fields[key] = buf
        else:
            i += 1
    block = []
    for line in lines[i:] + [""]:
        if line.strip() == "":
            if block:
                body.append(block); block = []
        else:
            block.append(line)
    return fields, body


def build():
    md = (PAPER / "draft.md").read_text()
    fields, blocks = parse(md)
    b = Builder()
    authors = [tuple(x.strip() for x in a.split("|")) for a in fields.get("AUTHORS", ["Long Yi | Independent researcher"])]
    b.header(" ".join(fields["TITLE"]), authors, " ".join(fields["ABSTRACT"]))
    in_refs = False
    for blk in blocks:
        first = blk[0]
        if first.startswith("## "):
            text = first[3:].strip(); b.heading(text, 2); in_refs = text == "References"; rest = blk[1:]
        elif first.startswith("### "):
            b.heading(first[4:].strip(), 3); rest = blk[1:]
        else:
            rest = blk
        if not rest:
            continue
        if rest[0].startswith("FIGURE:"):
            path, width, cap = [x.strip() for x in rest[0][7:].split("|", 2)]
            b.figure(path, float(width), cap)
        elif rest[0].startswith("TABLE:"):
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rest[1:]]
            b.table(rest[0][6:].strip(), rows)
        elif all(re.match(r"^\d+\.\s", r) for r in rest):
            for r in rest:
                m = re.match(r"^(\d+\.)\s+(.*)$", r); b.item(m.group(1), m.group(2))
        elif all(r.startswith("- ") for r in rest):
            for r in rest:
                b.item("•", r[2:])
        elif in_refs:
            for r in rest:
                b.reference(r)
        else:
            b.paragraph(" ".join(rest))
    BUILD.mkdir(exist_ok=True)
    out = BUILD / "paper.docx"
    b.save(out)
    subprocess.run(["zip", "-dq", str(out), "*/"], capture_output=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(BUILD), str(out)],
                   check=True, capture_output=True)
    for old in BUILD.glob("page-*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", "80", str(BUILD / "paper.pdf"), str(BUILD / "page")], check=True)
    n = len(list(BUILD.glob("page-*.png")))
    print(f"built {out} and paper.pdf, {n} pages")


if __name__ == "__main__":
    sys.exit(build())
