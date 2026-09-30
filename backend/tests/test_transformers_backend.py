import sys
from pathlib import Path

import pytest
from PIL import Image

from backend.ocr.base import SYSTEM_PROMPT
from backend.ocr.errors import MODEL_LOAD_MESSAGE, OOM_MESSAGE, ModelLoadError, OcrError
from backend.settings import ModelSettings, RuntimeSettings

from .fakes import FakeModel, FakeProcessor, make_fake_hub, make_fake_torch, make_fake_transformers

IDS = ["XingChen-AGI/TeleOCR", "StarDoc-AI/TeleOCR", "StarDoc-AI/NaviDC-OCR"]


@pytest.fixture()
def fake_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):  # type: ignore[no-untyped-def]
    def install(cached: set[str], available: set[str], cuda: bool = False, errors=None):  # type: ignore[no-untyped-def]
        torch = make_fake_torch(cuda=cuda)
        transformers = make_fake_transformers(errors)
        hub = make_fake_hub(tmp_path, cached, available)
        monkeypatch.setitem(sys.modules, "torch", torch)
        monkeypatch.setitem(sys.modules, "transformers", transformers)
        monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
        from backend.ocr.transformers_backend import TransformersBackend

        backend = TransformersBackend(
            ModelSettings(id=IDS[0], fallback_ids=IDS[1:], revision=None, max_new_tokens=4096),
            RuntimeSettings(device="auto", cpu_mps_dtype="float32"),
        )
        return backend, transformers, hub

    FakeModel.generate_error = None
    yield install
    FakeModel.generate_error = None


def test_uses_cached_model_without_network(fake_env) -> None:  # type: ignore[no-untyped-def]
    backend, transformers, hub = fake_env(cached={IDS[0]}, available=set())
    status = backend.status()
    assert status.downloaded and not status.loaded and status.model_id == IDS[0]
    backend.load()
    assert hub.downloads == []  # 캐시에 있으면 네트워크를 쓰지 않음
    assert backend.status().model_id == IDS[0]
    assert backend.status().revision == "c0ffee"
    assert transformers.loaded_paths[0][0] == "AutoModelForImageTextToText"
    assert backend._model.device == "cpu"


def test_downloads_and_falls_back_to_old_id(fake_env) -> None:  # type: ignore[no-untyped-def]
    backend, _, hub = fake_env(cached=set(), available={IDS[2]}, cuda=True)
    assert backend.status().downloaded is False
    backend.load()
    assert hub.downloads == [(IDS[2], None)]
    status = backend.status()
    assert status.model_id == IDS[2]
    assert status.device.kind == "cuda" and status.device.dtype == "bfloat16"
    assert backend._model.device == "cuda"
    assert status.download.total_bytes == 1000 and status.download.percent == 100.0
    backend.load()  # 두 번째 호출은 아무것도 하지 않음
    assert len(hub.downloads) == 1


def test_all_ids_fail(fake_env) -> None:  # type: ignore[no-untyped-def]
    backend, _, _ = fake_env(cached=set(), available=set())
    with pytest.raises(ModelLoadError) as info:
        backend.load()
    assert info.value.message_ko == MODEL_LOAD_MESSAGE
    status = backend.status()
    assert status.error == MODEL_LOAD_MESSAGE
    assert [a[0] for a in status.attempts] == IDS
    assert not status.loading


def test_model_class_fallback(fake_env) -> None:  # type: ignore[no-untyped-def]
    backend, transformers, _ = fake_env(
        cached={IDS[0]}, available=set(),
        errors={"AutoModelForImageTextToText": ValueError("unknown"), "AutoModelForVision2Seq": ValueError("x")},
    )
    backend.load()
    assert transformers.loaded_paths[0][0] == "AutoModelForCausalLM"


def test_no_model_class_works(fake_env) -> None:  # type: ignore[no-untyped-def]
    err = {n: ValueError("no") for n in ("AutoModelForImageTextToText", "AutoModelForVision2Seq", "AutoModelForCausalLM", "AutoModel")}
    backend, _, _ = fake_env(cached={IDS[0]}, available=set(), errors=err)
    with pytest.raises(ModelLoadError):
        backend.load()


def test_generate_builds_chat_and_trims_prompt(fake_env) -> None:  # type: ignore[no-untyped-def]
    backend, _, _ = fake_env(cached={IDS[0]}, available=set())
    out = backend.generate(Image.new("L", (10, 10)), "Please output the text content from the image.")
    assert out == "42 43"  # 입력 토큰(1,2,3)은 잘라 내고 새로 생성한 토큰만 디코딩
    messages = FakeProcessor.last_messages
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1]["content"][0] == {"type": "image"}
    kwargs = backend._model.generate_kwargs
    assert kwargs["max_new_tokens"] == 4096 and kwargs["do_sample"] is False
    assert kwargs["moved_to"] == ("cpu", "float32")


def test_generate_out_of_memory_message(fake_env) -> None:  # type: ignore[no-untyped-def]
    backend, _, _ = fake_env(cached={IDS[0]}, available=set(), cuda=True)
    backend.load()
    FakeModel.generate_error = RuntimeError("CUDA out of memory. Tried to allocate")
    with pytest.raises(OcrError) as info:
        backend.generate(Image.new("RGB", (4, 4)), "x")
    assert info.value.message_ko == OOM_MESSAGE
    assert info.value.code == "out_of_memory"


def test_generate_other_error_message(fake_env) -> None:  # type: ignore[no-untyped-def]
    backend, _, _ = fake_env(cached={IDS[0]}, available=set())
    backend.load()
    FakeModel.generate_error = ValueError("bad")
    with pytest.raises(OcrError) as info:
        backend.generate(Image.new("RGB", (4, 4)), "x")
    assert info.value.code == "inference_failed"
