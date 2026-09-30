"""Hugging Face transformers 로 TeleOCR 를 실행하는 백엔드.

모델 카드 예제의 infer() 구조(system 메시지 + 이미지 + 프롬프트 → generate)를 따르되,
- 장치와 dtype 은 device.py 의 자동 감지 결과를 사용하고(.cuda() 하드코딩 제거)
- 모델 ID 는 항상 config.yaml 값을 사용하며(대체 ID 포함)
- revision(커밋 해시)을 고정할 수 있게 했습니다.

네트워크 사용 원칙: 모델이 이미 내 PC 에 있으면(local_files_only) 인터넷에 전혀 접속하지 않습니다.
처음 한 번만 Hugging Face 에서 모델 파일을 내려받습니다.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from PIL import Image

# 모델 다운로드 외의 네트워크 요청(사용 통계 전송 등)을 막습니다. huggingface_hub 를 불러오기 전에 설정해야 합니다.
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("DO_NOT_TRACK", "1")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")

from ..settings import ModelSettings, RuntimeSettings  # noqa: E402
from .base import SYSTEM_PROMPT, BackendStatus, DownloadProgress, OcrBackend  # noqa: E402
from .device import DeviceInfo, detect_device  # noqa: E402
from .errors import INFERENCE_MESSAGE, OOM_MESSAGE, OcrError, is_out_of_memory  # noqa: E402
from .model_loader import load_with_fallback  # noqa: E402

logger = logging.getLogger(__name__)

WEIGHT_SUFFIXES = (".safetensors", ".bin")


def _repo_cache_dir(model_id: str) -> Path:
    from huggingface_hub import constants  # noqa: PLC0415

    return Path(constants.HF_HUB_CACHE) / ("models--" + model_id.replace("/", "--"))


def _has_weights(path: Path) -> bool:
    return any(p.suffix in WEIGHT_SUFFIXES for p in path.glob("*"))


class TransformersBackend(OcrBackend):
    name = "transformers"

    def __init__(self, model_settings: ModelSettings, runtime: RuntimeSettings) -> None:
        self.model_settings = model_settings
        self.runtime = runtime
        self._device: DeviceInfo = detect_device(runtime.device, runtime.cpu_mps_dtype)
        self._load_lock = threading.Lock()
        self._model: Any = None
        self._processor: Any = None
        self._model_id: str | None = None
        self._revision: str | None = None
        self._loading = False
        self._error: str | None = None
        self._attempts: list[tuple[str, str]] = []
        self._progress = DownloadProgress()

    # ------------------------------------------------------------------ 상태
    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def local_snapshot(self) -> tuple[str, Path] | None:
        """이미 내려받은 모델이 있으면 (모델 ID, 로컬 경로) 를 돌려줍니다. 네트워크를 쓰지 않습니다."""
        try:
            from huggingface_hub import snapshot_download  # noqa: PLC0415
        except ImportError:
            return None
        for model_id, revision in self.model_settings.candidates():
            try:
                path = Path(snapshot_download(model_id, revision=revision, local_files_only=True))
            except Exception:  # noqa: BLE001 - 캐시에 없음
                continue
            if _has_weights(path):
                return model_id, path
        return None

    def status(self) -> BackendStatus:
        snapshot = None if self.is_loaded else self.local_snapshot()
        model_id = self._model_id or (snapshot[0] if snapshot else None)
        revision = self._revision or (snapshot[1].name if snapshot else self.model_settings.revision)
        return BackendStatus(
            backend=self.name,
            loaded=self.is_loaded,
            loading=self._loading,
            model_id=model_id,
            revision=revision,
            device=self._device,
            downloaded=self.is_loaded or snapshot is not None,
            download=self._progress,
            error=self._error,
            attempts=list(self._attempts),
        )

    # ------------------------------------------------------------------ 불러오기
    def load(self) -> None:
        with self._load_lock:
            if self.is_loaded:
                return
            self._loading = True
            self._error = None
            self._attempts = []
            try:
                (model, processor, resolved), model_id, _ = load_with_fallback(
                    self.model_settings.candidates(), self._load_one
                )
            except OcrError as exc:
                self._error = exc.message_ko
                self._attempts = list(getattr(exc, "attempts", []))
                raise
            finally:
                self._loading = False
                self._progress.active = False
            self._model, self._processor = model, processor
            self._model_id, self._revision = model_id, resolved
            logger.info("모델 준비 완료: %s @ %s (%s)", model_id, resolved, self._device.kind)

    def _download(self, model_id: str, revision: str | None) -> Path:
        """모델 파일이 캐시에 있으면 그 경로를, 없으면 내려받은 뒤 경로를 돌려줍니다."""
        from huggingface_hub import HfApi, snapshot_download  # noqa: PLC0415

        try:
            path = Path(snapshot_download(model_id, revision=revision, local_files_only=True))
            if _has_weights(path):
                return path
        except Exception:  # noqa: BLE001 - 캐시에 없으면 아래에서 내려받습니다.
            pass

        progress = self._progress
        progress.active, progress.downloaded_bytes, progress.total_bytes = True, 0, None
        try:
            info = HfApi().model_info(model_id, revision=revision, files_metadata=True)
            progress.total_bytes = sum((s.size or 0) for s in (info.siblings or [])) or None
        except Exception:  # noqa: BLE001 - 전체 크기를 몰라도 내려받기는 계속합니다.
            logger.info("모델 전체 크기를 알 수 없어 진행률 없이 내려받습니다.")

        # 내려받는 동안 캐시 폴더 크기를 1초마다 재서 진행률을 계산합니다.
        stop = threading.Event()
        cache_dir = _repo_cache_dir(model_id) / "blobs"

        def watch() -> None:
            while not stop.is_set():
                if cache_dir.exists():
                    progress.downloaded_bytes = sum(
                        f.stat().st_size for f in cache_dir.iterdir() if f.is_file()
                    )
                stop.wait(1.0)

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        try:
            return Path(snapshot_download(model_id, revision=revision))
        finally:
            stop.set()
            watcher.join(timeout=2)
            if progress.total_bytes:
                progress.downloaded_bytes = progress.total_bytes
            progress.active = False

    def _load_one(self, model_id: str, revision: str | None) -> tuple[Any, Any, str]:
        import torch  # noqa: PLC0415
        import transformers  # noqa: PLC0415

        path = self._download(model_id, revision)
        # 스냅샷 폴더 이름이 실제 커밋 해시입니다. revision 을 비워 두었더라도 어떤 버전인지 기록할 수 있어요.
        resolved_revision = path.name
        dtype = getattr(torch, self._device.dtype)

        processor = transformers.AutoProcessor.from_pretrained(
            str(path), trust_remote_code=True, local_files_only=True
        )
        model = None
        last_error: Exception | None = None
        # 공식 저장소(TeleOCR_model.py)와 같은 순서로 모델 클래스를 찾습니다.
        for cls_name in (
            "AutoModelForImageTextToText",
            "AutoModelForVision2Seq",
            "AutoModelForCausalLM",
            "AutoModel",
        ):
            cls = getattr(transformers, cls_name, None)
            if cls is None:
                continue
            try:
                model = cls.from_pretrained(
                    str(path), trust_remote_code=True, torch_dtype=dtype, local_files_only=True
                )
                break
            except ValueError as exc:  # 이 Auto 클래스가 모델 구조를 모름 → 다음 클래스
                last_error = exc
        if model is None:
            raise RuntimeError(f"지원하는 모델 클래스를 찾지 못했습니다: {last_error}")
        model = model.to(self._device.kind).eval()
        return model, processor, resolved_revision

    # ------------------------------------------------------------------ 추론
    def generate(self, image: Image.Image, prompt: str) -> str:
        if not self.is_loaded:
            self.load()
        import torch  # noqa: PLC0415

        processor, model = self._processor, self._model
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]},
        ]
        try:
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = processor(text=[text], images=[image.convert("RGB")], padding=True, return_tensors="pt")
            # 정수(토큰 ID)는 그대로, 실수(이미지 픽셀)만 모델 dtype 으로 바꿔 장치로 옮깁니다.
            inputs = inputs.to(device=self._device.kind, dtype=model.dtype)
            started = time.monotonic()
            with torch.inference_mode():
                output_ids = model.generate(
                    **inputs, max_new_tokens=self.model_settings.max_new_tokens, do_sample=False
                )
            trimmed = output_ids[:, inputs["input_ids"].shape[1] :]
            result = processor.batch_decode(
                trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]
            logger.info("추론 %.1f초", time.monotonic() - started)
            return str(result)
        except Exception as exc:
            if is_out_of_memory(exc):
                self._free_memory(torch)
                raise OcrError(OOM_MESSAGE, code="out_of_memory", status_code=507) from exc
            logger.exception("추론 실패")
            raise OcrError(INFERENCE_MESSAGE, code="inference_failed") from exc

    def _free_memory(self, torch: Any) -> None:
        try:
            if self._device.kind == "cuda":
                torch.cuda.empty_cache()
            elif self._device.kind == "mps":
                torch.mps.empty_cache()
        except Exception:  # noqa: BLE001
            pass
