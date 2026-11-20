#!/usr/bin/env python3
"""Scope-adherence auditor: score tool sequences against a JSON scope policy."""
from __future__ import annotations
import argparse, fcntl, json, os, re, sys, tempfile, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
SESSIONS = _hermes_root / 'sessions'
POLICY_PATH = CACHE / 'scope-policy.json'
OUT_PATH = CACHE / 'scope-violations.json'

DEFAULT_POLICY = {
    'forbidden_tools': ['manage_connections'],
    'forbidden_arg_re': [r'rm\s+-rf\s+/(?:\s|$)', r'/etc/shadow'],
    'max_danger_streak': 6,
    'danger_tools': ['terminal', 'execute_code', 'write_file', 'patch'],
}


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


def load_policy() -> dict:
    if not POLICY_PATH.exists():
        return dict(DEFAULT_POLICY)
    try:
        data = json.loads(POLICY_PATH.read_text(encoding='utf-8'))
        if isinstance(data, dict) and data:
            pol = dict(DEFAULT_POLICY)
            pol.update(data)
            return pol
    except (OSError, json.JSONDecodeError):
        pass
    return dict(DEFAULT_POLICY)


def extract_calls(path: Path) -> list:
    calls = []
    try:
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            tool = rec.get('tool') or rec.get('tool_name') or rec.get('name')
            if not tool:
                continue
            args = rec.get('args') or rec.get('arguments') or rec.get('content') or ''
            calls.append({'tool': str(tool), 'args': str(args)[:500]})
    except OSError:
        return []
    return calls


def audit_calls(calls: list, policy: dict) -> dict:
    if not calls:
        return {'status': 'insufficient_data', 'violations': [], 'n': 0}
    forbidden = set(policy.get('forbidden_tools') or [])
    arg_res = [re.compile(p) for p in (policy.get('forbidden_arg_re') or [])]
    danger = set(policy.get('danger_tools') or [])
    max_streak = int(policy.get('max_danger_streak') or 6)
    viol = []
    streak = 0
    for i, c in enumerate(calls):
        t = c['tool']
        if t in forbidden:
            viol.append({'i': i, 'tool': t, 'kind': 'forbidden_tool'})
        for rx in arg_res:
            if rx.search(c.get('args') or ''):
                viol.append({'i': i, 'tool': t, 'kind': 'forbidden_arg'})
                break
        if t in danger:
            streak += 1
            if streak > max_streak:
                viol.append({'i': i, 'tool': t, 'kind': 'danger_streak'})
        else:
            streak = 0
    return {'status': 'ok', 'n': len(calls), 'n_violations': len(viol), 'violations': viol[:40]}


def run() -> dict:
    try:
        policy = load_policy()
        if not SESSIONS.exists():
            return {'status': 'insufficient_data', 'n_sessions': 0, 'ts': _now()}
        paths = sorted([p for p in SESSIONS.glob('*.jsonl') if re.match(r'^\d{8}_', p.stem)])[-8:]
        if not paths:
            return {'status': 'insufficient_data', 'n_sessions': 0, 'ts': _now()}
        sessions = []
        total_v = 0
        for p in paths:
            r = audit_calls(extract_calls(p), policy)
            r['session'] = p.stem
            sessions.append(r)
            total_v += r.get('n_violations') or 0
        out = {
            'status': 'ok',
            'ts': _now(),
            'n_sessions': len(sessions),
            'n_violations': total_v,
            'sessions': sessions,
        }
        _atomic_write(OUT_PATH, out)
        return out
    except Exception as e:
        return {'status': 'error', 'reason': str(e), 'ts': _now()}


def _self_test() -> int:
    pol = DEFAULT_POLICY
    empty = audit_calls([], pol)
    assert empty['status'] == 'insufficient_data'
    bad = audit_calls(
        [{'tool': 'terminal', 'args': 'rm -rf / '}] + [{'tool': 'terminal', 'args': 'ls'}] * 8,
        pol,
    )
    kinds = {v['kind'] for v in bad['violations']}
    assert 'forbidden_arg' in kinds
    assert 'danger_streak' in kinds
    tmp = Path(tempfile.gettempdir()) / ('scope-test-' + uuid.uuid4().hex + '.json')
    _atomic_write(tmp, bad)
    tmp.unlink(missing_ok=True)
    print('[scope-auditor] --self-test PASS')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[scope-auditor] --self-test FAIL: {exc}')
            return 1
    out = run()
    print(json.dumps({k: out.get(k) for k in out if k != 'sessions'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
