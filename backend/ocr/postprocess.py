"""모델 출력 후처리 순수 함수 모음.

- convert_otsl_to_html: 표 결과(OTSL 형식)를 HTML 표로 변환
- post_process: 수식 결과에서 \\[ \\] 를 제거하고 $$ 로 감싸기
- strip_output: 텍스트/코드 결과 앞뒤 공백 제거

모든 함수는 입력 문자열만 보고 결과를 돌려주는 순수 함수라서 모델 없이 테스트할 수 있습니다.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# OTSL (Optimized Table Structure Language)
# ---------------------------------------------------------------------------
# OTSL 은 표를 "격자 칸마다 토큰 하나"로 적는 형식입니다.
#   <fcel> 글자가 있는 칸 (뒤에 칸의 글자가 이어짐)
#   <ecel> 빈 칸
#   <lcel> 왼쪽 칸과 합쳐진 칸 (가로 병합, colspan)
#   <ucel> 위쪽 칸과 합쳐진 칸 (세로 병합, rowspan)
#   <xcel> 왼쪽·위쪽 모두와 합쳐진 칸 (가로+세로 병합의 안쪽)
#   <nl>   줄 바꿈 (한 행의 끝)
# 예) "<fcel>이름<lcel><nl><fcel>A<fcel>B<nl>" 는 첫 행이 두 칸을 합친 표입니다.

OTSL_NL = "<nl>"
OTSL_FCEL = "<fcel>"
OTSL_ECEL = "<ecel>"
OTSL_LCEL = "<lcel>"
OTSL_UCEL = "<ucel>"
OTSL_XCEL = "<xcel>"

CELL_TOKENS = (OTSL_FCEL, OTSL_ECEL, OTSL_LCEL, OTSL_UCEL, OTSL_XCEL)
ORIGIN_TOKENS = (OTSL_FCEL, OTSL_ECEL)
_TOKEN_PATTERN = re.compile(
    "(" + "|".join(re.escape(t) for t in (OTSL_NL, *CELL_TOKENS)) + ")"
)
_WRAPPER_PATTERN = re.compile(r"</?otsl>", re.IGNORECASE)


# 모델 카드 예제에는 아래 두 클래스에 @dataclass 데코레이터가 빠져 있어
# 생성자 인자를 받지 못하는 버그가 있었습니다. 여기서는 데코레이터를 붙여 수정했습니다.
@dataclass
class TableCell:
    """표의 한 칸(병합된 칸이면 병합 영역 전체)."""

    text: str
    start_row: int
    start_col: int
    row_span: int = 1
    col_span: int = 1


@dataclass
class TableData:
    num_rows: int = 0
    num_cols: int = 0
    cells: list[TableCell] = field(default_factory=list)


def is_html_table(content: str) -> bool:
    """이미 HTML 표 형태인 입력인지 확인합니다."""
    lowered = content.strip().lower()
    return lowered.startswith("<table") and lowered.endswith("</table>")


def _tokenize_otsl(content: str) -> list[list[tuple[str, str]]]:
    """OTSL 문자열을 행 목록으로 나눕니다. 각 칸은 (토큰, 글자) 쌍입니다.

    토큰 사이에 있는 글자는 바로 앞 칸의 내용으로 붙입니다.
    <nl> 이 나오면 새 행을 시작하고, 마지막에 <nl> 이 없어도 남은 칸을 한 행으로 인정합니다.
    """
    rows: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    for part in _TOKEN_PATTERN.split(_WRAPPER_PATTERN.sub("", content)):
        if not part:
            continue
        if part == OTSL_NL:
            if current:
                rows.append(current)
            current = []
        elif part in CELL_TOKENS:
            current.append((part, ""))
        elif current:
            # 글자는 바로 앞 칸에 붙입니다. (<ecel> 등에 붙은 글자는 모델 실수이므로 그대로 보존)
            token, text = current[-1]
            current[-1] = (token, text + part)
    if current:
        rows.append(current)
    return rows


def parse_otsl(content: str) -> TableData:
    """OTSL 문자열을 병합 정보가 포함된 TableData 로 해석합니다."""
    rows = _tokenize_otsl(content)
    if not rows:
        return TableData()

    # 1) 행마다 칸 수가 다르면 가장 긴 행에 맞춰 빈 칸(<ecel>)으로 채웁니다.
    num_cols = max(len(r) for r in rows)
    grid = [r + [(OTSL_ECEL, "")] * (num_cols - len(r)) for r in rows]
    num_rows = len(grid)

    covered = [[False] * num_cols for _ in range(num_rows)]
    cells: list[TableCell] = []

    for r in range(num_rows):
        for c in range(num_cols):
            if covered[r][c]:
                continue
            token, text = grid[r][c]
            if token not in ORIGIN_TOKENS:
                # 2) 어떤 병합 영역에도 속하지 않는 <lcel>/<ucel>/<xcel> 은
                #    모델 출력 오류이므로 빈 칸으로 취급해 표가 깨지지 않게 합니다.
                cells.append(TableCell(text=text.strip(), start_row=r, start_col=c))
                covered[r][c] = True
                continue

            # 3) 오른쪽으로 <lcel>/<xcel> 이 이어지는 만큼 colspan 을 늘립니다.
            col_span = 1
            while c + col_span < num_cols and grid[r][c + col_span][0] in (OTSL_LCEL, OTSL_XCEL):
                col_span += 1
            # 4) 아래쪽으로 <ucel>/<xcel> 이 이어지는 만큼 rowspan 을 늘립니다.
            row_span = 1
            while r + row_span < num_rows and grid[r + row_span][c][0] in (OTSL_UCEL, OTSL_XCEL):
                row_span += 1

            for rr in range(r, r + row_span):
                for cc in range(c, c + col_span):
                    covered[rr][cc] = True
            cells.append(
                TableCell(
                    text=text.strip(),
                    start_row=r,
                    start_col=c,
                    row_span=row_span,
                    col_span=col_span,
                )
            )

    return TableData(num_rows=num_rows, num_cols=num_cols, cells=cells)


def table_data_to_html(table: TableData) -> str:
    if not table.cells:
        return ""
    by_row: dict[int, list[TableCell]] = {}
    for cell in table.cells:
        by_row.setdefault(cell.start_row, []).append(cell)
    parts = ["<table>"]
    for r in range(table.num_rows):
        parts.append("<tr>")
        for cell in sorted(by_row.get(r, []), key=lambda x: x.start_col):
            attrs = ""
            if cell.row_span > 1:
                attrs += f' rowspan="{cell.row_span}"'
            if cell.col_span > 1:
                attrs += f' colspan="{cell.col_span}"'
            parts.append(f"<td{attrs}>{html.escape(cell.text)}</td>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def convert_otsl_to_html(content: str) -> str:
    """OTSL 표를 HTML 표로 변환합니다.

    - 이미 HTML 표(<table>...</table>)이면 그대로 돌려줍니다.
    - OTSL 토큰이 하나도 없으면 빈 문자열을 돌려줍니다(호출한 쪽에서 원문을 보여 줌).
    """
    stripped = content.strip()
    if is_html_table(stripped):
        return stripped
    return table_data_to_html(parse_otsl(stripped))


# ---------------------------------------------------------------------------
# 수식
# ---------------------------------------------------------------------------
_OPEN_BRACKET = re.compile(r"^\\[\[\(]\s*")
_CLOSE_BRACKET = re.compile(r"\s*\\[\]\)]$")


def _strip_dollars(text: str) -> str:
    """바깥쪽 $$...$$ 또는 $...$ 구분자만 벗겨 냅니다(안쪽의 \\$ 는 보존)."""
    for delim in ("$$", "$"):
        if len(text) >= 2 * len(delim) and text.startswith(delim) and text.endswith(delim):
            if not text.endswith("\\" + delim):
                return text[len(delim) : -len(delim)].strip()
    return text


def post_process(content: str) -> str:
    """수식 결과 정리: \\[ \\] (또는 \\( \\)) 를 제거하고 $$ 로 감쌉니다.

    예) "\\[ x^2 + 1 \\]" → "$$x^2 + 1$$"
        "$$\\[a\\]$$"      → "$$a$$"
    """
    text = content.strip()
    if not text:
        return ""
    # 바깥 $$ → \[ \] → 다시 $$ 순서로 한 겹씩 벗겨 중첩된 구분자도 처리합니다.
    for _ in range(3):
        before = text
        text = _strip_dollars(text)
        text = _CLOSE_BRACKET.sub("", _OPEN_BRACKET.sub("", text)).strip()
        if text == before:
            break
    if not text:
        return ""
    return f"$${text}$$"


def strip_output(content: str) -> str:
    return content.strip()
