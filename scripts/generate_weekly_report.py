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
        default=20,
        help="Number of highlighted events (default: 20)",
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


def trending_topics(
    corpus: Sequence[str],
    *,
    top_k: int,
    min_doc_frac: float = 0.05,
) -> List[Tuple[str, float]]:
    """
    Trích xuất "Trending Keywords" theo hướng topic-level:
    - Gộp các biến thể/synonym về 1 chủ đề canonical
    - Ưu tiên chủ đề xuất hiện ở NHIỀU bài (document frequency), tránh cụm ngẫu nhiên
    """

    topic_rules: List[Tuple[str, List[str]]] = [
        ("AI / Gemini", ["ai", "gemini", "chatbot", "llm", "claude", "chrome"]),
        ("Apple / iPhone / iOS", ["apple", "iphone", "ios", "ipad", "mac"]),
        ("Samsung / Galaxy", ["samsung", "galaxy", "one ui"]),
        ("An ninh mạng", ["an ninh mạng", "bảo mật", "mã độc", "hacker", "lỗ hổng", "defender"]),
        ("Xác thực SIM / VNeID", ["xác thực", "sim", "thuê bao", "vneid", "định danh"]),
        ("Chuyển đổi số", ["chuyển đổi số", "định danh số", "dữ liệu số"]),
        ("Robot / Humanoid", ["robot", "hình người", "humanoid", "drone"]),
        ("Thiết bị & phần mềm", ["thiết bị", "phần mềm", "máy tính", "máy tính bảng"]),
    ]

    n_docs = max(len(corpus), 1)

    # document frequency cho mỗi topic (đếm số bài có chứa bất kỳ hint)
    df: Dict[str, int] = {name: 0 for name, _ in topic_rules}
    for doc in corpus:
        d = doc.lower()
        for name, hints in topic_rules:
            if any(h in d for h in hints):
                df[name] += 1

    # TF-IDF để tạo score phụ trợ (tránh chỉ đếm thô)
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9, sublinear_tf=True)
    X = vec.fit_transform(corpus)
    scores = X.sum(axis=0).A1
    terms = vec.get_feature_names_out()
    term_score = dict(zip(terms, scores))

    topic_score: Dict[str, float] = {name: 0.0 for name, _ in topic_rules}
    for name, hints in topic_rules:
        for h in hints:
            # chỉ cộng nếu hint tồn tại đúng term (đơn giản hóa)
            if h in term_score:
                topic_score[name] += float(term_score[h])

    # rank theo độ phủ (df) + score
    ranked: List[Tuple[str, float]] = []
    for name, _ in topic_rules:
        frac = df[name] / n_docs
        if frac < min_doc_frac:
            continue
        ranked.append((name, df[name] + topic_score[name]))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked[:top_k]


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
    kw = trending_topics(corpus, top_k=args.top_keywords)

    clusters = cluster_articles(corpus, articles, threshold=args.cluster_threshold)
    highlights: List[Tuple[str, str, List[str]]] = []
    for c in clusters:
        h = format_highlight(c, articles)
        if looks_like_noise_topic(f"{h[0]}\n{h[1]}"):
            continue
        highlights.append(h)
        if len(highlights) >= args.top_events:
            break

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

