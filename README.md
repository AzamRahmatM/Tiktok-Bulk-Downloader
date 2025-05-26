# TikTok Bulk Video Downloader

[![CI Status](https://img.shields.io/github/actions/workflow/status/AzamRahmatM/Tiktok-Bulk-Downloader/ci.yml?branch=main)](https://github.com/AzamRahmatM/Tiktok-Bulk-Downloader/actions)
![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)
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

## 🔗 Extracting Your TikTok Video URLs

Before you run the downloader, you need a list of share-URLs—one per line—to feed into `urls.txt`. We’ll grab them in bulk right from your browser with a small JavaScript snippet.

### Motivation

During my internship, I was tasked with archiving **2 800+** corporate TikTok videos for our sales portfolio. Existing tools crashed after a few hundred downloads and offered no way to scrape thousands of links reliably. Rather than manually click each video, I wrote a tiny browser script to **auto-scroll**, **collect every URL**, and **export** them to CSV—and it saved over 200 hours of work.

### How it works

1. **Auto-scroll** your profile page until no new videos load  
2. **Select** each post’s `href` (video URL) and its title text  
3. **Build** a safe CSV (escaping quotes in titles)  
4. **Trigger** a download of `tiktok_videos.csv`

### 1-click console snippet

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
   python src/download_tiktok_videos.py --url-file urls.txt
```