"""실제 TeleOCR 모델로 불러오기와 작업별 동작을 확인하는 스모크 테스트.

사용법 (설치 후, 프로젝트 폴더에서):
    python scripts/smoke_test.py                  # 샘플 이미지로 전체 작업 확인
    python scripts/smoke_test.py --image 내사진.jpg --task text
    python scripts/smoke_test.py --json 결과.json  # 결과를 파일로 저장(README 기록용)

출력 내용
- 실제로 불러온 모델 ID(대체 ID 사용 여부)와 revision(커밋 해시)
- 장치(CUDA/MPS/CPU)와 dtype
- 작업별 원본 출력(raw)과 후처리 결과, 걸린 시간
  → 레이아웃 출력 형식과 한국어 인식 품질을 여기서 직접 확인해 README 에 기록하세요.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from backend.ocr.errors import OcrError  # noqa: E402
from backend.ocr.service import OcrService, create_backend  # noqa: E402
from backend.ocr.tasks import TaskType  # noqa: E402
from backend.settings import load_settings  # noqa: E402

DEFAULT_CASES: list[tuple[str, TaskType]] = [
    ("english_text.png", TaskType.TEXT),
    ("table.png", TaskType.TABLE),
    ("formula.png", TaskType.FORMULA),
    ("english_text.png", TaskType.LAYOUT),
    ("english_text.png", TaskType.LAYOUT_DISTORTED),
    ("table.png", TaskType.CHART),
    ("english_text.png", TaskType.CODE),
    ("english_text.png", TaskType.SEAL),
    ("korean_text.png", TaskType.TEXT),
]


async def run(args: argparse.Namespace) -> int:
    settings = load_settings()
    if args.backend:
        settings.runtime.backend = args.backend
    service = OcrService(create_backend(settings))

    print("== 1. 모델 불러오기 ==")
    started = time.monotonic()
    try:
        await service.ensure_loaded()
    except OcrError as exc:
        print("실패:", exc.message_ko)
        for model_id, error in getattr(exc, "attempts", []):
            print(f"  - {model_id}: {error}")
        return 1
    status = service.backend.status()
    report: dict[str, object] = {
        "model_id": status.model_id,
        "revision": status.revision,
        "configured_id": settings.model.id,
        "used_fallback": status.model_id != settings.model.id,
        "device": status.device.to_dict(),
        "load_seconds": round(time.monotonic() - started, 1),
        "results": [],
    }
    print(f"모델 ID : {status.model_id}  (설정값 {settings.model.id})")
    print(f"revision: {status.revision}")
    print(f"장치    : {status.device.kind} / {status.device.name} / {status.device.dtype}")
    print(f"불러오기: {report['load_seconds']}초\n")

    if args.image:
        cases = [(args.image, TaskType(args.task))]
    else:
        cases = [(str(ROOT / "samples" / name), task) for name, task in DEFAULT_CASES]

    print("== 2. 작업별 추론 ==")
    failures = 0
    for image_path, task in cases:
        path = Path(image_path)
        if not path.exists():
            print(f"[건너뜀] {path} 없음")
            continue
        image = Image.open(path).convert("RGB")
        try:
            result = await service.convert(image, task)
        except OcrError as exc:
            failures += 1
            print(f"[{task.value}] {path.name} 실패: {exc.message_ko}")
            continue
        out = result.output
        print(f"--- [{task.value}] {path.name} ({result.elapsed_seconds:.1f}초, 해석 {'성공' if out.parsed else '실패'})")
        print("원본 출력(raw):")
        print(out.raw)
        if out.content != out.raw.strip():
            print("후처리 결과:")
            print(out.content)
        print()
        report["results"].append(  # type: ignore[union-attr]
            {
                "image": path.name,
                "task": task.value,
                "seconds": round(result.elapsed_seconds, 2),
                "parsed": out.parsed,
                "raw": out.raw,
                "content": out.content,
            }
        )

    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"결과를 {args.json} 에 저장했어요.")
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="TeleOCR 스모크 테스트")
    parser.add_argument("--image", help="확인할 이미지 경로(생략하면 samples/ 전체)")
    parser.add_argument("--task", default="text", choices=[t.value for t in TaskType])
    parser.add_argument("--backend", choices=["transformers", "mock"], help="config.yaml 대신 사용할 백엔드")
    parser.add_argument("--json", help="결과를 저장할 JSON 파일 경로")
    raise SystemExit(asyncio.run(run(parser.parse_args())))


if __name__ == "__main__":
    main()
