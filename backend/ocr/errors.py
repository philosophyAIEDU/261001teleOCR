"""교사가 이해할 수 있는 한국어 오류 메시지를 담는 예외."""

from __future__ import annotations

OOM_MESSAGE = "메모리가 부족해요. 이미지를 더 작게 잘라서 다시 시도해 주세요."
MODEL_LOAD_MESSAGE = (
    "AI 모델을 불러오지 못했어요. 처음 한 번은 모델을 내려받기 위해 인터넷 연결이 필요해요. "
    "인터넷 연결과 저장 공간(약 5GB)을 확인한 뒤 '시스템 점검' 화면에서 다시 시도해 주세요."
)
LOAD_OOM_MESSAGE = (
    "메모리가 부족해서 AI 모델을 불러오지 못했어요. 다른 프로그램(특히 브라우저 탭)을 닫고 다시 시도해 주세요."
)
INFERENCE_MESSAGE = "변환 중에 문제가 생겼어요. 이미지를 다시 올리거나 영역을 잘라서 시도해 주세요."
MISSING_LIBS_MESSAGE = (
    "AI 실행에 필요한 프로그램(torch, transformers)이 설치되어 있지 않아요. "
    "설치 스크립트(install)를 다시 실행해 주세요."
)


class OcrError(Exception):
    """화면에 그대로 보여 줄 수 있는 한국어 메시지를 가진 예외."""

    def __init__(self, message_ko: str, code: str = "ocr_error", status_code: int = 500) -> None:
        super().__init__(message_ko)
        self.message_ko = message_ko
        self.code = code
        self.status_code = status_code


class ModelLoadError(OcrError):
    def __init__(self, attempts: list[tuple[str, str]], message_ko: str = MODEL_LOAD_MESSAGE) -> None:
        super().__init__(message_ko, code="model_load_failed", status_code=503)
        # (시도한 모델 ID, 영어 원본 오류) 목록. 문제 해결용으로 시스템 점검 화면에 함께 보여 줍니다.
        self.attempts = attempts


def is_out_of_memory(exc: BaseException) -> bool:
    """CUDA/MPS/CPU 메모리 부족 오류인지 판별합니다."""
    if isinstance(exc, MemoryError):
        return True
    name = type(exc).__name__
    text = str(exc).lower()
    return name == "OutOfMemoryError" or "out of memory" in text or "mps backend out of memory" in text
