#!/usr/bin/env python3
"""math-prefetch-abstracts.py — Pre-populate math sweep JSON with titles + abstracts.

Reads hermes-math-sweep-latest.json, fetches missing titles/abstracts from arXiv
using concurrent threads, then writes the enriched data back in-place.

Run this BEFORE math-paper-interpreter.py so the interpreter can run without
--fetch-abstracts (which is sequential and times out at 75 papers).

Concurrency: 8 threads, 0.1s inter-thread stagger, 15s per-request timeout.
75 papers × ~5s avg fetch / 8 threads ≈ 50s total. Safe under any cron budget.

Usage:
  python3 math-prefetch-abstracts.py [--input PATH] [--limit N] [--workers N]
  python3 math-prefetch-abstracts.py --dry-run   # show what would be fetched, no writes
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CACHE = Path.home() / ".hermes" / "cache" / "research"
SWEEP_LATEST = CACHE / "hermes-math-sweep-latest.json"

_ARXIV_RE = re.compile(r'(\d{4}\.\d{4,5})')
_TITLE_RE = re.compile(r'<h1 class="title[^"]*"[^>]*>(?:Title:)?\s*(.*?)</h1>', re.DOTALL)
_ABS_RE   = re.compile(r'<blockquote class="abstract[^"]*"[^>]*>(?:Abstract:)?\s*(.*?)</blockquote>', re.DOTALL)
_TAG_RE   = re.compile(r'<[^>]+>')

_stagger_lock = threading.Lock()
_stagger_count = 0


def fetch_abstract(arxiv_id: str, retries: int = 2) -> dict:
    """Fetch title + abstract from arXiv abs page. Returns {title, abstract}."""
    url = f"https://export.arxiv.org/abs/{arxiv_id}"
    headers = {"User-Agent": "hermes-math-prefetch/1.0 (research tool)"}
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            title_m = _TITLE_RE.search(html)
            abs_m   = _ABS_RE.search(html)
            title    = _TAG_RE.sub("", title_m.group(1)).strip() if title_m else ""
            abstract = _TAG_RE.sub("", abs_m.group(1)).strip()   if abs_m   else ""
            return {"title": title, "abstract": abstract}
        except (URLError, HTTPError, OSError) as exc:
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
            else:
                return {"title": "", "abstract": "", "error": str(exc)}
    return {"title": "", "abstract": ""}


def _worker(idx: int, paper: dict, stagger_s: float) -> tuple[int, dict]:
    """Thread worker: stagger start, fetch, return (idx, enriched_paper)."""
    global _stagger_count
    with _stagger_lock:
        my_slot = _stagger_count
        _stagger_count += 1
    time.sleep(my_slot * stagger_s)

    arxiv_id = None
    for field in ("id", "url"):
        m = _ARXIV_RE.search(str(paper.get(field, "") or ""))
        if m:
            arxiv_id = m.group(1)
            break

    if not arxiv_id:
        return idx, paper  # nothing to fetch

    already_has = bool(paper.get("title")) and bool(paper.get("abstract"))
    if already_has:
        return idx, paper  # already populated

    fetched = fetch_abstract(arxiv_id)
    enriched = dict(paper)
    if fetched["title"]:
        enriched["title"] = fetched["title"]
    if fetched["abstract"]:
        enriched["abstract"] = fetched["abstract"]
    return idx, enriched


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-fetch arXiv abstracts into math sweep JSON")
    parser.add_argument("--input",   default=str(SWEEP_LATEST), help="Path to sweep JSON")
    parser.add_argument("--limit",   type=int, default=0,       help="Max papers to process (0=all)")
    parser.add_argument("--workers", type=int, default=8,       help="Concurrent fetch threads")
    parser.add_argument("--stagger", type=float, default=0.12,  help="Inter-thread start stagger (s)")
    parser.add_argument("--dry-run", action="store_true",       help="Show what would be fetched, no writes")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[prefetch] ERROR: sweep file not found: {input_path}", file=sys.stderr)
        return 1

    sweep = json.loads(input_path.read_text())
    flat: list[dict] = sweep.get("new_papers_flat", [])
    total = len(flat)
    print(f"[prefetch] {total} papers in sweep", file=sys.stderr)

    # Identify which need fetching
    need_fetch = [
        (i, p) for i, p in enumerate(flat)
        if not (p.get("title") and p.get("abstract"))
    ]
    print(f"[prefetch] {len(need_fetch)} papers missing title/abstract", file=sys.stderr)

    if args.limit:
        need_fetch = need_fetch[:args.limit]
        print(f"[prefetch] Limited to {args.limit} papers", file=sys.stderr)

    if args.dry_run:
        print(f"[prefetch] DRY RUN — would fetch {len(need_fetch)} abstracts")
        for i, p in need_fetch[:10]:
            pid = p.get("id", p.get("url", "?"))
            print(f"  [{i}] {pid} | cat={p.get('category','?')}")
        if len(need_fetch) > 10:
            print(f"  ... and {len(need_fetch)-10} more")
        return 0

    if not need_fetch:
        print("[prefetch] All papers already have titles/abstracts — nothing to do", file=sys.stderr)
        return 0

    print(f"[prefetch] Fetching {len(need_fetch)} abstracts with {args.workers} workers "
          f"(stagger={args.stagger}s)...", file=sys.stderr)

    t0 = time.time()
    enriched_map: dict[int, dict] = {}
    fetch_ok = 0
    fetch_err = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_worker, i, p, args.stagger): i
            for i, p in need_fetch
        }
        done = 0
        for fut in as_completed(futures):
            done += 1
            if done % 10 == 0 or done == len(need_fetch):
                elapsed = time.time() - t0
                print(f"[prefetch] {done}/{len(need_fetch)} done ({elapsed:.0f}s elapsed)", file=sys.stderr)
            try:
                idx, enriched = fut.result()
                enriched_map[idx] = enriched
                if enriched.get("abstract"):
                    fetch_ok += 1
                else:
                    fetch_err += 1
            except Exception as exc:
                orig_idx = futures[fut]
                enriched_map[orig_idx] = need_fetch[orig_idx][1]  # keep original
                fetch_err += 1
                print(f"[prefetch] Worker error at idx {orig_idx}: {exc}", file=sys.stderr)

    # Apply enrichment back to flat list
    new_flat = list(flat)
    for idx, enriched in enriched_map.items():
        new_flat[idx] = enriched

    elapsed = time.time() - t0
    print(f"[prefetch] Done: {fetch_ok} fetched, {fetch_err} errors, {elapsed:.1f}s total", file=sys.stderr)

    # Write back
    sweep["new_papers_flat"] = new_flat
    sweep["prefetch_date"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).isoformat()
    input_path.write_text(json.dumps(sweep, indent=2, default=str))
    print(f"[prefetch] Written: {input_path}", file=sys.stderr)

    # Summary
    has_abstract = sum(1 for p in new_flat if p.get("abstract"))
    print(f"[prefetch] Coverage: {has_abstract}/{len(new_flat)} papers now have abstracts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
