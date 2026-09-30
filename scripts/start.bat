@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
title TeleOCR 교실 - 실행 중 (이 창을 닫으면 종료돼요)

if not exist ".venv\Scripts\python.exe" (
  echo 아직 설치가 되지 않았어요. 설치를 먼저 진행합니다.
  call "%~dp0install.bat" || exit /b 1
)

echo TeleOCR 교실을 시작하고 있어요. 잠시 후 브라우저가 열려요...
echo 브라우저가 열리지 않으면 주소창에 http://127.0.0.1:8765 를 입력하세요.
".venv\Scripts\python.exe" -m backend.main
if errorlevel 1 (
  echo.
  echo [오류] 프로그램이 멈췄어요. 이미 실행 중인 창이 있는지 확인해 주세요.
  pause
)
