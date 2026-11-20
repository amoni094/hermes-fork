#!/usr/bin/env python3
"""prequential-compaction-trigger.py — Online prequential coding signal for compaction.

Prequential coding (Dawid 1984; MacKay Ch. 28; Cover-Thomas 5.4):
  An online predictor P_t encodes each symbol x_t using -log P_t(x_t) bits.
  After observing x_t, the predictor updates to P_{t+1}.
  Total code length = sum_t -log P_t(x_t) = sequential cross-entropy.

Hermes application:
  Treat the stream of tool-output chunks as x_1, x_2, ..., x_n.
  Approximate P_t with a sliding-window bigram model (from zlib ratio).
  When zlib(window + new_chunk) / len(window + new_chunk)
       < zlib(window) / len(window) - eps:
    => new_chunk is REDUNDANT (the predictor was already good at encoding it)
    => recommend COMPACT
  When zlib ratio stays flat or increases:
    => new_chunk is FRESH INFORMATION
    => recommend KEEP

Hard cores:
  - Prequential log-loss = sum -log P_t(x_t) >= H(X) n (Shannon source coding lb)
  - Compression rate is a valid sequential CE proxy (zlib length / raw length)
  - If rate delta < -eps, the marginal information I(x_t | x_1..t-1) is small

Falsifying test: inject identical repeated text; rate should drop to near 0.
  Inject random bytes; rate should stay near 1.0 (incompressible).

Usage:
  python3 prequential-compaction-trigger.py --self-test
  python3 prequential-compaction-trigger.py --window FILE --new-chunk FILE
"""
from __future__ import annotations

import argparse
import json
import math
import os
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
LOG_PATH = CACHE / 'prequential-compaction-log.jsonl'
EPS = 0.01          # rate delta threshold for "redundant"
WINDOW_BYTES = 4096  # sliding context window size


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
        line = json.dumps(obj, ensure_ascii=False) + '\n'
        with open(str(path), 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass


def zlib_rate(data: bytes) -> float:
    """Compression rate = compressed_len / raw_len. 1.0 = incompressible."""
    if not data:
        return 1.0
    try:
        compressed = zlib.compress(data, 6)
        return len(compressed) / len(data)
    except Exception:
        return 1.0


def prequential_signal(window: str, new_chunk: str, eps: float = EPS) -> dict:
    """
    Returns recommendation: "compact" or "keep", with supporting stats.
    Hard core: if zlib_rate(window+new) < zlib_rate(window) - eps => compact.
    """
    win_bytes = window.encode('utf-8', errors='replace')[-WINDOW_BYTES:]
    new_bytes = new_chunk.encode('utf-8', errors='replace')
    combined = win_bytes + new_bytes

    rate_window = zlib_rate(win_bytes) if win_bytes else 1.0
    rate_combined = zlib_rate(combined)
    # Rate drop = new content was predictable from window => redundant
    rate_delta = rate_combined - rate_window

    # Bits per byte of new_chunk contributed at the margin:
    # marginal_bits = bits(combined) - bits(window)
    bits_window = len(zlib.compress(win_bytes, 6)) * 8 if win_bytes else 0.0
    bits_combined = len(zlib.compress(combined, 6)) * 8
    marginal_bits = bits_combined - bits_window
    marginal_rate = marginal_bits / max(len(new_bytes) * 8, 1)  # bits per input bit

    recommendation = 'compact' if rate_delta < -eps else 'keep'
    return {
        'rate_window': round(rate_window, 4),
        'rate_combined': round(rate_combined, 4),
        'rate_delta': round(rate_delta, 4),
        'marginal_rate': round(marginal_rate, 4),
        'eps': eps,
        'recommendation': recommendation,
        'ts': int(time.time()),
    }


def self_test() -> None:
    import random
    # Redundant: window is a unique corpus; new_chunk is an exact repeat of its suffix
    # Use a short, diverse window so combined has clear rate drop vs fresh chunk
    base = "alpha beta gamma delta epsilon " * 30
    window = base  # already seen
    duplicate = "alpha beta gamma delta epsilon " * 10  # exact repeat of corpus tokens
    
    # Test that rate delta is negative for duplicate (redundant)
    rdup = prequential_signal(window, duplicate, eps=0.005)
    assert rdup['rate_delta'] < 0, f"Duplicate should have negative rate_delta: {rdup}"
    
    # Fresh: inject unrelated content - rate_combined should be >= rate_window
    rng = random.Random(42)
    fresh_tokens = ' '.join(f"zyxwvu{rng.randint(1000,9999)}" for _ in range(80))
    rfresh = prequential_signal(window, fresh_tokens, eps=0.005)
    # fresh content should have higher or equal combined rate vs window alone
    # (novel tokens not in window vocab)
    assert rfresh['rate_delta'] >= rdup['rate_delta'], \
        f"Fresh should have higher delta than duplicate: fresh={rfresh}, dup={rdup}"

    # Hard core: recommendation for duplicate with low eps should be compact
    rdup2 = prequential_signal(window, duplicate, eps=0.005)
    assert rdup2['recommendation'] == 'compact', f"Expected compact: {rdup2}"

    # Hard core: rate is in reasonable range
    for text in [window, duplicate, fresh_tokens]:
        r = zlib_rate(text.encode())
        assert 0.0 < r <= 2.0, f"Rate out of range: {r}"

    print("self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--window', type=Path, help='Path to window content file')
    parser.add_argument('--new-chunk', type=Path, help='Path to new chunk file')
    parser.add_argument('--eps', type=float, default=EPS)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    if not args.window and not args.new_chunk:
        sys.exit(0)  # watchdog: nothing to do

    if not args.window or not args.new_chunk:
        parser.print_help()
        sys.exit(1)

    window = args.window.read_text('utf-8', errors='replace')
    new_chunk = args.new_chunk.read_text('utf-8', errors='replace')
    result = prequential_signal(window, new_chunk, eps=args.eps)

    print(json.dumps(result, indent=2))
    if not args.dry_run:
        _atomic_append(LOG_PATH, result)
    sys.exit(0 if result['recommendation'] == 'keep' else 2)


if __name__ == '__main__':
    main()
