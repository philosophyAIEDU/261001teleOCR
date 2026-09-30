"""Markdown(.md) 내보내기."""

from __future__ import annotations

import re

from .html_table import parse_html_table
from .models import ExportItem


def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", "<br>")


def table_to_markdown(html_table: str) -> str:
    """병합 칸이 없으면 Markdown 표로, 있으면 구조를 잃지 않도록 HTML 표 그대로 둡니다."""
    table = parse_html_table(html_table)
    if not table.cells:
        return html_table.strip()
    if table.has_spans:
        return html_table.strip()
    matrix = table.to_matrix()
    lines = ["| " + " | ".join(_escape_cell(c) for c in matrix[0]) + " |"]
    lines.append("| " + " | ".join("---" for _ in matrix[0]) + " |")
    for row in matrix[1:]:
        lines.append("| " + " | ".join(_escape_cell(c) for c in row) + " |")
    return "\n".join(lines)


def formula_to_markdown(content: str) -> str:
    text = content.strip()
    if not text:
        return ""
    if not text.startswith("$$"):
        text = f"$${text}$$"
    # 블록 수식은 $$ 를 별도 줄에 두어야 대부분의 Markdown 편집기가 인식합니다.
    return re.sub(r"^\$\$(.*)\$\$$", lambda m: f"$$\n{m.group(1).strip()}\n$$", text, flags=re.S)


def item_to_markdown(item: ExportItem) -> str:
    fmt = item.result_format
    if fmt == "html_table":
        body = table_to_markdown(item.content)
    elif fmt == "latex":
        body = formula_to_markdown(item.content)
    elif fmt == "code":
        body = f"```\n{item.content.rstrip()}\n```"
    else:
        body = item.content.strip()
    if item.title:
        return f"## {item.title}\n\n{body}"
    return body


def to_markdown(items: list[ExportItem]) -> str:
    return "\n\n".join(item_to_markdown(i) for i in items).strip() + "\n"
