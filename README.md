## Weekly Tech News Assistant (Ngày 1)

Pipeline ngày 1: **tải RSS** (VnExpress/Thanh Niên/Tuổi Trẻ) → **làm sạch snippet** (strip HTML) → **lọc 7 ngày** → **khử trùng lặp theo URL** → xuất `JSONL`.

### Cài đặt

```bash
python -m venv .venv
# PowerShell
.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
```

### Chạy ingest

```bash
python scripts/ingest_feeds.py --config config/feeds.json
```

Tuỳ chọn:

```bash
python scripts/ingest_feeds.py --config config/feeds.json --days 7 --out data/articles.jsonl
```

### Output

- `data/articles.jsonl` (1 dòng = 1 JSON record)
- Schema mỗi record:
  - `source`, `feed_url`, `title`, `url`, `published_at` (ISO/UTC), `snippet`

## Báo cáo tuần (đúng yêu cầu bài test)

Sau khi đã có `data/articles.jsonl`, chạy script sau để sinh báo cáo tuần gồm:
- Executive Summary
- Trending Keywords
- Highlighted News (kèm link nguồn)

```bash
python scripts/generate_weekly_report.py --articles data/articles.jsonl
```

Output mặc định:
- `reports/weekly_tech_digest_YYYY-MM-DD.md`

### (Tuỳ chọn) Dùng LLM để viết Executive Summary

Mặc định Executive Summary được tạo theo cách deterministic. Nếu muốn LLM viết cho "mượt" hơn và vẫn tối ưu token:

```bash
# PowerShell
$env:LLM_API_KEY="YOUR_KEY"
# Tuỳ chọn:
# $env:LLM_BASE_URL="https://api.openai.com"
# $env:LLM_MODEL="gpt-4o-mini"

python scripts/generate_weekly_report.py --articles data/articles.jsonl --llm_summary
```
