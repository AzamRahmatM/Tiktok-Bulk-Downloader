"""
Tests for the AI vector store and search logic.

These run without the heavy ML dependencies: the embedder is replaced
with a deterministic hashing embedding so we exercise the SQLite store,
segment indexing, frame indexing, cluster persistence, and cosine
search end-to-end.
"""
import sys
import hashlib
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai import store  # noqa: E402

DIM = 384


def _fake_embed(texts):
    """Deterministic bag-of-words hashing embedding, L2-normalized."""
    if isinstance(texts, str):
        texts = [texts]
    out = np.zeros((len(texts), DIM), dtype=np.float32)
    for i, t in enumerate(texts):
        for word in t.lower().split():
            h = int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM
            out[i, h] += 1.0
        norm = np.linalg.norm(out[i])
        if norm:
            out[i] /= norm
    return out


@pytest.fixture(autouse=True)
def patch_embedder(monkeypatch):
    monkeypatch.setattr(store.embedder, "embed", _fake_embed)


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "test_index.db")


def _result(*texts):
    return {
        "language": "en",
        "duration": 10.0,
        "transcript": " ".join(texts),
        "segments": [
            {"start": float(i), "end": float(i + 1), "text": t}
            for i, t in enumerate(texts)
        ],
    }


# ── Segment tests (original) ────────────────────────────────────────


def test_add_and_stats(db):
    store.add_video(db, "vid1", "downloads/vid1.mp4",
                    _result("hello world", "product demo outdoors"))
    s = store.stats(db)
    assert s["videos"] == 1
    assert s["segments"] == 2
    assert store.is_enriched(db, "vid1")
    assert not store.is_enriched(db, "missing")


def test_search_ranks_relevant_segment_first(db):
    store.add_video(db, "vid1", "downloads/vid1.mp4",
                    _result("cooking pasta in the kitchen"))
    store.add_video(db, "vid2", "downloads/vid2.mp4",
                    _result("annual pricing discussion with the client"))

    hits = store.search(db, "pricing discussion", top_k=1)
    assert len(hits) == 1
    assert hits[0]["video_id"] == "vid2"
    assert hits[0]["start"] == 0.0
    assert hits[0]["score"] > 0


def test_reenrich_replaces_segments(db):
    store.add_video(db, "vid1", "downloads/vid1.mp4", _result("a", "b", "c"))
    store.add_video(db, "vid1", "downloads/vid1.mp4", _result("x"))
    s = store.stats(db)
    assert s["videos"] == 1
    assert s["segments"] == 1


def test_search_empty_index_returns_empty(db):
    assert store.search(db, "anything") == []


# ── Frame tests ──────────────────────────────────────────────────────


def test_add_frames_and_stats(db):
    store.add_video(db, "vid1", "downloads/vid1.mp4",
                    _result("hello world"))
    frames = [
        {"timestamp": 0.0,
         "embedding": np.random.randn(512).astype(np.float32)},
        {"timestamp": 3.0,
         "embedding": np.random.randn(512).astype(np.float32)},
    ]
    store.add_frames(db, "vid1", frames)
    s = store.stats(db)
    assert s["frames"] == 2
    assert store.has_frames(db, "vid1")
    assert not store.has_frames(db, "vid2")


def test_add_frames_replaces_existing(db):
    store.add_video(db, "vid1", "downloads/vid1.mp4",
                    _result("hello"))
    frames1 = [
        {"timestamp": 0.0,
         "embedding": np.random.randn(512).astype(np.float32)},
    ]
    store.add_frames(db, "vid1", frames1)
    assert store.stats(db)["frames"] == 1

    frames2 = [
        {"timestamp": 0.0,
         "embedding": np.random.randn(512).astype(np.float32)},
        {"timestamp": 3.0,
         "embedding": np.random.randn(512).astype(np.float32)},
        {"timestamp": 6.0,
         "embedding": np.random.randn(512).astype(np.float32)},
    ]
    store.add_frames(db, "vid1", frames2)
    assert store.stats(db)["frames"] == 3


# ── Cluster persistence tests ───────────────────────────────────────


def test_save_and_get_clusters(db):
    store.add_video(db, "vid1", "downloads/vid1.mp4",
                    _result("pricing enterprise"))
    store.add_video(db, "vid2", "downloads/vid2.mp4",
                    _result("product demo"))
    store.add_video(db, "vid3", "downloads/vid3.mp4",
                    _result("customer story"))

    clusters = [
        {"cluster_id": 0, "label": "pricing, enterprise",
         "video_ids": ["vid1"]},
        {"cluster_id": 1, "label": "product, demo",
         "video_ids": ["vid2", "vid3"]},
    ]
    store.save_clusters(db, clusters)

    loaded = store.get_clusters(db)
    assert len(loaded) == 2
    assert loaded[0]["cluster_id"] == 0
    assert loaded[0]["video_ids"] == ["vid1"]
    assert loaded[1]["video_ids"] == ["vid2", "vid3"]
    assert store.stats(db)["clusters"] == 2


def test_save_clusters_replaces_existing(db):
    store.add_video(db, "vid1", "downloads/vid1.mp4",
                    _result("hello"))
    c1 = [{"cluster_id": 0, "label": "old", "video_ids": ["vid1"]}]
    store.save_clusters(db, c1)
    assert store.stats(db)["clusters"] == 1

    c2 = [
        {"cluster_id": 0, "label": "new_a", "video_ids": ["vid1"]},
        {"cluster_id": 1, "label": "new_b", "video_ids": ["vid1"]},
    ]
    store.save_clusters(db, c2)
    assert store.stats(db)["clusters"] == 2


# ── Video-level embedding aggregation ────────────────────────────────


def test_get_video_embeddings(db):
    store.add_video(db, "vid1", "downloads/vid1.mp4",
                    _result("hello world", "foo bar"))
    store.add_video(db, "vid2", "downloads/vid2.mp4",
                    _result("pricing discussion"))

    ids, vecs, transcripts = store.get_video_embeddings(db)
    assert len(ids) == 2
    assert vecs.shape == (2, DIM)
    assert len(transcripts) == 2
    # Vectors should be normalized
    for i in range(len(ids)):
        norm = np.linalg.norm(vecs[i])
        assert abs(norm - 1.0) < 1e-5
