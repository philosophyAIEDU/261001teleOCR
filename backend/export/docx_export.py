"""Word(.docx) 내보내기 (python-docx 사용)."""

from __future__ import annotations

import io

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

from .html_table import parse_html_table
from .models import ExportItem

MONO_FONT = "Consolas"
FORMULA_NOTE = (
    "※ 아래 수식은 LaTeX 형식입니다. Word 에서 [삽입 → 수식] 후 'LaTeX' 입력 방식을 선택하고 "
    "붙여 넣으면 수식으로 바뀝니다. 한글(HWP)은 수식 편집기의 'LaTeX 입력'을 이용하세요."
)


def _mono_paragraph(document: Document, text: str) -> None:
    for line in text.rstrip("\n").split("\n") or [""]:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(line)
        run.font.name = MONO_FONT
        run.font.size = Pt(10.5)
        # 동아시아 글꼴 설정이 없으면 한글이 다른 글꼴로 바뀌므로 함께 지정합니다.
        r_pr = run._element.get_or_add_rPr()
        r_fonts = r_pr.find(qn("w:rFonts"))
        if r_fonts is not None:
            r_fonts.set(qn("w:eastAsia"), MONO_FONT)


def _add_table(document: Document, html_table: str) -> None:
    table = parse_html_table(html_table)
    if not table.cells:
        document.add_paragraph(html_table)
        return
    doc_table = document.add_table(rows=table.num_rows, cols=table.num_cols)
    doc_table.style = "Table Grid"
    for cell in table.cells:
        target = doc_table.cell(cell.row, cell.col)
        if cell.row_span > 1 or cell.col_span > 1:
            end = doc_table.cell(cell.row + cell.row_span - 1, cell.col + cell.col_span - 1)
            target = target.merge(end)
        target.text = cell.text


def to_docx(items: list[ExportItem], title: str = "TeleOCR 변환 결과") -> bytes:
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "맑은 고딕"
    style.font.size = Pt(11)
    document.add_heading(title, level=1)

    for item in items:
        if item.title:
            document.add_heading(item.title, level=2)
        fmt = item.result_format
        if fmt == "html_table":
            _add_table(document, item.content)
        elif fmt == "latex":
            note = document.add_paragraph(FORMULA_NOTE)
            note.runs[0].font.size = Pt(9)
            _mono_paragraph(document, item.content.strip())
        elif fmt == "code":
            _mono_paragraph(document, item.content)
        else:
            for block in item.content.strip().split("\n"):
                document.add_paragraph(block)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
