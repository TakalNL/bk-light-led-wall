@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo This source preview needs the development environment described in README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import aiohttp" >nul 2>&1
if errorlevel 1 (
  echo Install the web extra once: .venv\Scripts\python.exe -m pip install -e ".[server]"
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m led_matrix_hacker.server --host 0.0.0.0 --open
if errorlevel 1 pause
