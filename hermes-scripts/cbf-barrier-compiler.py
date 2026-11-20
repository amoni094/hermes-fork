#!/usr/bin/env python3
"""Time-invariant control-barrier compiler for irreversible tool calls.

Compiles V(state) = margin - (turns_used + k * irreversible_actions).
Rejects a proposed irreversible action when predicted V would go negative.
Writes session-barrier-state.json.

Plugin pre_tool_call hook (loop-pid-plugin.py) is governance-gated and
is NOT installed by this script.

Usage:
  python3 cbf-barrier-compiler.py --self-test
  python3 cbf-barrier-compiler.py [--margin 10] [--k 3]
"""
from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'session-barrier-state.json'

IRREVERSIBLE = frozenset({'stop', 'delete', 'commit', 'rm', 'write_file', 'patch'})


def barrier(margin, turns_used, n_irrev, k=3.0):
    return float(margin) - (float(turns_used) + float(k) * float(n_irrev))


def predict_next(margin, turns_used, n_irrev, action, k=3.0):
    irrev = action.lower() in IRREVERSIBLE
    return barrier(margin, turns_used + 1, n_irrev + (1 if irrev else 0), k=k), irrev


def decide(margin, turns_used, n_irrev, action, k=3.0):
    v_now = barrier(margin, turns_used, n_irrev, k=k)
    v_next, irrev = predict_next(margin, turns_used, n_irrev, action, k=k)
    reject = irrev and v_next < 0
    return {
        'action': action,
        'irreversible': irrev,
        'V': v_now,
        'V_next': v_next,
        'reject': reject,
    }


def compile_state(margin=10.0, k=3.0, turns_used=0, n_irrev=0, last=None):
    return {
        'ts': datetime.now(UTC).isoformat(),
        'margin': margin,
        'k': k,
        'turns_used': turns_used,
        'irreversible_actions_taken': n_irrev,
        'V': barrier(margin, turns_used, n_irrev, k=k),
        'last_decision': last,
        'irreversible_set': sorted(IRREVERSIBLE),
    }


def run(margin=10.0, k=3.0):
    payload = compile_state(margin=margin, k=k)
    try:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = OUT_PATH.with_suffix(OUT_PATH.suffix + '.tmp')
        tmp.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, OUT_PATH)
    except Exception:
        pass
    try:
        shadow = Path.home() / '.hermes' / 'cache' / 'shadow' / 'session-barrier-state.json'
        shadow.parent.mkdir(parents=True, exist_ok=True)
        tmp = shadow.with_suffix('.tmp')
        tmp.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, shadow)
    except Exception:
        pass
    return payload


def _self_test() -> int:
    v0 = barrier(10, 0, 0, k=3)
    assert v0 == 10.0
    d = decide(10, 4, 1, 'delete', k=3)
    assert d['reject'] is True, d
    d_ok = decide(10, 0, 0, 'read_file', k=3)
    assert d_ok['reject'] is False
    # layer1: turn 4, one prior irrev, V-margin ~1 after next irrev => reject
    # V(4,1)=10-(4+3)=3; V_next delete=10-(5+6)=-1
    assert decide(10, 4, 1, 'delete', k=3)['V_next'] < 0
    # safe reversible never rejected
    for t in range(6):
        assert decide(10, t, 0, 'read', k=3)['reject'] is False
        assert barrier(10, t, 0, k=3) >= 0
    print('[cbf-barrier-compiler] --self-test PASS')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--margin', type=float, default=10.0)
    ap.add_argument('--k', type=float, default=3.0)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[cbf-barrier-compiler] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        run(margin=args.margin, k=args.k)
    except Exception as e:
        print(f'[cbf-barrier-compiler] ERROR (suppressed): {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
