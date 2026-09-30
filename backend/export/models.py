"""내보내기 입력 모델."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExportItem:
    """내보낼 결과 한 건.

    result_format: "text" | "html_table" | "latex" | "code" | "layout"
    content: 사용자가 화면에서 고친 최종 결과(표는 HTML, 수식은 $$...$$)
    title: 문서 안 소제목(예: "report.pdf - 2쪽")
    """

    result_format: str
    content: str
    title: str | None = None
