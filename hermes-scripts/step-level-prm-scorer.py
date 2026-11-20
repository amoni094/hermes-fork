#!/usr/bin/env python3
"""Score each tool-use step with a lightweight process reward (ToolPRMBench).

Also ranks candidate steps (process-reward-ranker) and scores subgoals
(subgoal-verifier-rubric).
"""
from __future__ import annotations
import argparse, json, os, sys, tempfile, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT = CACHE / 'prm-step-scores.json'
RANK_OUT = CACHE / 'process-reward-rankings.json'
SUBGOAL_OUT = CACHE / 'subgoal-verification.json'


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))


def _temp_out(prefix: str) -> Path:
    return Path(tempfile.gettempdir()) / (f'{prefix}-{uuid.uuid4().hex}.json')


def score_step(step: dict, seen: set) -> dict:
    completes = bool(step.get('completes_subgoal') or step.get('success') or step.get('achieved'))
    backtracks = bool(step.get('backtracks') or step.get('undo') or (str(step.get('action') or '').lower() in ('undo', 'retry', 'revert')))
    sig = json.dumps({'tool': step.get('tool') or step.get('action'), 'args': step.get('args')}, sort_keys=True, default=str)
    redundant = bool(step.get('redundant')) or sig in seen
    seen.add(sig)
    prm = 0.5 * float(completes) - 0.3 * float(backtracks) - 0.2 * float(redundant)
    return {
        'completes_subgoal': completes,
        'backtracks': backtracks,
        'redundant': redundant,
        'prm_score': round(prm, 6),
        'tool': step.get('tool') or step.get('action') or '',
    }


def score_steps(steps: list) -> dict:
    seen = set()
    rows = []
    for i, st in enumerate(steps or []):
        if not isinstance(st, dict):
            st = {'action': str(st)}
        row = score_step(st, seen)
        row['step'] = i
        rows.append(row)
    n = len(rows)
    if n == 0:
        return {
            'generated_at': _now(),
            'n': 0,
            'mean_prm': None,
            'steps': [],
            'status': 'insufficient_data',
        }
    mean = sum(r['prm_score'] for r in rows) / float(n)
    return {
        'generated_at': _now(),
        'n': n,
        'mean_prm': round(mean, 6),
        'steps': rows,
        'status': 'ok',
    }


def rank(candidates):
    ranked = []
    for i, c in enumerate(candidates or []):
        if not isinstance(c, dict):
            c = {'text': str(c)}
        corr = float(c.get('correctness_proxy', c.get('correctness', 0.5)))
        eff = float(c.get('efficiency_proxy', c.get('efficiency', 0.5)))
        score = 0.6 * corr + 0.4 * eff
        ranked.append({
            'id': c.get('id', i),
            'score': round(score, 6),
            'correctness_proxy': corr,
            'efficiency_proxy': eff,
        })
    if not ranked:
        return {
            'generated_at': _now(),
            'n': 0,
            'ranked': [],
            'status': 'insufficient_data',
        }
    ranked.sort(key=lambda r: -r['score'])
    return {
        'generated_at': _now(),
        'n': len(ranked),
        'ranked': ranked,
        'status': 'ok',
    }


def score_subgoal(expected, used):
    expected = expected or {}
    used = used or {}
    et = expected.get('expected_tool') or expected.get('tool')
    ut = used.get('used_tool') or used.get('tool')
    ea = expected.get('expected_args') if 'expected_args' in expected else expected.get('args')
    ua = used.get('used_args') if 'used_args' in used else used.get('args')
    if et is None and ea is None and ut is None and ua is None:
        return {
            'generated_at': _now(),
            'status': 'insufficient_data',
            'achieved': None,
            'correct_tool': None,
            'correct_args': None,
            'step_score': None,
            'aggregate_score': None,
        }
    correct_tool = (et == ut) if et is not None else None
    correct_args = (ea == ua) if ea is not None else None
    bits = [b for b in (correct_tool, correct_args) if b is not None]
    if not bits:
        return {
            'generated_at': _now(),
            'status': 'insufficient_data',
            'achieved': None,
            'correct_tool': correct_tool,
            'correct_args': correct_args,
            'step_score': None,
            'aggregate_score': None,
        }
    step_score = sum(1.0 for b in bits if b) / len(bits)
    achieved = all(bits)
    return {
        'generated_at': _now(),
        'status': 'ok',
        'achieved': achieved,
        'correct_tool': correct_tool,
        'correct_args': correct_args,
        'step_score': step_score,
        'aggregate_score': step_score,
    }


def self_test() -> dict:
    steps = [
        {'tool': 't', 'args': {'a': 1}, 'completes_subgoal': True},
        {'tool': 't', 'args': {'a': 1}, 'completes_subgoal': False},
        {'tool': 'undo', 'backtracks': True},
    ]
    r = score_steps(steps)
    assert r['steps'][0]['prm_score'] == 0.5, r
    assert r['steps'][1]['redundant'] is True
    assert r['steps'][2]['backtracks'] is True
    empty = score_steps([])
    assert empty['status'] == 'insufficient_data'
    rr = rank([{'id': 'a', 'correctness_proxy': 1.0, 'efficiency_proxy': 0.5}, {'id': 'b', 'correctness_proxy': 0.2, 'efficiency_proxy': 0.2}])
    assert rr['ranked'][0]['id'] == 'a'
    assert rank([])['status'] == 'insufficient_data'
    sg = score_subgoal({'expected_tool': 'read_file', 'expected_args': {'path': 'a'}}, {'used_tool': 'read_file', 'used_args': {'path': 'a'}})
    assert sg['achieved'] is True and sg['step_score'] == 1.0
    sg2 = score_subgoal({}, {})
    assert sg2['status'] == 'insufficient_data'
    tmp = _temp_out('prm')
    _atomic_write_json(tmp, r)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    return {'self_test': 'PASS', 'sample': r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--json', default='')
    ap.add_argument('--mode', choices=['steps', 'rank', 'subgoal'], default='steps')
    args = ap.parse_args()
    if args.self_test:
        try:
            r = self_test()
            print(json.dumps(r, indent=2))
            sys.exit(0 if r.get('self_test') == 'PASS' else 1)
        except Exception as exc:
            print(f'[step-level-prm-scorer] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        raw = args.json
        if not raw and not sys.stdin.isatty():
            raw = sys.stdin.read()
        obj = {}
        if raw:
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                obj = {}
        if args.mode == 'rank':
            cands = obj if isinstance(obj, list) else obj.get('candidates') or []
            out = rank(cands)
            if out.get('status') != 'insufficient_data':
                _atomic_write_json(RANK_OUT, out)
        elif args.mode == 'subgoal':
            expected = obj.get('expected') or obj
            used = obj.get('used') or {}
            out = score_subgoal(expected, used)
            if out.get('status') != 'insufficient_data':
                _atomic_write_json(SUBGOAL_OUT, out)
        else:
            steps = obj if isinstance(obj, list) else obj.get('steps') or []
            out = score_steps(steps)
            if out.get('status') != 'insufficient_data':
                _atomic_write_json(OUT, out)
        print(json.dumps(out, indent=2))
    except Exception:
        pass


if __name__ == '__main__':
    main()
