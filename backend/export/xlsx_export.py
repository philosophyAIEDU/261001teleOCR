"""Excel(.xlsx) 내보내기. 표 결과만 내보낼 수 있습니다."""

from __future__ import annotations

import io
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter

from .html_table import parse_html_table
from .models import ExportItem

TABLE_FORMATS = {"html_table"}
_NUMBER = re.compile(r"^[+-]?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?$")
_INVALID_SHEET_CHARS = re.compile(r"[\[\]\:\*\?\/\\]")


class NoTableError(ValueError):
    """표 결과가 하나도 없을 때."""


def _to_value(text: str) -> str | int | float:
    """숫자처럼 보이는 칸은 숫자로 저장해 엑셀에서 바로 계산할 수 있게 합니다."""
    stripped = text.strip()
    if _NUMBER.match(stripped):
        number = stripped.replace(",", "")
        if "." in number:
            return float(number)
        if len(number.lstrip("+-")) <= 15 and not (number.lstrip("+-").startswith("0") and len(number.lstrip("+-")) > 1):
            return int(number)
    return text


def _sheet_title(title: str | None, index: int, used: set[str]) -> str:
    base = _INVALID_SHEET_CHARS.sub(" ", title or f"표 {index}").strip()[:28] or f"표 {index}"
    name, n = base, 2
    while name in used:
        name = f"{base[:25]} ({n})"
        n += 1
    used.add(name)
    return name


def to_xlsx(items: list[ExportItem]) -> bytes:
    tables = [i for i in items if i.result_format in TABLE_FORMATS]
    if not tables:
        raise NoTableError("표 결과만 엑셀로 내보낼 수 있어요.")
    workbook = Workbook()
    workbook.remove(workbook.active)
    thin = Side(style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    used: set[str] = set()

    for index, item in enumerate(tables, start=1):
        sheet = workbook.create_sheet(_sheet_title(item.title, index, used))
        table = parse_html_table(item.content)
        for cell in table.cells:
            row, col = cell.row + 1, cell.col + 1
            target = sheet.cell(row=row, column=col, value=_to_value(cell.text))
            target.alignment = Alignment(wrap_text=True, vertical="center")
            if cell.row_span > 1 or cell.col_span > 1:
                sheet.merge_cells(
                    start_row=row, start_column=col,
                    end_row=row + cell.row_span - 1, end_column=col + cell.col_span - 1,
                )
        for r in range(1, table.num_rows + 1):
            for c in range(1, table.num_cols + 1):
                sheet.cell(row=r, column=c).border = border
        for c in range(1, table.num_cols + 1):
            sheet.cell(row=1, column=c).font = Font(bold=True)
        for index_col, column_cells in enumerate(sheet.columns, start=1):
            width = max((len(str(c.value)) for c in column_cells if c.value is not None), default=4)
            sheet.column_dimensions[get_column_letter(index_col)].width = min(50, max(8, width * 1.6))

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
