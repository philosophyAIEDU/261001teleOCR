"""모델 ID 대체(fallback) 로직.

TeleOCR 는 공개 후 이름과 조직이 바뀌었습니다.
    StarDoc-AI/NaviDC-OCR  →  StarDoc-AI/TeleOCR  →  XingChen-AGI/TeleOCR (현재 공식)
조직 이관 직후에는 옛 ID 가 리다이렉트되지 않거나, 반대로 새 ID 에 아직 파일이 없을 수 있어서
config.yaml 의 기본 ID 부터 차례로 시도하고, 처음 성공한 ID 를 사용합니다.

동작 원리
1. candidates 목록(기본 ID, 대체 ID...)을 앞에서부터 하나씩 loader(ID, revision) 로 불러 봅니다.
2. 성공하면 (불러온 객체, 사용한 ID, revision) 을 즉시 돌려주고 나머지는 시도하지 않습니다.
3. 실패하면 오류를 기록하고 다음 ID 로 넘어갑니다.
   단, 라이브러리 미설치(ImportError)나 메모리 부족처럼 ID 를 바꿔도 해결되지 않는 오류는 곧바로 중단합니다.
4. 모두 실패하면 교사가 이해할 수 있는 한국어 메시지와 시도 기록을 담은 ModelLoadError 를 던집니다.
"""

from __future__ import annotations

import logging
from typing import Callable, TypeVar

from .errors import LOAD_OOM_MESSAGE, MISSING_LIBS_MESSAGE, ModelLoadError, OcrError, is_out_of_memory

logger = logging.getLogger(__name__)

T = TypeVar("T")


def load_with_fallback(
    candidates: list[tuple[str, str | None]],
    loader: Callable[[str, str | None], T],
) -> tuple[T, str, str | None]:
    attempts: list[tuple[str, str]] = []
    for model_id, revision in candidates:
        try:
            logger.info("모델 불러오기 시도: %s (revision=%s)", model_id, revision or "main")
            loaded = loader(model_id, revision)
        except ImportError as exc:
            raise ModelLoadError([(model_id, repr(exc))], MISSING_LIBS_MESSAGE) from exc
        except OcrError:
            raise
        except Exception as exc:  # noqa: BLE001 - 어떤 오류든 다음 후보로 넘어갑니다.
            if is_out_of_memory(exc):
                raise ModelLoadError([(model_id, repr(exc))], LOAD_OOM_MESSAGE) from exc
            logger.warning("모델 %s 불러오기 실패: %s", model_id, exc)
            attempts.append((model_id, f"{type(exc).__name__}: {exc}"))
            continue
        return loaded, model_id, revision
    raise ModelLoadError(attempts)
