#!/usr/bin/env python3
"""Score a tool-use trajectory step-by-step (process-reward style)."""
from __future__ import annotations
import argparse, json, os, sqlite3, sys, tempfile, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))

def _lifecycle_db() -> Path:
    return _hermes_root / 'memory-facts' / 'lifecycle.db'

def _temp_out(prefix: str) -> Path:
    return Path(tempfile.gettempdir()) / (f'{prefix}-{uuid.uuid4().hex}.json')

OUT_PATH = CACHE / 'trajectory-audit.json'


DEFAULT_INVARIANTS = (
    'no_self_message_loop',
    'unique_step_ids',
    'actor_present',
    'action_present',
)


def _invariant_violations(steps):
    violations = []
    ids = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            step = {}
        actor = step.get('actor') or step.get('role') or ''
        target = step.get('target') or step.get('to') or ''
        action = step.get('action') or step.get('tool') or ''
        sid = step.get('id') if step.get('id') is not None else step.get('step_id')
        if sid is not None:
            ids.append(sid)
        if actor and target and str(actor) == str(target):
            violations.append({'step': i, 'invariant': 'no_self_message_loop'})
        if not actor:
            violations.append({'step': i, 'invariant': 'actor_present'})
        if not action:
            violations.append({'step': i, 'invariant': 'action_present'})
    if ids and len(ids) != len(set(ids)):
        violations.append({'step': None, 'invariant': 'unique_step_ids'})
    return violations


def score_step(step, i, n):
    tool = str(step.get('tool') or step.get('action') or '')
    ok = step.get('ok')
    if ok is None:
        ok = step.get('success')
    if ok is None:
        err = step.get('error')
        ok = False if err else True
    progress = (i + 1) / max(1, n)
    return {
        'i': i,
        'tool': tool,
        'ok': bool(ok),
        'progress': round(progress, 4),
        'score': (0.7 if ok else 0.2) * (0.5 + 0.5 * progress),
    }


def audit(steps):
    steps = list(steps or [])
    n = len(steps)
    if n == 0:
        return {
            'step_count': 0,
            'mean_score': None,
            'ok_rate': None,
            'steps': [],
            'ok': None,
            'invariants': list(DEFAULT_INVARIANTS),
            'violations': [],
            'status': 'insufficient_data',
            'ts': _now(),
        }
    scored = [score_step(s if isinstance(s, dict) else {'action': s}, i, n) for i, s in enumerate(steps)]
    mean = sum(s['score'] for s in scored) / n
    ok_rate = sum(1 for s in scored if s['ok']) / n
    violations = _invariant_violations(steps)
    return {
        'step_count': n,
        'mean_score': mean,
        'ok_rate': ok_rate,
        'steps': scored,
        'ok': len(violations) == 0,
        'invariants': list(DEFAULT_INVARIANTS),
        'violations': violations,
        'status': 'ok',
        'ts': _now(),
    }


def _maybe_log(report):
    db = _lifecycle_db()
    if not db.exists() or report.get('status') == 'insufficient_data':
        return
    try:
        conn = sqlite3.connect(str(db))
        conn.execute('PRAGMA journal_mode=WAL')
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'trajectory_audit' not in tables:
                return
            conn.execute(
                'INSERT INTO trajectory_audit(ts, step_count, mean_score) VALUES (?,?,?)',
                (report['ts'], report['step_count'], report['mean_score']),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def _self_test() -> int:
    empty = audit([])
    assert empty['status'] == 'insufficient_data'
    assert empty['ok'] is None
    r = audit([{'tool': 'a', 'ok': True, 'actor': 'x', 'id': 1}, {'tool': 'b', 'ok': False, 'actor': 'y', 'id': 2}])
    assert r['step_count'] == 2
    loop = audit([{'actor': 'x', 'target': 'x', 'action': 'msg', 'id': 1}])
    assert any(v['invariant'] == 'no_self_message_loop' for v in loop['violations'])
    assert loop['ok'] is False
    tmp = _temp_out('traj-audit')
    _atomic_write(tmp, r)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    print('[step-level-trajectory-auditor] --self-test PASS mean={:.3f}'.format(r['mean_score']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[step-level-trajectory-auditor] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        r = audit([])
        if r.get('status') != 'insufficient_data':
            _atomic_write(OUT_PATH, r)
            _maybe_log(r)
        print(json.dumps({k: r[k] for k in r if k != 'steps'}))
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
