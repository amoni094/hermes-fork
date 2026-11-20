#!/usr/bin/env python3
"""DIAL-style position-bias calibration for skill ranking (stdlib, no LLM)."""
from __future__ import annotations
import argparse, fcntl, json, math, os, sys, tempfile, uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
CALIB = CACHE / 'calibration-log.jsonl'
OUT_PATH = CACHE / 'routing-preferences.json'


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            try:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def calibrate(events: list) -> dict:
    """events: {skill, position, chosen}."""
    if len(events) < 10:
        return {'status': 'insufficient_data', 'n': len(events), 'ts': _now()}
    pos_win = defaultdict(lambda: [0, 0])
    skill_pref = defaultdict(lambda: [0.0, 0])
    for e in events:
        pos = int(e.get('position', 0) or 0)
        chosen = 1 if e.get('chosen') else 0
        pos_win[pos][0] += chosen
        pos_win[pos][1] += 1
        sk = str(e.get('skill') or '')
        if sk:
            skill_pref[sk][0] += float(e.get('score', chosen))
            skill_pref[sk][1] += 1
    # position offset vs mean win-rate
    rates = {p: w / n for p, (w, n) in pos_win.items() if n > 0}
    if not rates:
        return {'status': 'insufficient_data', 'n': len(events), 'ts': _now()}
    mu = sum(rates.values()) / len(rates)
    offsets = {str(p): rates[p] - mu for p in rates}
    prefs = {}
    for sk, (s, n) in skill_pref.items():
        prefs[sk] = {'mean': s / n, 'n': n, 'ci_half': 1.96 * math.sqrt(max(1e-9, (s / n) * (1 - s / n) / n))}
    return {
        'status': 'ok',
        'ts': _now(),
        'n': len(events),
        'position_offsets': offsets,
        'n_skills': len(prefs),
        'preferences': dict(list(prefs.items())[:80]),
        'first_position_bias': offsets.get('0', offsets.get('1', 0.0)),
    }


def load_events(path: Path, limit: int = 6000) -> list:
    if not path.exists():
        return []
    by_session = defaultdict(list)
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            n = 0
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                if rec.get('scope') == 'ue_blackbox':
                    continue
                skill = rec.get('scope') or rec.get('skill') or rec.get('tool_name')
                if not skill:
                    continue
                sid = rec.get('session_id') or rec.get('session') or 'global'
                conf = rec.get('predicted_confidence', rec.get('confidence'))
                try:
                    score = float(conf) if conf is not None else None
                except (TypeError, ValueError):
                    score = None
                by_session[str(sid)].append({'skill': str(skill), 'score': score})
                n += 1
                if n >= limit:
                    break
    except OSError:
        return []
    events = []
    for sid, items in by_session.items():
        for i, it in enumerate(items):
            chosen = False
            if it['score'] is not None:
                chosen = it['score'] >= 0.7
            events.append({'skill': it['skill'], 'position': i % 8, 'chosen': chosen, 'score': it['score'] if it['score'] is not None else (1.0 if chosen else 0.0)})
    return events


def run() -> dict:
    try:
        events = load_events(CALIB)
        out = calibrate(events)
        if out.get('status') != 'insufficient_data':
            _atomic_write(OUT_PATH, out)
        return out
    except Exception as e:
        return {'status': 'error', 'reason': str(e), 'ts': _now()}


def _self_test() -> int:
    empty = calibrate([])
    assert empty['status'] == 'insufficient_data'
    ev = []
    for i in range(40):
        ev.append({'skill': 'alpha', 'position': 0, 'chosen': True, 'score': 1.0})
        ev.append({'skill': 'beta', 'position': 1, 'chosen': i % 4 == 0, 'score': 0.2})
    r = calibrate(ev)
    assert r['status'] == 'ok'
    assert r['first_position_bias'] > 0
    tmp = Path(tempfile.gettempdir()) / ('dial-test-' + uuid.uuid4().hex + '.json')
    _atomic_write(tmp, r)
    tmp.unlink(missing_ok=True)
    print('[skill-dial-calibrate] --self-test PASS bias={:.3f}'.format(r['first_position_bias']))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[skill-dial-calibrate] --self-test FAIL: {exc}')
            return 1
    out = run()
    print(json.dumps({k: out.get(k) for k in out if k != 'preferences'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
