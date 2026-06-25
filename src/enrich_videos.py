#!/usr/bin/env python3
"""
AI enrichment CLI.

Walks a directory of downloaded .mp4 files, transcribes each one,
embeds the transcript segment-by-segment, and stores everything in a
local SQLite vector index that `search_videos.py` can query.

Optionally extracts visual keyframes and embeds them with CLIP for
image-based search (--visual flag).

Run this after the downloader finishes:

    python src/enrich_videos.py --download-dir downloads
    python src/enrich_videos.py --download-dir downloads --visual

Already-indexed videos are skipped, so it is safe to re-run after each
new batch of downloads.
"""
import os
import sys
import argparse
import logging
from pathlib import Path

# Allow "python src/enrich_videos.py" to find the local `ai` package.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai import transcribe, store  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("enrich.log"),
        logging.StreamHandler(),
    ],
)


def _enrich_visual(path, video_id, args):
    """Extract keyframes and embed with CLIP."""
    from ai import vision  # noqa: E402 — lazy import

    if not args.force and store.has_frames(args.db, video_id):
        return False

    logging.info(f"Extracting visual keyframes from {path.name} ...")
    frame_data = vision.process_video(path, interval=args.frame_interval)
    if frame_data:
        store.add_frames(args.db, video_id, frame_data)
        logging.info(
            f"  -> {len(frame_data)} frames embedded for {video_id}"
        )
    else:
        logging.warning(f"  -> No frames extracted from {path.name}")
    return True


def main(args):
    download_dir = Path(args.download_dir)
    if not download_dir.exists():
        logging.error(f"Directory not found: {download_dir}")
        sys.exit(1)

    videos = sorted(download_dir.glob("*.mp4"))
    if not videos:
        logging.warning(f"No .mp4 files found in {download_dir}")
        return

    logging.info(f"Found {len(videos)} videos. Index: {args.db}")
    if args.visual:
        logging.info(
            f"Visual enrichment ON (frame interval: {args.frame_interval}s)"
        )
    enriched, skipped, failed = 0, 0, 0

    for path in videos:
        video_id = path.stem
        text_done = (
            not args.force and store.is_enriched(args.db, video_id)
        )
        visual_done = (
            not args.visual
            or (not args.force and store.has_frames(args.db, video_id))
        )

        if text_done and visual_done:
            skipped += 1
            continue

        try:
            # ── Text enrichment ──
            if not text_done:
                logging.info(f"Transcribing {path.name} ...")
                result = transcribe.transcribe_file(
                    path,
                    model_size=args.model,
                    device=args.device,
                    compute_type=args.compute_type,
                )
                store.add_video(args.db, video_id, path, result)

            # ── Visual enrichment ──
            if args.visual and not visual_done:
                _enrich_visual(path, video_id, args)

            enriched += 1
        except Exception as e:  # keep going on a bad file
            logging.error(f"Failed to enrich {path.name}: {e}")
            failed += 1

    s = store.stats(args.db)
    logging.info(
        f"Done. enriched={enriched} skipped={skipped} failed={failed} | "
        f"index now holds {s['videos']} videos / {s['segments']} segments"
        f" / {s['frames']} frames"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI enrichment for videos")
    parser.add_argument(
        "--download-dir",
        default=os.environ.get("DOWNLOAD_DIR", "downloaded_videos"),
        help="Directory containing downloaded .mp4 files",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("VIDEO_INDEX_DB", "video_index.db"),
        help="Path to the SQLite vector index",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("WHISPER_MODEL", transcribe.DEFAULT_MODEL),
        help="faster-whisper model size (tiny|base|small|medium|large-v3)",
    )
    parser.add_argument(
        "--device",
        default=os.environ.get("WHISPER_DEVICE", "cpu"),
        help="cpu or cuda",
    )
    parser.add_argument(
        "--compute-type",
        default=os.environ.get("WHISPER_COMPUTE", "int8"),
        help="Compute type, e.g. int8 (cpu) or float16 (cuda)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-enrich videos even if already indexed",
    )
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Also extract and embed visual keyframes with CLIP",
    )
    parser.add_argument(
        "--frame-interval",
        type=float,
        default=float(os.environ.get("FRAME_INTERVAL", "3.0")),
        help="Seconds between extracted keyframes (default: 3.0)",
    )

    args = parser.parse_args()
    try:
        main(args)
    except KeyboardInterrupt:
        logging.warning("Interrupted by user. Exiting.")
        sys.exit(130)
