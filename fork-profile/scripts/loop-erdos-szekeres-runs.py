#!/usr/bin/env python3
"""loop-erdos-szekeres-runs.py — Erdos-Szekeres LIS/LDS flags on loop runs.

Any sequence of n > (r-1)*(s-1) distinct values has LIS >= r or LDS >= s.
LIS via patience sort (O(n log n)); LDS = LIS of negated sequence.
"""
from __future__ import annotations

import bisect
import json
import os
import random
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

home = os.environ.get('HERMES_HOME', '')
home = home.removesuffix('/profiles/fork')
if not home:
    home = os.path.expanduser('~/.hermes')
profile_dir = home + '/profiles/fork'
CACHE = Path(profile_dir) / 'cache'
OUT_PATH = CACHE / 'erdos-szekeres-runs.json'

R_THRESHOLD = 5


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _to_float(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except Exception:
            return None
    return None


def lis_len(seq) -> int:
    """Patience-sort LIS length (strictly increasing). O(n log n)."""
    tails = []
    for x in seq:
        i = bisect.bisect_left(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return len(tails)


def lds_len(seq) -> int:
    """LDS length = LIS of negated sequence."""
    return lis_len([-x for x in seq])


def lis_len_dp(seq) -> int:
    """O(n^2) DP LIS for verification."""
    n = len(seq)
    if n == 0:
        return 0
    dp = [1] * n
    for i in range(n):
        xi = seq[i]
        best = 1
        for j in range(i):
            if seq[j] < xi:
                cand = dp[j] + 1
                best = max(best, cand)
        dp[i] = best
    return max(dp)


def _extract_value(rec: dict):
    for key in ('predicted_confidence', 'score', 'ue_score'):
        v = _to_float(rec.get(key))
        if v is not None:
            return v
    return None


MAX_LINES_CAL = 10000  # cap calibration-log to avoid reading 168k lines every hour


def _load_jsonl(path: Path, max_lines: int = 0) -> list[dict]:
    recs = []
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return recs
    lines = text.splitlines()
    if max_lines > 0 and len(lines) > max_lines:
        lines = lines[-max_lines:]
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            recs.append(obj)
    return recs


def _flag(lis_n: int, lds_n: int, r: int) -> str | None:
    imp = lis_n >= r
    deg = lds_n >= r
    if imp and deg:
        return 'BOTH'
    if imp:
        return 'IMPROVING'
    if deg:
        return 'DEGRADING'
    return None


def analyze_sequence(values, session_id, r_threshold: int = R_THRESHOLD) -> dict:
    lis_n = lis_len(values)
    lds_n = lds_len(values)
    return {
        'session_id': session_id,
        'lis_len': lis_n,
        'lds_len': lds_n,
        'flag': _flag(lis_n, lds_n, r_threshold),
    }


def _sessions_from_calibration(r_threshold: int) -> list[dict]:
    path = CACHE / 'calibration-log.jsonl'
    recs = _load_jsonl(path, max_lines=MAX_LINES_CAL) if path.is_file() else []
    if not recs:
        return []
    has_sid = any(isinstance(r.get('session_id'), str) and r.get('session_id') for r in recs)
    groups: dict[str, list[float]] = {}
    order: list[str] = []
    if has_sid:
        for rec in recs:
            sid = rec.get('session_id')
            if not isinstance(sid, str) or not sid:
                continue
            v = _extract_value(rec)
            if v is None:
                continue
            if sid not in groups:
                groups[sid] = []
                order.append(sid)
            groups[sid].append(v)
    else:
        vals = []
        for rec in recs:
            v = _extract_value(rec)
            if v is not None:
                vals.append(v)
        if vals:
            groups['all'] = vals
            order = ['all']
    return [analyze_sequence(groups[sid], sid, r_threshold) for sid in order if groups[sid]]


def _session_from_pid(r_threshold: int) -> dict | None:
    path = CACHE / 'loop-pid-state.json'
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    hist = obj.get('history')
    if not isinstance(hist, list):
        return None
    vals = []
    for x in hist:
        if isinstance(x, dict):
            # loop-pid history entries: {ts, e, u, integrator, measurement?, ...}
            # prefer 'measurement' (setpoint tracking error), then 'u' (control output)
            v = _to_float(x.get('measurement', x.get('u', x.get('e'))))
        else:
            v = _to_float(x)
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    return analyze_sequence(vals, 'loop-pid', r_threshold)


def run(r_threshold: int = R_THRESHOLD) -> dict:
    try:
        sessions = _sessions_from_calibration(r_threshold)
        pid = _session_from_pid(r_threshold)
        if pid is not None:
            sessions.append(pid)
        improving = sum(1 for s in sessions if s.get('flag') in ('IMPROVING', 'BOTH'))
        degrading = sum(1 for s in sessions if s.get('flag') in ('DEGRADING', 'BOTH'))
        result = {
            'sessions': sessions,
            'improving_count': improving,
            'degrading_count': degrading,
            'timestamp': _now(),
        }
        try:
            _atomic_write(OUT_PATH, result)
        except Exception:
            pass
        return result
    except Exception:
        result = {
            'sessions': [],
            'improving_count': 0,
            'degrading_count': 0,
            'timestamp': _now(),
        }
        try:
            _atomic_write(OUT_PATH, result)
        except Exception:
            pass
        return result


def self_test() -> int:
    seq = [3, 1, 4, 1, 5, 9, 2, 6]
    assert lis_len(seq) == 4, lis_len(seq)
    assert lds_len([9, 5, 4, 3, 1]) == 5, lds_len([9, 5, 4, 3, 1])

    rng = random.Random(42)
    r, s = 4, 3
    n = 10
    assert n > (r - 1) * (s - 1)
    for i in range(100):
        seq = list(range(n))
        rng.shuffle(seq)
        ok = lis_len(seq) >= r or lds_len(seq) >= s
        assert ok, (i, seq, lis_len(seq), lds_len(seq))

    rng2 = random.Random(7)
    n20 = [rng2.random() for _ in range(20)]
    assert lis_len(n20) == lis_len_dp(n20), (lis_len(n20), lis_len_dp(n20))
    assert lds_len(n20) == lis_len_dp([-x for x in n20])

    print('self-test ok', {
        'lis_pi': lis_len(seq),
        'lds_desc': lds_len([9, 5, 4, 3, 1]),
        'es_trials': 100,
        'patience_eq_dp': True,
    })
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if '--self-test' in args:
        try:
            return self_test()
        except AssertionError as e:
            print('self-test FAILED:', e, file=sys.stderr)
            return 1
        except Exception as e:
            print('self-test ERROR:', type(e).__name__, e, file=sys.stderr)
            return 1
    result = run()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
