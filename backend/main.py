"""TeleOCR 교실 - FastAPI 앱.

한 프로세스에서 API(/api/...)와 프론트엔드 빌드 결과(frontend/dist)를 함께 서빙합니다.
실행: python -m backend.main  (또는 설치 폴더의 start 스크립트)
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
import time
import webbrowser
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .export import ExportItem, to_docx, to_markdown, to_xlsx
from .export.xlsx_export import NoTableError
from .ocr.base import OcrBackend
from .ocr.errors import OcrError
from .ocr.service import OcrService, create_backend
from .ocr.tasks import TASK_SPECS, TaskType
from .settings import PROJECT_DIR, AppSettings, load_settings
from .uploads import UploadError, UploadStore

logger = logging.getLogger("teleocr")

FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"
SAMPLES_DIR = PROJECT_DIR / "samples"
SAMPLE_FILES: dict[str, dict[str, str]] = {
    "english_text": {"file": "english_text.png", "task": "text", "title": "영어 지문"},
    "table": {"file": "table.png", "task": "table", "title": "표"},
    "formula": {"file": "formula.png", "task": "formula", "title": "수식"},
    "korean_text": {"file": "korean_text.png", "task": "text", "title": "한국어 지문(품질 점검용)"},
}
CLEANUP_INTERVAL_SECONDS = 300
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; "
    "font-src 'self' data:; script-src 'self'; connect-src 'self'; object-src 'none'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


# ---------------------------------------------------------------- 요청 모델
class CropBox(BaseModel):
    """0~1 로 정규화된 자르기 영역."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)


class ConvertRequest(BaseModel):
    upload_id: str
    page: int = Field(default=0, ge=0)
    task: TaskType
    crop: CropBox | None = None


class ParsePageRequest(BaseModel):
    upload_id: str
    page: int = Field(default=0, ge=0)
    distorted: bool = False
    crop: CropBox | None = None


class ExportItemModel(BaseModel):
    result_format: Literal["text", "html_table", "latex", "code", "layout"]
    content: str = Field(max_length=2_000_000)
    title: str | None = Field(default=None, max_length=200)


class ExportRequest(BaseModel):
    items: list[ExportItemModel] = Field(min_length=1, max_length=500)
    filename: str = Field(default="teleocr-결과", max_length=100)


EXPORT_TYPES: dict[str, tuple[str, str]] = {
    "md": ("text/markdown; charset=utf-8", ".md"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
}


def _content_disposition(filename: str) -> str:
    safe = "".join(ch for ch in filename if ch not in '\\/:*?"<>|\r\n') or "teleocr"
    return f"attachment; filename=\"teleocr{Path(safe).suffix}\"; filename*=UTF-8''{quote(safe)}"


def _crop(image, crop: CropBox | None):  # type: ignore[no-untyped-def]
    if crop is None:
        return image
    w, h = image.size
    left, top = int(crop.x * w), int(crop.y * h)
    right, bottom = min(w, int((crop.x + crop.width) * w)), min(h, int((crop.y + crop.height) * h))
    if right - left < 8 or bottom - top < 8:
        raise UploadError("잘라 낸 영역이 너무 작아요. 조금 더 크게 선택해 주세요.")
    return image.crop((left, top, right, bottom))


# ---------------------------------------------------------------- 앱 생성
def create_app(
    settings: AppSettings | None = None,
    backend: OcrBackend | None = None,
    upload_root: Path | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    service = OcrService(backend or create_backend(settings))
    store = UploadStore(
        max_bytes=settings.server.max_upload_bytes,
        ttl_seconds=settings.server.upload_ttl_minutes * 60,
        root=upload_root,
    )

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async def periodic_cleanup() -> None:
            while True:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                store.cleanup_expired()

        cleanup = asyncio.create_task(periodic_cleanup())
        try:
            yield
        finally:
            cleanup.cancel()
            store.clear_all()  # 서버를 끌 때 업로드 임시 파일을 모두 지웁니다.

    app = FastAPI(title="TeleOCR 교실", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.service = service
    app.state.store = store
    app.state.settings = settings
    # 다른 웹사이트가 이 로컬 서버에 접근하는 공격(DNS 리바인딩)을 막기 위해 Host 헤더를 제한합니다.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        # 화면이 외부 서버(CDN, 분석 스크립트 등)에 접속하지 못하도록 브라우저 차원에서 막습니다.
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    @app.exception_handler(OcrError)
    async def handle_ocr_error(_: Request, exc: OcrError) -> JSONResponse:
        return JSONResponse({"detail": exc.message_ko, "code": exc.code}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("처리하지 못한 오류", exc_info=exc)
        return JSONResponse(
            {"detail": "예상하지 못한 문제가 생겼어요. 프로그램을 다시 시작해 보세요.", "code": "internal"},
            status_code=500,
        )

    # ------------------------------------------------------------ 시스템
    @app.get("/api/system")
    async def system_status() -> dict[str, object]:
        status = await asyncio.to_thread(service.backend.status)
        return {
            "backend": status.backend,
            "device": status.device.to_dict(),
            "model": {
                "loaded": status.loaded,
                "loading": status.loading,
                "downloaded": status.downloaded,
                "model_id": status.model_id,
                "configured_id": settings.model.id,
                "fallback_ids": settings.model.fallback_ids,
                "revision": status.revision,
                "configured_revision": settings.model.revision,
                "error": status.error,
                "attempts": [{"model_id": m, "error": e} for m, e in status.attempts],
            },
            "download": {
                "active": status.download.active,
                "downloaded_bytes": status.download.downloaded_bytes,
                "total_bytes": status.download.total_bytes,
                "percent": status.download.percent,
            },
            "queue": {"busy": service.busy, "waiting": service.queue_size},
            "limits": {"max_upload_mb": settings.server.max_upload_mb},
        }

    @app.post("/api/model/load")
    async def load_model() -> dict[str, bool]:
        service.start_loading()
        return {"started": True}

    @app.get("/api/tasks")
    async def list_tasks() -> list[dict[str, object]]:
        return [
            {
                "id": spec.task.value,
                "name": spec.name_ko,
                "emoji": spec.emoji,
                "description": spec.description_ko,
                "result_format": spec.result_format.value,
            }
            for spec in TASK_SPECS.values()
        ]

    # ------------------------------------------------------------ 업로드
    def _upload_payload(record_id: str) -> dict[str, object]:
        record = store.get(record_id)
        return {
            "upload_id": record.upload_id,
            "filename": record.filename,
            "kind": record.kind,
            "page_count": record.page_count,
        }

    @app.post("/api/uploads")
    async def upload(file: UploadFile = File(...)) -> dict[str, object]:
        record = await asyncio.to_thread(store.save, file.filename or "", file.file)
        return _upload_payload(record.upload_id)

    @app.get("/api/uploads/{upload_id}/pages/{page}")
    async def page_image(upload_id: str, page: int) -> FileResponse:
        path = await asyncio.to_thread(store.page_file, upload_id, page)
        return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-store"})

    @app.delete("/api/uploads/{upload_id}")
    async def delete_upload(upload_id: str) -> dict[str, bool]:
        store.delete(upload_id)
        return {"deleted": True}

    @app.post("/api/uploads/{upload_id}/delete-beacon")
    async def delete_upload_beacon(upload_id: str) -> dict[str, bool]:
        """브라우저 창을 닫을 때(navigator.sendBeacon 은 POST 만 가능) 임시 파일을 지웁니다."""
        store.delete(upload_id)
        return {"deleted": True}

    @app.get("/api/samples")
    async def list_samples() -> list[dict[str, str]]:
        return [
            {"id": key, **value}
            for key, value in SAMPLE_FILES.items()
            if (SAMPLES_DIR / value["file"]).exists()
        ]

    @app.post("/api/samples/{sample_id}")
    async def use_sample(sample_id: str) -> dict[str, object]:
        meta = SAMPLE_FILES.get(sample_id)
        if meta is None or not (SAMPLES_DIR / meta["file"]).exists():
            raise UploadError("샘플 파일을 찾을 수 없어요.", 404)
        path = SAMPLES_DIR / meta["file"]
        with path.open("rb") as f:
            record = await asyncio.to_thread(store.save, path.name, f)
        return {**_upload_payload(record.upload_id), "task": meta["task"]}

    # ------------------------------------------------------------ 변환
    @app.post("/api/convert")
    async def convert(req: ConvertRequest) -> dict[str, object]:
        image = await asyncio.to_thread(store.load_page, req.upload_id, req.page)
        image = _crop(image, req.crop)
        result = await service.convert(image, req.task)
        out = result.output
        return {
            "task": out.task.value,
            "result_format": out.result_format.value,
            "raw": out.raw,
            "content": out.content,
            "blocks": out.blocks,
            "parsed": out.parsed,
            "elapsed_seconds": round(result.elapsed_seconds, 2),
        }

    @app.post("/api/parse-page")
    async def parse_page(req: ParsePageRequest) -> dict[str, object]:
        image = await asyncio.to_thread(store.load_page, req.upload_id, req.page)
        image = _crop(image, req.crop)
        started = time.monotonic()
        markdown, blocks = await service.parse_page(image, distorted=req.distorted)
        return {
            "markdown": markdown,
            "blocks": blocks,
            "elapsed_seconds": round(time.monotonic() - started, 2),
        }

    # ------------------------------------------------------------ 내보내기
    @app.post("/api/export/{fmt}")
    async def export(fmt: Literal["md", "docx", "xlsx"], req: ExportRequest) -> Response:
        items = [ExportItem(i.result_format, i.content, i.title) for i in req.items]
        media_type, suffix = EXPORT_TYPES[fmt]
        if fmt == "md":
            data = to_markdown(items).encode("utf-8")
        elif fmt == "docx":
            data = await asyncio.to_thread(to_docx, items)
        else:
            try:
                data = await asyncio.to_thread(to_xlsx, items)
            except NoTableError as exc:
                raise OcrError(str(exc), code="no_table", status_code=400) from exc
        filename = Path(req.filename).stem + suffix
        return Response(data, media_type=media_type, headers={"Content-Disposition": _content_disposition(filename)})

    # ------------------------------------------------------------ 프론트엔드
    _mount_frontend(app)
    return app


NO_FRONTEND_HTML = """<!doctype html><html lang="ko"><meta charset="utf-8">
<title>TeleOCR 교실</title><body style="font-family:sans-serif;font-size:18px;padding:2rem">
<h1>화면 파일이 없어요</h1><p>frontend/dist 폴더가 없습니다. 설치 파일을 다시 내려받거나
개발자라면 <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code> 를 실행해 주세요.</p></body></html>"""


def _mount_frontend(app: FastAPI) -> None:
    index = FRONTEND_DIST / "index.html"
    assets = FRONTEND_DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> Response:
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "없는 주소예요."}, status_code=404)
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        if index.exists():
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
        return HTMLResponse(NO_FRONTEND_HTML, status_code=200)


def main() -> None:
    import uvicorn  # noqa: PLC0415

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = load_settings()
    url = f"http://{settings.server.host}:{settings.server.port}"
    app = create_app(settings)
    if settings.server.open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"\n  TeleOCR 교실이 시작되었어요 → {url}\n  이 창을 닫으면 프로그램이 종료됩니다.\n")
    uvicorn.run(app, host=settings.server.host, port=settings.server.port, log_level="warning")


if __name__ == "__main__":
    main()
