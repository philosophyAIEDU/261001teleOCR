@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
title TeleOCR 교실 - 설치

echo ============================================
echo   TeleOCR 교실 설치를 시작합니다
echo   (처음 한 번만, 10~30분 정도 걸려요)
echo ============================================
echo.

set "PY="
where py >nul 2>nul && (py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=py -3")
if not defined PY (
  where python >nul 2>nul && (python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=python")
)
if not defined PY (
  echo [안내] Python 3.10 이상이 설치되어 있지 않아요.
  echo   1. https://www.python.org/downloads/ 에서 Python 을 내려받아 설치하세요.
  echo   2. 설치 첫 화면에서 "Add python.exe to PATH" 에 꼭 체크하세요.
  echo   3. 설치가 끝나면 이 파일을 다시 더블클릭하세요.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] 전용 실행 환경을 만들고 있어요...
  %PY% -m venv .venv || goto :fail
)
set "VPY=.venv\Scripts\python.exe"

echo [2/4] 설치 도구를 최신으로 바꾸고 있어요...
"%VPY%" -m pip install --upgrade pip >nul || goto :fail

echo [3/4] AI 실행 프로그램(PyTorch)을 설치하고 있어요...
where nvidia-smi >nul 2>nul
if %errorlevel%==0 (
  echo      NVIDIA 그래픽카드를 찾았어요. GPU 버전으로 설치합니다.
  "%VPY%" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126 || goto :fail
) else (
  echo      NVIDIA 그래픽카드가 없어 CPU 버전으로 설치합니다. ^(변환이 느릴 수 있어요^)
  "%VPY%" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu || goto :fail
)

echo [4/4] 나머지 프로그램을 설치하고 있어요...
"%VPY%" -m pip install -r requirements.txt || goto :fail

echo.
echo ============================================
echo   설치가 끝났어요!
echo   scripts 폴더의 start.bat 을 더블클릭해 실행하세요.
echo   (처음 변환할 때 AI 모델을 한 번 내려받아요)
echo ============================================
pause
exit /b 0

:fail
echo.
echo [오류] 설치 중 문제가 생겼어요. 인터넷 연결을 확인하고 다시 실행해 주세요.
echo        계속 안 되면 이 창의 내용을 사진으로 찍어 도움을 요청하세요.
pause
exit /b 1
