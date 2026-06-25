#!/usr/bin/env python3
"""
Visual (CLIP) embedding for video keyframes.

Extracts frames at a fixed interval from each .mp4, encodes them with
CLIP ViT-B/32, and returns per-frame embeddings that let you search
videos by *what is on screen* — not just spoken words.

Requires: transformers, Pillow, opencv-python-headless.
"""
import logging
from functools import lru_cache

import numpy as np

CLIP_MODEL = "openai/clip-vit-base-patch32"
CLIP_DIM = 512
DEFAULT_FRAME_INTERVAL = 3.0  # seconds between extracted frames


@lru_cache(maxsize=1)
def _load_clip():
    from transformers import CLIPModel, CLIPProcessor

    logging.info(f"Loading CLIP model: {CLIP_MODEL}")
    model = CLIPModel.from_pretrained(CLIP_MODEL)
    processor = CLIPProcessor.from_pretrained(CLIP_MODEL)
    return model, processor


def extract_keyframes(video_path, interval: float = DEFAULT_FRAME_INTERVAL):
    """Yield (timestamp_sec, PIL.Image) tuples from a video file.

    One frame is grabbed every *interval* seconds. We use OpenCV for
    decoding because it is the lightest option that works without an
    external ffmpeg binary.
    """
    import cv2
    from PIL import Image

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logging.warning(f"Cannot open video: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_step = max(1, int(fps * interval))
    idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % frame_step == 0:
            ts = idx / fps
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            yield ts, Image.fromarray(rgb)
        idx += 1

    cap.release()


def embed_frames(frames):
    """Embed a list of PIL Images with CLIP.

    Returns an (N, 512) float32 ndarray, L2-normalized.
    """
    if not frames:
        return np.empty((0, CLIP_DIM), dtype=np.float32)

    model, processor = _load_clip()
    import torch

    inputs = processor(images=frames, return_tensors="pt", padding=True)
    with torch.no_grad():
        vecs = model.get_image_features(**inputs)
    vecs = vecs.cpu().numpy().astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return vecs / norms


def embed_text_clip(texts):
    """Embed text queries with CLIP's text encoder.

    Returns an (N, 512) float32 ndarray, L2-normalized.
    Used for visual search: embed the query with the same model that
    embedded the frames, so cosine similarity is meaningful.
    """
    if isinstance(texts, str):
        texts = [texts]
    if not texts:
        return np.empty((0, CLIP_DIM), dtype=np.float32)

    model, processor = _load_clip()
    import torch

    inputs = processor(text=texts, return_tensors="pt", padding=True,
                       truncation=True)
    with torch.no_grad():
        vecs = model.get_text_features(**inputs)
    vecs = vecs.cpu().numpy().astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return vecs / norms


def process_video(video_path, interval: float = DEFAULT_FRAME_INTERVAL):
    """Extract + embed all keyframes from one video.

    Returns a list of {"timestamp": float, "embedding": np.ndarray}.
    """
    timestamps, images = [], []
    for ts, img in extract_keyframes(video_path, interval):
        timestamps.append(ts)
        images.append(img)

    if not images:
        return []

    vecs = embed_frames(images)
    return [
        {"timestamp": ts, "embedding": vec}
        for ts, vec in zip(timestamps, vecs)
    ]
