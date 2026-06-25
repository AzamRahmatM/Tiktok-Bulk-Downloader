"""
Tests for topic clustering and TF-IDF labeling.

Uses synthetic embeddings so no ML models are needed.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai import cluster  # noqa: E402


def _make_cluster_data(n_per_cluster=10, n_clusters=3, dim=384):
    """Generate clearly separable embeddings for testing."""
    rng = np.random.RandomState(42)
    ids, vecs, texts = [], [], []
    words = [
        ["pricing", "enterprise", "subscription", "tier"],
        ["demo", "product", "walkthrough", "feature"],
        ["testimonial", "customer", "success", "story"],
    ]
    for c in range(n_clusters):
        center = rng.randn(dim).astype(np.float32)
        center /= np.linalg.norm(center)
        for i in range(n_per_cluster):
            vid = f"vid_{c}_{i}"
            vec = center + rng.randn(dim).astype(np.float32) * 0.05
            vec /= np.linalg.norm(vec)
            ids.append(vid)
            vecs.append(vec)
            texts.append(" ".join(rng.choice(words[c], size=8)))
    return ids, np.vstack(vecs), texts


def test_kmeans_produces_clusters():
    ids, vecs, texts = _make_cluster_data()
    results = cluster.cluster_videos(
        ids, vecs, texts, method="kmeans", k=3
    )
    assert len(results) >= 2  # at least 2 clusters
    total_vids = sum(len(c["video_ids"]) for c in results)
    assert total_vids == len(ids)


def test_kmeans_labels_are_nonempty():
    ids, vecs, texts = _make_cluster_data()
    results = cluster.cluster_videos(
        ids, vecs, texts, method="kmeans", k=3
    )
    for c in results:
        assert c["label"]  # not empty
        assert isinstance(c["cluster_id"], int)


def test_hdbscan_produces_clusters():
    # With 30 points in 3 tight clusters, HDBSCAN should find them.
    ids, vecs, texts = _make_cluster_data(n_per_cluster=15)
    results = cluster.cluster_videos(
        ids, vecs, texts, method="hdbscan", min_cluster_size=3
    )
    assert len(results) >= 2


def test_tfidf_label():
    label = cluster._tfidf_label(
        ["pricing enterprise subscription tier cost"],
        n_terms=3,
    )
    assert label  # not empty
    # Should pick terms related to pricing
    terms = [t.strip().lower() for t in label.split(",")]
    assert len(terms) == 3


def test_too_few_videos_returns_empty():
    results = cluster.cluster_videos(
        ["vid1"], np.random.randn(1, 384).astype(np.float32),
        ["hello world"], method="kmeans", k=3,
    )
    assert results == []
