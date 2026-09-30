import io

import pytest
from docx import Document
from openpyxl import load_workbook

from backend.export import ExportItem, to_docx, to_markdown, to_xlsx
from backend.export.html_table import parse_html_table
from backend.export.markdown_export import formula_to_markdown, table_to_markdown
from backend.export.xlsx_export import NoTableError, _sheet_title, _to_value

SIMPLE = "<table><tr><td>이름</td><td>점수</td></tr><tr><td>민수</td><td>1,234</td></tr></table>"
MERGED = (
    '<table><tr><td rowspan="2">Name</td><td colspan="2">Score</td></tr>'
    "<tr><td>Math</td><td>English</td></tr><tr><td>Minsu</td><td>90</td><td>85.5</td></tr></table>"
)


class TestHtmlTable:
    def test_grid_with_spans(self) -> None:
        table = parse_html_table(MERGED)
        assert (table.num_rows, table.num_cols) == (3, 3)
        assert table.has_spans
        assert table.to_matrix() == [["Name", "Score", ""], ["", "Math", "English"], ["Minsu", "90", "85.5"]]

    def test_th_br_nested_and_bad_span(self) -> None:
        html = '<table><thead><tr><th colspan="x">A<br>B</th></tr></thead><tr><td><table><tr><td>in</td></tr></table>z</td></tr></table>'
        table = parse_html_table(html)
        assert table.to_matrix() == [["A\nB"], ["inz"]]

    def test_cell_without_tr(self) -> None:
        assert parse_html_table("<table><td>a</td></table>").to_matrix() == [["a"]]

    def test_empty(self) -> None:
        table = parse_html_table("")
        assert table.cells == [] and not table.has_spans


class TestMarkdown:
    def test_simple_table_becomes_gfm(self) -> None:
        md = table_to_markdown("<table><tr><td>a|b</td><td>c</td></tr><tr><td>1</td><td>2</td></tr></table>")
        assert md.splitlines() == ["| a\\|b | c |", "| --- | --- |", "| 1 | 2 |"]

    def test_merged_table_kept_as_html(self) -> None:
        assert table_to_markdown(MERGED) == MERGED

    def test_non_table_text_kept(self) -> None:
        assert table_to_markdown("oops") == "oops"

    def test_formula(self) -> None:
        assert formula_to_markdown("$$a+b$$") == "$$\na+b\n$$"
        assert formula_to_markdown("a+b") == "$$\na+b\n$$"
        assert formula_to_markdown("  ") == ""

    def test_document(self) -> None:
        md = to_markdown(
            [
                ExportItem("text", " 안녕하세요 ", "1쪽"),
                ExportItem("code", "print(1)\n"),
                ExportItem("latex", "$$x$$"),
                ExportItem("html_table", SIMPLE),
            ]
        )
        assert md.startswith("## 1쪽\n\n안녕하세요")
        assert "```\nprint(1)\n```" in md
        assert "$$\nx\n$$" in md
        assert "| 이름 | 점수 |" in md
        assert md.endswith("\n")


class TestDocx:
    def test_contains_text_table_formula_code(self) -> None:
        data = to_docx(
            [
                ExportItem("text", "첫 줄\n둘째 줄", "본문"),
                ExportItem("html_table", MERGED, "표"),
                ExportItem("latex", "$$E=mc^2$$"),
                ExportItem("code", "for i in range(3):\n    print(i)"),
                ExportItem("html_table", "not a table"),
            ]
        )
        doc = Document(io.BytesIO(data))
        texts = [p.text for p in doc.paragraphs]
        assert "첫 줄" in texts and "둘째 줄" in texts
        assert "$$E=mc^2$$" in texts
        assert "    print(i)" in texts
        assert "not a table" in texts
        table = doc.tables[0]
        assert table.cell(0, 0).text == "Name"
        assert table.cell(1, 0)._tc is table.cell(0, 0)._tc  # 세로 병합
        assert table.cell(0, 2)._tc is table.cell(0, 1)._tc  # 가로 병합


class TestXlsx:
    def test_merges_numbers_and_sheet_names(self) -> None:
        data = to_xlsx(
            [
                ExportItem("html_table", MERGED, "성적/1반"),
                ExportItem("text", "ignored"),
                ExportItem("html_table", SIMPLE, "성적/1반"),
            ]
        )
        wb = load_workbook(io.BytesIO(data))
        assert wb.sheetnames == ["성적 1반", "성적 1반 (2)"]
        ws = wb["성적 1반"]
        assert {str(r) for r in ws.merged_cells.ranges} == {"A1:A2", "B1:C1"}
        assert ws["B3"].value == 90 and ws["C3"].value == 85.5
        assert wb["성적 1반 (2)"]["B2"].value == 1234

    def test_requires_table(self) -> None:
        with pytest.raises(NoTableError):
            to_xlsx([ExportItem("text", "x")])

    def test_value_conversion(self) -> None:
        assert _to_value("007") == "007"  # 앞자리 0 은 글자로 유지(학번 등)
        assert _to_value("-12") == -12
        assert _to_value("3.5") == 3.5
        assert _to_value("12a") == "12a"
        assert _to_value("1234567890123456789") == "1234567890123456789"

    def test_sheet_title_default(self) -> None:
        assert _sheet_title(None, 3, set()) == "표 3"
        assert _sheet_title("***", 1, set()) == "표 1"
