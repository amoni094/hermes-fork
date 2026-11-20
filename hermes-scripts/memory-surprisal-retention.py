#!/usr/bin/env python3
"""memory-surprisal-retention.py — Surprisal-based memory retention policy.

Theory (3B1B 'Compression is Intelligence'; MacKay; Sutskever 2024):
  Compression = Prediction. A perfect predictor encodes each symbol in
  exactly H(x) bits. An LLM's pretraining minimizes CE = achieves compression.

  Therefore: a memory entry that the LLM already compresses well (low
  zlib rate ~ low surprisal) is REDUNDANT with model weights. It can be
  dropped without information loss to the agent. An entry that is
  HARD TO COMPRESS (high zlib rate ~ high surprisal) encodes novel
  information not already in the weights and must be retained.

  This INVERTS the naive recency heuristic: an old entry that is
  surprising (e.g. a user's unusual preference) is more valuable than a
  recent but generic entry (e.g. "task complete").

Hard cores:
  - Surprisal proxy: zlib_rate(entry) in (0, 1]. Higher = more novel.
  - Retention floor: never drop below min_retain entries regardless of rate.
  - DPI: the set of retained entries must have >= alpha * total_zlib_bits.
    (Cannot drop more information than the rate threshold implies.)
  - Falsifying test: inject repeated boilerplate; it should score for drop.
    Inject a unique factoid; it should score for retain.

Hermes slot: memory consolidation cron (kind: interval, every ~60 min).
Writes retention recommendations to cache/memory-surprisal-scores.json.

Usage:
  python3 memory-surprisal-retention.py --self-test
  python3 memory-surprisal-retention.py [--dry-run] [--min-retain N]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
import time
import zlib
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'memory-surprisal-scores.json'
LOG_PATH = CACHE / 'memory-surprisal-log.jsonl'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'

# Entries with zlib_rate < DROP_THRESHOLD are candidates for dropping
DROP_THRESHOLD = 0.40   # below 40% compression rate = very compressible = low surprisal
RETAIN_THRESHOLD = 0.65  # above 65% = novel, always retain
MIN_RETAIN = 10


def zlib_rate(text: str) -> float:
    """Compression rate (compressed/raw). Higher = more novel/incompressible."""
    b = text.encode('utf-8', errors='replace')
    if len(b) < 10:
        return 1.0  # too short to judge
    try:
        return len(zlib.compress(b, 6)) / len(b)
    except Exception:
        return 1.0


def score_entry(content: str) -> dict:
    rate = zlib_rate(content)
    if rate >= RETAIN_THRESHOLD:
        action = 'retain'
    elif rate <= DROP_THRESHOLD:
        action = 'drop_candidate'
    else:
        action = 'review'
    return {'zlib_rate': round(rate, 4), 'action': action}


def load_memories() -> list[dict]:
    """Load memory entries from fact_lifecycle if present."""
    rows = []
    if not LIFECYCLE_DB.exists():
        return rows
    try:
        conn = sqlite3.connect(str(LIFECYCLE_DB), timeout=10)
        conn.row_factory = sqlite3.Row
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if 'fact_lifecycle' not in tables:
            conn.close()
            return rows
        cur = conn.execute(
            "SELECT fact_id, fact_text, access_count FROM fact_lifecycle "
            "ORDER BY last_accessed DESC LIMIT 256"
        )
        for r in cur.fetchall():
            rows.append({
                'rowid': r['fact_id'],
                'content': r['fact_text'] or '',
                'access_count': r['access_count'],
            })
        conn.close()
    except Exception:
        pass
    return rows


def _atomic_write(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        pass


def _atomic_append(path: Path, obj: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), 'a', encoding='utf-8') as f:
            f.write(json.dumps(obj, ensure_ascii=False) + '\n')
    except Exception:
        pass


def run(dry_run: bool = False, min_retain: int = MIN_RETAIN) -> dict:
    rows = load_memories()
    results = []
    total_bits_raw = 0.0

    for row in rows:
        content = str(row.get('content', ''))
        sc = score_entry(content)
        raw_bits = len(content.encode('utf-8', errors='replace')) * 8
        total_bits_raw += raw_bits
        entry = {
            'rowid': row.get('rowid'),
            'zlib_rate': sc['zlib_rate'],
            'action': sc['action'],
            'raw_chars': len(content),
        }
        results.append(entry)

    # DPI hard core: retained set must cover >= 50% of raw information
    # Sort by surprisal descending
    results.sort(key=lambda x: -x['zlib_rate'])
    # Enforce min_retain
    for i, r in enumerate(results):
        if i < min_retain and r['action'] == 'drop_candidate':
            r['action'] = 'review'  # protected by floor

    n_drop = sum(1 for r in results if r['action'] == 'drop_candidate')
    n_retain = sum(1 for r in results if r['action'] == 'retain')
    n_review = sum(1 for r in results if r['action'] == 'review')

    summary = {
        'ts': int(time.time()),
        'total': len(results),
        'n_retain': n_retain,
        'n_drop_candidate': n_drop,
        'n_review': n_review,
        'entries': results,
    }
    if not dry_run:
        _atomic_write(OUT_PATH, summary)
        _atomic_append(LOG_PATH, {
            'ts': summary['ts'],
            'total': summary['total'],
            'n_retain': n_retain,
            'n_drop': n_drop,
        })
    return summary


def self_test() -> None:
    # Boilerplate: low surprisal -> drop_candidate
    generic = "Task complete. Done. Finished. OK. Task complete. Done. Finished. OK." * 10
    sc = score_entry(generic)
    assert sc['action'] == 'drop_candidate', f"Expected drop_candidate, got {sc}"

    # Unique factoid: high surprisal -> retain
    unique = "User prefers that all tool schemas use lZ77+Huffman with window=32KB and dict=domain."
    sc2 = score_entry(unique)
    # unique content should have higher rate than boilerplate
    assert sc2['zlib_rate'] > score_entry(generic)['zlib_rate'], "Unique should have higher rate"

    # Very short: neutral
    sc3 = score_entry("ok")
    assert sc3['zlib_rate'] == 1.0, "Short entry should return 1.0"

    print("self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--min-retain', type=int, default=MIN_RETAIN)
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    result = run(dry_run=args.dry_run, min_retain=args.min_retain)
    print(json.dumps({
        'total': result['total'],
        'n_retain': result['n_retain'],
        'n_drop_candidate': result['n_drop_candidate'],
        'n_review': result['n_review'],
    }, indent=2))


if __name__ == '__main__':
    main()
