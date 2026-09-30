# TeleOCR 교실

교사가 종이 자료(학습지·교과서·시험지·판서 사진)를 찍거나 스캔해서 올리면 **편집할 수 있는 텍스트·표·수식·코드**로 바꿔 주는 **로컬 실행 웹앱**입니다.
오픈소스 문서 인식 모델 [TeleOCR](https://huggingface.co/XingChen-AGI/TeleOCR)(Apache-2.0)을 **교사 PC 안에서만** 실행합니다.

- 🔒 **개인정보 보호**: 처음 모델을 내려받을 때 말고는 외부 네트워크를 쓰지 않습니다. 서버는 `127.0.0.1` 에만 바인딩합니다.
- 🧑‍🏫 **교사용 화면**: 모든 화면이 한국어이고, 글자는 16px 이상입니다. 키보드와 태블릿으로도 쓸 수 있습니다.
- 📦 **더블클릭 설치**: `scripts/install.bat`(Windows), `scripts/install.command`(macOS)

비개발자용 단계별 안내는 **[docs/설치가이드.md](docs/설치가이드.md)** 를 보세요.

---

## 기능

| 작업 카드 | 모델 프롬프트 | 결과 화면 | 내보내기 |
|---|---|---|---|
| 📝 글자 뽑기 | `Please output the text content from the image.` | 편집 가능한 텍스트 | 복사, .md, .docx |
| 📊 표 만들기 | `This is the image of a table. Please output the table in OTSL format.` | 칸 편집 가능한 표(병합 칸 유지) | + .xlsx |
| ➗ 수식 변환 | `Please write out the expression of the formula in the image using LaTeX format.` | KaTeX 미리보기 + LaTeX 원문 복사 | 복사, .md, .docx |
| 💻 코드 옮기기 | `The image contains a code snippet, please output the parsing result.` | 고정폭 편집기 + 복사 | 복사, .md, .docx |
| 🗂️ 문서 구조 분석 | `Analyze the image layout.` (1036×1036 BICUBIC) | 원본 위 영역 박스 오버레이 | – |
| 📱 휘어진 사진 분석 | `\nMulti-point Layout Segmentation Analysis.` (1036×1036) | 다각형 오버레이 | – |
| 📈 그래프→데이터표 | `This is a scientific figure. Please extract the table implied by this figure.` | 편집 가능한 표 | + .xlsx |
| 🔖 도장 인식 | `\nSeal Recognition:` (GitHub 저장소에서 확인) | 편집 가능한 텍스트 | 복사, .md, .docx |

그 밖의 기능
- 이미지(JPG/PNG/WEBP)·PDF를 끌어다 놓기, 파일 선택, **Ctrl+V 붙여넣기**로 올릴 수 있습니다. PDF는 쪽을 골라(범위 입력 가능) 한꺼번에 변환하며 진행률을 보여 줍니다.
- **✂️ 영역 잘라서 변환**: 원본 위에서 끌어서(또는 키보드로) 영역을 고르면 그 부분만 다시 변환합니다. 레이아웃 결과의 영역을 누르면 그 영역과 알맞은 작업이 자동으로 선택됩니다.
- **🧩 한 쪽 통째로 변환(실험)**: 레이아웃 분석 → 영역별 텍스트/표/수식/코드 추론 → 하나의 Markdown 문서로 조립(공식 저장소의 전체 파싱 파이프라인을 단순화해 구현).
- **시스템 점검**: 감지된 장치, 모델 다운로드 여부·진행률, 사용 중인 모델 ID와 revision, 예상 속도, 샘플 테스트.
- **최근 변환 기록**: 브라우저 localStorage 에만 저장(최근 30건), 개별·전체 삭제, 기록 끄기.
- **모델 소개(`/about`)**, **활용 가이드(`/guide`)** 페이지. 내용은 `frontend/src/content/*.md` 에 있습니다.

---

## 설치

### 권장 사양

| 구분 | 최소 | 권장 |
|---|---|---|
| 메모리(RAM) | 8GB | 16GB 이상 |
| 저장 공간 | 10GB 여유 (프로그램 + 모델) | 15GB 이상 |
| 장치 | CPU만 있어도 동작(느림) | NVIDIA GPU(VRAM 6GB 이상) 또는 Apple Silicon Mac |
| 운영체제 | Windows 10/11, macOS 12 이상 | |
| Python | 3.10 ~ 3.12 | 3.11 |

예상 속도(작업·이미지 크기에 따라 크게 달라짐): NVIDIA GPU 한 장당 수 초~20초, Apple Silicon 10초~1분, **CPU 1분~수 분**.
표 하나·수식 하나처럼 잘라서 넣으면 훨씬 빨라집니다.

### Windows

1. [python.org](https://www.python.org/downloads/) 에서 Python 3.11 설치 (설치 첫 화면에서 **Add python.exe to PATH** 체크)
2. 이 폴더의 `scripts\install.bat` 더블클릭
3. `scripts\start.bat` 더블클릭 → 브라우저에서 `http://127.0.0.1:8765` 가 열립니다.

### macOS

1. [python.org](https://www.python.org/downloads/) 에서 Python 3.11 설치
2. `scripts/install.command` 더블클릭 (처음에는 Finder 에서 **우클릭 → 열기**)
3. `scripts/start.command` 더블클릭

Apple Silicon 에서는 PyPI 의 기본 PyTorch 가 MPS 가속을 지원합니다. 실행 스크립트는 `PYTORCH_ENABLE_MPS_FALLBACK=1` 을 설정합니다.

### NVIDIA GPU (CUDA) 사용

`install.bat` 는 `nvidia-smi` 가 있으면 CUDA 12.6용 PyTorch를 자동으로 설치합니다. 직접 설치하려면:

```bash
# 가상환경 활성화 후
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

드라이버가 오래되어 CUDA 12.6을 지원하지 않으면 `cu121`/`cu118` 인덱스를 사용하세요([PyTorch 설치 안내](https://pytorch.org/get-started/locally/)).
CUDA 에서는 자동으로 bfloat16, MPS/CPU 에서는 float32(설정에서 변경 가능)를 사용합니다.

### 직접 실행 (개발자)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m backend.main                               # http://127.0.0.1:8765
```

---

## 설정 (`backend/config.yaml`)

```yaml
model:
  id: "XingChen-AGI/TeleOCR"          # 공식 ID
  fallback_ids: ["StarDoc-AI/TeleOCR", "StarDoc-AI/NaviDC-OCR"]   # 실패 시 순서대로 시도
  revision: ""                        # 커밋 해시를 적으면 그 버전으로 고정 (권장)
  fallback_revisions: {}              # 대체 ID 별 커밋 해시
  max_new_tokens: 4096
runtime:
  backend: "transformers"             # "mock" = GPU·모델 없이 고정 샘플 결과
  device: "auto"                      # auto(CUDA → MPS → CPU) / cuda / mps / cpu
  cpu_mps_dtype: "float32"            # float32 / bfloat16 / float16
server:
  host: "127.0.0.1"                   # 다른 값을 적어도 127.0.0.1 로 강제
  port: 8765
  max_upload_mb: 50
  upload_ttl_minutes: 60
```

**revision 고정을 권장합니다.** 모델은 `trust_remote_code=True` 로 저장소의 파이썬 코드를 내 PC에서 실행하므로, 해시를 고정해야 코드가 예고 없이 바뀌지 않습니다.
`python scripts/smoke_test.py` 를 실행하면 실제로 내려받은 커밋 해시가 출력되니, 결과를 확인한 뒤 그 값을 `revision` 에 적으세요.

---

## 확인된 사실 (작업 단계별 보고)

> 개발 환경(클라우드 컨테이너)에서는 **huggingface.co, hf-mirror, ModelScope, download.pytorch.org 접속이 네트워크 정책으로 차단**되어(HTTP 403) 실제 모델 가중치를 내려받을 수 없었습니다.
> GitHub 저장소 원본 코드(raw.githubusercontent.com)는 읽을 수 있었으므로, 아래 사실은 **공식 저장소 코드로 확인한 것**과 **아직 실제 모델로 확인하지 못한 것**을 구분해 적습니다.

| 항목 | 상태 | 내용 |
|---|---|---|
| 모델 ID `XingChen-AGI/TeleOCR` 로드 | ⚠️ 미확인 | 개발 환경에서 Hugging Face 차단. 대체 ID 순서 로직은 모킹 테스트로 검증. **처음 설치한 PC에서 `scripts/smoke_test.py` 로 확인 필요** |
| revision(커밋 해시) | ⚠️ 미확인 | 위와 같은 이유로 해시를 기록하지 못함. `config.yaml` 은 비워 둠(= main). smoke_test 출력값으로 채울 것 |
| 공식 저장소가 쓰는 ID | ✅ 확인 | `TeleOCR/config.py` 의 기본값은 이관 전 ID `StarDoc-AI/TeleOCR`. 이 앱은 항상 `config.yaml` 의 ID를 사용 |
| 레이아웃 출력 형식 | ✅ 코드로 확인 / ⚠️ 실제 출력 미확인 | `TeleOCR_client.py` 의 `parse_layout_output`: 한 줄에 `<box:x1 y1 x2 y2 ...><label:종류><방향>`. 좌표는 0~1000 정규화(1036×1036 입력 기준), 점 2개는 사각형, 그 이상은 다각형(휘어진 문서). 방향 태그 `up/right/down/left` = 0/90/180/270°. 종류는 text, title, table, equation, code, image, seal, char(과학 그림) 등 24종. 이 형식으로 `backend/ocr/layout.py` 를 작성했고 해석 실패 시 원문을 그대로 보여 줌 |
| 도장 인식 프롬프트 | ✅ 확인 | `DEFAULT_PROMPTS["seal"] = "\nSeal Recognition:"` → 🔖 도장 인식 카드 추가 |
| 수식 후처리 | ✅ 확인 | 공식 코드도 `\[ \]`·`\( \)` 제거 후 `$$` 로 감쌈. 이 앱은 요구사항대로 이 두 단계만 적용(공식 파이프라인의 추가 보정 단계는 생략) |
| OTSL 토큰 | ✅ 확인 | `<fcel> <ecel> <lcel> <ucel> <xcel> <nl>` |
| 한국어 인식 품질 | ⚠️ 미확인 | 모델을 실행할 수 없어 점검하지 못함. 아래 "알려진 한계" 참고. `samples/korean_text.png` 로 점검 가능 |

참고: 공식 저장소의 파이프라인은 모든 프롬프트 앞에 줄바꿈(`\n`)을 붙여 사용합니다(`"\nPlease output the text content from the image."` 등).
이 앱은 요구사항에 따라 **모델 카드 문구를 그대로** 사용하므로 텍스트·표·수식·코드·레이아웃·그래프 프롬프트에는 앞 줄바꿈이 없습니다.
실제 모델에서 품질 차이가 보이면 `backend/ocr/tasks.py` 의 문구 앞에 `\n` 을 붙여 비교해 보세요.

### 실제 모델 확인 방법

```bash
python scripts/smoke_test.py --json smoke_result.json
```

모델 ID(대체 ID 사용 여부), revision, 장치, 각 작업의 원본 출력·후처리 결과·소요 시간이 출력됩니다. 레이아웃 원본 출력이 위 형식과 같은지, 한국어 샘플 결과가 어떤지 확인해 이 README 에 기록하세요.

---

## 알려진 한계

- **한국어**: 공식 지원 언어는 영어·중국어이며 한국어는 명시되어 있지 않습니다. 이 개발 환경에서는 모델을 내려받을 수 없어 **한국어 인식 품질을 직접 점검하지 못했습니다.** 설치 후 `samples/korean_text.png`(가정통신문 형식의 인쇄체 한국어)로 `smoke_test.py` 를 실행해 결과를 이 절에 기록해 주세요. 그 전까지는 한국어 결과를 **반드시 원본과 비교**해야 합니다.
- **손글씨**: 성능이 공개되지 않았습니다. 학생 답안 자동 채점 용도로는 권장하지 않습니다.
- **레이아웃 파서**: 공식 코드 기준으로 작성했으며, 실제 출력이 다르면 원문 텍스트를 그대로 보여 줍니다.
- **Word 수식**: .docx 에는 수식이 LaTeX 원문으로 들어갑니다(Word/한글에서 LaTeX 입력으로 변환 필요).
- **한 쪽 통째로 변환**은 공식 파이프라인의 읽기 순서 보정·문단 병합·표 캡션 결합 등을 생략한 단순 버전입니다.
- **CPU 전용 PC**는 매우 느립니다(한 장 1분~수 분).
- 선택 요구사항 중 **폴더 일괄 변환·ZIP 다운로드**(1)와 **GGUF/MLX 백엔드**(3)는 구현하지 않았습니다. `OcrBackend` 인터페이스(`backend/ocr/base.py`)에 `load()/generate()/status()` 만 구현하면 `create_backend()` 에 추가할 수 있습니다. TeleOCR 텍스트 디코더는 표준 Qwen2.5-VL 과 다른 QK-norm 변형이라 범용 GGUF 변환본(예: 커뮤니티의 NaviDC-OCR-GGUF)이 그대로 맞는지 원본 출력과 비교하는 테스트가 반드시 필요합니다.

---

## 개인정보·보안 설계

- 서버는 `127.0.0.1` 에만 바인딩하고, `Host` 헤더를 `127.0.0.1`/`localhost` 로 제한해 DNS 리바인딩 공격을 막습니다.
- 화면에는 CSP(`default-src 'self'`)를 적용해 외부 스크립트·글꼴·분석 도구를 불러올 수 없습니다. 글꼴은 OS 기본 한글 글꼴, KaTeX 글꼴은 빌드 결과에 포함됩니다.
- Hugging Face 텔레메트리를 끄고(`HF_HUB_DISABLE_TELEMETRY=1`), 모델이 캐시에 있으면 `local_files_only` 로만 불러와 네트워크에 접속하지 않습니다.
- 업로드 파일은 OS 임시 폴더의 전용 폴더에 저장하고, 확장자와 파일 시그니처를 함께 검사하며, 50MB 상한을 둡니다. 사진은 PNG 로 바꾼 즉시 원본(EXIF 위치정보 포함)을 지우고, 파일 교체·창 닫기·60분 경과·서버 종료 시 폴더를 삭제합니다.
- 톈이(天翼) 유료 API 등 외부 API는 호출하지 않습니다.

---

## 개발

```
backend/
  main.py              FastAPI 앱 + 정적 파일(frontend/dist) 서빙
  config.yaml          모델 ID(+대체 ID), revision, 장치, dtype, 포트
  settings.py          설정 로더
  uploads.py           업로드 임시 보관·검증·PDF 렌더링(pypdfium2)
  ocr/
    base.py            OcrBackend 인터페이스
    transformers_backend.py
    mock_backend.py
    device.py          CUDA → MPS → CPU 자동 감지
    model_loader.py    모델 ID 대체 로직
    service.py         모델 싱글톤 + 추론 큐(동시 1건) + 전체 페이지 파싱
    tasks.py           작업 유형 → 프롬프트/전처리/후처리
    layout.py          레이아웃 출력 파서 (ContentBlock)
    postprocess.py     OTSL→HTML (TableCell), 수식 후처리
  export/              md / docx / xlsx 내보내기
  tests/
frontend/src/
  pages/  components/  content/  store/  api/  lib/
samples/               샘플 이미지 (scripts/make_samples.py 로 재생성)
scripts/               install/start 스크립트, smoke_test.py
docs/                  설치가이드.md
```

모델 카드 예제의 버그 수정: `ContentBlock`(`backend/ocr/layout.py`), `TableCell`(`backend/ocr/postprocess.py`)에 `@dataclass` 를 붙였고, `.cuda()` 하드코딩 대신 감지된 장치로 `model.to(device)` 합니다.

### 테스트

```bash
# 백엔드 (GPU·torch 불필요, MockBackend 사용)
pip install -r requirements-dev.txt
pytest --cov=backend/ocr --cov=backend/export

# 프론트엔드
cd frontend && npm install && npm test
```

현재 결과: 백엔드 107개 통과(`backend/ocr` + `backend/export` 커버리지 99%), 프론트엔드 29개 통과.

### 프론트엔드 빌드

교사가 Node.js 없이 쓸 수 있도록 빌드 결과(`frontend/dist`)를 저장소에 포함합니다. 화면을 고쳤다면 다시 빌드해 커밋하세요.

```bash
cd frontend && npm install && npm run build
# 개발 서버: npm run dev (API 는 127.0.0.1:8765 로 프록시) + 다른 창에서 TELEOCR_BACKEND=mock python -m backend.main
```

## 라이선스와 출처

- TeleOCR 모델: Apache-2.0 — <https://huggingface.co/XingChen-AGI/TeleOCR>, <https://github.com/caipeng328/TeleOCR>, arXiv 2608.12898
- PDF 렌더링은 pypdfium2(Apache-2.0/BSD)를 사용합니다. AGPL 인 PyMuPDF 는 사용하지 않습니다.
