@echo off
cd /d "%~dp0..\.."
if not exist ".venv\Scripts\pythonw.exe" (
  echo The project Python environment is missing. See games\starfall\README.md for setup.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m games.starfall.app --connect
