import argparse
import html
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.reporting.text_prep import basic_vi_tokenize, join_tokens, load_stopwords_vi
from src.llm.openai_compat import chat_completions_min_tokens


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate weekly digest report (Markdown).")
    p.add_argument(
        "--articles",
        default="data/articles.jsonl",
        help="Path to articles JSONL (default: data/articles.jsonl)",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Output markdown path (default: reports/weekly_tech_digest_YYYY-MM-DD.md)",
    )
    p.add_argument(
        "--top_keywords",
        type=int,
        default=25,
        help="Number of trending keywords to output (default: 25)",
    )
    p.add_argument(
        "--top_events",
        type=int,
        default=20,
        help="Number of highlighted events (default: 20)",
    )
    p.add_argument(
        "--cluster_threshold",
        type=float,
        default=0.62,
        help="Cosine similarity threshold for clustering (default: 0.62)",
    )
    p.add_argument(
        "--llm_summary",
        action="store_true",
        help="Use LLM API to write Executive Summary (requires LLM_API_KEY).",
    )
    return p.parse_args()


def load_articles(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run ingest first: python scripts/ingest_feeds.py"
        )

    rows: List[Dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def article_text(a: Dict[str, Any]) -> str:
    title = html.unescape((a.get("title") or "").strip())
    snippet = html.unescape((a.get("snippet") or "").strip())
    return f"{title}\n{snippet}".strip()


def build_corpus(articles: Sequence[Dict[str, Any]]) -> List[str]:
    stop = load_stopwords_vi()
    corpus: List[str] = []
    for a in articles:
        tokens = basic_vi_tokenize(article_text(a))
        corpus.append(join_tokens(tokens, stop))
    return corpus


def build_title_corpus(articles: Sequence[Dict[str, Any]]) -> List[str]:
    """
    Corpus chỉ từ tiêu đề để keyword tự nhiên hơn (giống headline),
    giảm nhiễu từ snippet dài.
    """
    stop = load_stopwords_vi()
    corpus: List[str] = []
    for a in articles:
        title = html.unescape((a.get("title") or "").strip())
        tokens = basic_vi_tokenize(title)
        corpus.append(join_tokens(tokens, stop))
    return corpus


def trending_phrases_clustered(
    corpus: Sequence[str],
    *,
    top_k: int,
    min_df_docs: int = 2,
) -> List[Tuple[str, float]]:
    if not corpus:
        return []

    vec = TfidfVectorizer(
        # 2-6 từ/cụm để ra keyword "tự nhiên" hơn
        ngram_range=(2, 6),
        min_df=1,
        max_df=0.85,
        sublinear_tf=True,
    )
    X = vec.fit_transform(corpus)
    terms = vec.get_feature_names_out()

    # tf-idf sum score
    tfidf_sum = X.sum(axis=0).A1
    # document frequency (số bài có term)
    df = (X > 0).sum(axis=0).A1

    TECH_SIGNALS = {
        "ai",
        "gemini",
        "chatbot",
        "chrome",
        "android",
        "ios",
        "iphone",
        "ipad",
        "mac",
        "apple",
        "google",
        "google photos",
        "samsung",
        "galaxy",
        "one ui",
        "sim",
        "vneid",
        "thuê bao",
        "định danh",
        "an ninh mạng",
        "bảo mật",
        "mã độc",
        "hacker",
        "lỗ hổng",
        "defender",
        "microsoft",
        "robot",
        "hình người",
        "drone",
        "5g",
        "ipv6",
        "phần mềm",
        "thiết bị",
        "máy tính",
    }

    STRONG_SIGNALS = {
        "gemini",
        "chatbot",
        "iphone",
        "ios",
        "apple",
        "galaxy",
        "samsung",
        "sim",
        "vneid",
        "an ninh mạng",
        "bảo mật",
        "mã độc",
        "lỗ hổng",
        "defender",
        "robot",
        "hình người",
        "google maps",
        "google photos",
        "ipv6",
        "5g",
    }

    VERY_STRONG_SINGLETONS = {
        "gemini",
        "chatbot gemini",
        "microsoft defender",
        "google photos",
        "google maps",
        "ios 27",
        "iphone 17",
        "iphone 17 pro",
        "iphone 17 pro max",
        "galaxy s26",
        "galaxy s26 ultra",
        "one ui",
        "one ui 8.5",
    }

    BAD_LAST_TOKENS = {"tự", "tích", "ứng", "hợp", "bổ", "nhằm", "dụng", "chính"}

    GENERIC_BAD = {
        "sử dụng",
        "hoạt động",
        "thành công",
        "trở thành",
        "nhiều người",
        "người dùng",  # quá chung nếu đứng 1 mình
        "triển khai",
        "thuê bao",  # quá chung nếu đứng 1 mình
        "hình người",  # sẽ lấy "robot hình người" thay vì "hình người"
    }

    def keep_phrase(term: str, dfi: int) -> bool:
        t = term.lower()
        parts = t.split()
        if parts and parts[-1] in BAD_LAST_TOKENS:
            return False
        if t in GENERIC_BAD:
            return False
        # phải có tín hiệu công nghệ (token/phrase)
        if not any(sig in t for sig in TECH_SIGNALS):
            return False
        # ưu tiên tín hiệu mạnh để tránh cụm chung chung
        if not any(sig in t for sig in STRONG_SIGNALS):
            return False

        # cần xuất hiện ở nhiều bài; nếu df=1 thì chỉ giữ nếu thuộc nhóm "rất mạnh"
        if dfi < min_df_docs:
            if not any(v in t for v in VERY_STRONG_SINGLETONS):
                return False
        # loại cụm quá chung kiểu "người dùng iphone trung thành" (động từ)
        if any(v in t for v in ["trung thành", "phổ biến", "sai lầm"]):
            return False
        # loại cụm bị cắt: "thực sim" nhưng không phải "xác thực ..."
        if "thực" in t and "xác thực" not in t:
            return False
        # loại cụm robot hình nhưng thiếu "người"
        if "robot hình" in t and "người" not in t:
            return False
        return True

    candidates: List[Tuple[str, int, float]] = []
    for term, dfi, si in zip(terms, df, tfidf_sum):
        if keep_phrase(term, int(dfi)):
            candidates.append((term, int(dfi), float(si)))

    # sort by df first, then tfidf
    candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)

    # clustering rule-based (synonyms/variants)
    def cluster_id(term: str) -> str:
        t = term.lower()
        if "google maps" in t:
            return "google_maps"
        if "google photos" in t:
            return "google_photos"
        # SIM/VNeID/thuê bao
        if any(k in t for k in ["sim", "thuê bao", "vneid", "định danh"]):
            return "sim_vneid"
        # AI/Gemini/Chatbot/Chrome
        if any(k in t for k in ["gemini", "chatbot", "ai", "chrome"]):
            return "ai_gemini"
        # Apple/iPhone/iOS
        if any(k in t for k in ["apple", "iphone", "ios", "ipad", "mac"]):
            return "apple_ios"
        # Samsung/Galaxy/One UI
        if any(k in t for k in ["samsung", "galaxy", "one ui"]):
            return "samsung_galaxy"
        # Security
        if any(k in t for k in ["an ninh mạng", "bảo mật", "mã độc", "hacker", "lỗ hổng", "defender"]):
            return "security"
        # Robot/Humanoid/Drone
        if any(k in t for k in ["robot", "hình người", "humanoid", "drone"]):
            return "robot"
        return term  # self cluster

    # pick representative per cluster (highest df, then tfidf)
    best: Dict[str, Tuple[str, int, float]] = {}
    cluster_best_score: Dict[str, float] = {}

    for term, dfi, si in candidates:
        cid = cluster_id(term)
        score = dfi + si
        # keep best representative phrase
        cur = best.get(cid)
        # ưu tiên phrase "đúng lõi" cho cluster SIM (chứa sim/vneid)
        if cid == "sim_vneid":
            t = term.lower()
            core = ("sim" in t) and (("vneid" in t) or ("chính chủ" in t) or ("xác thực" in t))
            cur_core = (
                cur is not None
                and (
                    ("sim" in cur[0].lower())
                    and (
                        ("vneid" in cur[0].lower())
                        or ("chính chủ" in cur[0].lower())
                        or ("xác thực" in cur[0].lower())
                    )
                )
            )
            if cur is None or (core and not cur_core) or ((dfi, si) > (cur[1], cur[2]) and (core == cur_core)):
                best[cid] = (term, dfi, si)
        else:
            if cur is None or (dfi, si) > (cur[1], cur[2]):
                best[cid] = (term, dfi, si)
        cluster_best_score[cid] = max(cluster_best_score.get(cid, 0.0), score)

    ranked_clusters = sorted(
        cluster_best_score.items(), key=lambda x: x[1], reverse=True
    )

    out: List[Tuple[str, float]] = []
    for cid, score in ranked_clusters:
        term, dfi, si = best[cid]
        out.append((term, score))
        if len(out) >= top_k:
            break
    return out


def looks_like_noise_topic(text: str) -> bool:
    t = text.lower()
    return any(
        k in t
        for k in [
            "audition",
            "esports",
            "marathon",
            "tên lửa",
            "quỹ đạo",
            "vệ tinh",
            "blue origin",
            "bitcoin",
            "btc",
        ]
    )


def highlight_category(text: str) -> str:
    t = text.lower()
    tokens = set(re.findall(r"[0-9A-Za-zÀ-ỹ]+", t))

    def has_word(w: str) -> bool:
        return w in tokens

    if any(has_word(k) for k in ["ai", "gemini", "chatbot", "llm", "claude"]):
        return "AI"
    if any(
        k in t
        for k in [
            "apple",
            "iphone",
            "ios",
            "ipad",
            "mac",
            "galaxy",
            "samsung",
            "thiết bị",
        ]
    ):
        return "Apple & thiết bị"
    if any(
        k in t
        for k in ["an ninh mạng", "mã độc", "bảo mật", "hacker", "lỗ hổng", "defender"]
    ):
        return "An ninh mạng"
    if any(
        k in t
        for k in ["chuyển đổi số", "định danh", "vneid", "dữ liệu số", "thuê bao", "sim"]
    ):
        return "Chuyển đổi số / Định danh"
    return "Khác"


@dataclass
class Cluster:
    idxs: List[int]
    score: float
    sources: List[str]


def cluster_articles(
    corpus: Sequence[str],
    articles: Sequence[Dict[str, Any]],
    *,
    threshold: float,
) -> List[Cluster]:
    if not corpus:
        return []

    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_df=0.95, sublinear_tf=True)
    X = vec.fit_transform(corpus)
    sim = cosine_similarity(X)

    n = sim.shape[0]
    unassigned = set(range(n))
    clusters: List[List[int]] = []

    # Greedy clustering: pick newest first (articles already sorted by published_at desc)
    while unassigned:
        seed = min(unassigned)  # because list is sorted, smaller idx = newer
        unassigned.remove(seed)
        group = [seed]

        # collect items similar to seed
        close = [j for j in list(unassigned) if sim[seed, j] >= threshold]
        for j in close:
            unassigned.remove(j)
            group.append(j)

        clusters.append(sorted(group))

    out: List[Cluster] = []
    for idxs in clusters:
        srcs = [articles[i].get("source", "") for i in idxs]
        unique_sources = sorted({s for s in srcs if s})
        size = len(idxs)
        # score: ưu tiên nhiều bài + nhiều nguồn
        score = size + 0.6 * len(unique_sources)
        out.append(Cluster(idxs=idxs, score=score, sources=unique_sources))

    out.sort(key=lambda c: c.score, reverse=True)
    return out


def executive_summary(
    articles: Sequence[Dict[str, Any]],
    keywords: Sequence[Tuple[str, float]],
    top_clusters: Sequence[Cluster],
) -> str:
    total = len(articles)
    by_source = Counter(a.get("source") for a in articles if a.get("source"))
    time_min = min((a.get("published_at") for a in articles if a.get("published_at")), default=None)
    time_max = max((a.get("published_at") for a in articles if a.get("published_at")), default=None)

    kw = [k for (k, _) in keywords[:8]]
    trends = ", ".join(kw) if kw else "chưa đủ dữ liệu để rút trích xu hướng"

    lines: List[str] = []
    lines.append(
        f"Tuần qua, hệ thống thu thập được **{total}** bài thuộc chủ đề **Công nghệ** "
        f"từ các nguồn {', '.join(f'**{k}** ({v})' for k, v in by_source.items())}."
    )
    if time_min and time_max:
        lines.append(f"Khoảng thời gian dữ liệu: từ **{time_min}** đến **{time_max}** (UTC).")
    lines.append(f"Các chủ đề nổi bật xoay quanh: **{trends}**.")

    if top_clusters:
        lines.append(
            "Những diễn biến đáng chú ý tập trung ở các nhóm sự kiện có độ phủ cao "
            "(nhiều bài/đa nguồn), được liệt kê ở phần Highlighted News."
        )

    return "\n\n".join(lines)


def llm_executive_summary_min_tokens(
    *,
    keywords: Sequence[Tuple[str, float]],
    highlights: Sequence[Tuple[str, str, List[str]]],
    max_highlights: int = 8,
) -> str:
    # Truncate để tiết kiệm token: chỉ gửi title + 1 câu mô tả ngắn
    def short(s: str, n: int) -> str:
        s = (s or "").strip()
        return s if len(s) <= n else s[: n - 1] + "…"

    kw = [k for (k, _) in keywords[:12]]
    hi = highlights[:max_highlights]

    system = (
        "Viết Executive Summary tiếng Việt, chỉ 1 đoạn (không xuống dòng), 4–6 câu đầy đủ."
        "Không xuống dòng giữa câu. Không dùng bullet/đánh số. Kết thúc mỗi đoạn bằng dấu chấm."

    )
    user = (
        "Trending keywords:\n- "
        + "\n- ".join(kw)
        + "\n\nTop highlights (title — snippet):\n"
        + "\n".join(
            f"- {short(t, 90)} — {short(s, 180)}" for (t, s, _links) in hi
        )
    )

    return chat_completions_min_tokens(system=system, user=user)


def format_highlight(
    cluster: Cluster, articles: Sequence[Dict[str, Any]]
) -> Tuple[str, str, List[str]]:
    # representative: newest article in cluster (smallest idx)
    rep_idx = min(cluster.idxs)
    rep = articles[rep_idx]
    title = html.unescape(rep.get("title") or "(khong tieu de)")
    snippet = html.unescape((rep.get("snippet") or "").strip())

    # collect up to 3 distinct links
    links: List[str] = []
    seen = set()
    for i in cluster.idxs:
        url = (articles[i].get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        links.append(url)
        if len(links) >= 3:
            break

    src_str = ", ".join(cluster.sources) if cluster.sources else "n/a"
    summary = snippet if snippet else "Bai viet khong co mo ta trong RSS."
    return title, f"Nguồn: {src_str}. {summary}", links


def write_markdown_report(
    *,
    out_path: Path,
    topic: str,
    articles: Sequence[Dict[str, Any]],
    keywords: Sequence[Tuple[str, float]],
    highlights: Sequence[Tuple[str, str, List[str]]],
    executive: str,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    lines: List[str] = []
    lines.append(f"## Weekly News Update — {topic} ({today})\n")

    lines.append("### Executive Summary\n")
    lines.append(executive)
    lines.append("")

    lines.append("### Trending Keywords\n")
    for term, score in keywords:
        lines.append(f"- **{term}**")
    lines.append("")

    lines.append("### Highlighted News\n")
    grouped: Dict[str, List[Tuple[str, str, List[str]]]] = {
        "AI": [],
        "Apple & thiết bị": [],
        "An ninh mạng": [],
        "Chuyển đổi số / Định danh": [],
        "Khác": [],
    }
    for title, summary, links in highlights:
        grouped[highlight_category(f"{title}\n{summary}")].append((title, summary, links))

    for section in ["AI", "Apple & thiết bị", "An ninh mạng", "Chuyển đổi số / Định danh", "Khác"]:
        items = grouped.get(section) or []
        if not items:
            continue
        lines.append(f"#### {section}\n")
        for title, summary, links in items:
            lines.append(f"- **{title}**")
            lines.append(f"  - {summary}")
            for u in links:
                lines.append(f"  - Link: [{u}]({u})")
            lines.append("")

    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    articles = load_articles(args.articles)
    # sort newest -> oldest by published_at (string ISO)
    articles.sort(key=lambda a: a.get("published_at") or "", reverse=True)

    corpus = build_corpus(articles)
    kw = trending_phrases_clustered(build_title_corpus(articles), top_k=args.top_keywords)

    clusters = cluster_articles(corpus, articles, threshold=args.cluster_threshold)
    highlights: List[Tuple[str, str, List[str]]] = []
    for c in clusters:
        h = format_highlight(c, articles)
        if looks_like_noise_topic(f"{h[0]}\n{h[1]}"):
            continue
        highlights.append(h)
        if len(highlights) >= args.top_events:
            break

    exec_text = executive_summary(articles, kw, [])
    if args.llm_summary:
        try:
            exec_text = llm_executive_summary_min_tokens(
                keywords=kw, highlights=highlights, max_highlights=8
            )
        except Exception as e:
            # fallback to deterministic summary if LLM call fails
            exec_text = exec_text + f"\n\n(Lưu ý: LLM summary thất bại: {e})"

    out_path = (
        Path(args.out)
        if args.out
        else Path("reports") / f"weekly_tech_digest_{datetime.now().strftime('%Y-%m-%d')}.md"
    )
    write_markdown_report(
        out_path=out_path,
        topic="Technology",
        articles=articles,
        keywords=kw,
        highlights=highlights,
        executive=exec_text,
    )
    print(f"Report generated: {out_path.as_posix()}")


if __name__ == "__main__":
    main()

