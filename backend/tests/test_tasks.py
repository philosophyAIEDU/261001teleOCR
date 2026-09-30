from PIL import Image

from backend.ocr.tasks import (
    LAYOUT_IMAGE_SIZE,
    TASK_SPECS,
    ResultFormat,
    TaskType,
    get_spec,
    postprocess_output,
    preprocess_image,
)


def test_prompts_match_model_card_exactly() -> None:
    expected = {
        TaskType.TEXT: "Please output the text content from the image.",
        TaskType.TABLE: "This is the image of a table. Please output the table in OTSL format.",
        TaskType.FORMULA: "Please write out the expression of the formula in the image using LaTeX format.",
        TaskType.CODE: "The image contains a code snippet, please output the parsing result.",
        TaskType.LAYOUT: "Analyze the image layout.",
        TaskType.LAYOUT_DISTORTED: "\nMulti-point Layout Segmentation Analysis.",
        TaskType.CHART: "This is a scientific figure. Please extract the table implied by this figure.",
        TaskType.SEAL: "\nSeal Recognition:",
    }
    assert {t: s.prompt for t, s in TASK_SPECS.items()} == expected


def test_layout_tasks_resize_to_1036() -> None:
    image = Image.new("RGBA", (500, 300))
    for task in (TaskType.LAYOUT, TaskType.LAYOUT_DISTORTED):
        out = preprocess_image(image, get_spec(task))
        assert out.size == LAYOUT_IMAGE_SIZE and out.mode == "RGB"
    kept = preprocess_image(image, get_spec("text"))
    assert kept.size == (500, 300) and kept.mode == "RGB"


def test_postprocess_table_and_fallback() -> None:
    ok = postprocess_output(get_spec(TaskType.TABLE), "<fcel>a<nl>")
    assert ok.result_format == ResultFormat.HTML_TABLE and ok.parsed
    bad = postprocess_output(get_spec(TaskType.CHART), " not a table ")
    assert bad.result_format == ResultFormat.TEXT and not bad.parsed
    assert bad.content == "not a table"


def test_postprocess_layout_and_fallback() -> None:
    ok = postprocess_output(get_spec(TaskType.LAYOUT), "<box:1 2 3 4><label:text><up>")
    assert ok.blocks and ok.blocks[0]["type"] == "text"
    bad = postprocess_output(get_spec(TaskType.LAYOUT), "raw text")
    assert bad.result_format == ResultFormat.TEXT and bad.blocks is None and not bad.parsed


def test_postprocess_formula_and_code() -> None:
    assert postprocess_output(get_spec("formula"), r"\[a\]").content == "$$a$$"
    assert postprocess_output(get_spec("code"), "\nprint(1)\n").content == "print(1)"
