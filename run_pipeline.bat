@echo off
setlocal enableextensions

REM One-click pipeline for Windows recruiters:
REM - create venv (if missing)
REM - install dependencies
REM - ingest RSS -> data/articles.jsonl
REM - generate weekly report -> reports/*.md

pushd "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating venv...
  py -m venv .venv
  if errorlevel 1 exit /b 1
)

echo [2/4] Installing dependencies...
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [3/4] Ingesting RSS feeds...
call ".venv\Scripts\python.exe" scripts\ingest_feeds.py --config config\feeds.json
if errorlevel 1 exit /b 1

echo [4/4] Generating weekly report (deterministic summary)...
call ".venv\Scripts\python.exe" scripts\generate_weekly_report.py --articles data\articles.jsonl --top_keywords 25 --top_events 20
if errorlevel 1 exit /b 1

echo Done. Output report is under reports\
popd
endlocal

