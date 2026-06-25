"""
AI enrichment layer for the TikTok Bulk Downloader.

Turns a folder of downloaded .mp4 files into an intelligent,
semantically searchable video library:

    transcribe (faster-whisper) -> embed segments (sentence-transformers)
    -> CLIP visual embeddings (transformers) -> HDBSCAN topic clustering
    -> store in a local SQLite vector index -> search by meaning.

Everything runs locally and offline. No API keys required.
"""

__all__ = ["transcribe", "embedder", "store", "vision", "cluster"]
