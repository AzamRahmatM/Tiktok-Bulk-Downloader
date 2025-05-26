# TikTok Bulk Video Downloader

[![CI Status](https://img.shields.io/github/actions/workflow/status/AzamRahmatM/Tiktok-Bulk-Downloader/ci.yml?branch=main)](https://github.com/AzamRahmatM/Tiktok-Bulk-Downloader/actions)  
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Asynchronously download hundreds or thousands of TikTok videos with a single command. Designed for reliability (semaphore-driven concurrency, randomized delays), observability (structured logging, CSV of failures), and easy deployment (Docker & Kubernetes).

---

## 🔥 Key Features

- **Async + Concurrency Control**  
  Uses `asyncio` + `aiohttp` + an `asyncio.Semaphore` cap to safely burst requests without overwhelming the network or TikTok’s servers.

- **Rate-Limit Friendly**  
  Randomized batch delays between downloads minimize the risk of throttling or blocks.

- **Watermark-Free Streams**  
  Extracts the `playAddrNoWaterMark` URL via regex to save clean MP4s.

- **Robust Logging & Metrics**  
  Console + file logging (`tiktokdownload.log`), automatic retries, and a final `failed_urls.csv` for audit or re-runs.

- **CLI-Driven**  
  Fully configurable via flags or environment variables: URL list, output dir, batch size, concurrency, delays, and User-Agent.

- **Container & Cloud-Native Ready**  
  Comes with a Dockerfile and optional Kubernetes CronJob manifest for one-click deploy.

---

## 🚀 Quick Start

1. **Clone and enter**  
   ```bash
   git clone https://github.com/AzamRahmatM/Tiktok-Bulk-Downloader.git
   cd Tiktok-Bulk-Downloader