@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -c "import amd_scenario_lab, streamlit, plotly" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install ".[ui]"
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m amd_scenario_lab ui
if errorlevel 1 goto fail
exit /b 0
:fail
echo Launch failed. Check the error above and confirm Python 3.10+ is installed.
pause
exit /b 1
