@echo off
setlocal enableextensions

REM Optional: generate report using LLM for Executive Summary.
REM Requires environment variables:
REM - LLM_API_KEY
REM Optional:
REM - LLM_BASE_URL
REM - LLM_MODEL

pushd "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Missing venv. Run run_pipeline.bat first (or create venv and install deps).
  exit /b 1
)

if "%LLM_API_KEY%"=="" (
  echo Missing LLM_API_KEY. Set it in your shell before running this script.
  echo Example (PowerShell^):
  echo   $env:LLM_API_KEY="YOUR_KEY"
  exit /b 1
)

call ".venv\Scripts\python.exe" scripts\generate_weekly_report.py --articles data\articles.jsonl --top_keywords 25 --top_events 20 --llm_summary
if errorlevel 1 exit /b 1

echo Done. Output report is under reports\
popd
endlocal

