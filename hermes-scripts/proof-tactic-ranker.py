#!/usr/bin/env python3
"""Heuristic tactic ranker for formal-proof scaffolding (no LLM calls)."""
from __future__ import annotations
import argparse, fcntl, json, math, os, sys, tempfile, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
STATE_PATH = CACHE / 'proof-state.json'
OUT_PATH = CACHE / 'tactic-rank.json'
FB_PATH = CACHE / 'tactic-feedback.jsonl'


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


def _append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec) + '\n')
        finally:
            try:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if data is not None else default
    except (OSError, json.JSONDecodeError):
        return default


def _feedback_rates(path: Path) -> dict:
    rates = {}
    counts = {}
    if not path.exists():
        return rates
    try:
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            tac = str(rec.get('tactic') or rec.get('name') or '')
            if not tac:
                continue
            acc = rec.get('accepted', rec.get('success'))
            if acc is None:
                continue
            ok = 1.0 if acc in (True, 1, '1', 'true', 'accept') else 0.0
            counts[tac] = counts.get(tac, 0) + 1
            rates[tac] = rates.get(tac, 0.0) + ok
    except OSError:
        return {}
    return {k: rates[k] / counts[k] for k in rates}


def score_tactic(tac: str, rates: dict, goal: str = '') -> float:
    t = (tac or '').strip()
    if not t:
        return 0.0
    prior = float(rates.get(t, 0.5))
    length_pen = 1.0 / (1.0 + math.log1p(len(t)))
    g = (goal or '').lower()
    overlap = 0.0
    if g:
        toks = set(t.lower().replace('_', ' ').split())
        gtoks = set(g.replace('_', ' ').split())
        if toks and gtoks:
            overlap = len(toks & gtoks) / len(toks | gtoks)
    s = 0.5 * prior + 0.3 * length_pen + 0.2 * overlap
    return max(0.0, min(1.0, s))


def rank_tactics(tactics, rates, goal=''):
    scored = []
    for t in tactics:
        name = t if isinstance(t, str) else str((t or {}).get('tactic') or (t or {}).get('name') or '')
        scored.append({'tactic': name, 'score': score_tactic(name, rates, goal)})
    scored.sort(key=lambda r: r['score'], reverse=True)
    return scored


def run() -> dict:
    try:
        state = _load_json(STATE_PATH, {})
        if not isinstance(state, dict):
            state = {}
        rates = _feedback_rates(FB_PATH)
        tactics = state.get('candidate_tactics') or state.get('tactics') or []
        if not isinstance(tactics, list):
            tactics = []
        goal = str(state.get('goal') or state.get('current_goal') or '')
        if not tactics:
            history = state.get('tactic_history') or state.get('history') or []
            if isinstance(history, list):
                tactics = [h if isinstance(h, str) else str((h or {}).get('tactic') or '') for h in history[-12:]]
                tactics = [t for t in tactics if t]
        if not tactics:
            return {'status': 'insufficient_data', 'n': 0, 'ts': _now()}
        ranked = rank_tactics(tactics, rates, goal)
        out = {
            'status': 'ok',
            'ts': _now(),
            'n': len(ranked),
            'goal': goal[:200],
            'ranked': ranked[:20],
            'top': ranked[0] if ranked else None,
            'n_feedback_tactics': len(rates),
        }
        _atomic_write(OUT_PATH, out)
        return out
    except Exception as e:
        return {'status': 'error', 'reason': str(e), 'ts': _now()}


def _self_test() -> int:
    rates = {'simp': 0.9, 'blast': 0.1, 'rewrite': 0.6}
    ranked = rank_tactics(['blast', 'simp', 'rewrite'], rates, goal='simp nat')
    assert ranked[0]['tactic'] == 'simp'
    empty = rank_tactics([], {})
    assert empty == []
    assert score_tactic('', {}) == 0.0
    tmp = Path(tempfile.gettempdir()) / ('tactic-rank-test-' + uuid.uuid4().hex + '.json')
    _atomic_write(tmp, {'ok': True})
    tmp.unlink(missing_ok=True)
    print('[proof-tactic-ranker] --self-test PASS')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[proof-tactic-ranker] --self-test FAIL: {exc}')
            return 1
    out = run()
    print(json.dumps({k: out.get(k) for k in out if k != 'ranked'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
