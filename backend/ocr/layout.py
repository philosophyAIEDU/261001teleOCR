"""레이아웃 분석 결과 해석.

TeleOCR 공식 저장소(caipeng328/TeleOCR, TeleOCR/vlm_utils/TeleOCR_client.py 의
parse_layout_output)에서 확인한 출력 형식은 한 줄에 영역 하나입니다.

    <box:x1 y1 x2 y2><label:text><up>
    <box:x1 y1 x2 y2 x3 y3 ...><label:table><up>     ← 휘어진 문서(다각형)

- box: 0~1000 으로 정규화된 좌표. 일반 레이아웃은 점 2개(좌상단·우하단),
  휘어진 문서 분석(Multi-point)은 여러 점으로 된 다각형입니다.
- label: 영역 종류(text, title, table, equation, code, image, seal ...)
- 마지막 태그: 글자 방향(up=0°, right=90°, down=180°, left=270°)

실제 모델 출력은 이 개발 환경에서 직접 확인하지 못했으므로(README 참고), 형식에 맞지 않는
줄은 건너뛰고, 한 줄도 해석하지 못하면 호출한 쪽이 원문 텍스트를 그대로 보여 줍니다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

BLOCK_TYPES: frozenset[str] = frozenset(
    {
        "text", "title", "table", "image", "code", "algorithm", "header", "footer",
        "page_number", "page_footnote", "aside_text", "equation", "equation_block",
        "ref_text", "list", "phonetic", "table_caption", "image_caption", "code_caption",
        "table_footnote", "image_footnote", "unknown", "seal", "char",
    }
)

BLOCK_LABELS_KO: dict[str, str] = {
    "text": "본문", "title": "제목", "table": "표", "image": "그림", "code": "코드",
    "algorithm": "알고리즘", "header": "머리글", "footer": "바닥글", "page_number": "쪽 번호",
    "page_footnote": "각주", "aside_text": "옆글", "equation": "수식",
    "equation_block": "수식 묶음", "ref_text": "참고문헌", "list": "목록", "phonetic": "발음 기호",
    "table_caption": "표 제목", "image_caption": "그림 설명", "code_caption": "코드 제목",
    "table_footnote": "표 주석", "image_footnote": "그림 주석", "unknown": "기타",
    "seal": "도장", "char": "그래프",
}

ANGLE_MAPPING: dict[str, int] = {"up": 0, "right": 90, "down": 180, "left": 270}

_LAYOUT_LINE = re.compile(r"^<box:([\d\s]+)><label:(\w+)><([^>]+)>$")
COORD_MAX = 1000


# 모델 카드 예제에서 @dataclass 가 빠져 있던 ContentBlock 을 데코레이터와 함께 정의합니다.
@dataclass
class ContentBlock:
    """레이아웃의 한 영역. points 는 0~1 로 정규화된 [x, y] 목록입니다."""

    type: str
    points: list[list[float]]
    angle: int | None = None
    content: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return (min(xs), min(ys), max(xs), max(ys))

    @property
    def label_ko(self) -> str:
        return BLOCK_LABELS_KO.get(self.type, self.type)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.type,
            "label": self.label_ko,
            "points": self.points,
            "bbox": list(self.bbox),
            "angle": self.angle,
            "content": self.content,
        }


def _parse_points(numbers: str) -> list[list[float]] | None:
    try:
        values = [int(v) for v in numbers.split()]
    except ValueError:
        return None
    if len(values) < 4 or len(values) % 2 != 0:
        return None
    if any(v < 0 or v > COORD_MAX for v in values):
        return None
    points = [[values[i] / COORD_MAX, values[i + 1] / COORD_MAX] for i in range(0, len(values), 2)]
    if len(points) == 2:
        # 점 2개(좌상단·우하단)는 사각형 네 꼭짓점으로 펼쳐 오버레이를 그리기 쉽게 합니다.
        (x1, y1), (x2, y2) = points
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        points = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
    return points


def _parse_angle(tag: str) -> int | None:
    for token, angle in ANGLE_MAPPING.items():
        if token in tag:
            return angle
    return None


def parse_layout_output(output: str) -> list[ContentBlock]:
    """레이아웃 출력 문자열을 ContentBlock 목록으로 바꿉니다. 형식이 틀린 줄은 건너뜁니다."""
    blocks: list[ContentBlock] = []
    for line in output.splitlines():
        match = _LAYOUT_LINE.match(line.strip())
        if not match:
            continue
        numbers, label, tag = match.groups()
        block_type = label.lower()
        if block_type not in BLOCK_TYPES:
            block_type = "unknown"
        points = _parse_points(numbers)
        if points is None:
            continue
        blocks.append(ContentBlock(type=block_type, points=points, angle=_parse_angle(tag)))
    return blocks
