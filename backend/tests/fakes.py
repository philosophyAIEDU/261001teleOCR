"""torch / transformers / huggingface_hub 를 흉내 내는 가짜 모듈 (GPU·모델 없이 테스트하기 위함)."""

from __future__ import annotations

import types
from pathlib import Path
from typing import Any


def make_fake_torch(cuda: bool = False, mps: bool = False, gpu_name: str = "NVIDIA RTX 4060") -> Any:
    torch = types.SimpleNamespace()
    torch.float32, torch.bfloat16, torch.float16 = "float32", "bfloat16", "float16"
    torch.cuda = types.SimpleNamespace(
        is_available=lambda: cuda,
        get_device_name=lambda idx: gpu_name,
        empty_cache=lambda: None,
    )
    torch.mps = types.SimpleNamespace(empty_cache=lambda: None)
    torch.backends = types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: mps))

    class InferenceMode:
        def __enter__(self) -> None:
            return None

        def __exit__(self, *args: object) -> None:
            return None

    torch.inference_mode = InferenceMode
    return torch


class FakeTensor:
    def __init__(self, rows: list[list[int]]) -> None:
        self.rows = rows

    @property
    def shape(self) -> tuple[int, int]:
        return (len(self.rows), len(self.rows[0]))

    def __getitem__(self, key: Any) -> "FakeTensor":
        _, cols = key
        return FakeTensor([row[cols] for row in self.rows])


class FakeInputs(dict):
    def to(self, device: str, dtype: Any = None) -> "FakeInputs":
        self["moved_to"] = (device, dtype)
        return self


class FakeProcessor:
    last_messages: Any = None

    def apply_chat_template(self, messages: Any, tokenize: bool, add_generation_prompt: bool) -> str:
        FakeProcessor.last_messages = messages
        return "CHAT:" + messages[-1]["content"][1]["text"]

    def __call__(self, text: list[str], images: list[Any], padding: bool, return_tensors: str) -> FakeInputs:
        return FakeInputs(input_ids=FakeTensor([[1, 2, 3]]), text=text[0])

    def batch_decode(self, ids: FakeTensor, skip_special_tokens: bool, clean_up_tokenization_spaces: bool) -> list[str]:
        return [" ".join(str(i) for i in ids.rows[0])]


class FakeModel:
    dtype = "float32"
    generate_error: Exception | None = None

    def __init__(self) -> None:
        self.device: str | None = None
        self.generate_kwargs: dict[str, Any] = {}

    def to(self, device: str) -> "FakeModel":
        self.device = device
        return self

    def eval(self) -> "FakeModel":
        return self

    def generate(self, **kwargs: Any) -> FakeTensor:
        if FakeModel.generate_error is not None:
            raise FakeModel.generate_error
        self.generate_kwargs = kwargs
        return FakeTensor([[1, 2, 3, 42, 43]])


def make_fake_transformers(model_class_errors: dict[str, Exception] | None = None) -> Any:
    errors = model_class_errors or {}
    module = types.SimpleNamespace()
    module.loaded_paths = []

    class AutoProcessor:
        @staticmethod
        def from_pretrained(path: str, **kwargs: Any) -> FakeProcessor:
            assert kwargs["trust_remote_code"] is True
            return FakeProcessor()

    def auto_class(name: str) -> type:
        class Auto:
            @staticmethod
            def from_pretrained(path: str, **kwargs: Any) -> FakeModel:
                if name in errors:
                    raise errors[name]
                assert kwargs["trust_remote_code"] is True
                module.loaded_paths.append((name, path, kwargs["torch_dtype"]))
                return FakeModel()

        return Auto

    module.AutoProcessor = AutoProcessor
    for name in ("AutoModelForImageTextToText", "AutoModelForVision2Seq", "AutoModelForCausalLM", "AutoModel"):
        setattr(module, name, auto_class(name))
    return module


def make_fake_hub(cache_root: Path, cached: set[str], available: set[str]) -> Any:
    """cached: 이미 내려받은 모델 ID, available: 온라인에서 내려받을 수 있는 모델 ID."""
    hub = types.SimpleNamespace()
    hub.downloads = []
    hub.constants = types.SimpleNamespace(HF_HUB_CACHE=str(cache_root))

    def snapshot(repo_id: str, revision: str | None) -> Path:
        path = cache_root / repo_id.replace("/", "--") / (revision or "c0ffee")
        path.mkdir(parents=True, exist_ok=True)
        (path / "model.safetensors").write_bytes(b"x")
        return path

    def snapshot_download(repo_id: str, revision: str | None = None, local_files_only: bool = False, **_: Any) -> str:
        if local_files_only:
            if repo_id not in cached:
                raise FileNotFoundError("not cached")
            return str(snapshot(repo_id, revision))
        if repo_id not in available:
            raise OSError(f"Repository Not Found: {repo_id}")
        hub.downloads.append((repo_id, revision))
        cached.add(repo_id)
        return str(snapshot(repo_id, revision))

    class HfApi:
        def model_info(self, repo_id: str, revision: str | None = None, files_metadata: bool = False) -> Any:
            if repo_id not in available:
                raise OSError("not found")
            return types.SimpleNamespace(siblings=[types.SimpleNamespace(size=1000), types.SimpleNamespace(size=None)])

    hub.snapshot_download = snapshot_download
    hub.HfApi = HfApi
    return hub
