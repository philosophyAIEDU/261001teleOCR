"""HTML 표를 격자로 해석합니다(rowspan/colspan 포함). 외부 라이브러리 없이 표준 라이브러리만 사용합니다."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class GridCell:
    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1


@dataclass
class ParsedTable:
    num_rows: int = 0
    num_cols: int = 0
    cells: list[GridCell] = field(default_factory=list)

    @property
    def has_spans(self) -> bool:
        return any(c.row_span > 1 or c.col_span > 1 for c in self.cells)

    def to_matrix(self) -> list[list[str]]:
        """병합된 칸은 첫 칸에만 글자를 두고 나머지는 빈 문자열로 채운 2차원 목록."""
        matrix = [["" for _ in range(self.num_cols)] for _ in range(self.num_rows)]
        for cell in self.cells:
            matrix[cell.row][cell.col] = cell.text
        return matrix


def _span(value: str | None) -> int:
    try:
        return max(1, int(value or 1))
    except ValueError:
        return 1


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[tuple[str, int, int]]] = []
        self._cell: list[str] | None = None
        self._spans = (1, 1)
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._depth += 1
        if self._depth > 1:  # 표 안의 표는 글자로만 취급
            return
        if tag == "tr":
            self.rows.append([])
        elif tag in ("td", "th"):
            if not self.rows:
                self.rows.append([])
            a = dict(attrs)
            self._spans = (_span(a.get("rowspan")), _span(a.get("colspan")))
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self._depth -= 1
        if self._depth > 1:
            return
        if tag in ("td", "th") and self._cell is not None:
            self.rows[-1].append(("".join(self._cell).strip(), *self._spans))
            self._cell = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def parse_html_table(html_text: str) -> ParsedTable:
    parser = _TableParser()
    parser.feed(html_text)
    parser.close()

    occupied: dict[tuple[int, int], bool] = {}
    cells: list[GridCell] = []
    num_cols = 0
    num_rows = len(parser.rows)
    for r, row in enumerate(parser.rows):
        c = 0
        for text, row_span, col_span in row:
            while occupied.get((r, c)):
                c += 1
            for rr in range(r, r + row_span):
                for cc in range(c, c + col_span):
                    occupied[(rr, cc)] = True
            cells.append(GridCell(text, r, c, row_span, col_span))
            c += col_span
            num_cols = max(num_cols, c)
        num_rows = max(num_rows, max((cell.row + cell.row_span for cell in cells), default=0))
    return ParsedTable(num_rows=num_rows, num_cols=num_cols, cells=cells)
