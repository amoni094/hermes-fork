#!/usr/bin/env python3
"""Feed anytime eval scores from calibration-log.jsonl into eval-scores.jsonl."""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

import argparse
import fcntl
import json
import sys
import tempfile
import uuid

CACHE = _hermes_root / 'cache'
CALIB = CACHE / 'calibration-log.jsonl'
OUT_PATH = CACHE / 'eval-scores.jsonl'
STATE_PATH = CACHE / 'anytime-eval-feeder-state.json'
DEFAULT_LIMIT = 1000


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            tmp.replace(path)
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {'last_processed_ts': ''}
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'last_processed_ts': ''}
    if not isinstance(obj, dict):
        return {'last_processed_ts': ''}
    return {'last_processed_ts': str(obj.get('last_processed_ts') or '')}


def _clip_score(val) -> float | None:
    try:
        s = float(val)
    except (TypeError, ValueError):
        return None
    if s != s:  # NaN
        return None
    if s < 0.0:
        s = 0.0
    if s > 1.0:
        s = 1.0
    return s


def feed(calib_path: Path, out_path: Path, state_path: Path, limit: int) -> dict:
    if limit <= 0:
        return {'ok': True, 'written': 0, 'skipped': 0, 'insufficient_data': True,
                'reason': 'limit<=0'}
    if not calib_path.exists():
        return {'ok': True, 'written': 0, 'skipped': 0, 'insufficient_data': True,
                'reason': 'missing_calib'}
    state = _load_state(state_path)
    last_ts = state['last_processed_ts']
    written = 0
    skipped = 0
    max_ts = last_ts
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lock = out_path.with_suffix('.lock')
    try:
        with open(str(calib_path), encoding='utf-8', errors='replace') as fh, \
             open(str(lock), 'a', encoding='utf-8') as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                with open(str(out_path), 'a', encoding='utf-8') as out:
                    for line in fh:
                        if written >= limit:
                            break
                        raw = line.strip()
                        if not raw:
                            skipped += 1
                            continue
                        try:
                            rec = json.loads(raw)
                        except json.JSONDecodeError:
                            skipped += 1
                            continue
                        if not isinstance(rec, dict):
                            skipped += 1
                            continue
                        ts = rec.get('ts')
                        if not ts:
                            skipped += 1
                            continue
                        ts = str(ts)
                        if last_ts and ts <= last_ts:
                            skipped += 1
                            continue
                        score = _clip_score(rec.get('predicted_confidence'))
                        if score is None:
                            skipped += 1
                            continue
                        out.write(json.dumps({
                            'ts': ts,
                            'score': score,
                            'source': 'calibration-log',
                        }) + '\n')
                        written += 1
                        if ts > max_ts:
                            max_ts = ts
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
    except OSError as exc:
        return {'ok': False, 'written': written, 'skipped': skipped,
                'error': str(exc)}
    if written:
        _atomic_write_json(state_path, {'last_processed_ts': max_ts})
    insufficient = written == 0
    return {
        'ok': True,
        'written': written,
        'skipped': skipped,
        'insufficient_data': insufficient,
        'last_processed_ts': max_ts if written else last_ts,
    }


def _self_test() -> int:
    import shutil
    td = Path(tempfile.mkdtemp(prefix='aef-%s-' % uuid.uuid4().hex[:8]))
    try:
        calib = td / 'calibration-log.jsonl'
        out = td / 'eval-scores.jsonl'
        state = td / 'anytime-eval-feeder-state.json'
        rows = [
            {'ts': '2026-01-01T00:00:00+00:00', 'predicted_confidence': 0.4, 'scope': 'a'},
            {'ts': '2026-01-01T00:00:01+00:00', 'predicted_confidence': 1.5, 'scope': 'b'},
            {'ts': '2026-01-01T00:00:02+00:00', 'scope': 'c'},
            'not-json',
            {'ts': '2026-01-01T00:00:03+00:00', 'predicted_confidence': 0.2},
        ]
        calib.write_text(
            '\n'.join(json.dumps(r) if isinstance(r, dict) else r for r in rows) + '\n',
            encoding='utf-8',
        )
        r1 = feed(calib, out, state, limit=1000)
        assert r1['ok'] and r1['written'] == 3, r1
        lines = out.read_text(encoding='utf-8').splitlines()
        assert len(lines) == 3, lines
        p0 = json.loads(lines[0])
        assert p0['source'] == 'calibration-log'
        assert abs(p0['score'] - 0.4) < 1e-9
        p1 = json.loads(lines[1])
        assert abs(p1['score'] - 1.0) < 1e-9  # clipped
        r2 = feed(calib, out, state, limit=1000)
        assert r2['written'] == 0, r2
        assert len(out.read_text(encoding='utf-8').splitlines()) == 3
        missing = feed(td / 'nope.jsonl', out, state, limit=10)
        assert missing.get('insufficient_data') is True
        print('[anytime-eval-feeder] --self-test PASS')
        return 0
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--limit', type=int, default=DEFAULT_LIMIT)
    ap.add_argument('--calib', default=str(CALIB))
    ap.add_argument('--out', default=str(OUT_PATH))
    ap.add_argument('--state', default=str(STATE_PATH))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print('[anytime-eval-feeder] --self-test FAIL: %s' % exc)
            sys.exit(1)
    result = feed(Path(args.calib), Path(args.out), Path(args.state), int(args.limit))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get('ok') else 1)


if __name__ == '__main__':
    main()
