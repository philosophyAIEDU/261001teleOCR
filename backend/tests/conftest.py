from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.ocr.mock_backend import MockBackend
from backend.settings import AppSettings


@pytest.fixture()
def settings() -> AppSettings:
    s = AppSettings()
    s.runtime.backend = "mock"
    s.server.max_upload_mb = 1
    return s


@pytest.fixture()
def client(settings: AppSettings, tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(settings, backend=MockBackend(), upload_root=tmp_path / "uploads")
    with TestClient(app, base_url="http://127.0.0.1") as test_client:
        yield test_client
