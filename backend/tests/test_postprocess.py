from backend.ocr.postprocess import (
    TableCell,
    TableData,
    convert_otsl_to_html,
    is_html_table,
    parse_otsl,
    post_process,
    strip_output,
)


class TestOtslToHtml:
    def test_simple_table(self) -> None:
        otsl = "<fcel>A<fcel>B<nl><fcel>1<fcel>2<nl>"
        assert convert_otsl_to_html(otsl) == (
            "<table><tr><td>A</td><td>B</td></tr><tr><td>1</td><td>2</td></tr></table>"
        )

    def test_colspan(self) -> None:
        otsl = "<fcel>제목<lcel><lcel><nl><fcel>a<fcel>b<fcel>c<nl>"
        html = convert_otsl_to_html(otsl)
        assert '<td colspan="3">제목</td>' in html
        assert html.count("<tr>") == 2

    def test_rowspan(self) -> None:
        otsl = "<fcel>이름<fcel>국어<nl><ucel><fcel>90<nl>"
        html = convert_otsl_to_html(otsl)
        assert '<td rowspan="2">이름</td>' in html
        # 두 번째 행에는 병합으로 가려진 칸이 없어야 합니다.
        assert html.endswith("<tr><td>90</td></tr></table>")

    def test_rowspan_and_colspan_with_xcel(self) -> None:
        otsl = "<fcel>X<lcel><fcel>c<nl><ucel><xcel><fcel>d<nl><fcel>e<fcel>f<fcel>g<nl>"
        table = parse_otsl(otsl)
        first = table.cells[0]
        assert (first.row_span, first.col_span, first.text) == (2, 2, "X")
        html = convert_otsl_to_html(otsl)
        assert '<td rowspan="2" colspan="2">X</td>' in html
        assert "<tr><td>d</td></tr>" in html

    def test_merged_header_example(self) -> None:
        otsl = "<fcel>Name<fcel>Score<lcel><nl><ucel><fcel>Math<fcel>English<nl><fcel>Minsu<fcel>90<fcel>85<nl>"
        html = convert_otsl_to_html(otsl)
        assert '<td rowspan="2">Name</td><td colspan="2">Score</td>' in html

    def test_empty_cells(self) -> None:
        otsl = "<fcel>a<ecel><nl><ecel><fcel>b<nl>"
        assert convert_otsl_to_html(otsl) == (
            "<table><tr><td>a</td><td></td></tr><tr><td></td><td>b</td></tr></table>"
        )

    def test_fcel_without_text_is_empty(self) -> None:
        assert convert_otsl_to_html("<fcel><fcel>x<nl>") == "<table><tr><td></td><td>x</td></tr></table>"

    def test_short_rows_are_padded(self) -> None:
        table = parse_otsl("<fcel>a<fcel>b<fcel>c<nl><fcel>d<nl>")
        assert table.num_cols == 3
        assert len([c for c in table.cells if c.start_row == 1]) == 3

    def test_missing_final_newline(self) -> None:
        assert convert_otsl_to_html("<fcel>a<fcel>b") == "<table><tr><td>a</td><td>b</td></tr></table>"

    def test_orphan_merge_tokens_become_empty_cells(self) -> None:
        html = convert_otsl_to_html("<lcel><fcel>a<nl><ucel><fcel>b<nl>")
        assert html == "<table><tr><td></td><td>a</td></tr><tr><td></td><td>b</td></tr></table>"

    def test_text_is_html_escaped(self) -> None:
        assert "<td>a &lt; b &amp; c</td>" in convert_otsl_to_html("<fcel>a < b & c<nl>")

    def test_otsl_wrapper_tags_ignored(self) -> None:
        assert convert_otsl_to_html("<otsl><fcel>a<nl></otsl>") == "<table><tr><td>a</td></tr></table>"

    def test_html_input_passes_through(self) -> None:
        html = "<table><tr><td rowspan=\"2\">x</td></tr></table>"
        assert convert_otsl_to_html(html) == html
        assert convert_otsl_to_html(f"  {html}\n") == html
        assert is_html_table("<TABLE border='1'><tr><td>1</td></tr></TABLE>")

    def test_no_otsl_tokens_returns_empty(self) -> None:
        assert convert_otsl_to_html("그냥 글자") == ""
        assert convert_otsl_to_html("") == ""

    def test_dataclasses_are_constructible(self) -> None:
        # 모델 카드 예제의 @dataclass 누락 버그가 고쳐졌는지 확인합니다.
        cell = TableCell(text="a", start_row=0, start_col=1, row_span=2)
        assert cell.col_span == 1 and cell.row_span == 2
        assert TableData(num_rows=1, num_cols=1, cells=[cell]).cells[0] is cell


class TestFormula:
    def test_removes_display_brackets_and_wraps(self) -> None:
        assert post_process(r"\[ x^2 + 1 \]") == "$$x^2 + 1$$"

    def test_removes_inline_brackets(self) -> None:
        assert post_process(r"\(\frac{1}{2}\)") == r"$$\frac{1}{2}$$"

    def test_already_wrapped_in_double_dollar(self) -> None:
        assert post_process("$$a+b$$") == "$$a+b$$"

    def test_nested_dollar_and_brackets(self) -> None:
        assert post_process(r"$$\[a=b\]$$") == "$$a=b$$"

    def test_single_dollar(self) -> None:
        assert post_process("$y=mx$") == "$$y=mx$$"

    def test_plain_latex_is_wrapped(self) -> None:
        assert post_process(r"  E=mc^{2} ") == "$$E=mc^{2}$$"

    def test_inner_brackets_preserved(self) -> None:
        assert post_process(r"\[\frac{\[a\]}{2}\]") == r"$$\frac{\[a\]}{2}$$"

    def test_escaped_dollar_is_kept(self) -> None:
        assert post_process(r"\$5 + 3") == r"$$\$5 + 3$$"

    def test_empty(self) -> None:
        assert post_process("  ") == ""
        assert post_process(r"\[ \]") == ""


def test_strip_output() -> None:
    assert strip_output("\n  hello \n") == "hello"
