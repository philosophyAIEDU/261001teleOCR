"""GPU·모델 없이 개발/테스트하기 위한 가짜 백엔드.

프롬프트별로 고정된 샘플 출력을 돌려줍니다. 샘플 출력은 실제 모델 출력 형식
(표는 OTSL, 수식은 \\[ \\] 로 감싼 LaTeX, 레이아웃은 <box:...><label:...><up>)을 흉내 냅니다.
"""

from __future__ import annotations

import time

from PIL import Image

from .base import BackendStatus, DownloadProgress, OcrBackend
from .device import DeviceInfo
from .tasks import TASK_SPECS, TaskType

MOCK_OUTPUTS: dict[TaskType, str] = {
    TaskType.TEXT: (
        "The Little Prince\n"
        "It is only with the heart that one can see rightly; "
        "what is essential is invisible to the eye.\n"
    ),
    TaskType.TABLE: (
        "<fcel>Name<fcel>Score<lcel><nl>"
        "<ucel><fcel>Math<fcel>English<nl>"
        "<fcel>Minsu<fcel>90<fcel>85<nl>"
        "<fcel>Jiwoo<fcel>78<ecel><nl>"
    ),
    TaskType.FORMULA: r"\[ x = \frac{-b \pm \sqrt{b^{2}-4ac}}{2a} \]",
    TaskType.CODE: (
        "def average(scores):\n"
        "    total = sum(scores)\n"
        "    return total / len(scores)\n\n"
        "print(average([90, 85, 78]))\n"
    ),
    TaskType.LAYOUT: (
        "<box:080 050 920 110><label:title><up>\n"
        "<box:080 140 920 420><label:text><up>\n"
        "<box:080 450 920 700><label:table><up>\n"
        "<box:300 730 700 800><label:equation><up>\n"
        "<box:450 940 550 970><label:page_number><up>"
    ),
    TaskType.LAYOUT_DISTORTED: (
        "<box:090 060 900 080 905 130 095 120><label:title><up>\n"
        "<box:085 160 910 150 915 460 080 470><label:text><up>\n"
        "<box:080 500 920 490 925 760 075 770><label:table><up>"
    ),
    TaskType.CHART: (
        "<fcel>Month<fcel>Temperature (°C)<nl>"
        "<fcel>Jan<fcel>-2.4<nl>"
        "<fcel>Apr<fcel>12.5<nl>"
        "<fcel>Jul<fcel>25.7<nl>"
        "<fcel>Oct<fcel>14.8<nl>"
    ),
    TaskType.SEAL: "SAMPLE SCHOOL SEAL",
}

_PROMPT_TO_TASK: dict[str, TaskType] = {spec.prompt: task for task, spec in TASK_SPECS.items()}


class MockBackend(OcrBackend):
    name = "mock"

    def __init__(self, delay_seconds: float = 0.0) -> None:
        self.delay_seconds = delay_seconds
        self._loaded = False
        self.calls: list[str] = []

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        self._loaded = True

    def generate(self, image: Image.Image, prompt: str) -> str:
        if not self._loaded:
            self.load()
        self.calls.append(prompt)
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        task = _PROMPT_TO_TASK.get(prompt, TaskType.TEXT)
        return MOCK_OUTPUTS[task]

    def status(self) -> BackendStatus:
        return BackendStatus(
            backend=self.name,
            loaded=self._loaded,
            loading=False,
            model_id="mock (샘플 결과)",
            revision=None,
            device=DeviceInfo("cpu", "개발용 가짜 백엔드", "float32"),
            downloaded=True,
            download=DownloadProgress(),
        )
