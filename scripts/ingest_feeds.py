import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.ingest.rss_ingest import collect_articles, load_feeds_config


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest RSS feeds and write JSONL.")
    p.add_argument(
        "--config",
        default="config/feeds.json",
        help="Path to feeds config JSON (default: config/feeds.json)",
    )
    p.add_argument(
        "--days",
        type=int,
        default=None,
        help="Override days window (default: value in config or 7)",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Override output path (default: value in config or data/articles.jsonl)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    feeds, cfg = load_feeds_config(args.config)
    days = int(args.days if args.days is not None else cfg.get("days", 7))
    out_path = str(
        args.out
        if args.out is not None
        else cfg.get("out_path", "data/articles.jsonl")
    )

    results, errors = collect_articles(feeds, days=days)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results)
        + ("\n" if results else ""),
        encoding="utf-8",
    )

    by_source: dict[str, int] = {}
    for r in results:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1

    published_list = [r["published_at"] for r in results if r.get("published_at")]
    min_dt = min(published_list) if published_list else None
    max_dt = max(published_list) if published_list else None

    print(f"Saved: {len(results)} articles -> {out.as_posix()}")
    print("By source:", by_source)
    print("Published range:", {"min": min_dt, "max": max_dt})

    if errors:
        print(f"Feed errors: {len(errors)}")
        for er in errors:
            print(er)


if __name__ == "__main__":
    main()
