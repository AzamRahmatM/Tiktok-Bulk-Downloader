#!/usr/bin/env python3
"""
Auto-tag and cluster videos by topic.

Groups the enriched video library into coherent topic clusters using
HDBSCAN (auto-picks the number of clusters) or KMeans, then labels
each cluster with its most distinctive terms via TF-IDF.

    python src/cluster_videos.py
    python src/cluster_videos.py --method kmeans --k 10

Cluster assignments are stored in the SQLite index so the Streamlit
dashboard can display them.
"""
import os
import sys
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai import store, cluster  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("cluster.log"),
        logging.StreamHandler(),
    ],
)


def main(args):
    if not Path(args.db).exists():
        print(
            f"No index found at '{args.db}'. "
            f"Run enrich_videos.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    logging.info("Loading video embeddings ...")
    video_ids, embeddings, transcripts = store.get_video_embeddings(args.db)

    if len(video_ids) < 2:
        logging.error(
            f"Need at least 2 enriched videos to cluster "
            f"(found {len(video_ids)}). Enrich more videos first."
        )
        sys.exit(1)

    logging.info(
        f"Clustering {len(video_ids)} videos "
        f"(method={args.method}, k={args.k}) ..."
    )
    results = cluster.cluster_videos(
        video_ids, embeddings, transcripts,
        method=args.method, k=args.k,
        min_cluster_size=args.min_cluster_size,
    )

    if not results:
        logging.warning("Clustering produced no results.")
        return

    # Save to the index
    store.save_clusters(args.db, results)

    # Print summary
    print(f"\n{'='*60}")
    print(f"  Topic Clusters ({len(results)} groups)")
    print(f"{'='*60}\n")

    noise_count = 0
    for c in results:
        cid = c["cluster_id"]
        label = c["label"]
        count = len(c["video_ids"])
        if cid == -1:
            noise_count = count
            continue
        print(f"  Cluster {cid}: \"{label}\" ({count} videos)")

    if noise_count:
        print(f"\n  Noise: {noise_count} unclustered videos")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Auto-tag videos into topic clusters"
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("VIDEO_INDEX_DB", "video_index.db"),
        help="Path to the SQLite vector index",
    )
    parser.add_argument(
        "--method",
        choices=["hdbscan", "kmeans"],
        default="hdbscan",
        help="Clustering algorithm (default: hdbscan)",
    )
    parser.add_argument(
        "--k", type=int, default=8,
        help="Number of clusters for KMeans (ignored by HDBSCAN)",
    )
    parser.add_argument(
        "--min-cluster-size", type=int, default=5,
        help="Min cluster size for HDBSCAN (default: 5)",
    )

    args = parser.parse_args()
    try:
        main(args)
    except KeyboardInterrupt:
        logging.warning("Interrupted by user. Exiting.")
        sys.exit(130)
