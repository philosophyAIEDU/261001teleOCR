"""업로드 파일 임시 보관소.

- 파일은 운영체제 임시 폴더 아래 전용 폴더에만 저장하고, 사용이 끝나면(삭제 요청, 유효 시간 경과,
  서버 종료) 지웁니다.
- 확장자와 실제 파일 내용(매직 바이트)을 모두 확인하고, 크기 상한을 넘으면 저장을 중단합니다.
- PDF 는 pypdfium2(Apache/BSD 라이선스)로 쪽마다 PNG 이미지로 바꿉니다. (PyMuPDF 는 AGPL 이라 사용하지 않습니다.)
"""

from __future__ import annotations

import io
import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps

from .ocr.errors import OcrError

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PDF_EXTENSIONS = {".pdf"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS
PDF_RENDER_DPI = 200
MAX_PDF_PAGES = 300
# 너무 큰 사진(예: 1억 화소)은 메모리 폭주를 막기 위해 거부합니다.
Image.MAX_IMAGE_PIXELS = 12000 * 12000
# 모델에 넣기 전 긴 변 최대 길이. 스마트폰 원본(4000px 이상)은 느리고 메모리를 많이 써서 줄입니다.
MAX_IMAGE_EDGE = 2480

_MAGIC: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".webp": (b"RIFF",),
}


class UploadError(OcrError):
    def __init__(self, message_ko: str, status_code: int = 400) -> None:
        super().__init__(message_ko, code="upload_error", status_code=status_code)


@dataclass
class UploadRecord:
    upload_id: str
    filename: str
    kind: str  # "image" | "pdf"
    directory: Path
    page_count: int
    created_at: float = field(default_factory=time.time)
    rendered: set[int] = field(default_factory=set)

    @property
    def source_path(self) -> Path:
        return self.directory / ("source.pdf" if self.kind == "pdf" else "source.img")

    def page_path(self, index: int) -> Path:
        return self.directory / f"page-{index:04d}.png"


def _check_magic(ext: str, head: bytes) -> bool:
    if ext == ".webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    return any(head.startswith(sig) for sig in _MAGIC[ext])


def normalize_image(image: Image.Image) -> Image.Image:
    """사진의 회전 정보(EXIF)를 반영하고 RGB 로 바꾼 뒤, 너무 크면 줄입니다."""
    image = ImageOps.exif_transpose(image) or image
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")
    if max(image.size) > MAX_IMAGE_EDGE:
        image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
    return image


class UploadStore:
    def __init__(self, max_bytes: int, ttl_seconds: int, root: Path | None = None) -> None:
        self.max_bytes = max_bytes
        self.ttl_seconds = ttl_seconds
        self.root = root or Path(tempfile.gettempdir()) / "teleocr_classroom_uploads"
        self._records: dict[str, UploadRecord] = {}
        self._lock = threading.Lock()
        # 이전 실행에서 남은 파일이 있으면 시작할 때 모두 지웁니다.
        self.clear_all()
        self.root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------ 저장
    def save(self, filename: str, stream: BinaryIO) -> UploadRecord:
        ext = Path(filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise UploadError("JPG, PNG, WEBP 사진이나 PDF 파일만 올릴 수 있어요.", 415)

        upload_id = uuid.uuid4().hex
        directory = self.root / upload_id
        directory.mkdir(parents=True)
        kind = "pdf" if ext in PDF_EXTENSIONS else "image"
        record = UploadRecord(upload_id, Path(filename).name, kind, directory, page_count=0)
        try:
            size = 0
            with record.source_path.open("wb") as out:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise UploadError(
                            f"파일이 너무 커요. {self.max_bytes // (1024 * 1024)}MB 이하로 올려 주세요.", 413
                        )
                    out.write(chunk)
            if size == 0:
                raise UploadError("빈 파일이에요. 다른 파일을 올려 주세요.")
            with record.source_path.open("rb") as f:
                head = f.read(16)
            if not _check_magic(ext, head):
                raise UploadError("파일 내용이 확장자와 달라요. 사진이나 PDF 파일이 맞는지 확인해 주세요.", 415)

            if kind == "pdf":
                record.page_count = self._pdf_page_count(record.source_path)
            else:
                self._convert_image(record)
                record.page_count = 1
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise
        with self._lock:
            self._records[upload_id] = record
        return record

    def save_bytes(self, filename: str, data: bytes) -> UploadRecord:
        return self.save(filename, io.BytesIO(data))

    def _convert_image(self, record: UploadRecord) -> None:
        try:
            with Image.open(record.source_path) as img:
                img.load()
                image = normalize_image(img)
        except Image.DecompressionBombError as exc:
            raise UploadError("사진 해상도가 너무 커요. 크기를 줄여서 다시 올려 주세요.", 413) from exc
        except Exception as exc:  # noqa: BLE001
            raise UploadError("사진을 열 수 없어요. 파일이 손상되지 않았는지 확인해 주세요.") from exc
        image.save(record.page_path(0), format="PNG")
        record.rendered.add(0)
        # 원본은 PNG 로 바꾼 뒤 바로 지웁니다(원본에 있는 촬영 위치 등 메타데이터도 함께 사라짐).
        record.source_path.unlink(missing_ok=True)

    @staticmethod
    def _pdf_page_count(path: Path) -> int:
        import pypdfium2 as pdfium  # noqa: PLC0415

        try:
            pdf = pdfium.PdfDocument(str(path))
        except Exception as exc:  # noqa: BLE001
            raise UploadError("PDF 를 열 수 없어요. 암호가 걸려 있거나 손상된 파일일 수 있어요.") from exc
        try:
            count = len(pdf)
        finally:
            pdf.close()
        if count == 0:
            raise UploadError("PDF 에 쪽이 없어요.")
        if count > MAX_PDF_PAGES:
            raise UploadError(f"PDF 가 너무 길어요. {MAX_PDF_PAGES}쪽 이하로 나눠서 올려 주세요.", 413)
        return count

    # ------------------------------------------------------------ 조회
    def get(self, upload_id: str) -> UploadRecord:
        with self._lock:
            record = self._records.get(upload_id)
        if record is None or not record.directory.exists():
            raise UploadError("파일을 찾을 수 없어요. 파일을 다시 올려 주세요.", 404)
        return record

    def page_file(self, upload_id: str, index: int) -> Path:
        """쪽 이미지 경로. PDF 쪽은 처음 요청될 때 렌더링합니다."""
        record = self.get(upload_id)
        if index < 0 or index >= record.page_count:
            raise UploadError("없는 쪽 번호예요.", 404)
        path = record.page_path(index)
        if index not in record.rendered or not path.exists():
            self._render_pdf_page(record, index)
        return path

    def load_page(self, upload_id: str, index: int) -> Image.Image:
        with Image.open(self.page_file(upload_id, index)) as img:
            return img.convert("RGB")

    def _render_pdf_page(self, record: UploadRecord, index: int) -> None:
        import pypdfium2 as pdfium  # noqa: PLC0415

        pdf = pdfium.PdfDocument(str(record.source_path))
        try:
            page = pdf[index]
            bitmap = page.render(scale=PDF_RENDER_DPI / 72)
            image = normalize_image(bitmap.to_pil())
            image.save(record.page_path(index), format="PNG")
            page.close()
        finally:
            pdf.close()
        record.rendered.add(index)

    # ------------------------------------------------------------ 삭제
    def delete(self, upload_id: str) -> None:
        with self._lock:
            record = self._records.pop(upload_id, None)
        if record is not None:
            shutil.rmtree(record.directory, ignore_errors=True)

    def cleanup_expired(self, now: float | None = None) -> int:
        current = now if now is not None else time.time()
        with self._lock:
            expired = [k for k, r in self._records.items() if current - r.created_at > self.ttl_seconds]
        for upload_id in expired:
            self.delete(upload_id)
        return len(expired)

    def clear_all(self) -> None:
        with self._lock:
            self._records.clear()
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
