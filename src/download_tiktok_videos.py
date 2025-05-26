#!/usr/bin/env python3
import os
import sys
import argparse
import time
import random
import asyncio
import aiohttp
import logging
import pandas as pd
from tqdm import tqdm
import re
from pathlib import Path

# SETUP LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("tiktokdownload.log"),
        logging.StreamHandler()
    ]
)

# CORE ---
async def download_video(session, url, download_dir, headers):
    try:
        video_id = url.rstrip("/").split("/")[-1]
        file_path = download_dir / f"{video_id}.mp4"

        if file_path.exists():
            logging.info(f"Video {video_id} already exists, skipping.")
            return None

        # fetch share page
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                logging.error(f"Failed to fetch page {url}: HTTP {resp.status}")
                return url
            content = await resp.text()

        # extract direct video URL
        match = re.search(r'"playAddr(?:NoWaterMark)?":"([^"]+)"', content)
        if not match:
            logging.error(f"Could not find video URL in the page content for {url}")
            return url

        video_url = match.group(1).replace("\\u002F", "/")
        # fetch video bytes
        async with session.get(video_url, headers=headers) as video_resp:
            if video_resp.status != 200:
                logging.error(f"Failed to download from {video_url}: HTTP {video_resp.status}")
                return url
            data = await video_resp.read()

        # write file
        file_path.write_bytes(data)
        logging.info(f"Downloaded: {file_path}")
        return None

    except Exception as e:
        logging.error(f"Failed to download {url}: {e}")
        return url

async def process_batch(session, batch, sem, download_dir, headers):
    failed = []

    async def bounded_download(u):
        async with sem:
            return await download_video(session, u, download_dir, headers)

    tasks = [bounded_download(u) for u in batch]
    for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Downloading videos"):
        result = await coro
        if result:
            failed.append(result)
    return failed

async def main(args):
    # parse and prepare paths
    url_file = Path(args.url_file)
    download_dir = Path(args.download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)

    # read URLs
    video_urls = [u.strip() for u in url_file.read_text().splitlines() if u.strip()]
    total = len(video_urls)
    logging.info(f"Processing {total} URLs from {url_file}")

    # HTTP headers
    headers = {
        "User-Agent": args.user_agent,
        "Referer": "https://www.tiktok.com/"
    }

    # concurrency control
    sem = asyncio.Semaphore(args.concurrency)

    all_failed = []
    async with aiohttp.ClientSession() as session:
        for i in range(0, total, args.batch_size):
            batch = video_urls[i : i + args.batch_size]
            idx = i // args.batch_size + 1
            logging.info(f"Processing batch {idx} of {(total + args.batch_size - 1)//args.batch_size}")

            failed = await process_batch(session, batch, sem, download_dir, headers)
            all_failed.extend(failed)

            # persist failed so far
            Path("failed_urls.txt").write_text("\n".join(all_failed))
            logging.info(f"Completed batch {idx}. Total failed: {len(all_failed)}")

            # delay
            await asyncio.sleep(random.uniform(args.min_delay, args.max_delay))

    # final CSV report
    df = pd.DataFrame({"Failed URLs": all_failed})
    df.to_csv("failed_urls.csv", index=False)
    logging.info("Download completed. Reports written to failed_urls.txt / .csv")

#CLI ENTRYPOINT

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk TikTok Video Downloader")
    parser.add_argument("--url-file",       default=os.environ.get("URL_FILE", "urls.txt"),
                        help="Path to text file with one TikTok URL per line")
    parser.add_argument("--download-dir",   default=os.environ.get("DOWNLOAD_DIR", "downloaded_videos"),
                        help="Directory to save downloaded MP4s")
    parser.add_argument("--batch-size",     type=int, default=int(os.environ.get("BATCH_SIZE", 50)),
                        help="Number of concurrent tasks per batch")
    parser.add_argument("--concurrency",    type=int, default=int(os.environ.get("CONCURRENCY", 20)),
                        help="Max simultaneous HTTP requests")
    parser.add_argument("--min-delay",      type=float, default=float(os.environ.get("MIN_DELAY", 2)),
                        help="Minimum delay (s) between batches")
    parser.add_argument("--max-delay",      type=float, default=float(os.environ.get("MAX_DELAY", 5)),
                        help="Maximum delay (s) between batches")
    parser.add_argument("--user-agent",     default=os.environ.get("USER_AGENT",
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"),
                        help="User-Agent string to use for HTTP requests")

    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        logging.warning("Script interrupted by user. Exiting.")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)
