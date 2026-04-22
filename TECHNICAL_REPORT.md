## Technical Report — Weekly Technology News Update

### Objective

Build an "Intelligent Assistant" that:
- Collects news articles from Vietnamese electronic newspapers (VnExpress, Thanh Nien, Tuoi Tre)
- Filters the **Technology** topic within the **last 7 days**
- Produces a weekly report with:
  - Executive Summary
  - Trending Keywords
  - Highlighted News (with source links)

### Data sources

RSS list (configured in `config/feeds.json`):
- VnExpress: `https://vnexpress.net/rss/so-hoa.rss`
- Thanh Nien: `https://thanhnien.vn/rss/cong-nghe.rss`
- Tuoi Tre: `https://tuoitre.vn/rss/cong-nghe.rss`

### Implementation workflow

#### 1) Ingest & normalization (Day 1)

Script: `scripts/ingest_feeds.py`

- Fetch RSS via `requests`
- Parse feeds via `feedparser`
- Clean descriptions:
  - `snippet` is taken from `summary/description`
  - strip HTML using `beautifulsoup4`
- Normalize timestamps:
  - parse datetime using `python-dateutil`
  - convert to UTC for a consistent 7-day window filter
- Deduplicate by normalized URL (drop `#fragment`, remove `utm_*`)

Output:
- `data/articles.jsonl` (1 line = 1 article)

#### 2) Trending Keywords

Script: `scripts/generate_weekly_report.py`

- Keyword corpus: **title-only** to keep phrases concise and reduce snippet noise
- Lightweight Vietnamese tokenization (regex) + minimal stopwords
- Extract candidate phrases with **TF-IDF n-grams (2–6 words)**
- Rule-based filtering to reduce noise:
  - remove overly generic / truncated phrases
  - require strong tech signals (Gemini/Chrome, iPhone/iOS, SIM/VNeID, Galaxy, Defender, Google Photos/Maps, etc.)
- Cluster/merge variants (canonical cluster IDs) to avoid duplicates and prioritize phrases that appear in **multiple articles** (document frequency)

#### 3) Highlighted News (key events)

Script: `scripts/generate_weekly_report.py`

- Vectorize weekly articles using TF-IDF
- Compute cosine similarity
- Greedy clustering with a similarity threshold
- Cluster scoring:
  - prefer clusters with more articles
  - add bonus for clusters covered by multiple sources
- Select top \(N\) clusters as highlighted events
- For each highlighted event:
  - representative title = newest article in the cluster
  - short summary = representative RSS snippet
  - include 1–3 source URLs
- Display grouping (rule-based): AI / Apple & Devices / Cybersecurity / Digital Transformation & eID / Other

#### 4) Weekly report generation

Output:
- `reports/weekly_tech_digest_YYYY-MM-DD.md`

Optional (not required):
- Enable `--llm_summary` to have an OpenAI-compatible LLM generate the Executive Summary.
- For token efficiency, only a compact set of keywords + truncated top highlights is sent, with hash-based caching.

### Achieved results (Weekly Summary Report)

Weekly report file:
- `reports/weekly_tech_digest_2026-04-22.md`

Excerpt:

---

## Weekly News Update — Technology (2026-04-22)

### Executive Summary

Tuần qua, hệ thống thu thập được **131** bài thuộc chủ đề **Công nghệ** từ các nguồn **thanhnien** (50), **vnexpress** (60), **tuoitre** (21).

Khoảng thời gian dữ liệu: từ **2026-04-14T16:50:42+00:00** đến **2026-04-21T14:28:00+00:00** (UTC).

Các chủ đề nổi bật xoay quanh: **robot hình người, iPhone Pro, SIM chính chủ, Galaxy S27, Google Maps, chatbot Gemini, Google Photos, Microsoft Defender**.

### Trending Keywords

- **robot hình người**
- **iphone pro**
- **sim chính chủ**
- **galaxy s27**
- **google maps**
- **chatbot gemini**
- **google photos**
- **microsoft defender**


### Highlighted News

- **Trình duyệt Chrome ở Việt Nam được tích hợp chatbot Gemini**
  - Nguồn: vnexpress. Gemini tích hợp vào Chrome cho phép người dùng có thể tương tác nhanh với mọi website trên trình duyệt, nhưng cũng đặt ra câu hỏi về quyền riêng tư.
  - Link: [https://vnexpress.net/trinh-duyet-chrome-o-viet-nam-duoc-tich-hop-chatbot-gemini-5064827.html](https://vnexpress.net/trinh-duyet-chrome-o-viet-nam-duoc-tich-hop-chatbot-gemini-5064827.html)

- **3 sai lầm khiến iPhone hư hỏng nhanh hơn**
  - Nguồn: thanhnien. Nhiều người dùng iPhone thường mắc phải 3 sai lầm tai hại khiến thiết bị dễ trở thành 'cục chặn giấy'.
  - Link: [https://thanhnien.vn/3-sai-lam-khien-iphone-hu-hong-nhanh-hon-185260420210548112.htm](https://thanhnien.vn/3-sai-lam-khien-iphone-hu-hong-nhanh-hon-185260420210548112.htm)

- **Microsoft Defender bị biến thành công cụ tiếp tay cho hacker**
  - Nguồn: thanhnien. Lỗ hổng Red Sun khiến phần mềm diệt virus trở thành công cụ giúp hacker chiếm quyền điều khiển máy tính.
  - Link: [https://thanhnien.vn/microsoft-defender-bi-bien-thanh-cong-cu-tiep-tay-cho-hacker-185260421103654325.htm](https://thanhnien.vn/microsoft-defender-bi-bien-thanh-cong-cu-tiep-tay-cho-hacker-185260421103654325.htm)

- **Thị trường robot hút bụi Việt Nam 'ngày càng nóng'**
  - Nguồn: thanhnien. Việt Nam là thị trường robot hút bụi thông minh năng động hàng đầu khu vực, có sự chuyển dịch rõ rệt sang phân khúc cao cấp và dần trở thành cuộc đua khốc liệt của những "gã khổng lồ" công nghệ toàn cầu.
  - Link: [https://thanhnien.vn/thi-truong-robot-hut-bui-viet-nam-ngay-cang-nong-185260421165646371.htm](https://thanhnien.vn/thi-truong-robot-hut-bui-viet-nam-ngay-cang-nong-185260421165646371.htm)



