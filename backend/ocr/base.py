"""OcrBackend 추상 인터페이스.

백엔드는 "이미지 + 프롬프트 → 모델 출력 문자열" 한 가지 일만 합니다.
작업별 프롬프트·전처리·후처리(tasks.py)와 동시 실행 제어(service.py)는 백엔드 밖에서
처리하므로, 나중에 GgufBackend(llama.cpp)나 MlxBackend(Apple) 를 추가할 때도
load() / generate() / 상태 정보만 구현하면 됩니다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from PIL import Image

from .device import DeviceInfo

SYSTEM_PROMPT = "You are a helpful assistant."


@dataclass
class DownloadProgress:
    """모델 내려받기 진행 상황(바이트 단위)."""

    active: bool = False
    downloaded_bytes: int = 0
    total_bytes: int | None = None

    @property
    def percent(self) -> float | None:
        if not self.total_bytes:
            return None
        return min(100.0, 100.0 * self.downloaded_bytes / self.total_bytes)


@dataclass
class BackendStatus:
    backend: str
    loaded: bool
    loading: bool
    model_id: str | None
    revision: str | None
    device: DeviceInfo
    downloaded: bool
    download: DownloadProgress = field(default_factory=DownloadProgress)
    error: str | None = None
    attempts: list[tuple[str, str]] = field(default_factory=list)


class OcrBackend(ABC):
    """모든 추론 백엔드가 따라야 하는 인터페이스."""

    name: str = "base"

    @abstractmethod
    def load(self) -> None:
        """모델을 메모리에 올립니다. 실패하면 OcrError 를 던집니다. (블로킹 함수)"""

    @abstractmethod
    def generate(self, image: Image.Image, prompt: str) -> str:
        """RGB 이미지와 프롬프트로 추론해 원본 출력 문자열을 돌려줍니다. (블로킹 함수)"""

    @property
    @abstractmethod
    def is_loaded(self) -> bool: ...

    @abstractmethod
    def status(self) -> BackendStatus: ...
