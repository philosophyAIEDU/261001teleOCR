"""config.yaml 을 읽어 앱 설정 객체로 만드는 모듈."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
DEFAULT_CONFIG_PATH = BACKEND_DIR / "config.yaml"

# 서버는 이 컴퓨터 안에서만 접속되도록 루프백 주소에만 바인딩합니다.
LOCAL_HOST = "127.0.0.1"


@dataclass
class ModelSettings:
    id: str = "XingChen-AGI/TeleOCR"
    fallback_ids: list[str] = field(
        default_factory=lambda: ["StarDoc-AI/TeleOCR", "StarDoc-AI/NaviDC-OCR"]
    )
    revision: str | None = None
    fallback_revisions: dict[str, str] = field(default_factory=dict)
    max_new_tokens: int = 4096

    def candidates(self) -> list[tuple[str, str | None]]:
        """(모델 ID, revision) 시도 순서를 돌려줍니다. 중복 ID 는 한 번만 시도합니다."""
        result: list[tuple[str, str | None]] = [(self.id, self.revision)]
        for fid in self.fallback_ids:
            if fid and all(fid != existing for existing, _ in result):
                result.append((fid, self.fallback_revisions.get(fid) or None))
        return result


@dataclass
class RuntimeSettings:
    backend: str = "transformers"
    device: str = "auto"
    cpu_mps_dtype: str = "float32"


@dataclass
class ServerSettings:
    host: str = LOCAL_HOST
    port: int = 8765
    max_upload_mb: int = 50
    upload_ttl_minutes: int = 60
    open_browser: bool = True

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@dataclass
class AppSettings:
    model: ModelSettings = field(default_factory=ModelSettings)
    runtime: RuntimeSettings = field(default_factory=RuntimeSettings)
    server: ServerSettings = field(default_factory=ServerSettings)


def _section(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name) or {}
    return value if isinstance(value, dict) else {}


def load_settings(path: Path | None = None) -> AppSettings:
    """설정 파일을 읽습니다. 파일이 없으면 기본값을 사용합니다.

    환경변수 TELEOCR_CONFIG 로 다른 설정 파일을, TELEOCR_BACKEND 로 백엔드
    ("mock"/"transformers")를 덮어쓸 수 있습니다(개발·테스트용).
    """
    config_path = path or Path(os.environ.get("TELEOCR_CONFIG", DEFAULT_CONFIG_PATH))
    raw: dict[str, Any] = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw = loaded

    m = _section(raw, "model")
    r = _section(raw, "runtime")
    s = _section(raw, "server")

    model = ModelSettings(
        id=str(m.get("id") or ModelSettings.id),
        fallback_ids=[str(x) for x in (m.get("fallback_ids") or [])]
        if "fallback_ids" in m
        else ModelSettings().fallback_ids,
        revision=str(m["revision"]) if m.get("revision") else None,
        fallback_revisions={
            str(k): str(v) for k, v in (m.get("fallback_revisions") or {}).items() if v
        },
        max_new_tokens=int(m.get("max_new_tokens") or 4096),
    )
    runtime = RuntimeSettings(
        backend=str(os.environ.get("TELEOCR_BACKEND") or r.get("backend") or "transformers"),
        device=str(r.get("device") or "auto").lower(),
        cpu_mps_dtype=str(r.get("cpu_mps_dtype") or "float32").lower(),
    )
    host = str(s.get("host") or LOCAL_HOST)
    if host != LOCAL_HOST:
        logger.warning("보안을 위해 host=%s 대신 %s 에만 바인딩합니다.", host, LOCAL_HOST)
        host = LOCAL_HOST
    server = ServerSettings(
        host=host,
        port=int(s.get("port") or 8765),
        max_upload_mb=int(s.get("max_upload_mb") or 50),
        upload_ttl_minutes=int(s.get("upload_ttl_minutes") or 60),
        open_browser=bool(s.get("open_browser", True)),
    )
    return AppSettings(model=model, runtime=runtime, server=server)
