#!/usr/bin/env python3
"""context-heat-kernel.py — 1-D heat equation kernel for position-weighted compaction.

Theory (3B1B DE series): Heat diffuses from query anchor outward.
w_i = exp(-(i-q)^2 / (4*kappa*t)) / Z. Near t->0: concentrated at q.
Large t: near-uniform. Low-weight segments = compact candidates.
"""
from __future__ import annotations
import argparse, json, math, os, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'context-heat-kernel.json'
KAPPA = 1.0
T_DEFAULT = 2.0
EPS = 0.02
SESSIONS_DIR = _root / 'sessions'

def heat_weights(n, q, kappa=KAPPA, t=T_DEFAULT):
    t = max(t, 1e-9)
    s = 4.0 * kappa * t
    raw = [math.exp(-((i - q) ** 2) / s) for i in range(n)]
    z = sum(raw) or 1.0
    return [x / z for x in raw]

def annotate(n, q, kappa=KAPPA, t=T_DEFAULT, eps=EPS):
    ws = heat_weights(n, q, kappa, t)
    return [{'i': i, 'w': round(w, 6), 'dilute': w < eps} for i, w in enumerate(ws)]

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def _load_latest_session():
    """Return segment count from newest *.json or *.jsonl session. 0 if none."""
    files = []
    for pattern in ('*.json', '*.jsonl'):
        for f in SESSIONS_DIR.glob(pattern):
            try:
                files.append((f.stat().st_mtime, f))
            except Exception:
                pass
    if not files:
        return 0
    files.sort(reverse=True)
    latest = files[0][1]
    try:
        text = latest.read_text('utf-8', errors='replace')
        if latest.suffix == '.jsonl':
            n = 0
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    n += 1
            return n
        data = json.loads(text)
        msgs = data if isinstance(data, list) else data.get('messages', [])
        return len([m for m in msgs if isinstance(m, dict)])
    except Exception:
        return 0


def run(dry_run=False):
    n_seg = _load_latest_session()
    if n_seg == 0:
        if not dry_run:
            result = {'ts': int(time.time()), 'n_segments': 0, 'error': 'no session found'}
            _atomic_write(OUT, result)
        return {'ts': int(time.time()), 'n_segments': 0}
    q = max(0, n_seg - 1)  # anchor = last segment
    segs = annotate(n_seg, q)
    result = {'ts': int(time.time()), 'n_segments': n_seg, 'q': q,
              'kappa': KAPPA, 't': T_DEFAULT, 'segments': segs}
    if not dry_run: _atomic_write(OUT, result)
    return result

def self_test():
    # Concentrated: t near 0, q=5 in n=11
    ws = heat_weights(11, 5, kappa=1.0, t=0.001)
    assert abs(sum(ws) - 1.0) < 1e-9, f"sum!=1: {sum(ws)}"
    assert ws[5] > 0.9, f"w[5] not concentrated: {ws[5]}"
    assert ws.index(max(ws)) == 5

    # Monotone: for t=1.0, w[|i-5|] non-increasing
    ws2 = heat_weights(11, 5, kappa=1.0, t=1.0)
    for d in range(1, 6):
        assert ws2[5-d] <= ws2[5-d+1] + 1e-12, f"not monotone at d={d}"
        assert ws2[5+d] <= ws2[5+d-1] + 1e-12, f"not monotone at d={d} (right)"

    # Near-uniform: large t
    ws3 = heat_weights(11, 5, kappa=1.0, t=100.0)
    assert abs(sum(ws3) - 1.0) < 1e-9
    assert max(ws3) - min(ws3) < 0.05, f"not near-uniform: range={max(ws3)-min(ws3)}"

    # sum=1 always
    for t in [0.01, 1.0, 10.0]:
        w = heat_weights(5, 2, t=t)
        assert abs(sum(w) - 1.0) < 1e-9, f"sum!=1 at t={t}"

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--kappa', type=float, default=KAPPA)
    p.add_argument('--t', type=float, default=T_DEFAULT)
    args = p.parse_args()
    if args.self_test: self_test(); return
    print(json.dumps(run(args.dry_run), indent=2))

if __name__ == '__main__': main()
