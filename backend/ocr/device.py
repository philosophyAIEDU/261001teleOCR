"""실행 장치(GPU/Apple Silicon/CPU) 자동 감지.

감지 순서와 원리
1. CUDA: torch.cuda.is_available() 가 참이면 NVIDIA GPU 를 사용합니다.
   GPU 는 bfloat16(16비트)으로 계산해도 품질 손실이 거의 없고 메모리를 절반만 쓰므로 bfloat16 을 씁니다.
2. MPS: Apple Silicon(M1~M4 등) Mac 에서 torch.backends.mps.is_available() 가 참이면 사용합니다.
3. CPU: 둘 다 없으면 CPU 로 계산합니다.
   MPS/CPU 는 16비트 연산 지원이 장치마다 달라 결과가 틀어질 수 있으므로 기본값은 float32 이고,
   config.yaml 의 runtime.cpu_mps_dtype 으로 바꿀 수 있습니다.

모델 카드 예제처럼 .cuda() 를 코드에 박아 두면 GPU 가 없는 교사 PC 에서 바로 오류가 나므로,
여기서 고른 장치 이름("cuda"/"mps"/"cpu")을 model.to(device) 에 넘깁니다.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from types import ModuleType
from typing import Any

VALID_DTYPES = ("float32", "bfloat16", "float16")

SPEED_HINTS_KO: dict[str, str] = {
    "cuda": "NVIDIA GPU 로 실행해요. 한 장에 보통 수 초~20초 정도 걸려요.",
    "mps": "Apple Silicon(M 시리즈) 가속을 사용해요. 한 장에 보통 10초~1분 정도 걸려요.",
    "cpu": (
        "GPU 없이 CPU 로만 실행해요. 한 장에 1분~수 분이 걸릴 수 있어 느려요. "
        "표 하나, 수식 하나처럼 작게 잘라서 넣으면 훨씬 빨라져요."
    ),
}


@dataclass
class DeviceInfo:
    kind: str  # "cuda" | "mps" | "cpu"
    name: str  # 사람이 읽는 장치 이름
    dtype: str  # "bfloat16" | "float32" | "float16"
    torch_available: bool = True

    @property
    def speed_hint_ko(self) -> str:
        return SPEED_HINTS_KO[self.kind]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "dtype": self.dtype,
            "torch_available": self.torch_available,
            "speed_hint": self.speed_hint_ko,
        }


def _import_torch() -> ModuleType | None:
    try:
        import torch  # noqa: PLC0415 - torch 는 무거워서 필요할 때만 불러옵니다.
    except ImportError:
        return None
    return torch


def _cpu_name() -> str:
    name = platform.processor() or platform.machine() or "CPU"
    return f"CPU ({name})"


def _cuda_ok(torch: Any) -> bool:
    try:
        return bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001 - 드라이버 문제 등은 "CUDA 없음"으로 처리
        return False


def _mps_ok(torch: Any) -> bool:
    try:
        backend = getattr(torch.backends, "mps", None)
        return bool(backend is not None and backend.is_available())
    except Exception:  # noqa: BLE001
        return False


def detect_device(
    preference: str = "auto",
    cpu_mps_dtype: str = "float32",
    torch_module: Any | None = None,
) -> DeviceInfo:
    """설정(preference)과 실제 하드웨어를 보고 사용할 장치를 고릅니다.

    preference 가 "cuda"/"mps" 인데 해당 장치가 없으면 자동 감지 순서로 되돌아갑니다.
    torch_module 은 테스트에서 가짜 torch 를 넣기 위한 인자입니다.
    """
    dtype = cpu_mps_dtype if cpu_mps_dtype in VALID_DTYPES else "float32"
    torch = torch_module if torch_module is not None else _import_torch()
    if torch is None:
        return DeviceInfo("cpu", _cpu_name(), dtype, torch_available=False)

    pref = (preference or "auto").lower()
    if pref == "cpu":
        return DeviceInfo("cpu", _cpu_name(), dtype)

    cuda = _cuda_ok(torch)
    mps = _mps_ok(torch)

    if pref in ("auto", "cuda") and cuda:
        try:
            name = str(torch.cuda.get_device_name(0))
        except Exception:  # noqa: BLE001
            name = "NVIDIA GPU"
        return DeviceInfo("cuda", name, "bfloat16")
    if pref in ("auto", "mps", "cuda") and mps:
        return DeviceInfo("mps", "Apple Silicon (MPS)", dtype)
    if pref == "mps" and cuda:
        return DeviceInfo("cuda", str(torch.cuda.get_device_name(0)), "bfloat16")
    return DeviceInfo("cpu", _cpu_name(), dtype)
