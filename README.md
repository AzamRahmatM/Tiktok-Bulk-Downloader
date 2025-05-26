# TikTok Bulk Video Downloader
> Download hundreds—or thousands—of watermark-free TikTok videos in parallel.  
> **CLI-driven • Docker-ready • Kubernetes-friendly • Observability baked-in**

[![CI](https://img.shields.io/github/actions/workflow/status/AzamRahmatM/Tiktok-Bulk-Downloader/ci.yml?branch=main)](https://github.com/AzamRahmatM/Tiktok-Bulk-Downloader/actions)
![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
  - [pip](#-pip-local-run)
  - [Docker](#-docker-zero-setup)
  - [Kubernetes CronJob](#-kubernetes-cronjob-optional)
- [Quick Start](#quick-start)
- [Extracting Video URLs](#extracting-video-urls)
- [CLI Options](#cli-options)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Credits](#credits)

---

## Features

| Category | Details |
|---|---|
| **Async bursts, sane limits** | `asyncio` + `aiohttp` with a semaphore cap keeps your IP off TikTok’s naughty list. |
| **Watermark-free MP4s** | Regex-parses the `playAddrNoWaterMark` source URL for clean streams. |
| **Built-in back-pressure** | Random per-batch sleeps fight rate-limits automatically. |
| **Observability first** | Structured logs to console **and** `tiktokdownload.log`; automatic retries; audit trail in `failed_urls.csv`. |
| **Container-native** | Dockerfile, multi-arch image, and a ready-to-copy Kubernetes CronJob. |
| **Fail-fast CLI** | One file does it all—no hidden globals, no external databases. |

---

## Architecture

```text
┌─────────────────────────────┐
│  url-producer (CSV / txt)   │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  asyncio worker-pool        │
│  ─ semaphore (N jobs)       │
│  ─ randomized batch delay   │
│  ─ exponential back-off     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  MP4 writer (async streams) │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Observability layer        │
│  ─ console + file log       │
│  ─ failed_urls.csv          │
└─────────────────────────────┘
