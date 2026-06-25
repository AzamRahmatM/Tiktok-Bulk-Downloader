#!/usr/bin/env python3
"""
Auto-tagging and topic clustering over video embeddings.

Groups videos into coherent topics using HDBSCAN (auto-picks cluster
count) with optional KMeans fallback. Each cluster gets a human-readable
label extracted via TF-IDF over its transcripts.

Requires: hdbscan, scikit-learn, numpy.
"""
import logging
from collections import defaultdict

import numpy as np


def _tfidf_label(transcripts, n_terms=3):
    """Pick the top-N distinguishing terms for a cluster via TF-IDF."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    if not transcripts:
        return "unknown"
    joined = [" ".join(transcripts)]
    try:
        vec = TfidfVectorizer(
            max_features=200, stop_words="english", min_df=1
        )
        mat = vec.fit_transform(joined)
        names = vec.get_feature_names_out()
        scores = mat.toarray()[0]
        top_idx = np.argsort(-scores)[:n_terms]
        return ", ".join(names[i] for i in top_idx)
    except ValueError:
        return "unknown"


def cluster_hdbscan(embeddings, min_cluster_size=5):
    """Cluster with HDBSCAN. Returns labels array (-1 = noise).

    We use metric='euclidean' on L2-normalized vectors, which gives the
    same ranking as cosine distance and is supported by all versions.
    """
    import hdbscan

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric="euclidean",
    )
    labels = clusterer.fit_predict(embeddings)
    return labels


def cluster_kmeans(embeddings, k=8):
    """Cluster with KMeans. Returns labels array."""
    from sklearn.cluster import KMeans

    km = KMeans(n_clusters=min(k, len(embeddings)), n_init="auto",
                random_state=42)
    return km.fit_predict(embeddings)


def cluster_videos(video_ids, embeddings, transcripts=None,
                   method="hdbscan", k=8, min_cluster_size=5):
    """Run clustering and return structured results.

    Parameters
    ----------
    video_ids : list[str]
    embeddings : np.ndarray (N, D)
    transcripts : list[str] | None
        Full transcript per video, used for TF-IDF label generation.
    method : str
        "hdbscan" (auto-picks k) or "kmeans" (uses *k*).
    k : int
        Number of clusters for KMeans.
    min_cluster_size : int
        Minimum cluster size for HDBSCAN.

    Returns
    -------
    list[dict]
        Each dict: {"cluster_id": int, "label": str,
                     "video_ids": list[str]}
        cluster_id=-1 is the noise/outlier bucket.
    """
    if len(video_ids) < 2:
        logging.warning("Need at least 2 videos to cluster.")
        return []

    if method == "kmeans":
        labels = cluster_kmeans(embeddings, k=k)
    else:
        labels = cluster_hdbscan(embeddings,
                                 min_cluster_size=min_cluster_size)
        n_clusters = len(set(labels) - {-1})
        if n_clusters < 2:
            logging.info(
                f"HDBSCAN found {n_clusters} cluster(s); "
                f"falling back to KMeans(k={k})"
            )
            labels = cluster_kmeans(embeddings, k=k)

    # Group video_ids by cluster label
    groups = defaultdict(list)
    for vid, lbl in zip(video_ids, labels):
        groups[int(lbl)].append(vid)

    transcripts = transcripts or [""] * len(video_ids)
    vid_to_transcript = dict(zip(video_ids, transcripts))

    results = []
    for cluster_id in sorted(groups):
        vids = groups[cluster_id]
        cluster_texts = [vid_to_transcript.get(v, "") for v in vids]
        label = _tfidf_label(cluster_texts)
        results.append({
            "cluster_id": cluster_id,
            "label": label,
            "video_ids": vids,
        })

    return results
