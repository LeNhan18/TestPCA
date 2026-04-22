## Weekly Tech News Assistant

An assistant that collects and summarizes **weekly Technology news** from Vietnamese newspaper RSS feeds:
- VnExpress (`so-hoa`)
- Thanh Nien (`cong-nghe`)
- Tuoi Tre (`cong-nghe`)

Deliverables:
- **Executive Summary**: overall landscape + key trends + notable developments
- **Trending Keywords**: a list of important keywords/topics
- **Highlighted News**: key events with short summaries and source links

## Requirements

- Python 3.10+ (3.11+ recommended)
- Windows / macOS / Linux

## Quickstart 

### Windows (one command)

```bash
run_pipeline.bat
```

Outputs:
- `data/articles.jsonl`
- `reports/weekly_tech_digest_YYYY-MM-DD.md`

### macOS/Linux

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python scripts/ingest_feeds.py --config config/feeds.json
python scripts/generate_weekly_report.py --articles data/articles.jsonl --top_keywords 25 --top_events 20
```

## Manual run (step-by-step)

### 1) Setup

```bash
python -m venv .venv
```

PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2) Ingest RSS → `data/articles.jsonl`

```bash
python scripts/ingest_feeds.py --config config/feeds.json
```

Optional:

```bash
python scripts/ingest_feeds.py --config config/feeds.json --days 7 --out data/articles.jsonl
```

Output schema:
- `source`, `feed_url`, `title`, `url`, `published_at` (ISO/UTC), `snippet`

### 3) Generate weekly report → `reports/*.md`

```bash
python scripts/generate_weekly_report.py --articles data/articles.jsonl
```

Optional (tune counts):

```bash
python scripts/generate_weekly_report.py --articles data/articles.jsonl --top_keywords 25 --top_events 20
```

## (Optional) Use an LLM for the Executive Summary

By default, the Executive Summary is deterministic so the repo runs end-to-end right after cloning.
To enable LLM summary, pass `--llm_summary` and configure environment variables (do not hardcode keys).

PowerShell example (Groq OpenAI-compatible):

```bash
$env:LLM_API_KEY="YOUR_KEY"
$env:LLM_BASE_URL="https://api.groq.com/openai"
$env:LLM_MODEL="llama-3.1-8b-instant"

python scripts/generate_weekly_report.py --articles data/articles.jsonl --llm_summary
```

Or (Windows):

```bash
run_llm_summary.bat
```

Notes:
- If `LLM_API_KEY` is missing while `--llm_summary` is enabled, the script falls back to the deterministic summary and writes a note in the report.
- LLM outputs are cached under `.cache/llm/`.

## Project structure

- `config/feeds.json`: RSS feed list and defaults
- `scripts/ingest_feeds.py`: RSS ingest + 7-day filtering + URL dedup
- `scripts/generate_weekly_report.py`: trending keywords, highlight clustering, Markdown report
- `src/ingest/`: RSS ingest logic
- `src/reporting/`: Vietnamese text preprocessing
- `src/llm/`: OpenAI-compatible client (optional)
- `reports/`: generated Markdown reports

## Troubleshooting (Windows)

- If PowerShell blocks venv activation:
  - `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
