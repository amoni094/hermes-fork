#!/usr/bin/env python3
"""routing-skill-markov.py — bigram skill-transition entropy from calibration-log.

P(s_t | s_{t-1}) MLE. Alarm if max self-loop > 0.8 (router stuck) or H(next|prev) < 0.5 bits
with n_trans>=20 (collapsed dialogue state).

Source: Jurafsky & Martin, Speech and Language Processing (N-gram / HMM).
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
import time
from collections import defaultdict, deque, Counter
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

EPS = 1e-15


def _cache_dir() -> Path:
    override = os.environ.get('HERMES_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write_json(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n')
        os.replace(str(tmp), str(path))
    except Exception:
        try:
            tmp = path.with_suffix(path.suffix + '.tmp')
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, FileNotFoundError, json.JSONDecodeError):
        return default

SELF_LOOP = 0.8
H_MIN = 0.15
N_MIN = 20


def _load_jsonl(path):
    rows = []
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except (OSError, FileNotFoundError):
        pass
    return rows


def entropy(probs):
    h = 0.0
    for p in probs:
        if p > 0:
            h -= p * math.log2(p)
    return h


def compute(rows):
    seq = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        s = r.get('skill') or r.get('chosen') or r.get('top1') or r.get('name')
        if s:
            seq.append(str(s))
    trans = defaultdict(Counter)
    for a, b in zip(seq, seq[1:]):
        trans[a][b] += 1
    n_trans = sum(sum(c.values()) for c in trans.values())
    self_max, self_skill = 0.0, None
    cond_h = []
    for a, c in trans.items():
        tot = sum(c.values()) or 1
        pself = c.get(a, 0) / tot
        if pself > self_max:
            self_max, self_skill = pself, a
        cond_h.append(entropy([v / tot for v in c.values()]))
    h = sum(cond_h) / len(cond_h) if cond_h else 0.0
    alarm = False
    reason = 'ok'
    if n_trans >= N_MIN and self_max > SELF_LOOP:
        alarm, reason = True, 'stuck_self_loop'
    elif n_trans >= N_MIN and h < H_MIN:
        alarm, reason = True, 'collapsed_state'
    return {
        'ts': time.time(),
        'n_events': len(seq),
        'n_transitions': n_trans,
        'max_self_loop': round(self_max, 6),
        'self_loop_skill': self_skill,
        'H_next_given_prev': round(h, 6),
        'alarm': alarm,
        'reason': reason,
    }


def run(cache=None):
    cache = cache or _cache_dir()
    rows = _load_jsonl(cache / 'calibration-log.jsonl')
    if not rows:
        rows = _load_jsonl(cache / 'routing-calibration.jsonl')
    result = compute(rows)
    try:
        _atomic_write_json(cache / 'routing-skill-markov.json', result)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        rows = [{'skill': 'a'}] * 30
        r = compute(rows)
        assert r['alarm'] is True
        assert r['max_self_loop'] == 1.0
    except Exception as e:
        failures.append(f'stuck: {e}')
    try:
        rows = []
        for i in range(20):
            rows.append({'skill': 'a'})
            rows.append({'skill': 'b' if i % 2 == 0 else 'c'})
        r = compute(rows)
        assert r['alarm'] is False
        assert r['max_self_loop'] < 0.5
        assert r['n_transitions'] >= 20
    except Exception as e:
        failures.append(f'alt: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d)
            assert (d / 'routing-skill-markov.json').exists()
    except Exception as e:
        failures.append(f'io: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        print(json.dumps(run(), indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
