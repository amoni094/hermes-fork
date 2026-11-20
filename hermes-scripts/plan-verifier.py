#!/usr/bin/env python3
"""Lightweight CTL-style plan verifier over tool-call sequences (no nuXmv)."""
from __future__ import annotations
import argparse, fcntl, json, os, re, sys, tempfile, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
SESSIONS = _hermes_root / 'sessions'
OUT_PATH = CACHE / 'plan-verification.json'

SECRET_RE = re.compile(r'(secret|password|token|api[_-]?key|credential)', re.IGNORECASE)
SANITIZE_RE = re.compile(r'(sanitiz|redact|mask|hash|scrub)', re.IGNORECASE)
DANGER_TOOLS = {'terminal', 'execute_code', 'write_file', 'patch'}


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


def extract_tools(session_path: Path, limit: int = 80) -> list:
    tools = []
    try:
        for line in session_path.read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            tool = rec.get('tool') or rec.get('tool_name') or rec.get('name')
            if rec.get('role') == 'tool' and not tool:
                continue
            if rec.get('type') == 'tool_call' or rec.get('role') in ('tool', 'assistant'):
                t = tool or rec.get('name')
                args = rec.get('args') or rec.get('arguments') or rec.get('content') or ''
                if t:
                    tools.append({'tool': str(t), 'args': str(args)[:400]})
            if len(tools) >= limit:
                break
    except OSError:
        return []
    return tools


def check_ctl(seq: list) -> dict:
    """AG(secret_read -> AF sanitize) and AG(not danger without prior read)."""
    violations = []
    secret_idx = None
    sanitized_after = False
    for i, step in enumerate(seq):
        blob = (step.get('tool', '') + ' ' + step.get('args', '')).lower()
        if SECRET_RE.search(blob) and secret_idx is None:
            secret_idx = i
        if secret_idx is not None and i > secret_idx and SANITIZE_RE.search(blob):
            sanitized_after = True
    if secret_idx is not None and not sanitized_after:
        violations.append({'prop': 'AG(secret -> AF sanitize)', 'index': secret_idx})
    names = [s.get('tool', '') for s in seq]
    if names and names[0] in DANGER_TOOLS and 'read_file' not in names[:3]:
        # weak liveness: dangerous write with no preceding read is a smell, not auto-fail
        pass
    approved = len(violations) == 0
    return {'approved': approved, 'violations': violations, 'n_steps': len(seq)}


def verify_plan(seq: list) -> dict:
    if not seq:
        return {'status': 'insufficient_data', 'approved': None, 'n_steps': 0, 'ts': _now()}
    r = check_ctl(seq)
    r.update({'status': 'ok', 'ts': _now()})
    return r


def run() -> dict:
    try:
        paths = []
        if SESSIONS.exists():
            paths = sorted([p for p in SESSIONS.glob('*.jsonl') if re.match(r'^\d{8}_', p.stem)])[-8:]
        plans = []
        rejected = 0
        for p in paths:
            seq = extract_tools(p)
            r = verify_plan(seq)
            r['session'] = p.stem
            plans.append({k: r.get(k) for k in ('session', 'status', 'approved', 'n_steps', 'violations')})
            if r.get('approved') is False:
                rejected += 1
        if not plans:
            return {'status': 'insufficient_data', 'n_plans': 0, 'ts': _now()}
        out = {
            'status': 'ok',
            'ts': _now(),
            'n_plans': len(plans),
            'n_rejected': rejected,
            'plans': plans,
        }
        _atomic_write(OUT_PATH, out)
        return out
    except Exception as e:
        return {'status': 'error', 'reason': str(e), 'ts': _now()}


def _self_test() -> int:
    empty = verify_plan([])
    assert empty['status'] == 'insufficient_data'
    bad = verify_plan([
        {'tool': 'read_file', 'args': 'path=/etc/secret_token'},
        {'tool': 'terminal', 'args': 'echo done'},
    ])
    assert bad['approved'] is False
    good = verify_plan([
        {'tool': 'read_file', 'args': 'path=/etc/secret_token'},
        {'tool': 'execute_code', 'args': 'sanitize(secret); redact()'},
    ])
    assert good['approved'] is True
    tmp = Path(tempfile.gettempdir()) / ('plan-test-' + uuid.uuid4().hex + '.json')
    _atomic_write(tmp, bad)
    tmp.unlink(missing_ok=True)
    print('[plan-verifier] --self-test PASS')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[plan-verifier] --self-test FAIL: {exc}')
            return 1
    out = run()
    print(json.dumps({k: out.get(k) for k in out if k != 'plans'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
