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
import time
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT = CACHE / 'sprt-measurement-tamper.json'
H1 = 4.0



SHADOW_MAX_AGE_SEC = 90 * 60


def _shadow_stale() -> dict | None:
    """Refuse to certify yesterday's shadow-sprt-decisions.json (mtime > 90 min).
    Fail-closed: stale shadow means the tamper check cannot run — treat as alarm=True,
    not alarm=False. The bridge skips any source whose report is missing/stale;
    emitting alarm=False would silently clear the sidecar.
    """
    p = CACHE / 'shadow-sprt-decisions.json'
    try:
        age = time.time() - p.stat().st_mtime
    except OSError:
        age = float('inf')
    if age > SHADOW_MAX_AGE_SEC:
        return {
            'status': 'shadow_stale',
            'alarm': True,
            'alarm_reason': f'shadow_stale: shadow-sprt-decisions.json age={age:.0f}s > {SHADOW_MAX_AGE_SEC}s',
            'skipped': True,
        }
    return None


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def detect(
    scores: list[float],
    n_zero_err: int,
    n_turns: int,
    n_sampled: int | None = None,
    n_zero_sampled: int | None = None,
) -> dict:
    scores = [s for s in scores if s is not None]
    n_sampled = n_turns if n_sampled is None else n_sampled
    n_zero_sampled = n_zero_err if n_zero_sampled is None else n_zero_sampled
    flags = []
    if len(scores) >= 8:
        var = statistics.pvariance(scores)
        if var < 1e-12:
            flags.append('zero_variance')
        if all(abs(s - H1) < 1e-9 for s in scores):
            flags.append('all_equal_h1')
        mean = statistics.mean(scores)
        # collapsed_at_h1: enough numeric scores, near-zero variance, mean near H1
        if var < 0.001 and abs(mean - H1) < 0.05:
            flags.append('collapsed_at_h1')
    # W24-ADV-006: identically-zero uses sampled turns only (errors/error/had_error present)
    if n_sampled >= 8 and n_zero_sampled == n_sampled:
        flags.append('identically_zero_error_rate')
    return {
        'n_scores': len(scores),
        'n_scores_numeric': len(scores),
        'n_turns': n_turns,
        'n_zero_err': n_zero_err,
        'n_zero': n_zero_err,
        'n_sampled': n_sampled,
        'n_zero_sampled': n_zero_sampled,
        'variance': statistics.pvariance(scores) if len(scores) >= 2 else None,
        'flags': flags,
        'alarm': len(flags) > 0,
        'theorem': 'Hendrycks measurement tampering; Amodei reward hacking of outer SPRT',
    }


def _extract_numeric_scores(obj: dict) -> list[float]:
    """Collect non-None numeric scores from top-level 'score' and 'scores' dict."""
    raw: list[float] = []
    s = obj.get('score')
    if s is not None and isinstance(s, (int, float)) and not isinstance(s, bool):
        raw.append(float(s))
    s_dict = obj.get('scores')
    if isinstance(s_dict, dict):
        for v in s_dict.values():
            if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool):
                raw.append(float(v))
    return [x for x in raw if x is not None]


def _row_sample_error(obj: dict) -> tuple[bool, bool]:
    """Return (sampled, zero_error). Unsampled rows have no error evidence either way."""
    sampled = ('errors' in obj) or ('error' in obj) or ('had_error' in obj)
    if not sampled:
        return False, False
    if 'errors' in obj:
        return True, not obj.get('errors')
    err = obj.get('error')
    had_err = obj.get('had_error')
    zero = err in (0, False) or had_err in (0, False)
    return True, zero


def _load_scores() -> tuple[list[float], int, int, int, int]:
    scores: list[float] = []
    n_zero = 0
    n = 0
    n_sampled = 0
    n_zero_sampled = 0
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
            n += 1
            scores.extend(_extract_numeric_scores(obj))
            sampled, zero_s = _row_sample_error(obj)
            if sampled:
                n_sampled += 1
                if zero_s:
                    n_zero_sampled += 1
                    n_zero += 1
            else:
                # Back-compat n_zero: explicit error_rate==0 still counts as zero-err
                # but does NOT count as sampled (no errors/error/had_error key).
                if obj.get('error_rate') == 0:
                    n_zero += 1
        if scores or n:
            break
    scores = [s for s in scores if s is not None]
    return scores, n_zero, n, n_sampled, n_zero_sampled


def run() -> dict:
    stale = _shadow_stale()
    if stale is not None:
        stale['ts'] = datetime.now(timezone.utc).isoformat()
        try:
            _atomic_write(OUT, stale)
            stale['output'] = str(OUT)
        except OSError as exc:
            stale['write_error'] = str(exc)
        return stale
    scores, n_zero, n, n_sampled, n_zero_sampled = _load_scores()
    out = detect(scores, n_zero, n, n_sampled=n_sampled, n_zero_sampled=n_zero_sampled)
    out['ts'] = datetime.now(timezone.utc).isoformat()
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
    # W24-ADV-006: unsampled rows must not dilute the identically-zero denominator
    r3 = detect([3.0] * 8, n_zero_err=8, n_turns=100, n_sampled=8, n_zero_sampled=8)
    if 'identically_zero_error_rate' not in r3['flags']:
        failures.append(f'sampled-only identically_zero should fire, got {r3}')
    r4 = detect([3.0] * 8, n_zero_err=8, n_turns=100, n_sampled=8, n_zero_sampled=7)
    if 'identically_zero_error_rate' in r4['flags']:
        failures.append(f'partial sampled zeros should not fire identically_zero, got {r4}')
    r5 = detect([3.0] * 8, n_zero_err=3, n_turns=100, n_sampled=3, n_zero_sampled=3)
    if 'identically_zero_error_rate' in r5['flags']:
        failures.append(f'n_sampled<8 must not fire identically_zero, got {r5}')
    # W24-ADV-007: None-filtered scores dict values can populate variance
    extracted = _extract_numeric_scores({
        'score': None,
        'scores': {'a': None, 'b': 4.0, 'c': 4.0, 'd': None},
    })
    if extracted != [4.0, 4.0]:
        failures.append(f'scores dict extraction, got {extracted}')
    collapsed = detect([4.0] * 8 + [None], 0, 8, n_sampled=0, n_zero_sampled=0)  # type: ignore[list-item]
    if 'collapsed_at_h1' not in collapsed['flags'] or collapsed.get('n_scores_numeric') != 8:
        failures.append(f'collapsed_at_h1 should fire on numeric scores, got {collapsed}')
    sampled, zero = _row_sample_error({'foo': 1})
    if sampled or zero:
        failures.append(f'unsampled row should be (False, False), got {(sampled, zero)}')
    sampled, zero = _row_sample_error({'errors': []})
    if not sampled or not zero:
        failures.append(f'empty errors list should be sampled zero, got {(sampled, zero)}')
    sampled, zero = _row_sample_error({'errors': ['boom']})
    if not sampled or zero:
        failures.append(f'non-empty errors should be sampled non-zero, got {(sampled, zero)}')
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
    if out.get('status') == 'shadow_stale':
        print(json.dumps({k: out.get(k) for k in ('status', 'alarm', 'alarm_reason', 'skipped')}))
        return 0
    print(json.dumps({k: out.get(k) for k in (
        'n_scores', 'n_scores_numeric', 'n_turns', 'n_zero', 'n_sampled',
        'n_zero_sampled', 'flags', 'alarm', 'output',
    )}))
    return 1 if out.get('write_error') else 0  # ADV2-017: alarm is not a process failure


if __name__ == '__main__':
    sys.exit(main())
