#!/usr/bin/env python3
"""sprt-measurement-tamper.py — Hendrycks/Amodei measurement tampering on SPRT.

If scores have zero variance, are all equal to the H1 mean, or error_rate
is identically 0 across many turns, treat as possible reward hacking of
the sequential test (inner optimiser gaming the outer SPRT).

Usage:
  python3 sprt-measurement-tamper.py --self-test
  python3 sprt-measurement-tamper.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT = CACHE / 'sprt-measurement-tamper.json'
H1 = 4.0


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def detect(scores: list[float], n_zero_err: int, n_turns: int) -> dict:
    flags = []
    if len(scores) >= 8:
        var = statistics.pvariance(scores)
        if var < 1e-12:
            flags.append('zero_variance')
        if all(abs(s - H1) < 1e-9 for s in scores):
            flags.append('all_equal_h1')
        mean = statistics.mean(scores)
        if mean >= H1 - 1e-9 and var < 0.01:
            flags.append('collapsed_at_h1')
    # None-score rows are not numeric evidence; require real scores.
    if len(scores) >= 8 and n_turns >= 8 and n_zero_err == n_turns:
        flags.append('identically_zero_error_rate')
    return {
        'n_scores': len(scores),
        'n_turns': n_turns,
        'n_zero_err': n_zero_err,
        'variance': statistics.pvariance(scores) if len(scores) >= 2 else None,
        'flags': flags,
        'alarm': len(flags) > 0,
        'theorem': 'Hendrycks measurement tampering; Amodei reward hacking of outer SPRT',
    }


def _load_scores() -> tuple[list[float], int, int]:
    scores: list[float] = []
    n_zero = 0
    n = 0
    for p in (
        CACHE / 'jev-turn-scores.jsonl',
        _hermes_base / 'cache' / 'jev-turn-scores.jsonl',
        _hermes_root / 'logs' / 'jev-turn-scores.jsonl',
    ):
        try:
            lines = p.read_text(encoding='utf-8').splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            scores_dict = obj.get('scores')
            if isinstance(scores_dict, dict) and all(v is None for v in scores_dict.values()):
                # Insufficient data, not zero-error. Skip entirely.
                continue
            n += 1
            s = obj.get('score')
            if isinstance(s, (int, float)) and not isinstance(s, bool):
                scores.append(float(s))
            has_numeric = isinstance(s, (int, float)) and not isinstance(s, bool)
            if isinstance(scores_dict, dict) and any(
                v is not None and isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in scores_dict.values()
            ):
                has_numeric = True
            err = obj.get('error') if 'error' in obj else obj.get('had_error')
            # None means unscored, not zero errors.
            if has_numeric and (err in (0, False) or obj.get('error_rate') == 0):
                n_zero += 1
        # First readable jsonl is canonical (even if all rows were None-scored).
        break
    return scores, n_zero, n


def run() -> dict:
    scores, n_zero, n = _load_scores()
    out = detect(scores, n_zero, n)
    out['ts'] = datetime.now(UTC).isoformat()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    r = detect([4.0] * 10, 10, 10)
    if not r['alarm'] or 'all_equal_h1' not in r['flags']:
        failures.append(str(r))
    r2 = detect([3.0, 4.0, 2.0, 5.0, 3.5, 4.2, 2.8, 3.9], 3, 8)
    if r2['alarm']:
        failures.append(f'natural spread {r2}')
    r3 = detect([], 5306, 5306)
    if r3['alarm'] or 'identically_zero_error_rate' in r3['flags']:
        failures.append(f'no numeric scores must not identically_zero {r3}')
    r4 = detect([3.1, 3.9, 2.5, 4.2, 3.3, 4.0, 2.8, 3.7], 8, 8)
    if 'identically_zero_error_rate' not in r4['flags']:
        failures.append(f'numeric scores with explicit zero-err should flag {r4}')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS'}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({k: out.get(k) for k in ('n_scores', 'flags', 'alarm', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
