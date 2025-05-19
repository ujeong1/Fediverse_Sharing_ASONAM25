# Interaction-Driven Snowball Sampling (IDSS) for Threads Users via Mastodon API

This repository provides a pipeline for **Interaction-Driven Snowball Sampling (IDSS)** to collect Threads users who have enabled **Fediverse Sharing**. The sampling is conducted through the **Mastodon API**, using `mastodon.social` as the primary instance.

## 📂 Files

- `IDSS_pipeline.py`: Main script that includes all stages of the IDSS process, including:
  - Seed user discovery via `@threads.net` profile search
  - Recursive expansion by tracing replies to seed users
  - Deduplication and interaction tracking

- `requirements.txt`: Lists all Python dependencies needed to run the pipeline.

## 🔧 Installation

Install the required dependencies with:

```bash
pip install -r requirements.txt
