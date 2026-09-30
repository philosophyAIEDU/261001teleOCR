#!/bin/bash
# TeleOCR 교실 실행 (macOS) - 더블클릭해서 실행하세요. 이 창을 닫으면 프로그램이 종료돼요.
cd "$(dirname "$0")/.." || exit 1

if [ ! -x ".venv/bin/python" ]; then
  echo "아직 설치가 되지 않았어요. 설치를 먼저 진행합니다."
  bash scripts/install.command || exit 1
fi

# Apple Silicon 에서 MPS 가 지원하지 않는 연산은 CPU 로 대신 계산하게 합니다.
export PYTORCH_ENABLE_MPS_FALLBACK=1
echo "TeleOCR 교실을 시작하고 있어요. 잠시 후 브라우저가 열려요..."
echo "브라우저가 열리지 않으면 주소창에 http://127.0.0.1:8765 를 입력하세요."
.venv/bin/python -m backend.main || read -r -p "[오류] 프로그램이 멈췄어요. 엔터를 누르면 창이 닫혀요..." _
