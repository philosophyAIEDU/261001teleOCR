"""MockBackend 로 업로드 → 변환 → 내보내기 전 과정을 검증하는 통합 테스트 (GPU 불필요)."""

import io
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from PIL import Image


def png_bytes(size: tuple[int, int] = (400, 300), color: str = "white") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, "PNG")
    return buffer.getvalue()


def pdf_bytes(pages: int = 3) -> bytes:
    buffer = io.BytesIO()
    images = [Image.new("RGB", (300, 400), c) for c in ("white", "gray", "black")[:pages]]
    images[0].save(buffer, "PDF", save_all=True, append_images=images[1:])
    return buffer.getvalue()


def upload(client: TestClient, name: str = "worksheet.png", data: bytes | None = None) -> dict:
    response = client.post("/api/uploads", files={"file": (name, data or png_bytes(), "application/octet-stream")})
    assert response.status_code == 200, response.text
    return response.json()


def test_full_flow_upload_convert_export(client: TestClient) -> None:
    info = upload(client)
    assert info["kind"] == "image" and info["page_count"] == 1

    page = client.get(f"/api/uploads/{info['upload_id']}/pages/0")
    assert page.status_code == 200 and page.headers["content-type"] == "image/png"

    table = client.post("/api/convert", json={"upload_id": info["upload_id"], "task": "table"}).json()
    assert table["result_format"] == "html_table"
    assert '<td rowspan="2">Name</td>' in table["content"]
    assert table["raw"].startswith("<fcel>")

    formula = client.post("/api/convert", json={"upload_id": info["upload_id"], "task": "formula"}).json()
    assert formula["content"].startswith("$$") and "\\[" not in formula["content"]

    edited_table = table["content"].replace("Minsu", "민수")
    items = [
        {"result_format": "html_table", "content": edited_table, "title": "성적표"},
        {"result_format": "latex", "content": formula["content"], "title": "근의 공식"},
    ]
    md = client.post("/api/export/md", json={"items": items, "filename": "수업자료"})
    assert md.status_code == 200
    assert "filename*=UTF-8''%EC%88%98%EC%97%85%EC%9E%90%EB%A3%8C.md" in md.headers["content-disposition"]
    assert "민수" in md.text and "## 근의 공식" in md.text

    docx = client.post("/api/export/docx", json={"items": items})
    assert docx.status_code == 200
    assert Document(io.BytesIO(docx.content)).tables[0].cell(2, 0).text == "민수"

    xlsx = client.post("/api/export/xlsx", json={"items": items})
    assert xlsx.status_code == 200
    assert load_workbook(io.BytesIO(xlsx.content)).active["A3"].value == "민수"

    no_table = client.post("/api/export/xlsx", json={"items": items[1:]})
    assert no_table.status_code == 400 and "표 결과만" in no_table.json()["detail"]

    assert client.delete(f"/api/uploads/{info['upload_id']}").json() == {"deleted": True}
    gone = client.post("/api/convert", json={"upload_id": info["upload_id"], "task": "text"})
    assert gone.status_code == 404 and "다시 올려" in gone.json()["detail"]


def test_all_tasks_listed_and_convertible(client: TestClient) -> None:
    tasks = client.get("/api/tasks").json()
    assert [t["id"] for t in tasks] == [
        "text", "table", "formula", "code", "layout", "layout_distorted", "chart", "seal",
    ]
    assert tasks[0]["name"] == "글자 뽑기" and tasks[-1]["name"] == "도장 인식"
    info = upload(client)
    for task in tasks:
        result = client.post("/api/convert", json={"upload_id": info["upload_id"], "task": task["id"]}).json()
        assert result["result_format"] == task["result_format"], task["id"]
    layout = client.post("/api/convert", json={"upload_id": info["upload_id"], "task": "layout"}).json()
    assert layout["blocks"][0]["label"] == "제목"


def test_pdf_upload_pages(client: TestClient) -> None:
    info = upload(client, "시험지.pdf", pdf_bytes(3))
    assert info["kind"] == "pdf" and info["page_count"] == 3
    image = Image.open(io.BytesIO(client.get(f"/api/uploads/{info['upload_id']}/pages/2").content))
    assert image.size[0] > 300  # 200dpi 로 렌더링
    result = client.post("/api/convert", json={"upload_id": info["upload_id"], "page": 1, "task": "text"})
    assert result.status_code == 200
    assert client.get(f"/api/uploads/{info['upload_id']}/pages/3").status_code == 404


def test_crop_and_parse_page(client: TestClient) -> None:
    info = upload(client)
    crop = {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}
    ok = client.post("/api/convert", json={"upload_id": info["upload_id"], "task": "code", "crop": crop})
    assert ok.status_code == 200
    tiny = {"x": 0, "y": 0, "width": 0.001, "height": 0.001}
    bad = client.post("/api/convert", json={"upload_id": info["upload_id"], "task": "code", "crop": tiny})
    assert bad.status_code == 400 and "너무 작아요" in bad.json()["detail"]
    parsed = client.post("/api/parse-page", json={"upload_id": info["upload_id"], "crop": crop}).json()
    assert parsed["markdown"].startswith("## ") and len(parsed["blocks"]) == 5


def test_upload_validation(client: TestClient) -> None:
    bad_ext = client.post("/api/uploads", files={"file": ("virus.exe", b"MZ....", "application/octet-stream")})
    assert bad_ext.status_code == 415 and "PDF" in bad_ext.json()["detail"]
    fake_png = client.post("/api/uploads", files={"file": ("a.png", b"%PDF-1.4 not png", "image/png")})
    assert fake_png.status_code == 415 and "확장자" in fake_png.json()["detail"]
    empty = client.post("/api/uploads", files={"file": ("a.png", b"", "image/png")})
    assert empty.status_code == 400
    too_big = client.post("/api/uploads", files={"file": ("a.png", b"\x89PNG\r\n\x1a\n" + b"0" * (1024 * 1024 + 1), "image/png")})
    assert too_big.status_code == 413 and "1MB" in too_big.json()["detail"]
    broken = client.post("/api/uploads", files={"file": ("a.jpg", b"\xff\xd8\xff" + b"0" * 100, "image/jpeg")})
    assert broken.status_code == 400 and "열 수 없어요" in broken.json()["detail"]
    broken_pdf = client.post("/api/uploads", files={"file": ("a.pdf", b"%PDF-garbage", "application/pdf")})
    assert broken_pdf.status_code == 400
    bad_task = client.post("/api/convert", json={"upload_id": "x", "task": "magic"})
    assert bad_task.status_code == 422


def test_temp_files_deleted(client: TestClient, tmp_path: Path) -> None:
    info = upload(client)
    folder = tmp_path / "uploads" / info["upload_id"]
    assert folder.exists()
    # 사진 원본(메타데이터 포함)은 PNG 로 바꾼 뒤 바로 지워집니다.
    assert [p.name for p in folder.iterdir()] == ["page-0000.png"]
    client.delete(f"/api/uploads/{info['upload_id']}")
    assert not folder.exists()


def test_system_status_and_load(client: TestClient) -> None:
    status = client.get("/api/system").json()
    assert status["backend"] == "mock"
    assert status["model"]["configured_id"] == "XingChen-AGI/TeleOCR"
    assert status["model"]["fallback_ids"] == ["StarDoc-AI/TeleOCR", "StarDoc-AI/NaviDC-OCR"]
    assert status["queue"] == {"busy": False, "waiting": 0}
    assert status["limits"]["max_upload_mb"] == 1
    assert client.post("/api/model/load").json() == {"started": True}
    assert client.get("/api/system").json()["model"]["loaded"] is True


def test_samples(client: TestClient) -> None:
    samples = {s["id"]: s for s in client.get("/api/samples").json()}
    assert {"english_text", "table", "formula"} <= set(samples)
    created = client.post("/api/samples/table").json()
    assert created["task"] == "table" and created["page_count"] == 1
    assert client.post("/api/samples/nope").status_code == 404


def test_rejects_foreign_host_header(client: TestClient) -> None:
    response = client.get("/api/system", headers={"host": "evil.example.com"})
    assert response.status_code == 400


def test_frontend_fallback_and_unknown_api(client: TestClient) -> None:
    page = client.get("/guide")
    assert page.status_code == 200 and "<html" in page.text.lower()
    assert client.get("/api/does-not-exist").status_code == 404


def test_unexpected_error_is_korean(client: TestClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    info = upload(client)

    def boom(*args: object) -> None:
        raise RuntimeError("unexpected")

    monkeypatch.setattr(client.app.state.service, "convert", boom)
    with TestClient(client.app, base_url="http://127.0.0.1", raise_server_exceptions=False) as c:
        response = c.post("/api/convert", json={"upload_id": info["upload_id"], "task": "text"})
    assert response.status_code == 500 and "다시 시작" in response.json()["detail"]


def test_delete_beacon_and_security_headers(client: TestClient, tmp_path: Path) -> None:
    info = upload(client)
    response = client.post(f"/api/uploads/{info['upload_id']}/delete-beacon")
    assert response.json() == {"deleted": True}
    assert not (tmp_path / "uploads" / info["upload_id"]).exists()
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp and "connect-src 'self'" in csp
    assert response.headers["referrer-policy"] == "no-referrer"
