#!/usr/bin/env python3
"""
Local SQLite-backed vector store for enriched videos.

Tables:
  * videos   - one row per enriched .mp4 (full transcript, metadata)
  * segments - one row per transcript segment with its own embedding,
               so search can return the exact timestamp inside a video.
  * frames   - one row per extracted keyframe with a CLIP embedding,
               enabling visual (image-based) search.
  * clusters - cluster assignments from auto-tagging.

Embeddings are stored as raw float32 blobs. Search loads all segment
vectors into one matrix and does a single normalized dot product, which
is plenty fast for tens of thousands of segments.
"""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone

import numpy as np

from . import embedder

DEFAULT_DB = "video_index.db"

CLIP_DIM = 512  # CLIP ViT-B/32 output dimension


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS videos (
            video_id    TEXT PRIMARY KEY,
            path        TEXT NOT NULL,
            transcript  TEXT,
            language    TEXT,
            duration    REAL,
            enriched_at TEXT
        );
        CREATE TABLE IF NOT EXISTS segments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id   TEXT NOT NULL,
            start      REAL,
            end        REAL,
            text       TEXT,
            embedding  BLOB,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        );
        CREATE INDEX IF NOT EXISTS idx_segments_video
            ON segments(video_id);
        CREATE TABLE IF NOT EXISTS frames (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id   TEXT NOT NULL,
            timestamp  REAL,
            embedding  BLOB,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        );
        CREATE INDEX IF NOT EXISTS idx_frames_video
            ON frames(video_id);
        CREATE TABLE IF NOT EXISTS clusters (
            cluster_id INTEGER NOT NULL,
            label      TEXT,
            video_id   TEXT NOT NULL,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        );
        CREATE INDEX IF NOT EXISTS idx_clusters_cluster
            ON clusters(cluster_id);
        """
    )
    conn.commit()
    return conn


# ── Video + segment operations ──────────────────────────────────────


def is_enriched(db_path: str, video_id: str) -> bool:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT 1 FROM videos WHERE video_id = ?", (video_id,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def add_video(db_path: str, video_id: str, path: str, result: dict) -> None:
    """Persist one enriched video and its segment embeddings.

    `result` is the dict returned by transcribe.transcribe_file():
        {language, duration, transcript, segments: [{start, end, text}]}
    """
    segments = result.get("segments", [])
    texts = [s["text"] for s in segments if s.get("text", "").strip()]
    vecs = embedder.embed(texts) if texts else np.empty((0, embedder.EMBED_DIM))

    conn = _connect(db_path)
    try:
        # Re-enriching: clear any previous rows for this video first.
        conn.execute("DELETE FROM segments WHERE video_id = ?", (video_id,))
        conn.execute("DELETE FROM videos WHERE video_id = ?", (video_id,))

        conn.execute(
            "INSERT INTO videos "
            "(video_id, path, transcript, language, duration, enriched_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                video_id,
                str(path),
                result.get("transcript", ""),
                result.get("language"),
                result.get("duration"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        vi = 0
        rows = []
        for s in segments:
            text = s.get("text", "").strip()
            if not text:
                continue
            rows.append(
                (
                    video_id,
                    s.get("start"),
                    s.get("end"),
                    text,
                    vecs[vi].tobytes(),
                )
            )
            vi += 1
        conn.executemany(
            "INSERT INTO segments "
            "(video_id, start, end, text, embedding) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        logging.info(f"Indexed {video_id}: {len(rows)} segments")
    finally:
        conn.close()


# ── Frame (CLIP) operations ─────────────────────────────────────────


def has_frames(db_path: str, video_id: str) -> bool:
    """Check if a video already has frame embeddings."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT 1 FROM frames WHERE video_id = ? LIMIT 1", (video_id,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def add_frames(db_path: str, video_id: str, frame_data: list) -> None:
    """Store CLIP frame embeddings for a video.

    frame_data: list of {"timestamp": float, "embedding": np.ndarray}
    """
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM frames WHERE video_id = ?", (video_id,))
        rows = [
            (video_id, f["timestamp"], f["embedding"].tobytes())
            for f in frame_data
        ]
        conn.executemany(
            "INSERT INTO frames (video_id, timestamp, embedding) "
            "VALUES (?, ?, ?)",
            rows,
        )
        conn.commit()
        logging.info(
            f"Indexed {video_id}: {len(rows)} frame embeddings"
        )
    finally:
        conn.close()


def _load_frame_matrix(conn):
    """Load all frame embeddings into (meta, matrix)."""
    cur = conn.execute(
        "SELECT f.video_id, f.timestamp, f.embedding, v.path "
        "FROM frames f JOIN videos v ON v.video_id = f.video_id"
    )
    meta, blobs = [], []
    for video_id, ts, emb, path in cur:
        meta.append({
            "video_id": video_id,
            "start": ts,
            "end": None,
            "text": f"[visual frame @ {ts:.1f}s]",
            "path": path,
        })
        blobs.append(np.frombuffer(emb, dtype=np.float32))
    if not blobs:
        return [], np.empty((0, CLIP_DIM), dtype=np.float32)
    return meta, np.vstack(blobs)


def search_visual(db_path: str, query: str, top_k: int = 5) -> list:
    """Search frame embeddings using CLIP text encoder."""
    if not Path(db_path).exists():
        return []

    # Import lazily to avoid loading CLIP for text-only searches.
    from . import vision

    conn = _connect(db_path)
    try:
        meta, matrix = _load_frame_matrix(conn)
    finally:
        conn.close()

    if matrix.shape[0] == 0:
        return []

    qvec = vision.embed_text_clip(query)[0]
    scores = matrix @ qvec
    top_idx = np.argsort(-scores)[:top_k]

    results = []
    for i in top_idx:
        hit = dict(meta[i])
        hit["score"] = float(scores[i])
        results.append(hit)
    return results


# ── Text segment search ─────────────────────────────────────────────


def _load_matrix(conn: sqlite3.Connection):
    """Return (meta, matrix) for every segment in the store."""
    cur = conn.execute(
        "SELECT s.video_id, s.start, s.end, s.text, s.embedding, v.path "
        "FROM segments s JOIN videos v ON v.video_id = s.video_id"
    )
    meta, blobs = [], []
    for video_id, start, end, text, emb, path in cur:
        meta.append(
            {
                "video_id": video_id,
                "start": start,
                "end": end,
                "text": text,
                "path": path,
            }
        )
        blobs.append(np.frombuffer(emb, dtype=np.float32))
    if not blobs:
        return [], np.empty((0, embedder.EMBED_DIM), dtype=np.float32)
    return meta, np.vstack(blobs)


def search(db_path: str, query: str, top_k: int = 5) -> list:
    """Return the top_k best-matching segments for a natural-language query."""
    if not Path(db_path).exists():
        return []

    conn = _connect(db_path)
    try:
        meta, matrix = _load_matrix(conn)
    finally:
        conn.close()

    if matrix.shape[0] == 0:
        return []

    qvec = embedder.embed(query)[0]            # already normalized
    scores = matrix @ qvec                      # cosine similarity
    top_idx = np.argsort(-scores)[:top_k]

    results = []
    for i in top_idx:
        hit = dict(meta[i])
        hit["score"] = float(scores[i])
        results.append(hit)
    return results


# ── Cluster operations ──────────────────────────────────────────────


def save_clusters(db_path: str, clusters: list) -> None:
    """Persist cluster assignments.

    clusters: list of {"cluster_id": int, "label": str,
                        "video_ids": list[str]}
    """
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM clusters")
        rows = []
        for c in clusters:
            for vid in c["video_ids"]:
                rows.append((c["cluster_id"], c["label"], vid))
        conn.executemany(
            "INSERT INTO clusters (cluster_id, label, video_id) "
            "VALUES (?, ?, ?)",
            rows,
        )
        conn.commit()
        logging.info(f"Saved {len(clusters)} clusters ({len(rows)} videos)")
    finally:
        conn.close()


def get_clusters(db_path: str) -> list:
    """Load clusters. Returns list of {cluster_id, label, video_ids}."""
    if not Path(db_path).exists():
        return []
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "SELECT cluster_id, label, video_id FROM clusters "
            "ORDER BY cluster_id"
        )
        from collections import defaultdict
        groups = defaultdict(lambda: {"label": "", "video_ids": []})
        for cid, label, vid in cur:
            groups[cid]["label"] = label
            groups[cid]["video_ids"].append(vid)
        return [
            {"cluster_id": cid, "label": g["label"],
             "video_ids": g["video_ids"]}
            for cid, g in sorted(groups.items())
        ]
    finally:
        conn.close()


def get_video_embeddings(db_path: str):
    """Load mean-of-segments embedding per video for clustering.

    Returns (video_ids: list[str], embeddings: np.ndarray,
             transcripts: list[str]).
    """
    if not Path(db_path).exists():
        return [], np.empty((0, embedder.EMBED_DIM)), []

    conn = _connect(db_path)
    try:
        videos = conn.execute(
            "SELECT video_id, transcript FROM videos ORDER BY video_id"
        ).fetchall()

        ids, vecs, transcripts = [], [], []
        for video_id, transcript in videos:
            cur = conn.execute(
                "SELECT embedding FROM segments WHERE video_id = ?",
                (video_id,),
            )
            blobs = [np.frombuffer(row[0], dtype=np.float32) for row in cur]
            if not blobs:
                continue
            mean_vec = np.mean(np.vstack(blobs), axis=0)
            norm = np.linalg.norm(mean_vec)
            if norm:
                mean_vec /= norm
            ids.append(video_id)
            vecs.append(mean_vec)
            transcripts.append(transcript or "")

        if not vecs:
            return [], np.empty((0, embedder.EMBED_DIM)), []
        return ids, np.vstack(vecs), transcripts
    finally:
        conn.close()


# ── Stats ────────────────────────────────────────────────────────────


def stats(db_path: str) -> dict:
    if not Path(db_path).exists():
        return {"videos": 0, "segments": 0, "frames": 0, "clusters": 0}
    conn = _connect(db_path)
    try:
        v = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        s = conn.execute("SELECT COUNT(*) FROM segments").fetchone()[0]
        f = conn.execute("SELECT COUNT(*) FROM frames").fetchone()[0]
        c = conn.execute(
            "SELECT COUNT(DISTINCT cluster_id) FROM clusters"
        ).fetchone()[0]
        return {"videos": v, "segments": s, "frames": f, "clusters": c}
    finally:
        conn.close()
