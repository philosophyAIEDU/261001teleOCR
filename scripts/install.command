#!/bin/bash
# TeleOCR 교실 설치 (macOS) - 더블클릭해서 실행하세요.
cd "$(dirname "$0")/.." || exit 1

echo "============================================"
echo "  TeleOCR 교실 설치를 시작합니다"
echo "  (처음 한 번만, 10~30분 정도 걸려요)"
echo "============================================"

PY=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && \
     "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    PY="$candidate"; break
  fi
done

if [ -z "$PY" ]; then
  echo "[안내] Python 3.10 이상이 필요해요."
  echo "  https://www.python.org/downloads/ 에서 macOS 용 Python 을 설치한 뒤 이 파일을 다시 실행하세요."
  read -r -p "엔터를 누르면 창이 닫혀요..." _
  exit 1
fi

fail() {
  echo ""
  echo "[오류] 설치 중 문제가 생겼어요. 인터넷 연결을 확인하고 다시 실행해 주세요."
  read -r -p "엔터를 누르면 창이 닫혀요..." _
  exit 1
}

if [ ! -x ".venv/bin/python" ]; then
  echo "[1/3] 전용 실행 환경을 만들고 있어요..."
  "$PY" -m venv .venv || fail
fi

echo "[2/3] 설치 도구를 최신으로 바꾸고 있어요..."
.venv/bin/python -m pip install --upgrade pip >/dev/null || fail

echo "[3/3] AI 실행 프로그램과 나머지 프로그램을 설치하고 있어요..."
if [ "$(uname -m)" = "arm64" ]; then
  echo "     Apple Silicon(M 시리즈)을 찾았어요. 가속(MPS)을 사용할 수 있어요."
else
  echo "     Intel Mac 이라 CPU 로 실행돼요. 변환이 느릴 수 있어요."
fi
.venv/bin/python -m pip install -r requirements.txt || fail

chmod +x scripts/start.command 2>/dev/null
echo ""
echo "============================================"
echo "  설치가 끝났어요!"
echo "  scripts 폴더의 start.command 를 더블클릭해 실행하세요."
echo "============================================"
read -r -p "엔터를 누르면 창이 닫혀요..." _
