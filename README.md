# TikTok Bulk Video Downloader - Automation

[![CI Status](https://img.shields.io/github/actions/workflow/status/AzamRahmatM/Tiktok-Bulk-Downloader/ci.yml?branch=main)](https://github.com/AzamRahmatM/Tiktok-Bulk-Downloader/actions)
![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Asynchronously download hundreds or thousands of TikTok videos with a single command. Designed for reliability (semaphore-driven concurrency, randomized delays), observability (structured logging, CSV of failures), and easy deployment (Docker & Kubernetes).

---
## Table of Contents

- [Key Features](#-key-features)
- [AI Semantic Search](#-ai-semantic-search)
- [Visual Search (CLIP)](#-visual-search-clip)
- [Auto-Tagging & Topic Clustering](#-auto-tagging--topic-clustering)
- [Web Dashboard](#-web-dashboard)
- [Quick Start](#-quick-start)
- [Automated Deployment using Ansible (IaC)](#%EF%B8%8F-automated-deployment-using-ansible-iac)
- [Extracting Your TikTok Video URLs](#-extracting-your-tiktok-video-urls)
---
## 🔥 Key Features

- **Async + Concurrency Control**  
  Uses `asyncio` + `aiohttp` + an `asyncio.Semaphore` cap to safely burst requests without overwhelming the network or TikTok’s servers.

- **Rate-Limit Friendly**  
  Randomized batch delays between downloads minimize the risk of throttling or blocks.

- **Watermark-Free Streams**  
  Extracts the `playAddrNoWaterMark` URL via regex to save clean MP4s.

- **Robust Logging & Metrics**  
  Console + file logging (tiktokdownload.log), automatic retries with exponential backoff on 403/5xx errors, and a final failed_urls.csv for audit or re-runs.

- **Automatic Retry Logic**  
  On any non-200 or network error, the downloader will retry up to 3 times with exponential backoff (1 s -> 2 s -> 4 s) before marking a URL as failed.

- **CLI-Driven**  
  Fully configurable via flags or environment variables: URL list, output dir, batch size, concurrency, delays, and User-Agent.

- **Container & Cloud-Native Ready**  
  Comes with a Dockerfile and optional Kubernetes CronJob manifest for one-click deploy.

- **🧠 AI Semantic Search (local, offline)**  
  Transcribes every downloaded video (`faster-whisper`), embeds transcripts
  segment-by-segment (`sentence-transformers`), and stores vectors in a local
  SQLite index. Search thousands of videos by meaning and jump to the exact timestamp.

- **🖼️ CLIP Visual Search**  
  Extracts keyframes from each video and embeds them with OpenAI CLIP (ViT-B/32).
  Search by what's *on screen* — "person outdoors with product" — not just spoken words.

- **🏷️ Auto-Tagging & Topic Clustering**  
  HDBSCAN auto-discovers topic groups, TF-IDF generates human-readable labels.
  2,800 videos → organized clusters like "pricing, enterprise" or "product, demo".

- **📊 Streamlit Web Dashboard**  
  Dark-themed, portfolio-ready UI with semantic search, inline video playback
  with timestamp jumping, topic cluster browser, and library statistics.
---
## 🧠 AI Semantic Search

A folder of 2,800 `7234985.mp4` files is impossible to search. This layer turns that pile
into a queryable library: ask for an idea in plain English and get back the exact video and
moment that matches — even if those words were never written down anywhere.

**Full pipeline:**

```
transcribe (faster-whisper) → embed segments (MiniLM) → SQLite vector index → cosine search
                            ↘ extract keyframes (OpenCV) → embed frames (CLIP) → visual search
                            ↘ mean embeddings → HDBSCAN clustering → TF-IDF labels
```

### Setup

```bash
pip install -r requirements-ai.txt
```

### 1. Enrich your downloaded videos

Run this after the downloader finishes. Already-indexed videos are skipped, so it is safe to
re-run after each new batch.

```bash
# Text-only enrichment (transcription + text embeddings)
python src/enrich_videos.py --download-dir downloads

# Full enrichment with visual keyframes (adds CLIP embeddings)
python src/enrich_videos.py --download-dir downloads --visual

# Options: --model base|small|medium  --device cuda  --force  --frame-interval 3
```

### 2. Search by meaning (text)

```bash
python src/search_videos.py "someone demoing the product outdoors"
python src/search_videos.py "pricing discussion" --top-k 10
```

```text
Top 2 matches for: "pricing discussion"

1. [0.731] 7234985123  @ 01:12
   downloads/7234985123.mp4
   "so our enterprise tier starts at forty nine a month per seat …"
```

Each hit points at the exact `.mp4` and the timestamp inside it. Everything runs locally on CPU
(`int8` quantization) — switch to `--device cuda` for a large speedup.

---
## 🖼️ Visual Search (CLIP)

Search videos by what's *on screen*, not just spoken words. CLIP embeds video frames and text
queries into the same vector space, so "person holding product outdoors" matches frames where
that happens — even if nobody said those words.

```bash
# First, enrich with --visual to extract keyframes
python src/enrich_videos.py --download-dir downloads --visual

# Visual search is available in the Streamlit dashboard
# or programmatically:
#   from ai.store import search_visual
#   results = search_visual("video_index.db", "outdoor product demo")
```

**How it works:**
- Extracts 1 keyframe every 3 seconds (configurable via `--frame-interval`)
- Embeds each frame with CLIP ViT-B/32 (512-dim vectors)
- Stores frame embeddings in the SQLite index
- At search time, embeds the text query with CLIP's text encoder and cosine-searches against frames

---
## 🏷️ Auto-Tagging & Topic Clustering

Automatically organize your video library into topic groups without manual labels.

```bash
# Auto-cluster with HDBSCAN (auto-picks number of clusters)
python src/cluster_videos.py

# Or use KMeans with a fixed number of clusters
python src/cluster_videos.py --method kmeans --k 10
```

```text
============================================================
  Topic Clusters (5 groups)
============================================================

  Cluster 0: "pricing, enterprise, subscription" (47 videos)
  Cluster 1: "product, demo, walkthrough" (123 videos)
  Cluster 2: "testimonial, customer, success" (31 videos)
  Cluster 3: "tutorial, setup, getting started" (58 videos)
  Cluster 4: "announcement, update, release" (22 videos)

  Noise: 14 unclustered videos
```

**How it works:**
- Aggregates segment embeddings into one mean vector per video
- Runs HDBSCAN (falls back to KMeans if too few clusters found)
- Labels each cluster with TF-IDF's top distinguishing terms from transcripts
- Saves cluster assignments to the index for the dashboard to display

---
## 📊 Web Dashboard

A polished Streamlit dashboard with a warm, editorial "museum" aesthetic (cream palette, serif headings, split-text reveal animations) for browsing and searching your video library.

```bash
streamlit run src/app.py
```

**Pages:**
- 🔍 **Search** — Semantic text search or CLIP visual search with animated result cards, inline video playback, and timestamp jumping
- 📊 **Library** — Index stats (videos, segments, frames, clusters), full video table, language breakdown, duration distribution
- 🏷️ **Topics** — Browse auto-discovered topic clusters with expandable video lists and TF-IDF labels

## 🔗 Extracting Your TikTok Video URLs

Before you run the downloader, you need a list of share-URLs, one per line, to feed into `urls.txt`. We’ll grab them in bulk right from your browser with a small JavaScript snippet.

### Motivation

During my internship, I was tasked with archiving **2,800+** corporate TikTok videos for our sales portfolio. Existing tools crashed after a few hundred downloads and offered no way to scrape thousands of links reliably. Rather than manually click each video, I wrote a tiny browser script to **auto-scroll**, **collect every URL**, and **export** them to CSV, and it, along with my downloader, saved over 200 hours of work.

### How it works

1. **Auto-scroll** your profile page until no new videos load  
2. **Select** each post’s `href` (video URL) and its title text  
3. **Build** a safe CSV (escaping quotes in titles)  
4. **Trigger** a download of `tiktok_videos.csv`

### one-click console snippet

Open your browser’s DevTools → Console on **`https://www.tiktok.com/@yourtag`**, paste this, and hit **Enter**:

```js
(async () => {
  const scrollDelay = 1500, maxScrolls = 50;
  let lastHeight = 0;   
  // 1)Auto-scroll until no more new posts (you can increase the speed to your liking)
  for (let i = 0; i < maxScrolls; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(r => setTimeout(r, scrollDelay));
    if (document.body.scrollHeight === lastHeight) break;
    lastHeight = document.body.scrollHeight;
  }

  // 2)Grab each video link & title
  const posts = Array.from(
    document.querySelectorAll(
      'div[data-e2e="user-post-item"] a[href*="/video/"]'
    )
  );
  const rows = posts.map(a => {
    const url = a.href.split('?')[0];
    const title = a
      .querySelector('[data-e2e="user-post-item-desc"]')
      ?.innerText.trim() || '';
    return { title, url };
  });
  if (!rows.length) {
    return console.warn("No videos found – check your page and selectors");
  }

  // 3)Building CSV, escaping quotes
  const header = ['Title','URL'];
  const csv = [
    header.join(','),
    ...rows.map(r =>
      `"${r.title.replace(/"/g, '""')}","${r.url}"`
    )
  ].join('\n');

  // 4) Trigger download
  const blob = new Blob([csv], { type: 'text/csv' });
  const dl = document.createElement('a');
  dl.href = URL.createObjectURL(blob);
  dl.download = 'tiktok_videos.csv';
  document.body.appendChild(dl);
  dl.click();
  document.body.removeChild(dl);

  console.log(`Exported ${rows.length} URLs to tiktok_videos.csv`);
})();
```

1. **Paste & run**  
   Paste the snippet into your browser console on your TikTok profile page and press **Enter**.

2. **Wait**  
   Let it auto‐scroll and collect all posts (you’ll see a log message when it’s finished).

3. **Download**  
   A file named `tiktok_videos.csv` will appear in your **Downloads** folder.

4. **Prepare URLs**  
   Open `tiktok_videos.csv`, copy the **URL** column values (one per line) into `urls.txt`.

5. **Run the downloader**  
   
```bash
python src/download_tiktok_videos.py \
  --url-file urls.txt \
  --download-dir downloads \
  --batch-size 20 \
  --concurrency 5 \
  --min-delay 1 \
  --max-delay 3 \
  --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)…"
```
---
## 🚀 Quick Start for for the files

1. **Clone and enter**  
   ```bash
   git clone https://github.com/AzamRahmatM/Tiktok-Bulk-Downloader.git
   cd Tiktok-Bulk-Downloader
2. **Download Python**  
   Download & install from https://www.python.org/downloads/  
   During install, **check “Add Python to PATH.”**
3. **Download your videos**
```bash
python src/download_tiktok_videos.py \
  --url-file urls.txt \
  --download-dir downloads \
  --batch-size 20 \
  --concurrency 5 \
  --min-delay 1 \
  --max-delay 3 \
  --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)…"
```
3. **How to get URLs?**  
    I know what you are thinking. How do I get 1000+ of URLs? See [here](#-extracting-your-tiktok-video-urls):
---
## 🛠️ Automated Deployment using Ansible (IaC)

We ship an Ansible playbook that:

* Installs Git & Python
* Clones this repo into `/opt/tiktok-bulk-downloader`
* Sets up a virtualenv + requirements
* Creates the `downloads/` folder
* Schedules a daily Cron job at 02:00

### Quick start (local test)

1. **Inventory** (`inventory.ini`)
   ```ini
   [downloaders]
   localhost ansible_connection=local
    ```

2. **Syntax check**
   ```bash
   ansible-playbook --syntax-check ansible/deploy-downloader.yml
    ```

3. **Dry-run**
   ```bash 
   ansible-playbook -i inventory.ini ansible/deploy-downloader.yml --check
   ```

4. **Apply for real** 
   ```bash
   ansible-playbook -i inventory.ini ansible/deploy-downloader.yml
   ```
---
