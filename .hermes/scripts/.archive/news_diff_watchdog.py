#!/usr/bin/env python3
"""
news_diff_watchdog.py — Zero-token news change detector.

Pattern from aliaihub/awesome-hermes-usecases (zero-token-notifications.md):
- Run as a cron `script` with no_agent=True OR as a pre-filter script before an LLM briefing cron.
- Compares today's feed item IDs/URLs against a rolling cache file.
- If nothing new: outputs nothing → gateway suppresses delivery (SILENT).
- If new items exist: outputs a compact summary → triggers agent or delivers directly.

Usage:
    python3 news_diff_watchdog.py [--sources all] [--limit 20] [--cache-dir ~/.hermes/cache/news]

Cron integration examples:

  # Pure zero-token watchdog (no LLM, only fires when new items appear):
  cronjob(
    schedule="every 60m",
    no_agent=True,
    script="news_diff_watchdog.py",
    deliver="origin",  # SILENT when empty stdout, fires when new items found
  )

  # As a pre-filter for an LLM briefing cron (context_from):
  # 1. Create this as a no_agent script job that saves to output
  # 2. Create a second LLM briefing job with context_from=[watchdog_job_id]
  #    — the briefing only has real content when the watchdog found new items

Exit codes:
    0 — always (errors are silent to avoid false-alarm cron notifications)

Output:
    Empty string → no new items (SILENT delivery suppression)
    Compact text → new items found (triggers delivery or LLM briefing)
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).parent
DEFAULT_CACHE_DIR = Path.home() / ".hermes" / "cache" / "news"
INGEST_SCRIPT = SCRIPTS_DIR / "news_feed_ingest.py"
CACHE_FILE = "seen_items.json"
CACHE_MAX_SIZE = 2000  # max URLs to remember (rolling)


def load_cache(cache_path: Path) -> set:
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text())
            return set(data.get("seen", []))
        except Exception:
            pass
    return set()


def save_cache(cache_path: Path, seen: set) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    # Keep rolling window
    seen_list = list(seen)
    if len(seen_list) > CACHE_MAX_SIZE:
        seen_list = seen_list[-CACHE_MAX_SIZE:]
    cache_path.write_text(json.dumps({
        "seen": seen_list,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))


def item_key(item: dict) -> str:
    """Stable dedup key: prefer URL, fall back to title hash."""
    url = item.get("url", "")
    if url:
        return url
    title = item.get("title", "")
    return "title:" + hashlib.sha1(title.encode()).hexdigest()


def run_ingest(sources: str, limit: int) -> list[dict]:
    """Call news_feed_ingest.py and parse JSON output."""
    if not INGEST_SCRIPT.exists():
        return []
    cmd = [sys.executable, str(INGEST_SCRIPT),
           "--sources", sources,
           "--limit", str(limit),
           "--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(description="Zero-token news diff watchdog")
    parser.add_argument("--sources", default="all",
                        help="Sources to poll (default: all)")
    parser.add_argument("--limit", type=int, default=20,
                        help="Items to fetch per run (default: 20)")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR),
                        help="Cache directory (default: ~/.hermes/cache/news)")
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    cache_path = cache_dir / CACHE_FILE

    # Load existing seen set
    seen = load_cache(cache_path)

    # Fetch new items
    items = run_ingest(args.sources, args.limit)
    if not items:
        # Network failure / script error — stay silent
        sys.exit(0)

    # Find genuinely new items
    new_items = []
    for item in items:
        key = item_key(item)
        if key not in seen:
            new_items.append(item)
            seen.add(key)

    # Save updated cache
    save_cache(cache_path, seen)

    if not new_items:
        # Nothing new → empty stdout → SILENT delivery suppression
        sys.exit(0)

    # New items found → emit compact summary for delivery or LLM context
    lines = [f"[news-diff] {len(new_items)} new item(s) — {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    for item in new_items[:15]:  # cap output length
        title = item.get("title", "(no title)")[:100]
        source = item.get("source", "")
        url = item.get("url", "")
        lines.append(f"  [{source}] {title}")
        if url:
            lines.append(f"    {url}")

    if len(new_items) > 15:
        lines.append(f"  ... and {len(new_items) - 15} more")

    print("\n".join(lines))
    sys.exit(0)


if __name__ == "__main__":
    main()
