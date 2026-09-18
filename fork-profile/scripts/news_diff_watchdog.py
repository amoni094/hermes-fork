#!/usr/bin/env python3
"""
news_diff_watchdog.py - Hermes cron watchdog: emits new news items only.

Fetches news URLs from configured sources, compares against a rolling cache,
and outputs only genuinely new items to stdout. Empty output = no new items
(silent cron tick). Non-empty output is delivered verbatim by the cron system.

Cache: ~/.hermes/cache/news/seen_items.json
Config: URLs are hardcoded below; extend as needed.

Usage (cron):
  cronjob(schedule="every 60m", no_agent=True, script="news_diff_watchdog.py")
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────
CACHE_FILE = Path.home() / ".hermes" / "cache" / "news" / "seen_items.json"
MAX_CACHE_ITEMS = 500  # Rolling window to prevent unbounded growth

# Feed sources: list of (name, url) tuples
# Add RSS/Atom feeds or raw news endpoint URLs here
FEEDS = [
    # ── General news ──────────────────────────────────────────────────────
    ("Reuters Markets", "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters World", "https://feeds.reuters.com/Reuters/worldNews"),
    ("Hacker News", "https://news.ycombinator.com/rss"),
    ("AI News (MIT Tech Review)", "https://www.technologyreview.com/feed/"),
    ("The Guardian AU", "https://www.theguardian.com/australia-news/rss"),
    # ── AI agent research — arXiv category RSS ────────────────────────────
    # Covers the 7 hermes-research categories natively; published daily
    # NOTE: arXiv RSS removed — covered by hermes-research-sweep.py (weekly, deduplicated)
    # Adding it here would flood the news diff with 100+ items per tick per category
    # (\"arXiv cs.AI\", \"https://rss.arxiv.org/rss/cs.AI\"),
    # (\"arXiv cs.CL\", \"https://rss.arxiv.org/rss/cs.CL\"),
    # (\"arXiv cs.MA\", \"https://rss.arxiv.org/rss/cs.MA\"),
    # (\"arXiv cs.LG\", \"https://rss.arxiv.org/rss/cs.LG\"),
    # (\"arXiv cs.IR\", \"https://rss.arxiv.org/rss/cs.IR\"),
    # ── Hugging Face Papers (community-voted, high signal) ─────────────────
    ("HF Papers", "https://huggingface.co/papers/rss"),
    # ── Papers With Code (leaderboard/benchmark papers) ────────────────────
    ("Papers With Code", "https://paperswithcode.com/latest/rss"),
    # ── AI blog RSS (practitioner signal) ─────────────────────────────────
    ("Google DeepMind Blog", "https://deepmind.google/blog/rss.xml"),
    ("Anthropic News", "https://www.anthropic.com/news/rss"),
    ("OpenAI Blog", "https://openai.com/research/rss.xml"),
]

# ── Cache helpers ─────────────────────────────────────────────────────────
def load_cache() -> dict:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            return {"seen": [], "last_updated": None}
    return {"seen": [], "last_updated": None}


def save_cache(cache: dict) -> None:
    # Keep rolling window
    if len(cache["seen"]) > MAX_CACHE_ITEMS:
        cache["seen"] = cache["seen"][-MAX_CACHE_ITEMS:]
    cache["last_updated"] = datetime.now(timezone.utc).isoformat()
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def item_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


# ── Feed fetcher ──────────────────────────────────────────────────────────
def fetch_items(feed_url: str) -> list[dict]:
    """Fetch and parse an RSS/Atom feed. Returns list of {title, url, pub_date}."""
    import urllib.request
    import xml.etree.ElementTree as ET

    items = []
    try:
        req = urllib.request.Request(
            feed_url,
            headers={"User-Agent": "Hermes-news-watchdog/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)

        # RSS 2.0
        ns = {}
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            if link:
                items.append({"title": title, "url": link, "pub_date": pub})

        # Atom
        atom_ns = "http://www.w3.org/2005/Atom"
        for entry in root.findall(f"{{{atom_ns}}}entry"):
            title = (entry.findtext(f"{{{atom_ns}}}title") or "").strip()
            link_el = entry.find(f"{{{atom_ns}}}link")
            link = link_el.get("href", "") if link_el is not None else ""
            pub = (entry.findtext(f"{{{atom_ns}}}updated") or "").strip()
            if link:
                items.append({"title": title, "url": link, "pub_date": pub})

    except Exception as e:
        # Watchdog must stay silent on transient failures
        pass

    return items


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> None:
    if not FEEDS:
        # No feeds configured - silent exit
        sys.exit(0)

    cache = load_cache()
    seen_keys = set(cache.get("seen", []))
    new_items = []

    for feed_name, feed_url in FEEDS:
        items = fetch_items(feed_url)
        for item in items:
            k = item_key(item["url"])
            if k not in seen_keys:
                seen_keys.add(k)
                new_items.append((feed_name, item))

    if new_items:
        lines = [f"[news-diff] {len(new_items)} new item(s) — {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}"]
        for feed_name, item in new_items:
            title = item["title"] or "(no title)"
            url = item["url"]
            lines.append(f"• [{feed_name}] {title}\n  {url}")
        print("\n".join(lines))

    # Update cache
    cache["seen"] = list(seen_keys)
    save_cache(cache)
    # Empty stdout when nothing new → silent cron tick


if __name__ == "__main__":
    main()
