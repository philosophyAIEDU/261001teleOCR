import asyncio
import threading
import time

import pytest
from PIL import Image

from backend.ocr.base import BackendStatus
from backend.ocr.device import DeviceInfo
from backend.ocr.errors import ModelLoadError
from backend.ocr.layout import ContentBlock
from backend.ocr.mock_backend import MOCK_OUTPUTS, MockBackend
from backend.ocr.service import OcrService, block_to_markdown, create_backend, crop_block
from backend.ocr.tasks import ResultFormat, TaskOutput, TaskType
from backend.settings import AppSettings


class SlowBackend(MockBackend):
    """동시에 몇 건이 실행되는지 기록하는 느린 백엔드."""

    def __init__(self) -> None:
        super().__init__(delay_seconds=0.05)
        self.active = 0
        self.max_active = 0
        self._guard = threading.Lock()

    def generate(self, image: Image.Image, prompt: str) -> str:
        with self._guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            return super().generate(image, prompt)
        finally:
            with self._guard:
                self.active -= 1


async def test_only_one_inference_at_a_time() -> None:
    backend = SlowBackend()
    service = OcrService(backend)
    image = Image.new("RGB", (32, 32), "white")
    seen_waiting: list[int] = []

    async def watch() -> None:
        for _ in range(10):
            seen_waiting.append(service.queue_size)
            await asyncio.sleep(0.01)

    results = await asyncio.gather(*(service.convert(image, "text") for _ in range(5)), watch())
    assert backend.max_active == 1
    assert max(seen_waiting) >= 1
    assert all(r.output.content for r in results[:5])
    assert service.queue_size == 0 and not service.busy


async def test_cancelled_request_keeps_lock_until_thread_finishes() -> None:
    backend = SlowBackend()
    service = OcrService(backend)
    image = Image.new("RGB", (32, 32))
    first = asyncio.create_task(service.convert(image, "text"))
    await asyncio.sleep(0.01)
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    await service.convert(image, "text")
    assert backend.max_active == 1


async def test_model_loaded_once_on_first_request() -> None:
    backend = MockBackend()
    service = OcrService(backend)
    assert not backend.is_loaded
    await service.convert(Image.new("RGB", (16, 16)), TaskType.FORMULA)
    assert backend.is_loaded


class FailingBackend(MockBackend):
    def load(self) -> None:
        raise ModelLoadError([("x", "boom")])

    def status(self) -> BackendStatus:
        return BackendStatus("f", False, False, None, None, DeviceInfo("cpu", "c", "float32"), False)


async def test_start_loading_swallows_error() -> None:
    service = OcrService(FailingBackend())
    service.start_loading()
    await asyncio.sleep(0.05)
    assert service._load_task is not None and service._load_task.done()
    with pytest.raises(ModelLoadError):
        await service.convert(Image.new("RGB", (16, 16)), "text")


async def test_start_loading_success_and_noop_when_loaded() -> None:
    backend = MockBackend()
    service = OcrService(backend)
    service.start_loading()
    await asyncio.sleep(0.01)
    assert backend.is_loaded
    service.start_loading()  # 이미 불러왔으면 아무것도 하지 않음


async def test_parse_page_assembles_markdown() -> None:
    backend = MockBackend()
    service = OcrService(backend)
    markdown, blocks = await service.parse_page(Image.new("RGB", (400, 600), "white"))
    assert len(blocks) == 5
    assert markdown.startswith("## The Little Prince")
    assert "<table>" in markdown and "$$x = " in markdown
    # 쪽 번호(page_number)는 건너뜀 → 레이아웃 1회 + 영역 4개
    assert len(backend.calls) == 5
    assert "Analyze the image layout." == backend.calls[0]


async def test_parse_page_distorted_uses_multipoint_prompt() -> None:
    backend = MockBackend()
    markdown, blocks = await OcrService(backend).parse_page(Image.new("RGB", (300, 300)), distorted=True)
    assert backend.calls[0] == "\nMulti-point Layout Segmentation Analysis."
    assert len(blocks) == 3 and markdown


class NoLayoutBackend(MockBackend):
    def generate(self, image: Image.Image, prompt: str) -> str:
        self.calls.append(prompt)
        return "no layout here" if "layout" in prompt else "plain text"


async def test_parse_page_without_layout_falls_back_to_text() -> None:
    markdown, blocks = await OcrService(NoLayoutBackend()).parse_page(Image.new("RGB", (100, 100)))
    assert (markdown, blocks) == ("plain text", [])


def test_crop_block_rectangle_polygon_and_rotation() -> None:
    image = Image.new("RGB", (200, 100), (0, 0, 0))
    rect = ContentBlock("text", [[0.0, 0.0], [0.5, 0.0], [0.5, 1.0], [0.0, 1.0]])
    assert crop_block(image, rect).size == (100, 100)
    rotated = ContentBlock("text", [[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]], angle=90)
    assert crop_block(image, rotated).size == (50, 100)
    polygon = ContentBlock("text", [[0, 0], [1, 0], [1, 1], [0.5, 1], [0, 1]])
    assert crop_block(image, polygon).size == (200, 100)
    tiny = ContentBlock("text", [[0, 0], [0.01, 0], [0.01, 0.01], [0, 0.01]])
    assert crop_block(image, tiny) is None


def test_block_to_markdown_variants() -> None:
    title = ContentBlock("title", [[0, 0], [1, 1]])
    out = TaskOutput(TaskType.TEXT, ResultFormat.TEXT, "", "Hello\nWorld")
    assert block_to_markdown(title, out) == "## Hello World"
    code = TaskOutput(TaskType.CODE, ResultFormat.CODE, "", "x = 1")
    assert block_to_markdown(ContentBlock("code", [[0, 0], [1, 1]]), code) == "```\nx = 1\n```"
    empty = TaskOutput(TaskType.TEXT, ResultFormat.TEXT, "", "  ")
    assert block_to_markdown(title, empty) == ""


def test_create_backend_by_name() -> None:
    settings = AppSettings()
    settings.runtime.backend = "mock"
    assert isinstance(create_backend(settings), MockBackend)
    settings.runtime.backend = "transformers"
    assert create_backend(settings).name == "transformers"
    settings.runtime.backend = "nope"
    with pytest.raises(ValueError):
        create_backend(settings)


def test_mock_backend_basics() -> None:
    backend = MockBackend(delay_seconds=0.001)
    started = time.monotonic()
    assert backend.generate(Image.new("RGB", (4, 4)), "unknown prompt") == MOCK_OUTPUTS[TaskType.TEXT]
    assert time.monotonic() - started >= 0.001
    assert backend.status().downloaded
