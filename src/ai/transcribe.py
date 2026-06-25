#!/usr/bin/env python3
"""
Speech-to-text for downloaded videos using faster-whisper.

faster-whisper decodes the audio track straight from the .mp4 (via its
bundled PyAV), so no separate ffmpeg binary is required. The model is
loaded lazily and cached for the life of the process.
"""
import logging
from functools import lru_cache

DEFAULT_MODEL = "base"          # tiny | base | small | medium | large-v3


@lru_cache(maxsize=2)
def _load_model(model_size: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel

    logging.info(
        f"Loading faster-whisper '{model_size}' "
        f"({device}/{compute_type})"
    )
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe_file(
    path,
    model_size: str = DEFAULT_MODEL,
    device: str = "cpu",
    compute_type: str = "int8",
) -> dict:
    """Transcribe one media file.

    Returns:
        {
            "language": str,
            "duration": float,
            "transcript": str,           # full joined text
            "segments": [{"start", "end", "text"}],
        }
    """
    model = _load_model(model_size, device, compute_type)
    segments_iter, info = model.transcribe(str(path), vad_filter=True)

    segments = []
    for seg in segments_iter:
        text = seg.text.strip()
        if not text:
            continue
        segments.append(
            {"start": float(seg.start), "end": float(seg.end), "text": text}
        )

    return {
        "language": info.language,
        "duration": float(getattr(info, "duration", 0.0)),
        "transcript": " ".join(s["text"] for s in segments),
        "segments": segments,
    }
