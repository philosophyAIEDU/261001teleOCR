from backend.ocr.device import detect_device

from .fakes import make_fake_torch


def test_cuda_first_uses_bfloat16() -> None:
    info = detect_device("auto", "float32", make_fake_torch(cuda=True, mps=True))
    assert (info.kind, info.dtype, info.name) == ("cuda", "bfloat16", "NVIDIA RTX 4060")
    assert "GPU" in info.speed_hint_ko


def test_mps_when_no_cuda() -> None:
    info = detect_device("auto", "float32", make_fake_torch(mps=True))
    assert (info.kind, info.dtype) == ("mps", "float32")


def test_cpu_when_nothing() -> None:
    info = detect_device("auto", "float32", make_fake_torch())
    assert info.kind == "cpu"
    assert "느려요" in info.speed_hint_ko


def test_configurable_dtype_for_cpu_and_mps() -> None:
    assert detect_device("auto", "bfloat16", make_fake_torch()).dtype == "bfloat16"
    assert detect_device("auto", "float16", make_fake_torch(mps=True)).dtype == "float16"
    assert detect_device("auto", "int4", make_fake_torch()).dtype == "float32"


def test_forced_cpu_even_with_gpu() -> None:
    assert detect_device("cpu", "float32", make_fake_torch(cuda=True)).kind == "cpu"


def test_preference_falls_back_when_missing() -> None:
    assert detect_device("cuda", "float32", make_fake_torch(mps=True)).kind == "mps"
    assert detect_device("mps", "float32", make_fake_torch(cuda=True)).kind == "cuda"
    assert detect_device("mps", "float32", make_fake_torch()).kind == "cpu"


def test_broken_cuda_driver_is_treated_as_missing() -> None:
    torch = make_fake_torch()

    def boom() -> bool:
        raise RuntimeError("driver error")

    torch.cuda.is_available = boom
    torch.backends.mps.is_available = boom
    assert detect_device("auto", "float32", torch).kind == "cpu"


def test_gpu_name_failure_uses_generic_name() -> None:
    torch = make_fake_torch(cuda=True)

    def boom(idx: int) -> str:
        raise RuntimeError("x")

    torch.cuda.get_device_name = boom
    assert detect_device("auto", "float32", torch).name == "NVIDIA GPU"


def test_without_torch_installed(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("backend.ocr.device._import_torch", lambda: None)
    info = detect_device()
    assert info.kind == "cpu" and info.torch_available is False
    assert info.to_dict()["torch_available"] is False
