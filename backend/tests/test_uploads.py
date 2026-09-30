import io
import time
from pathlib import Path

import pytest
from PIL import Image

from backend.uploads import MAX_IMAGE_EDGE, UploadError, UploadStore, normalize_image


def store(tmp_path: Path, max_bytes: int = 5 * 1024 * 1024) -> UploadStore:
    return UploadStore(max_bytes=max_bytes, ttl_seconds=60, root=tmp_path / "up")


def encode(image: Image.Image, fmt: str, **kwargs: object) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, fmt, **kwargs)
    return buffer.getvalue()


def test_webp_and_jpeg_accepted(tmp_path: Path) -> None:
    s = store(tmp_path)
    webp = s.save_bytes("a.webp", encode(Image.new("RGB", (50, 50)), "WEBP"))
    jpg = s.save_bytes("b.JPEG", encode(Image.new("RGB", (50, 50)), "JPEG"))
    assert s.load_page(webp.upload_id, 0).size == (50, 50)
    assert jpg.kind == "image"


def test_webp_magic_mismatch(tmp_path: Path) -> None:
    with pytest.raises(UploadError):
        store(tmp_path).save_bytes("a.webp", b"RIFF0000WAVEfmt ")


def test_normalize_transparency_rotation_and_size() -> None:
    rgba = Image.new("RGBA", (10, 10), (255, 0, 0, 0))
    assert normalize_image(rgba).getpixel((0, 0)) == (255, 255, 255)
    assert normalize_image(Image.new("L", (5, 5))).mode == "RGB"
    big = normalize_image(Image.new("RGB", (MAX_IMAGE_EDGE * 2, 100)))
    assert max(big.size) == MAX_IMAGE_EDGE
    exif = Image.Exif()
    exif[0x0112] = 6  # 90도 회전해서 찍은 사진
    rotated = Image.open(io.BytesIO(encode(Image.new("RGB", (40, 20)), "JPEG", exif=exif)))
    assert normalize_image(rotated).size == (20, 40)


def test_ttl_cleanup_and_clear(tmp_path: Path) -> None:
    s = store(tmp_path)
    record = s.save_bytes("a.png", encode(Image.new("RGB", (20, 20)), "PNG"))
    assert s.cleanup_expired(now=time.time()) == 0
    assert s.cleanup_expired(now=time.time() + 3600) == 1
    assert not record.directory.exists()
    with pytest.raises(UploadError):
        s.get(record.upload_id)
    s.save_bytes("b.png", encode(Image.new("RGB", (20, 20)), "PNG"))
    s.clear_all()
    assert not s.root.exists()


def test_pdf_page_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.uploads.MAX_PDF_PAGES", 1)
    pages = [Image.new("RGB", (50, 50)) for _ in range(2)]
    data = encode(pages[0], "PDF", save_all=True, append_images=pages[1:])
    with pytest.raises(UploadError) as info:
        store(tmp_path).save_bytes("a.pdf", data)
    assert info.value.status_code == 413
    assert not any((tmp_path / "up").iterdir())  # 실패하면 임시 폴더도 지움


def test_decompression_bomb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    data = encode(Image.new("RGB", (100, 100)), "PNG")
    with pytest.raises(UploadError) as info:
        store(tmp_path).save_bytes("a.png", data)
    assert "해상도" in info.value.message_ko
