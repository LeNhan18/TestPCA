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

- Corpus: `title + snippet` của từng bài
- Tokenize tiếng Việt kiểu nhẹ (regex word)
- Lọc stopwords tối thiểu để giảm nhiễu
- Gộp từ khóa theo **chủ đề (topic-level)** để tránh trùng nghĩa:
  - Ví dụ: "xác thực SIM" / "SIM chính chủ" / "thuê bao" / "VNeID" → **Xác thực SIM / VNeID**
- Xếp hạng theo **độ phủ nhiều bài (document frequency)**, có TF-IDF hỗ trợ để giảm nhiễu từ 1 bài đơn lẻ

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

### Kết quả đạt được (Weekly Summary Report)

File báo cáo tuần:
- `reports/weekly_tech_digest_2026-04-21.md`

Nội dung:

---

## Weekly News Update — Technology (2026-04-21)

### Executive Summary

Tuần qua, hệ thống thu thập được **131** bài thuộc chủ đề **Công nghệ** từ các nguồn **thanhnien** (50), **vnexpress** (60), **tuoitre** (21).

Khoảng thời gian dữ liệu: từ **2026-04-14T16:50:42+00:00** đến **2026-04-21T13:37:00+00:00** (UTC).

Các chủ đề nổi bật xoay quanh: **robot hình người, iPhone Pro, xác thực SIM, Galaxy S26, Google Maps, bảo mật, Google Photos, Gemini tự động**.

### Trending Keywords

- **robot hình người**
- **iphone pro**
- **xác thực sim**
- **galaxy s26**
- **google maps**
- **bảo mật**
- **google photos**
- **gemini tự động**

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



