## Weekly Tech News Assistant

Trợ lý tổng hợp tin **Công nghệ** theo tuần từ RSS của:
- VnExpress (`so-hoa`)
- Thanh Niên (`cong-nghe`)
- Tuổi Trẻ (`cong-nghe`)

Mục tiêu (đúng yêu cầu bài test):
- **Executive Summary**: bối cảnh chung + xu hướng + diễn biến đáng chú ý
- **Trending Keywords**: danh sách từ khóa/cụm từ nổi bật trong tuần
- **Highlighted News**: các sự kiện quan trọng, có tóm tắt ngắn và link nguồn

## Yêu cầu

- Python 3.10+ (khuyến nghị 3.11+)
- Windows / macOS / Linux

## Chạy nhanh 

### Windows 

Chạy trực tiếp:

```bash
run_pipeline.bat
```

Kết quả:
- `data/articles.jsonl`
- `reports/weekly_tech_digest_YYYY-MM-DD.md`

### macOS/Linux (3 lệnh)

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/ingest_feeds.py --config config/feeds.json
python scripts/generate_weekly_report.py --articles data/articles.jsonl --top_keywords 25 --top_events 20
```

## Cài đặt

```bash
python -m venv .venv
```

PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Chạy pipeline

### 1) Ingest dữ liệu RSS → `data/articles.jsonl`

```bash
python scripts/ingest_feeds.py --config config/feeds.json
```

Tuỳ chọn:

```bash
python scripts/ingest_feeds.py --config config/feeds.json --days 7 --out data/articles.jsonl
```

Output:
- `data/articles.jsonl` (1 dòng = 1 bài)
- Trường chính: `source`, `feed_url`, `title`, `url`, `published_at` (ISO/UTC), `snippet`

### 2) Sinh báo cáo tuần → `reports/*.md`

```bash
python scripts/generate_weekly_report.py --articles data/articles.jsonl
```

Output mặc định:
- `reports/weekly_tech_digest_YYYY-MM-DD.md`

Tuỳ chọn (điều chỉnh số lượng):

```bash
python scripts/generate_weekly_report.py --articles data/articles.jsonl --top_keywords 25 --top_events 20
```

## (Tuỳ chọn) Dùng LLM để viết Executive Summary

Mặc định Executive Summary được tạo theo cách deterministic để **chạy được ngay khi clone repo**. Nếu muốn LLM viết “mượt” hơn, bật `--llm_summary` và cấu hình qua biến môi trường (không hardcode key).

PowerShell:

```bash
$env:LLM_API_KEY="YOUR_KEY"
$env:LLM_BASE_URL="https://api.groq.com/openai"
$env:LLM_MODEL="llama-3.1-8b-instant"

python scripts/generate_weekly_report.py --articles data/articles.jsonl --llm_summary
```

Hoặc (Windows) chạy file:

```bash
run_llm_summary.bat
```

Ghi chú:
- Nếu thiếu `LLM_API_KEY` mà bật `--llm_summary`, chương trình sẽ tự fallback sang bản deterministic và ghi chú lỗi trong báo cáo.
- Kết quả LLM có cache ở `.cache/llm/` để tránh gọi lại tốn token khi chạy nhiều lần.

## Cấu trúc thư mục

- `config/feeds.json`: danh sách RSS + tham số mặc định
- `scripts/ingest_feeds.py`: ingest RSS, lọc 7 ngày, dedupe URL
- `scripts/generate_weekly_report.py`: trending keywords, clustering highlights, sinh Markdown report
- `src/ingest/`: logic ingest RSS
- `src/reporting/`: tiền xử lý text tiếng Việt
- `src/llm/`: gọi API OpenAI-compatible (tuỳ chọn)
- `reports/`: báo cáo Markdown đã sinh

## Troubleshooting (Windows)

- Nếu PowerShell chặn activate venv, chạy:
  - `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
