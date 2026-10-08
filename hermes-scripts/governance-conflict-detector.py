#!/usr/bin/env python3
"""governance-conflict-detector.py — Multi-principal conflict surface.

Critch ARCHES (multi-principal), Shoham multiagent systems.
When tool-auth-gate and governance-hard-block disagree, the conflict is
currently resolved by silent priority. This script makes conflicts visible.

CONFLICT_TYPE_A: auth_gate=ALLOW and hard_block=DENY
CONFLICT_TYPE_B: auth_gate=DENY and hard_block=ALLOW

Usage:
  python3 governance-conflict-detector.py --self-test
  python3 governance-conflict-detector.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

EVENTS_PATH = _hermes_root / 'cache' / 'governance-conflicts.jsonl'
SUMMARY_PATH = _hermes_root / 'cache' / 'governance-conflict-summary.json'
WINDOW_H = 24


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _atomic_append(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(obj) + '\n')
            fh.flush()
    except OSError:
        pass


def _parse_ts(rec: dict):
    for key in ('ts', 'timestamp', 'time', 'at', 'created_at'):
        v = rec.get(key)
        if v is None:
            continue
        if isinstance(v, (int, float)):
            try:
                return datetime.fromtimestamp(float(v), tz=timezone.utc)
            except (OSError, ValueError, OverflowError):
                continue
        if isinstance(v, str):
            s = v.replace('Z', '+00:00')
            try:
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
    return None


def _decision(rec: dict) -> str | None:
    for key in ('decision', 'verdict', 'action', 'result', 'status', 'gate'):
        v = rec.get(key)
        if isinstance(v, str):
            u = v.strip().upper()
            if u in ('ALLOW', 'ALLOWED', 'PERMIT', 'PASS', 'OK'):
                return 'ALLOW'
            if u in ('DENY', 'DENIED', 'BLOCK', 'BLOCKED', 'REJECT', 'FAIL'):
                return 'DENY'
        if isinstance(v, bool):
            return 'ALLOW' if v else 'DENY'
    if rec.get('allowed') is True:
        return 'ALLOW'
    if rec.get('allowed') is False:
        return 'DENY'
    if rec.get('blocked') is True:
        return 'DENY'
    if rec.get('blocked') is False:
        return 'ALLOW'
    return None


def _tool_key(rec: dict) -> str:
    for key in ('tool_call_id', 'call_id', 'id', 'tool', 'name'):
        v = rec.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ''


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return rows
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def load_logs(auth_path: Path | None = None, block_path: Path | None = None) -> tuple[list[dict], list[dict], dict]:
    meta = {'auth_log_present': False, 'block_log_present': False}
    auth_candidates = [
        auth_path,
        _hermes_root / 'cache' / 'tool-auth-gate-log.jsonl',
        _hermes_base / 'cache' / 'tool-auth-gate-log.jsonl',
        _hermes_root / 'logs' / 'tool-auth-gate-log.jsonl',
    ]
    block_candidates = [
        block_path,
        _hermes_root / 'cache' / 'governance-hard-block-log.jsonl',
        _hermes_base / 'cache' / 'governance-hard-block-log.jsonl',
        _hermes_root / 'logs' / 'governance-hard-block-log.jsonl',
    ]
    auth_rows: list[dict] = []
    block_rows: list[dict] = []
    for p in auth_candidates:
        if p is None:
            continue
        try:
            if p.is_file():
                auth_rows = _read_jsonl(p)
                meta['auth_log_present'] = True
                meta['auth_log'] = str(p)
                break
        except OSError:
            continue
    for p in block_candidates:
        if p is None:
            continue
        try:
            if p.is_file():
                block_rows = _read_jsonl(p)
                meta['block_log_present'] = True
                meta['block_log'] = str(p)
                break
        except OSError:
            continue
    return auth_rows, block_rows, meta


def detect_conflicts(auth_rows: list[dict], block_rows: list[dict],
                     now: datetime | None = None, window_h: float = WINDOW_H) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_h)

    def in_window(rec):
        ts = _parse_ts(rec)
        if ts is None:
            return True  # keep undated rather than drop silently
        return ts >= cutoff

    auth_idx: dict[str, list[tuple[str, dict]]] = {}
    for rec in auth_rows:
        if not in_window(rec):
            continue
        d = _decision(rec)
        k = _tool_key(rec)
        if not d or not k:
            continue
        auth_idx.setdefault(k, []).append((d, rec))
    block_idx: dict[str, list[tuple[str, dict]]] = {}
    for rec in block_rows:
        if not in_window(rec):
            continue
        d = _decision(rec)
        k = _tool_key(rec)
        if not d or not k:
            continue
        block_idx.setdefault(k, []).append((d, rec))

    events = []
    keys = set(auth_idx) | set(block_idx)
    for k in sorted(keys):
        a_list = auth_idx.get(k) or []
        b_list = block_idx.get(k) or []
        if not a_list or not b_list:
            continue
        # last decision per principal
        a_dec = a_list[-1][0]
        b_dec = b_list[-1][0]
        ctype = None
        if a_dec == 'ALLOW' and b_dec == 'DENY':
            ctype = 'CONFLICT_TYPE_A'
        elif a_dec == 'DENY' and b_dec == 'ALLOW':
            ctype = 'CONFLICT_TYPE_B'
        if ctype:
            events.append({
                'ts': now.isoformat(),
                'key': k,
                'type': ctype,
                'auth_gate': a_dec,
                'hard_block': b_dec,
                'theorem': 'Critch ARCHES multi-principal; Shoham MAS disagreement',
            })
    return events


def run(auth_path: Path | None = None, block_path: Path | None = None) -> dict:
    auth_rows, block_rows, meta = load_logs(auth_path, block_path)
    events = detect_conflicts(auth_rows, block_rows)
    for ev in events:
        _atomic_append(EVENTS_PATH, ev)
    n_a = sum(1 for e in events if e['type'] == 'CONFLICT_TYPE_A')
    n_b = sum(1 for e in events if e['type'] == 'CONFLICT_TYPE_B')
    summary = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'n_conflicts': len(events),
        'n_type_a': n_a,
        'n_type_b': n_b,
        'most_recent': events[-1] if events else None,
        'skipped_auth': not meta.get('auth_log_present'),
        'skipped_block': not meta.get('block_log_present'),
        **meta,
        'theorem': 'Critch ARCHES multi-principal conflict surface',
    }
    try:
        _atomic_write(SUMMARY_PATH, summary)
        summary['output'] = str(SUMMARY_PATH)
    except OSError as exc:
        summary['write_error'] = str(exc)
    return summary


def self_test() -> int:
    failures = []
    now = datetime.now(timezone.utc)
    auth = [
        {'tool': 'write_file', 'decision': 'ALLOW', 'ts': now.isoformat()},
        {'tool': 'read_file', 'decision': 'ALLOW', 'ts': now.isoformat()},
        {'tool': 'terminal', 'decision': 'DENY', 'ts': now.isoformat()},
    ]
    block = [
        {'tool': 'write_file', 'verdict': 'DENY', 'ts': now.isoformat()},
        {'tool': 'read_file', 'verdict': 'ALLOW', 'ts': now.isoformat()},
        {'tool': 'terminal', 'verdict': 'ALLOW', 'ts': now.isoformat()},
    ]
    ev = detect_conflicts(auth, block, now=now)
    types = {e['key']: e['type'] for e in ev}
    if types.get('write_file') != 'CONFLICT_TYPE_A':
        failures.append(f'write_file should be TYPE_A, got {types}')
    if types.get('terminal') != 'CONFLICT_TYPE_B':
        failures.append(f'terminal should be TYPE_B, got {types}')
    if 'read_file' in types:
        failures.append('read_file should not conflict')
    # graceful skip
    a, b, meta = load_logs(
        auth_path=Path('/nonexistent/tool-auth-gate-log.jsonl'),
        block_path=Path('/nonexistent/governance-hard-block-log.jsonl'),
    )
    if a or b or meta.get('auth_log_present') or meta.get('block_log_present'):
        failures.append('missing logs should skip gracefully')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS', 'n_events': len(ev)}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({
        'n_conflicts': out.get('n_conflicts'),
        'n_type_a': out.get('n_type_a'),
        'n_type_b': out.get('n_type_b'),
        'skipped_auth': out.get('skipped_auth'),
        'skipped_block': out.get('skipped_block'),
        'output': out.get('output'),
    }))
    return 0


if __name__ == '__main__':
    sys.exit(main())
