from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


@dataclass(frozen=True)
class FeedSource:
    source: str
    feed_url: str


def html_to_text(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def normalize_url(url: str) -> str:
    if not url:
        return ""

    parts = urlsplit(url.strip())
    parts = parts._replace(fragment="")  # bỏ phần #fragment

    q = [
        (k, v)
        for (k, v) in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_")
    ]
    parts = parts._replace(query=urlencode(q, doseq=True))
    return urlunsplit(parts)


def parse_datetime_from_entry(entry: Any) -> Optional[datetime]:
    s = entry.get("published") or entry.get("updated") or entry.get("created")
    if not s:
        return None

    try:
        dt = date_parser.parse(s)
    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def fetch_feed_text(feed_url: str, timeout_s: int = 25) -> str:
    r = requests.get(
        feed_url,
        timeout=timeout_s,
        headers={"User-Agent": "WeeklyTechNewsAssistant/1.0"},
    )
    r.raise_for_status()
    return r.text


def iter_feed_records(feed: FeedSource) -> Iterator[Dict[str, Any]]:
    xml = fetch_feed_text(feed.feed_url)
    parsed = feedparser.parse(xml)

    for entry in parsed.entries:
        title = (entry.get("title") or "").strip()
        url = normalize_url((entry.get("link") or "").strip())
        published_dt = parse_datetime_from_entry(entry)

        summary_html = entry.get("summary") or entry.get("description") or ""
        snippet = html_to_text(summary_html)

        yield {
            "source": feed.source,
            "feed_url": feed.feed_url,
            "title": title,
            "url": url,
            "published_at": published_dt,
            "snippet": snippet,
        }


def collect_articles(
    feeds: Sequence[FeedSource],
    *,
    days: int = 7,
    now: Optional[datetime] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    cutoff = now - timedelta(days=days)

    seen_urls: Set[str] = set()
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for feed in feeds:
        try:
            for rec in iter_feed_records(feed):
                url = rec.get("url") or ""
                if not url:
                    continue

                if url in seen_urls:
                    continue

                published_dt = rec.get("published_at")
                if not isinstance(published_dt, datetime):
                    continue

                published_utc = published_dt.astimezone(timezone.utc)
                if published_utc < cutoff or published_utc > now:
                    continue

                seen_urls.add(url)

                out = dict(rec)
                out["published_at"] = published_utc.isoformat()
                results.append(out)

        except Exception as e:
            errors.append(
                {"source": feed.source, "feed_url": feed.feed_url, "error": str(e)}
            )

    results.sort(key=lambda r: r.get("published_at") or "", reverse=True)
    return results, errors


def load_feeds_config(path: str) -> Tuple[List[FeedSource], Dict[str, Any]]:
    cfg = json.loads(open(path, "r", encoding="utf-8").read())
    feeds_raw = cfg.get("feeds") or []

    feeds: List[FeedSource] = []
    for f in feeds_raw:
        feeds.append(FeedSource(source=f["source"], feed_url=f["feed_url"]))

    return feeds, cfg

