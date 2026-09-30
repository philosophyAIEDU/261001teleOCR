"""작업 유형 → 프롬프트 / 전처리 / 후처리 매핑.

프롬프트 문구는 모델이 학습한 문장과 한 글자라도 다르면 품질이 떨어질 수 있으므로
모델 카드에 적힌 문구를 그대로 사용합니다. 도장 인식 프롬프트는 모델 카드에 없어서
공식 GitHub 저장소(TeleOCR/vlm_utils/TeleOCR_client.py 의 DEFAULT_PROMPTS["seal"])에서
확인한 문구를 사용합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from PIL import Image

from .layout import parse_layout_output
from .postprocess import convert_otsl_to_html, post_process, strip_output

LAYOUT_IMAGE_SIZE = (1036, 1036)


class TaskType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    FORMULA = "formula"
    CODE = "code"
    LAYOUT = "layout"
    LAYOUT_DISTORTED = "layout_distorted"
    CHART = "chart"
    SEAL = "seal"


class ResultFormat(str, Enum):
    TEXT = "text"
    HTML_TABLE = "html_table"
    LATEX = "latex"
    CODE = "code"
    LAYOUT = "layout"


@dataclass(frozen=True)
class TaskSpec:
    task: TaskType
    prompt: str
    name_ko: str
    emoji: str
    description_ko: str
    result_format: ResultFormat
    resize_to: tuple[int, int] | None = None


TASK_SPECS: dict[TaskType, TaskSpec] = {
    TaskType.TEXT: TaskSpec(
        TaskType.TEXT,
        "Please output the text content from the image.",
        "글자 뽑기", "📝", "사진 속 글자를 편집할 수 있는 텍스트로 바꿔요.",
        ResultFormat.TEXT,
    ),
    TaskType.TABLE: TaskSpec(
        TaskType.TABLE,
        "This is the image of a table. Please output the table in OTSL format.",
        "표 만들기", "📊", "표 사진을 고칠 수 있는 표로 바꾸고 엑셀로 내보내요.",
        ResultFormat.HTML_TABLE,
    ),
    TaskType.FORMULA: TaskSpec(
        TaskType.FORMULA,
        "Please write out the expression of the formula in the image using LaTeX format.",
        "수식 변환", "➗", "수식 사진을 LaTeX 수식으로 바꿔요.",
        ResultFormat.LATEX,
    ),
    TaskType.CODE: TaskSpec(
        TaskType.CODE,
        "The image contains a code snippet, please output the parsing result.",
        "코드 옮기기", "💻", "교재 속 코드 사진을 실행할 수 있는 코드로 옮겨요.",
        ResultFormat.CODE,
    ),
    TaskType.LAYOUT: TaskSpec(
        TaskType.LAYOUT,
        "Analyze the image layout.",
        "문서 구조 분석", "🗂️", "제목·본문·표·그림이 어디 있는지 찾아 표시해요.",
        ResultFormat.LAYOUT,
        LAYOUT_IMAGE_SIZE,
    ),
    TaskType.LAYOUT_DISTORTED: TaskSpec(
        TaskType.LAYOUT_DISTORTED,
        "\nMulti-point Layout Segmentation Analysis.",
        "휘어진 사진 분석", "📱", "비스듬히·휘어지게 찍은 사진의 구조를 찾아요.",
        ResultFormat.LAYOUT,
        LAYOUT_IMAGE_SIZE,
    ),
    TaskType.CHART: TaskSpec(
        TaskType.CHART,
        "This is a scientific figure. Please extract the table implied by this figure.",
        "그래프→데이터표", "📈", "그래프 그림에서 데이터 표를 뽑아내요.",
        ResultFormat.HTML_TABLE,
    ),
    TaskType.SEAL: TaskSpec(
        TaskType.SEAL,
        "\nSeal Recognition:",
        "도장 인식", "🔖", "도장(인장) 속 글자를 읽어요.",
        ResultFormat.TEXT,
    ),
}


def get_spec(task: TaskType | str) -> TaskSpec:
    return TASK_SPECS[TaskType(task)]


def preprocess_image(image: Image.Image, spec: TaskSpec) -> Image.Image:
    """모델 입력 전처리: RGB 변환, 레이아웃 작업이면 1036×1036(BICUBIC) 리사이즈."""
    rgb = image.convert("RGB") if image.mode != "RGB" else image
    if spec.resize_to is not None:
        rgb = rgb.resize(spec.resize_to, Image.Resampling.BICUBIC)
    return rgb


@dataclass
class TaskOutput:
    """후처리가 끝난 결과. content 가 비어 있으면 화면에서 raw 원문을 보여 줍니다."""

    task: TaskType
    result_format: ResultFormat
    raw: str
    content: str
    blocks: list[dict[str, object]] | None = None
    parsed: bool = True


def _table_output(spec: TaskSpec, raw: str) -> TaskOutput:
    html_table = convert_otsl_to_html(raw)
    if not html_table:
        return TaskOutput(spec.task, ResultFormat.TEXT, raw, strip_output(raw), parsed=False)
    return TaskOutput(spec.task, spec.result_format, raw, html_table)


def _layout_output(spec: TaskSpec, raw: str) -> TaskOutput:
    blocks = parse_layout_output(raw)
    if not blocks:
        # 형식을 해석하지 못하면 원문 텍스트를 그대로 보여 줍니다.
        return TaskOutput(spec.task, ResultFormat.TEXT, raw, strip_output(raw), parsed=False)
    return TaskOutput(
        spec.task, spec.result_format, raw, strip_output(raw), [b.to_dict() for b in blocks]
    )


_POSTPROCESSORS: dict[ResultFormat, Callable[[TaskSpec, str], TaskOutput]] = {
    ResultFormat.TEXT: lambda s, r: TaskOutput(s.task, s.result_format, r, strip_output(r)),
    ResultFormat.CODE: lambda s, r: TaskOutput(s.task, s.result_format, r, strip_output(r)),
    ResultFormat.LATEX: lambda s, r: TaskOutput(s.task, s.result_format, r, post_process(r)),
    ResultFormat.HTML_TABLE: _table_output,
    ResultFormat.LAYOUT: _layout_output,
}


def postprocess_output(spec: TaskSpec, raw: str) -> TaskOutput:
    return _POSTPROCESSORS[spec.result_format](spec, raw)
