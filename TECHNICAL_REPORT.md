## Technical Report — Weekly Technology News Update

### Mục tiêu

Xây dựng một "Intelligent Assistant" có khả năng:
- Thu thập dữ liệu tin tức từ báo điện tử (VnExpress, Thanh Niên, Tuổi Trẻ)
- Lọc theo chủ đề **Technology** trong **7 ngày gần nhất**
- Tạo báo cáo tuần gồm:
  - Executive Summary
  - Trending Keywords
  - Highlighted News (kèm link nguồn)

### Nguồn dữ liệu

Danh sách RSS (cấu hình tại `config/feeds.json`):
- VnExpress: `https://vnexpress.net/rss/so-hoa.rss`
- Thanh Niên: `https://thanhnien.vn/rss/cong-nghe.rss`
- Tuổi Trẻ: `https://tuoitre.vn/rss/cong-nghe.rss`

### Workflow triển khai

#### 1) Ingest & chuẩn hóa (Ngày 1)

Script: `scripts/ingest_feeds.py`

- Tải RSS bằng `requests`
- Parse RSS bằng `feedparser`
- Làm sạch mô tả:
  - `snippet` lấy từ `summary/description`
  - strip HTML bằng `beautifulsoup4`
- Chuẩn hóa thời gian:
  - parse datetime bằng `python-dateutil`
  - quy về UTC để lọc cửa sổ 7 ngày
- Dedupe theo URL (bỏ `#fragment`, loại `utm_*`)

Output:
- `data/articles.jsonl` (1 dòng = 1 bài)

#### 2) Tính Trending Keywords

Script: `scripts/generate_weekly_report.py`

- Corpus cho keyword: **title-only** để cụm từ gọn và ít nhiễu hơn snippet
- Tokenize tiếng Việt kiểu nhẹ (regex word) + stopwords tối thiểu
- Trích xuất cụm từ bằng **TF-IDF n-gram 2–6 từ**
- Lọc rule để giảm nhiễu:
  - loại cụm quá chung / cụm bị cắt
  - yêu cầu “tín hiệu công nghệ” (Gemini/Chrome, iPhone/iOS, SIM/VNeID, Galaxy, Defender, Google Photos/Maps…)
- Gộp biến thể (clustering theo canonical id) để tránh trùng nghĩa và ưu tiên cụm xuất hiện ở **nhiều bài** (document frequency)

#### 3) Chọn Highlighted News (sự kiện nổi bật)

Script: `scripts/generate_weekly_report.py`

- Vector hóa (TF-IDF) toàn tập bài trong tuần
- Tính cosine similarity
- Gom cụm theo ngưỡng similarity (greedy clustering)
- Chấm điểm cụm:
  - ưu tiên cụm có nhiều bài hơn
  - cộng điểm nếu cụm có nhiều nguồn khác nhau
- Lấy top \(N\) cụm làm Highlighted News
- Mỗi mục:
  - tiêu đề đại diện = bài mới nhất trong cụm
  - tóm tắt ngắn = snippet bài đại diện
  - kèm 1–3 link nguồn
 - Nhóm hiển thị theo chủ đề (rule-based): AI / Apple & thiết bị / An ninh mạng / Chuyển đổi số / Khác

#### 4) Sinh Weekly Summary Report

Output:
- `reports/weekly_tech_digest_YYYY-MM-DD.md`

Tuỳ chọn (không bắt buộc):
- Có thể bật `--llm_summary` để dùng LLM API viết Executive Summary.
- Để tiết kiệm token, input gửi lên chỉ gồm: danh sách keyword + một số highlight top đã cắt ngắn, và có cache theo hash.

### Kết quả đạt được (Weekly Summary Report)

File báo cáo tuần:
- `reports/weekly_tech_digest_2026-04-22.md`

Nội dung:

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



