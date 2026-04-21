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
