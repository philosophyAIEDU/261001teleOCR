import pytest

from backend.ocr.errors import LOAD_OOM_MESSAGE, MISSING_LIBS_MESSAGE, MODEL_LOAD_MESSAGE, ModelLoadError, OcrError
from backend.ocr.model_loader import load_with_fallback
from backend.settings import ModelSettings

CANDIDATES = [
    ("XingChen-AGI/TeleOCR", "abc123"),
    ("StarDoc-AI/TeleOCR", None),
    ("StarDoc-AI/NaviDC-OCR", None),
]


class RecordingLoader:
    def __init__(self, fail_ids: set[str], exc: Exception | None = None) -> None:
        self.fail_ids = fail_ids
        self.exc = exc
        self.calls: list[tuple[str, str | None]] = []

    def __call__(self, model_id: str, revision: str | None) -> str:
        self.calls.append((model_id, revision))
        if model_id in self.fail_ids:
            raise self.exc or OSError(f"{model_id} not found")
        return f"model:{model_id}"


def test_first_candidate_success_stops_early() -> None:
    loader = RecordingLoader(set())
    loaded, model_id, revision = load_with_fallback(CANDIDATES, loader)
    assert loaded == "model:XingChen-AGI/TeleOCR"
    assert (model_id, revision) == ("XingChen-AGI/TeleOCR", "abc123")
    assert loader.calls == [("XingChen-AGI/TeleOCR", "abc123")]


def test_falls_back_in_order() -> None:
    loader = RecordingLoader({"XingChen-AGI/TeleOCR"})
    loaded, model_id, _ = load_with_fallback(CANDIDATES, loader)
    assert model_id == "StarDoc-AI/TeleOCR"
    assert [c[0] for c in loader.calls] == ["XingChen-AGI/TeleOCR", "StarDoc-AI/TeleOCR"]


def test_falls_back_to_oldest_name() -> None:
    loader = RecordingLoader({"XingChen-AGI/TeleOCR", "StarDoc-AI/TeleOCR"})
    _, model_id, _ = load_with_fallback(CANDIDATES, loader)
    assert model_id == "StarDoc-AI/NaviDC-OCR"


def test_all_fail_raises_korean_error_with_attempts() -> None:
    loader = RecordingLoader({c[0] for c in CANDIDATES})
    with pytest.raises(ModelLoadError) as info:
        load_with_fallback(CANDIDATES, loader)
    err = info.value
    assert err.message_ko == MODEL_LOAD_MESSAGE
    assert "인터넷" in err.message_ko
    assert [a[0] for a in err.attempts] == [c[0] for c in CANDIDATES]
    assert "OSError" in err.attempts[0][1]
    assert err.status_code == 503


def test_import_error_stops_immediately() -> None:
    loader = RecordingLoader({c[0] for c in CANDIDATES}, ImportError("no torch"))
    with pytest.raises(ModelLoadError) as info:
        load_with_fallback(CANDIDATES, loader)
    assert info.value.message_ko == MISSING_LIBS_MESSAGE
    assert len(loader.calls) == 1


def test_out_of_memory_stops_immediately() -> None:
    loader = RecordingLoader({c[0] for c in CANDIDATES}, RuntimeError("CUDA out of memory"))
    with pytest.raises(ModelLoadError) as info:
        load_with_fallback(CANDIDATES, loader)
    assert info.value.message_ko == LOAD_OOM_MESSAGE
    assert len(loader.calls) == 1


def test_ocr_error_is_propagated() -> None:
    loader = RecordingLoader({c[0] for c in CANDIDATES}, OcrError("직접 만든 오류"))
    with pytest.raises(OcrError, match="직접 만든 오류"):
        load_with_fallback(CANDIDATES, loader)


def test_settings_candidates_order_and_dedupe() -> None:
    settings = ModelSettings(
        id="XingChen-AGI/TeleOCR",
        fallback_ids=["StarDoc-AI/TeleOCR", "XingChen-AGI/TeleOCR", "StarDoc-AI/NaviDC-OCR"],
        revision="deadbeef",
        fallback_revisions={"StarDoc-AI/TeleOCR": "cafe"},
    )
    assert settings.candidates() == [
        ("XingChen-AGI/TeleOCR", "deadbeef"),
        ("StarDoc-AI/TeleOCR", "cafe"),
        ("StarDoc-AI/NaviDC-OCR", None),
    ]
