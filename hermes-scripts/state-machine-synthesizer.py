#!/usr/bin/env python3
"""Synthesize a tiny FSM from observed (state, action, next) traces."""
from __future__ import annotations
import argparse, json, os, sqlite3, sys, tempfile, uuid
from collections import defaultdict
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

OUT_PATH = CACHE / 'state-machine.json'


def synthesize(traces):
    trans = defaultdict(Counterish)
    states = set()
    n = 0
    for tr in traces or []:
        if not isinstance(tr, (list, tuple)) or len(tr) < 3:
            continue
        s, a, sp = tr[0], tr[1], tr[2]
        states.add(s)
        states.add(sp)
        trans[(s, a)][sp] += 1
        n += 1
    if n == 0:
        return {
            'n_traces': 0,
            'n_states': 0,
            'n_transitions': 0,
            'start': None,
            'transitions': [],
            'status': 'insufficient_data',
            'ts': _now(),
        }
    edges = []
    for (s, a), dests in trans.items():
        tot = sum(dests.values()) or 1
        best = max(dests, key=lambda k: dests[k])
        edges.append({'from': s, 'action': a, 'to': best, 'p': dests[best] / tot})
    return {
        'n_traces': n,
        'n_states': len(states),
        'n_transitions': len(edges),
        'start': min(states) if states else None,
        'transitions': edges[:80],
        'status': 'ok',
        'ts': _now(),
    }


class Counterish(dict):
    def __missing__(self, k):
        self[k] = 0
        return 0


def _self_test() -> int:
    empty = synthesize([])
    assert empty['status'] == 'insufficient_data'
    traces = [('idle', 'go', 'run'), ('run', 'ok', 'idle'), ('run', 'fail', 'idle')]
    r = synthesize(traces)
    assert r['n_states'] >= 2
    tmp = _temp_out('sms')
    _atomic_write(tmp, r)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    print('[state-machine-synthesizer] --self-test PASS n={}'.format(r['n_states']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[state-machine-synthesizer] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        r = synthesize([])
        print(json.dumps(r))
    except Exception:
        pass


if __name__ == '__main__':
    main()
