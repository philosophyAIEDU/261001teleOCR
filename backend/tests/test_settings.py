from pathlib import Path

import pytest

from backend.settings import DEFAULT_CONFIG_PATH, load_settings


def test_default_config_file() -> None:
    settings = load_settings(DEFAULT_CONFIG_PATH)
    assert settings.model.id == "XingChen-AGI/TeleOCR"
    assert settings.model.fallback_ids == ["StarDoc-AI/TeleOCR", "StarDoc-AI/NaviDC-OCR"]
    assert settings.model.max_new_tokens == 4096
    assert settings.server.host == "127.0.0.1" and settings.server.port == 8765
    assert settings.server.max_upload_bytes == 50 * 1024 * 1024


def test_custom_values_and_forced_localhost(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEOCR_BACKEND", raising=False)
    path = tmp_path / "c.yaml"
    path.write_text(
        "model:\n  id: my/model\n  fallback_ids: []\n  revision: abc123\n"
        "runtime:\n  device: CPU\n  cpu_mps_dtype: bfloat16\n"
        "server:\n  host: 0.0.0.0\n  port: 9000\n  open_browser: false\n",
        encoding="utf-8",
    )
    settings = load_settings(path)
    assert settings.model.candidates() == [("my/model", "abc123")]
    assert settings.runtime.device == "cpu" and settings.runtime.cpu_mps_dtype == "bfloat16"
    assert settings.server.host == "127.0.0.1"  # 외부 공개 주소는 무시
    assert settings.server.port == 9000 and settings.server.open_browser is False


def test_missing_file_and_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEOCR_BACKEND", "mock")
    settings = load_settings(tmp_path / "none.yaml")
    assert settings.runtime.backend == "mock"
    assert settings.model.fallback_ids == ["StarDoc-AI/TeleOCR", "StarDoc-AI/NaviDC-OCR"]
    empty = tmp_path / "empty.yaml"
    empty.write_text("- just a list\n", encoding="utf-8")
    assert load_settings(empty).model.id == "XingChen-AGI/TeleOCR"
