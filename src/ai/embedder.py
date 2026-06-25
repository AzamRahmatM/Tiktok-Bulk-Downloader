#!/usr/bin/env python3
"""
Text embedding helper built on sentence-transformers.

A single small model (all-MiniLM-L6-v2, 384-dim) is loaded lazily and
cached for the process. Vectors are L2-normalized so that a plain dot
product equals cosine similarity, which keeps search a single matmul.
"""
import logging
from functools import lru_cache

import numpy as np

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    # Imported here so the base scraper never pays the import cost.
    from sentence_transformers import SentenceTransformer

    logging.info(f"Loading embedding model: {model_name}")
    return SentenceTransformer(model_name)


def embed(texts, model_name: str = DEFAULT_MODEL) -> np.ndarray:
    """Embed a string or list of strings into normalized float32 vectors.

    Returns a 2-D array of shape (len(texts), EMBED_DIM).
    """
    if isinstance(texts, str):
        texts = [texts]
    if not texts:
        return np.empty((0, EMBED_DIM), dtype=np.float32)

    model = _load_model(model_name)
    vecs = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vecs.astype(np.float32)
