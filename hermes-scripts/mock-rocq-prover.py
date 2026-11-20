#!/usr/bin/env python3
"""mock-rocq-prover.py — mock Rocq-style structured proof feedback.

Deterministic: the same (state, tactic) pair always yields the same result.
When a tactic is accepted, the response includes the updated proof state.
The caller (verify-proof-agent.py) persists that state.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

DEFAULT_GOAL = 'forall l, rev(rev(l)) = l'
INDUCTION_SCHEMA_VALUE = (
    'forall P, P(nil) /\\ (forall x xs, P(xs) -> P(cons x xs)) -> forall l, P(l)'
)
BASE_CASE_VALUE = 'rev(nil) = nil'
COMPLETING = frozenset(('qed', 'done', 'reflexivity'))
BASE_TACTICS = frozenset(('base_case', 'base'))


def empty_state(goal=None):
    return {
        'hypotheses': {},
        'goal': DEFAULT_GOAL if goal is None else goal,
        'proof_tree': [],
        'complete': False,
    }


def error_payload(message, missing=None, state=None):
    out = {
        'status': 'error',
        'missing': missing,
        'message': message,
        'accepted_tactic': None,
    }
    if state is not None:
        out['state'] = state
    return out


def ok_payload(tactic, message, state):
    return {
        'status': 'ok',
        'missing': None,
        'message': message,
        'accepted_tactic': tactic,
        'state': state,
    }


def normalize_state(raw):
    if not isinstance(raw, dict):
        raise ValueError('state must be a JSON object')
    hyps = raw.get('hypotheses')
    if hyps is None:
        hyps = {}
    if not isinstance(hyps, dict):
        raise ValueError('hypotheses must be an object')
    goal = raw.get('goal', '')
    if goal is None:
        goal = ''
    if not isinstance(goal, str):
        goal = str(goal)
    tree = raw.get('proof_tree')
    if tree is None:
        tree = []
    if not isinstance(tree, list):
        raise ValueError('proof_tree must be a list')
    complete = bool(raw.get('complete', False))
    return {
        'hypotheses': {str(k): v for k, v in hyps.items()},
        'goal': goal,
        'proof_tree': list(tree),
        'complete': complete,
    }


def apply_tactic(state, tactic):
    """Apply tactic to state. Never accept a tactic that leaves a known gap unfilled."""
    state = normalize_state(state)
    tactic = '' if tactic is None else str(tactic).strip()

    if state.get('complete'):
        return error_payload('proof already complete', state=state)

    hyps = state['hypotheses']
    tree = state['proof_tree']
    has_ind = 'induction_schema' in hyps
    has_base = 'base_case' in hyps

    # Hard core: NEVER accept a tactic that leaves a known gap unfilled.
    if (not tree) and tactic != 'induction':
        return error_payload(
            'proof_tree is empty; first tactic must be induction',
            missing='induction_schema',
            state=state,
        )
    if (not has_ind) and tactic != 'induction':
        return error_payload(
            'induction_schema is not in hypotheses; apply induction first',
            missing='induction_schema',
            state=state,
        )
    if has_ind and (not has_base) and tactic not in BASE_TACTICS:
        return error_payload(
            'base_case is not in hypotheses; apply base_case (or base) next',
            missing='base_case',
            state=state,
        )

    new_state = copy.deepcopy(state)

    if tactic == 'induction':
        new_state['hypotheses']['induction_schema'] = INDUCTION_SCHEMA_VALUE
        new_state['proof_tree'].append(tactic)
        new_state['complete'] = False
        return ok_payload(tactic, 'applied induction; induction_schema added', new_state)

    if tactic in BASE_TACTICS:
        new_state['hypotheses']['base_case'] = BASE_CASE_VALUE
        new_state['proof_tree'].append(tactic)
        new_state['complete'] = False
        return ok_payload(tactic, 'applied base case; base_case added', new_state)

    if has_ind and has_base and tactic in COMPLETING:
        new_state['proof_tree'].append(tactic)
        new_state['complete'] = True
        return ok_payload(tactic, 'proof complete', new_state)

    return error_payload(
        'tactic does not discharge remaining goals',
        missing=None,
        state=state,
    )


def load_state(path):
    if path == '-':
        text = sys.stdin.read()
    else:
        text = Path(path).read_text(encoding='utf-8')
    return json.loads(text)


def emit(obj, exit_code):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + '\n')
    raise SystemExit(exit_code)


def layer1_demo():
    """List-reversal proof: induction -> base_case -> reflexivity."""
    state = empty_state()
    r1 = apply_tactic(state, 'induction')
    if r1.get('status') != 'ok':
        return False, f'step1 induction not ok: {r1}'
    state = r1['state']
    if 'induction_schema' not in state.get('hypotheses', {}):
        return False, 'step1 did not add induction_schema'
    r2 = apply_tactic(state, 'base_case')
    if r2.get('status') != 'ok':
        return False, f'step2 base_case not ok: {r2}'
    state = r2['state']
    if 'base_case' not in state.get('hypotheses', {}):
        return False, 'step2 did not add base_case'
    r3 = apply_tactic(state, 'reflexivity')
    if r3.get('status') != 'ok':
        return False, f'step3 reflexivity not ok: {r3}'
    state = r3['state']
    hyps = state.get('hypotheses') or {}
    if 'induction_schema' not in hyps or 'base_case' not in hyps:
        return False, f'final state missing keys: {sorted(hyps)}'
    if not state.get('complete'):
        return False, 'final state not complete'
    if r1['status'] != 'ok' or r2['status'] != 'ok' or r3['status'] != 'ok':
        return False, 'not all steps ok'
    return True, 'ok'


def self_test():
    ok, _detail = layer1_demo()
    if ok:
        print('PASS')
        raise SystemExit(0)
    print('FAIL')
    raise SystemExit(1)


def main(argv=None):
    p = argparse.ArgumentParser(description='Mock Rocq-style theorem prover')
    p.add_argument('--state', help="Path to proof state JSON, or '-' for stdin")
    p.add_argument('--tactic', help='Proposed tactic')
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        self_test()
    if args.state is None or args.tactic is None:
        emit(error_payload('require --state PATH and --tactic TACTIC (or --self-test)'), 1)
    try:
        raw = load_state(args.state)
    except json.JSONDecodeError as e:
        emit(error_payload(f'invalid JSON: {e}'), 1)
    except OSError as e:
        emit(error_payload(f'cannot read state: {e}'), 1)
    except Exception as e:
        emit(error_payload(f'invalid input: {e}'), 1)
    try:
        result = apply_tactic(raw, args.tactic)
    except Exception as e:
        emit(error_payload(f'invalid state: {e}'), 1)
    emit(result, 0)


if __name__ == '__main__':
    main()
