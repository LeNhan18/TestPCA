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
        default=10,
        help="Number of highlighted events (default: 10)",
    )
    p.add_argument(
        "--cluster_threshold",
        type=float,
        default=0.62,
        help="Cosine similarity threshold for clustering (default: 0.62)",
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


def trending_keywords_tfidf(
    corpus: Sequence[str], top_k: int
) -> List[Tuple[str, float]]:
    """
    Trả về cụm từ có nghĩa (ưu tiên 2-3 từ).

    Lưu ý: Đây là baseline cho bài test, không phụ thuộc NLP nặng.
    """
    vec = TfidfVectorizer(
        # Ưu tiên cụm từ dài hơn để ra "keyword" có nghĩa (3-6 từ)
        ngram_range=(2, 6),
        min_df=2,
        max_df=0.85,
        sublinear_tf=True,
    )
    X = vec.fit_transform(corpus)
    scores = X.sum(axis=0).A1
    terms = vec.get_feature_names_out()
    ranked = sorted(
        zip(terms, scores),
        key=lambda x: (x[1], len(x[0].split())),  # prefer higher score, then longer phrase
        reverse=True,
    )

    # Nhóm tín hiệu "công nghệ" để hạn chế keyword noise
    TECH_HINTS = {
        # AI
        "ai",
        "gemini",
        "chatbot",
        "claude",
        "llm",
        # web/browser
        "chrome",
        # mobile/os
        "android",
        "ios",
        "iphone",
        "ipad",
        "mac",
        "samsung",
        "galaxy",
        # companies
        "apple",
        "google",
        "meta",
        "microsoft",
        "defender",
        # telecom / id
        "ipv6",
        "5g",
        "sim",
        "vneid",
        "định danh",
        "thuê bao",
        "an ninh mạng",
        "tấn công mạng",
        "mã độc",
        "bảo mật",
        "lỗ hổng",
        "chuyển đổi số",
        "định danh số",
        "dữ liệu số",
        # robotics
        "robot",
        "drone",
        # computing
        "máy tính",
        "lượng tử",
        "quantum",
        # health-tech
        "mrna",
        "vaccine",
        "ung thư",
        # general tech
        "internet",
        "thiết bị",
        "phần mềm",
    }

    NOISE_TOKENS = {
        # các cụm dễ kéo sai domain/không phải "keyword chủ đề"
        "marathon",
        "quỹ đạo",
        "tên lửa",
        "vệ tinh",
        "audition",
        "esports",
    }

    SHORT_OK = {"ai", "ios", "5g", "sim", "ipv6", "mrna"}

    def looks_truncated(term: str) -> bool:
        parts = term.split()
        for p in parts:
            pl = p.lower()
            if pl in SHORT_OK:
                continue
            # token quá ngắn thường là cụt (vd "di", "lo", "ve"...)
            if len(pl) < 3 and not any(ch.isdigit() for ch in pl):
                return True
        return False

    def is_meaningful_phrase(term: str) -> bool:
        parts = term.split()
        # yêu cầu cụm >= 3 từ để giống "keyword có nghĩa"
        if len(parts) < 3:
            return False

        # loại các cụm bị cắt cụt/không tự nhiên
        bad_prefixes = {"thực", "việc"}
        if parts[0].lower() in bad_prefixes:
            return False

        t = term.lower()
        if looks_truncated(term):
            return False
        if any(tok in t for tok in NOISE_TOKENS):
            return False
        # Ưu tiên cụm có "tín hiệu" công nghệ/policy
        for hint in TECH_HINTS:
            if hint in t:
                return True

        # Hoặc chứa chữ-số kiểu IPv6/5G/iOS 27...
        if any(ch.isdigit() for ch in t):
            return True

        return False

    def normalize_phrase(term: str) -> str:
        # normalize đơn giản để dedupe (xóa khoảng trắng thừa)
        return " ".join(term.lower().split())

    def token_jaccard(a: str, b: str) -> float:
        sa = set(a.split())
        sb = set(b.split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    def is_redundant(term: str, chosen: List[str]) -> bool:
        t = normalize_phrase(term)
        for c in chosen:
            c_norm = normalize_phrase(c)
            # substring/prefix redundancy
            if t in c_norm or c_norm in t:
                return True
            # near-duplicate by token overlap
            if token_jaccard(t, c_norm) >= 0.8:
                return True
        return False

    # chỉ giữ cụm từ có ý nghĩa, và loại cụm lặp/na ná nhau
    filtered_terms: List[str] = []
    filtered: List[Tuple[str, float]] = []
    for term, score in ranked:
        if not is_meaningful_phrase(term):
            continue
        if is_redundant(term, filtered_terms):
            continue
        filtered_terms.append(term)
        filtered.append((term, float(score)))
        if len(filtered) >= top_k:
            break
    return filtered


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
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    lines: List[str] = []
    lines.append(f"## Weekly News Update — {topic} ({today})\n")

    lines.append("### Executive Summary\n")
    # Executive summary dựa trên keywords + thống kê dataset
    lines.append(executive_summary(articles, keywords, []))
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
        for i, (title, summary, links) in enumerate(items, start=1):
            lines.append(f"{i}. **{title}**")
            lines.append(f"   - {summary}")
            for u in links:
                lines.append(f"   - Link: {u}")
            lines.append("")

    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    articles = load_articles(args.articles)
    # sort newest -> oldest by published_at (string ISO)
    articles.sort(key=lambda a: a.get("published_at") or "", reverse=True)

    corpus = build_corpus(articles)
    kw = trending_keywords_tfidf(corpus, top_k=args.top_keywords)

    clusters = cluster_articles(corpus, articles, threshold=args.cluster_threshold)
    top_clusters = clusters[: args.top_events]
    highlights = [format_highlight(c, articles) for c in top_clusters]
    highlights = [
        h for h in highlights if not looks_like_noise_topic(f"{h[0]}\n{h[1]}")
    ]

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
    )
    print(f"Report generated: {out_path.as_posix()}")


if __name__ == "__main__":
    main()

