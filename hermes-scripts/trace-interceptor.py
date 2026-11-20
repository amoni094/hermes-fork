#!/usr/bin/env python3
"""Append-only hash-chained trace log. Agent-facing APIs never write the chain file."""
from __future__ import annotations
import argparse, fcntl, hashlib, json, os, re, sys, tempfile, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
SESSIONS = _hermes_root / 'sessions'
CHAIN_PATH = CACHE / 'trace-audit.jsonl'
OUT_PATH = CACHE / 'trace-interceptor.json'


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


def _hash_rec(prev: str, payload: dict) -> str:
    blob = (prev or 'GENESIS') + '|' + json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def verify_chain(path: Path) -> dict:
    if not path.exists():
        return {'ok': True, 'n': 0, 'breaks': []}
    breaks = []
    prev = 'GENESIS'
    n = 0
    try:
        for i, line in enumerate(path.read_text(encoding='utf-8').splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                breaks.append({'i': i, 'kind': 'malformed'})
                continue
            if rec.get('prev') != prev:
                breaks.append({'i': i, 'kind': 'prev_mismatch'})
            expect = _hash_rec(prev, rec.get('payload') or {})
            if rec.get('hash') != expect:
                breaks.append({'i': i, 'kind': 'hash_mismatch'})
            prev = rec.get('hash') or prev
            n += 1
    except OSError:
        return {'ok': False, 'n': 0, 'breaks': [{'kind': 'read_error'}]}
    return {'ok': len(breaks) == 0, 'n': n, 'breaks': breaks[:20]}


def append_events(path: Path, events: list) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    added = 0
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            prev = 'GENESIS'
            if path.exists():
                try:
                    lines = [ln for ln in path.read_text(encoding='utf-8').splitlines() if ln.strip()]
                    if lines:
                        last = json.loads(lines[-1])
                        prev = last.get('hash') or prev
                except (OSError, json.JSONDecodeError):
                    prev = 'GENESIS'
            with open(path, 'a', encoding='utf-8') as f:
                for ev in events:
                    payload = {'ts': _now(), 'event': ev}
                    h = _hash_rec(prev, payload)
                    rec = {'prev': prev, 'hash': h, 'payload': payload}
                    f.write(json.dumps(rec) + '\n')
                    prev = h
                    added += 1
        finally:
            try:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    return added


def collect_session_events(limit_sessions: int = 5, limit_events: int = 40) -> list:
    if not SESSIONS.exists():
        return []
    paths = sorted([p for p in SESSIONS.glob('*.jsonl') if re.match(r'^\d{8}_', p.stem)])[-limit_sessions:]
    events = []
    for p in paths:
        try:
            for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                tool = rec.get('tool') or rec.get('tool_name') or rec.get('name')
                role = rec.get('role')
                if tool or role in ('tool', 'assistant'):
                    events.append({'session': p.stem, 'tool': tool, 'role': role})
                if len(events) >= limit_events:
                    return events
        except OSError:
            continue
    return events


def detect_tamper_signals() -> list:
    """Heuristic scan of the chain file for deletion attempts in payload text."""
    hits = []
    if not CHAIN_PATH.exists():
        return hits
    try:
        text = CHAIN_PATH.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return hits
    for pat, kind in (
        (r'DELETE\s+FROM\s+trace', 'sql_delete'),
        (r'\brm\b.*trace-audit', 'rm_chain'),
    ):
        if re.search(pat, text, re.IGNORECASE):
            hits.append(kind)
    return hits


def run() -> dict:
    try:
        v0 = verify_chain(CHAIN_PATH)
        events = collect_session_events()
        added = 0
        if events:
            added = append_events(CHAIN_PATH, events)
        v1 = verify_chain(CHAIN_PATH)
        tamper = detect_tamper_signals()
        out = {
            'status': 'ok' if v1.get('ok') else 'tamper',
            'ts': _now(),
            'chain_ok_before': v0.get('ok'),
            'chain_ok_after': v1.get('ok'),
            'n_before': v0.get('n'),
            'n_after': v1.get('n'),
            'added': added,
            'breaks': v1.get('breaks'),
            'tamper_signals': tamper,
        }
        if events or v1.get('n', 0) > 0:
            _atomic_write(OUT_PATH, out)
        else:
            out = {'status': 'insufficient_data', 'n': 0, 'ts': _now()}
        return out
    except Exception as e:
        return {'status': 'error', 'reason': str(e), 'ts': _now()}


def _self_test() -> int:
    td = Path(tempfile.mkdtemp(prefix='trace-int-'))
    chain = td / 'chain.jsonl'
    append_events.__defaults__  # keep
    # local chain via monkeypatch of path: call append with explicit path
    n = append_events(chain, [{'tool': 'read_file'}, {'tool': 'terminal'}])
    assert n == 2
    v = verify_chain(chain)
    assert v['ok'] is True and v['n'] == 2
    # tamper last line
    lines = chain.read_text().splitlines()
    rec = json.loads(lines[-1])
    rec['payload']['event'] = {'tool': 'forged'}
    chain.write_text(lines[0] + '\n' + json.dumps(rec) + '\n')
    v2 = verify_chain(chain)
    assert v2['ok'] is False
    for p in td.iterdir():
        p.unlink()
    td.rmdir()
    print('[trace-interceptor] --self-test PASS')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[trace-interceptor] --self-test FAIL: {exc}')
            return 1
    out = run()
    print(json.dumps(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
