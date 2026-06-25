#!/usr/bin/env python3
"""
Semantic search CLI over the enriched video index.

Search your downloaded library by meaning, not filenames or exact words:

    python src/search_videos.py "someone demoing the product outdoors"
    python src/search_videos.py "pricing discussion" --top-k 10

Each result points at the exact video file and the timestamp inside it
where the match occurs.
"""
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai import store  # noqa: E402


def _fmt_ts(seconds) -> str:
    if seconds is None:
        return "--:--"
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def main(args):
    if not Path(args.db).exists():
        print(
            f"No index found at '{args.db}'. "
            f"Run enrich_videos.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    results = store.search(args.db, args.query, top_k=args.top_k)
    if not results:
        print("No matches found.")
        return

    print(f'\nTop {len(results)} matches for: "{args.query}"\n')
    for rank, hit in enumerate(results, 1):
        ts = _fmt_ts(hit["start"])
        print(f"{rank}. [{hit['score']:.3f}] {hit['video_id']}  @ {ts}")
        print(f"   {hit['path']}")
        print(f"   “{hit['text']}”\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Semantic video search")
    parser.add_argument("query", help="Natural-language search query")
    parser.add_argument(
        "--db",
        default=os.environ.get("VIDEO_INDEX_DB", "video_index.db"),
        help="Path to the SQLite vector index",
    )
    parser.add_argument(
        "--top-k", type=int, default=5, help="Number of results to return"
    )

    args = parser.parse_args()
    main(args)
