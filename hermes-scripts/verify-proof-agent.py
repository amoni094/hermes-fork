#!/usr/bin/env python3
"""Proof refinement loop: call mock Rocq prover, persist proof-state.json."""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

import argparse
import fcntl
import json
import subprocess
import sys
import tempfile
import traceback
from copy import deepcopy
from datetime import datetime, timezone, UTC
from typing import Any

CACHE = _hermes_root / 'cache'
PROBLEMS_PATH = CACHE / 'proof-problems.jsonl'
STATE_PATH = CACHE / 'proof-state.json'
METRICS_PATH = CACHE / 'proof-metrics.jsonl'
PROVER_PATH = Path(__file__).resolve().parent / 'mock-rocq-prover.py'

SEED_PROBLEMS = [
    {'id': 'list-reversal', 'goal': 'forall l, rev (rev l) = l', 'max_steps': 5},
    {'id': 'nat-add-comm', 'goal': 'forall n m, n + m = m + n', 'max_steps': 10},
]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_suffix('.tmp')
    payload = json.dumps(obj, indent=2) + '\n'
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            try:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def _append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    line = json.dumps(obj, separators=(',', ':')) + '\n'
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            with open(str(path), 'a', encoding='utf-8') as f:
                f.write(line)
        finally:
            try:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def _empty_state_doc() -> dict:
    return {'ts': _now_iso(), 'problems': {}}


def load_state(path: Path) -> dict:
    if not path.exists():
        return _empty_state_doc()
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return _empty_state_doc()
    if not isinstance(obj, dict):
        return _empty_state_doc()
    problems = obj.get('problems')
    if not isinstance(problems, dict):
        problems = {}
    return {'ts': str(obj.get('ts') or _now_iso()), 'problems': problems}


def save_state(path: Path, doc: dict) -> None:
    doc = dict(doc)
    doc['ts'] = _now_iso()
    if not isinstance(doc.get('problems'), dict):
        doc['problems'] = {}
    _atomic_write_json(path, doc)


def seed_problems(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(p, separators=(',', ':')) for p in SEED_PROBLEMS]
    tmp = path.with_suffix('.tmp')
    tmp.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))


def load_problems(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        pid = str(rec.get('id') or '').strip()
        goal = str(rec.get('goal') or '')
        try:
            max_steps = int(rec.get('max_steps', 0))
        except (TypeError, ValueError):
            max_steps = 0
        if not pid or max_steps <= 0:
            continue
        out.append({'id': pid, 'goal': goal, 'max_steps': max_steps})
    return out


def _new_problem_state(goal: str) -> dict:
    return {
        'hypotheses': {},
        'goal': goal,
        'proof_tree': [],
        'complete': False,
        'steps': 0,
        'status': 'open',
    }


def _normalize_problem(raw: Any, goal: str) -> dict:
    st = _new_problem_state(goal)
    if not isinstance(raw, dict):
        return st
    hyps = raw.get('hypotheses')
    st['hypotheses'] = dict(hyps) if isinstance(hyps, dict) else {}
    st['goal'] = str(raw.get('goal') or goal)
    tree = raw.get('proof_tree')
    st['proof_tree'] = list(tree) if isinstance(tree, list) else []
    st['complete'] = bool(raw.get('complete'))
    try:
        st['steps'] = int(raw.get('steps', len(st['proof_tree'])))
    except (TypeError, ValueError):
        st['steps'] = len(st['proof_tree'])
    status = str(raw.get('status') or 'open')
    if status not in ('open', 'proved', 'stuck'):
        status = 'proved' if st['complete'] else 'open'
    if st['complete']:
        status = 'proved'
    st['status'] = status
    return st


def select_tactic(problem: dict) -> str:
    tree = problem.get('proof_tree') or []
    hyps = problem.get('hypotheses') or {}
    if not isinstance(tree, list) or len(tree) == 0:
        return 'induction'
    if not isinstance(hyps, dict) or 'induction_schema' not in hyps:
        return 'induction'
    if 'base_case' not in hyps:
        return 'base_case'
    return 'reflexivity'


def _prover_payload(problem: dict) -> dict:
    return {
        'hypotheses': dict(problem.get('hypotheses') or {}),
        'goal': str(problem.get('goal') or ''),
        'proof_tree': list(problem.get('proof_tree') or []),
        'complete': bool(problem.get('complete')),
    }


def _extract_updated_state(result: dict, fallback: dict) -> dict | None:
    if not isinstance(result, dict):
        return None
    if str(result.get('status') or '') != 'ok':
        return None
    st = result.get('state')
    if not isinstance(st, dict):
        if 'hypotheses' in result or 'proof_tree' in result or 'complete' in result:
            st = result
        else:
            return None
    hyps = st.get('hypotheses')
    tree = st.get('proof_tree')
    updated = {
        'hypotheses': dict(hyps) if isinstance(hyps, dict) else dict(fallback.get('hypotheses') or {}),
        'goal': str(st.get('goal') or fallback.get('goal') or ''),
        'proof_tree': list(tree) if isinstance(tree, list) else list(fallback.get('proof_tree') or []),
        'complete': bool(st.get('complete')),
    }
    return updated


def call_prover(prover: Path, problem: dict, tactic: str, timeout: float = 30.0) -> dict:
    """Return prover JSON. Fail-open: any subprocess/parse error -> status=error."""
    err = {
        'status': 'error',
        'missing': None,
        'message': 'prover_call_failed',
        'accepted_tactic': None,
    }
    try:
        if not prover.exists():
            err['message'] = 'prover_missing: ' + str(prover)
            return err
        proc = subprocess.run(
            [sys.executable, str(prover), '--state', '-', '--tactic', str(tactic)],
            input=json.dumps(_prover_payload(problem)),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        err['message'] = 'prover_exception: ' + type(exc).__name__
        return err
    text = (proc.stdout or '').strip()
    if not text:
        err['message'] = 'prover_empty_stdout: rc=' + str(proc.returncode)
        if proc.stderr:
            err['message'] += ' stderr=' + proc.stderr.strip()[:400]
        return err
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        err['message'] = 'prover_non_json'
        return err
    if not isinstance(obj, dict):
        err['message'] = 'prover_non_object'
        return err
    if 'status' not in obj:
        obj['status'] = 'error'
    return obj


def refine_problem(
    pid: str,
    goal: str,
    max_steps: int,
    state_doc: dict,
    state_path: Path,
    prover: Path,
) -> dict:
    problems = state_doc.setdefault('problems', {})
    current = _normalize_problem(problems.get(pid), goal)
    current['goal'] = goal or current['goal']
    problems[pid] = current
    if current.get('complete') or current.get('status') == 'proved':
        current['complete'] = True
        current['status'] = 'proved'
        return {
            'problem_id': pid,
            'steps_taken': 0,
            'proved': True,
            'final_state': deepcopy(current),
            'skipped': True,
        }

    steps_taken = 0
    proved = False
    for _ in range(max(0, int(max_steps))):
        if current.get('complete'):
            proved = True
            break
        tactic = select_tactic(current)
        result = call_prover(prover, current, tactic)
        steps_taken += 1
        updated = _extract_updated_state(result, current)
        if updated is None:
            # Hard core: rejected / unparseable tactic is a wasted step. No state write.
            continue
        current['hypotheses'] = updated['hypotheses']
        current['goal'] = updated['goal'] or current['goal']
        current['proof_tree'] = updated['proof_tree']
        current['complete'] = bool(updated['complete'])
        current['steps'] = len(current['proof_tree'])
        current['status'] = 'proved' if current['complete'] else 'open'
        problems[pid] = current
        try:
            save_state(state_path, state_doc)
        except Exception:
            pass
        if current['complete']:
            proved = True
            break

    if proved:
        current['complete'] = True
        current['status'] = 'proved'
    elif not current.get('complete'):
        current['status'] = 'stuck'
    problems[pid] = current
    try:
        save_state(state_path, state_doc)
    except Exception:
        pass
    return {
        'problem_id': pid,
        'steps_taken': steps_taken,
        'proved': bool(current.get('complete')),
        'final_state': deepcopy(current),
        'skipped': False,
    }


def write_metrics(path: Path, result: dict) -> None:
    rec = {
        'ts': _now_iso(),
        'problem_id': result.get('problem_id'),
        'steps_taken': int(result.get('steps_taken') or 0),
        'proved': bool(result.get('proved')),
        'final_state': result.get('final_state') or {},
    }
    try:
        _append_jsonl(path, rec)
    except Exception:
        pass


def run_all(
    problems_path: Path,
    state_path: Path,
    metrics_path: Path,
    prover: Path,
    seed: bool = True,
) -> dict:
    try:
        if seed:
            seed_problems(problems_path)
    except Exception:
        pass
    problems = load_problems(problems_path)
    state_doc = load_state(state_path)
    processed = 0
    proved = 0
    for rec in problems:
        pid = rec['id']
        existing = (state_doc.get('problems') or {}).get(pid)
        if isinstance(existing, dict) and (
            existing.get('complete') or existing.get('status') == 'proved'
        ):
            continue
        result = refine_problem(
            pid, rec['goal'], rec['max_steps'], state_doc, state_path, prover
        )
        if result.get('skipped'):
            continue
        write_metrics(metrics_path, result)
        processed += 1
        if result.get('proved'):
            proved += 1
    return {
        'ok': True,
        'processed': processed,
        'proved': proved,
        'open_remaining': sum(
            1
            for rec in problems
            if not ((state_doc.get('problems') or {}).get(rec['id']) or {}).get('complete')
        ),
    }


def status_summary(state_path: Path) -> dict:
    if not state_path.exists():
        return {'ok': True, 'insufficient_data': True, 'n': 0, 'problems': []}
    doc = load_state(state_path)
    rows = []
    for pid, st in (doc.get('problems') or {}).items():
        if not isinstance(st, dict):
            continue
        rows.append({
            'id': pid,
            'status': st.get('status'),
            'complete': bool(st.get('complete')),
            'steps': st.get('steps', len(st.get('proof_tree') or [])),
            'goal': st.get('goal'),
        })
    return {
        'ok': True,
        'ts': doc.get('ts'),
        'n': len(rows),
        'proved': sum(1 for r in rows if r['status'] == 'proved' or r['complete']),
        'open': sum(1 for r in rows if r['status'] == 'open'),
        'stuck': sum(1 for r in rows if r['status'] == 'stuck'),
        'problems': rows,
    }


def self_test() -> int:
    failures: list[str] = []
    prover = PROVER_PATH
    if not prover.exists():
        print('FAIL: mock-rocq-prover.py missing at ' + str(prover))
        return 1

    with tempfile.TemporaryDirectory(prefix='verify-proof-selftest-') as td:
        tdir = Path(td)
        problems_path = tdir / 'proof-problems.jsonl'
        state_path = tdir / 'proof-state.json'
        metrics_path = tdir / 'proof-metrics.jsonl'
        problems_path.write_text(
            json.dumps({
                'id': 'list-reversal',
                'goal': 'forall l, rev (rev l) = l',
                'max_steps': 5,
            }) + '\n',
            encoding='utf-8',
        )
        state_doc = _empty_state_doc()
        result = refine_problem(
            'list-reversal',
            'forall l, rev (rev l) = l',
            5,
            state_doc,
            state_path,
            prover,
        )
        write_metrics(metrics_path, result)
        if not result.get('proved'):
            failures.append('proved is not True: ' + json.dumps(result.get('final_state')))
        if int(result.get('steps_taken') or 0) > 3:
            failures.append('steps_taken={} > 3'.format(result.get('steps_taken')))
        final = result.get('final_state') or {}
        if not final.get('complete'):
            failures.append('final_state.complete is not True')
        if final.get('status') != 'proved':
            failures.append('final_state.status={!r}'.format(final.get('status')))

        # Hard core: a rejected tactic must not grow proof_tree.
        stuck = _new_problem_state('forall l, rev (rev l) = l')
        before_tree = list(stuck['proof_tree'])
        bad = call_prover(prover, stuck, 'reflexivity')
        if str(bad.get('status') or '') == 'ok':
            failures.append('prover accepted reflexivity on empty tree (hard-core gap)')
        extracted = _extract_updated_state(bad, stuck)
        if extracted is not None:
            failures.append('rejected tactic produced an applied state')
        if stuck['proof_tree'] != before_tree:
            failures.append('local proof_tree mutated on reject')

        # Fail-open: missing state file for --status
        missing = status_summary(tdir / 'no-such-proof-state.json')
        if not missing.get('ok'):
            failures.append('status on missing file is not fail-open')

        # Malformed JSONL skipped
        malformed = tdir / 'bad.jsonl'
        malformed.write_text('{not json\n\n', encoding='utf-8')
        loaded = load_problems(malformed)
        if loaded != []:
            failures.append('malformed jsonl was not skipped')

    if failures:
        print('FAIL')
        for f in failures:
            print(' - ' + f)
        return 1
    print('PASS')
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Proof refinement agent (mock Rocq).')
    parser.add_argument('--run', action='store_true', help='process all open problems')
    parser.add_argument('--self-test', action='store_true', help='isolated self-test')
    parser.add_argument('--status', action='store_true', help='print proof-state summary')
    args = parser.parse_args(argv)

    try:
        if args.self_test:
            return self_test()
        if args.status:
            summary = status_summary(STATE_PATH)
            print(json.dumps(summary, indent=2))
            return 0
        # default / --run
        result = run_all(PROBLEMS_PATH, STATE_PATH, METRICS_PATH, PROVER_PATH, seed=True)
        print(json.dumps(result, indent=2))
        return 0
    except Exception:
        # Fail-open: never crash cron.
        try:
            print(json.dumps({
                'ok': True,
                'fail_open': True,
                'error': traceback.format_exc()[-400:],
            }))
        except Exception:
            pass
        return 0


if __name__ == '__main__':
    sys.exit(main())
