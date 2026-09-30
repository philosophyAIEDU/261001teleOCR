"""모델 싱글톤 + 추론 큐.

추론 큐 동작 원리
- 모델은 메모리를 많이 쓰기 때문에 한 번에 한 건만 계산해야 안전합니다(동시에 두 건이면 메모리 부족 위험).
- asyncio.Lock 하나로 모든 추론을 줄 세웁니다. 먼저 온 요청이 락을 잡고, 나머지는 await 에서 차례를 기다립니다.
- 실제 계산(generate)은 블로킹 함수라 asyncio.to_thread 로 별도 스레드에서 실행합니다.
  그래서 계산 중에도 서버는 진행 상황 조회 같은 다른 요청에 응답할 수 있습니다.
- 대기 중인 요청 수(queue_size)를 세어 화면에 "앞에 n건 대기 중"을 보여 줄 수 있게 합니다.

모델 불러오기는 첫 추론 요청(또는 '시스템 점검'의 불러오기 버튼) 때 한 번만 수행됩니다.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from PIL import Image

from ..settings import AppSettings
from .base import OcrBackend
from .errors import OcrError
from .layout import ContentBlock, parse_layout_output
from .mock_backend import MockBackend
from .tasks import TaskOutput, TaskType, get_spec, postprocess_output, preprocess_image

# 전체 페이지 자동 파싱에서 레이아웃 영역 종류 → 사용할 작업
BLOCK_TASKS: dict[str, TaskType] = {
    "table": TaskType.TABLE,
    "equation": TaskType.FORMULA,
    "code": TaskType.CODE,
    "algorithm": TaskType.CODE,
    "seal": TaskType.SEAL,
    "char": TaskType.CHART,
}
# 글자로 읽지 않는 영역(그림) 과 공식 파이프라인이 건너뛰는 영역
SKIP_BLOCKS = {"image", "list", "equation_block"}
PARATEXT_BLOCKS = {"header", "footer", "page_number", "aside_text", "page_footnote", "unknown"}


def create_backend(settings: AppSettings) -> OcrBackend:
    """설정에 맞는 백엔드를 만듭니다. GgufBackend/MlxBackend 를 추가하면 여기에 분기를 넣습니다."""
    name = settings.runtime.backend.lower()
    if name == "mock":
        return MockBackend()
    if name == "transformers":
        from .transformers_backend import TransformersBackend  # noqa: PLC0415

        return TransformersBackend(settings.model, settings.runtime)
    raise ValueError(f"알 수 없는 백엔드: {settings.runtime.backend}")


@dataclass
class ConvertResult:
    output: TaskOutput
    elapsed_seconds: float


class OcrService:
    def __init__(self, backend: OcrBackend) -> None:
        self.backend = backend
        self._infer_lock = asyncio.Lock()
        self._load_lock = asyncio.Lock()
        self._waiting = 0
        self._load_task: asyncio.Task[None] | None = None

    @property
    def queue_size(self) -> int:
        return self._waiting

    @property
    def busy(self) -> bool:
        return self._infer_lock.locked()

    async def ensure_loaded(self) -> None:
        if self.backend.is_loaded:
            return
        async with self._load_lock:
            if not self.backend.is_loaded:
                await asyncio.to_thread(self.backend.load)

    def start_loading(self) -> None:
        """시스템 점검 화면에서 '모델 준비' 버튼을 누르면 백그라운드로 불러오기를 시작합니다."""
        if self.backend.is_loaded or (self._load_task and not self._load_task.done()):
            return

        async def runner() -> None:
            try:
                await self.ensure_loaded()
            except OcrError:
                pass  # 오류 내용은 backend.status().error 로 화면에 보여 줍니다.

        self._load_task = asyncio.get_running_loop().create_task(runner())

    async def _generate(self, image: Image.Image, prompt: str) -> str:
        await self.ensure_loaded()
        self._waiting += 1
        try:
            await self._infer_lock.acquire()  # ← 여기서 한 번에 한 건만 통과합니다.
        finally:
            self._waiting -= 1  # 차례가 왔거나(또는 요청이 취소되어) 대기열에서 빠집니다.
        # 사용자가 창을 닫아 요청이 취소되어도 스레드의 계산은 멈출 수 없으므로,
        # 락은 요청이 아니라 "계산이 실제로 끝났을 때" 풀어야 두 계산이 겹치지 않습니다.
        job = asyncio.ensure_future(asyncio.to_thread(self.backend.generate, image, prompt))
        job.add_done_callback(lambda _: self._infer_lock.release())
        return await asyncio.shield(job)

    async def convert(self, image: Image.Image, task: TaskType | str) -> ConvertResult:
        spec = get_spec(task)
        started = time.monotonic()
        raw = await self._generate(preprocess_image(image, spec), spec.prompt)
        output = postprocess_output(spec, raw)
        return ConvertResult(output, time.monotonic() - started)

    async def parse_page(self, image: Image.Image, distorted: bool = False) -> tuple[str, list[dict[str, object]]]:
        """전체 페이지 자동 파싱: 레이아웃 분석 → 영역별 추론 → 하나의 Markdown 문서로 조립."""
        layout_task = TaskType.LAYOUT_DISTORTED if distorted else TaskType.LAYOUT
        spec = get_spec(layout_task)
        raw = await self._generate(preprocess_image(image, spec), spec.prompt)
        blocks = parse_layout_output(raw)
        if not blocks:
            # 레이아웃을 해석하지 못하면 페이지 전체를 글자 뽑기로 처리합니다.
            result = await self.convert(image, TaskType.TEXT)
            return result.output.content, []

        rgb = image.convert("RGB")
        parts: list[str] = []
        for block in blocks:
            if block.type in SKIP_BLOCKS or block.type in PARATEXT_BLOCKS:
                continue
            crop = crop_block(rgb, block)
            if crop is None:
                continue
            task = BLOCK_TASKS.get(block.type, TaskType.TEXT)
            result = await self.convert(crop, task)
            block.content = result.output.content
            parts.append(block_to_markdown(block, result.output))
        return "\n\n".join(p for p in parts if p.strip()), [b.to_dict() for b in blocks]


def crop_block(image: Image.Image, block: ContentBlock, min_edge: int = 8) -> Image.Image | None:
    """정규화 좌표 영역을 잘라 냅니다. 다각형이면 바깥을 흰색으로 칠하고, 회전된 글자는 바로 세웁니다."""
    from PIL import ImageDraw  # noqa: PLC0415

    w, h = image.size
    x1, y1, x2, y2 = block.bbox
    box = (int(x1 * w), int(y1 * h), int(round(x2 * w)), int(round(y2 * h)))
    if box[2] - box[0] < min_edge or box[3] - box[1] < min_edge:
        return None
    crop = image.crop(box)
    if len(block.points) > 4:
        mask = Image.new("L", crop.size, 0)
        pts = [(p[0] * w - box[0], p[1] * h - box[1]) for p in block.points]
        ImageDraw.Draw(mask).polygon(pts, fill=255)
        white = Image.new("RGB", crop.size, (255, 255, 255))
        crop = Image.composite(crop, white, mask)
    if block.angle in (90, 180, 270):
        crop = crop.rotate(block.angle, expand=True)
    return crop


def block_to_markdown(block: ContentBlock, output: TaskOutput) -> str:
    content = (output.content or "").strip()
    if not content:
        return ""
    if block.type == "title":
        return "## " + content.replace("\n", " ")
    if output.task == TaskType.CODE:
        return f"```\n{content}\n```"
    return content
