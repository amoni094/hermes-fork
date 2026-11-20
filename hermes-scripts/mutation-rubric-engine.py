#!/usr/bin/env python3
"""Bloom-filter mutation testing for LLM tool-call evaluation rubrics."""
from __future__ import annotations
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
import argparse
import hashlib
import json
from typing import Iterable

def _h(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)

class Bloom:
    def __init__(self, m: int = 2048, k: int = 3):
        self.m = m
        self.k = k
        self.bits = [0] * m

    def add(self, item: str) -> None:
        for i in range(self.k):
            self.bits[(_h('%d:%s' % (i, item)) % self.m)] = 1

    def __contains__(self, item: str) -> bool:
        return all(self.bits[(_h('%d:%s' % (i, item)) % self.m)] for i in range(self.k))

def mutate_call(call: dict) -> list:
    name = str(call.get('tool') or call.get('name') or 'tool')
    args = dict(call.get('args') or {})
    extra = dict(args)
    extra['__injected'] = True
    return [
        {'mutation': 'drop_required_arg', 'tool': name, 'args': {}},
        {'mutation': 'widen_return', 'tool': name, 'args': args, 'returns': 'Any'},
        {'mutation': 'add_side_effect', 'tool': name, 'args': args, 'side_effect': 'fs_write'},
        {'mutation': 'rename_tool', 'tool': name + '_shadow', 'args': args},
        {'mutation': 'inject_extra_arg', 'tool': name, 'args': extra},
    ]

def _sig(call: dict) -> str:
    return json.dumps({'tool': call.get('tool'), 'args': sorted((call.get('args') or {}).keys())}, sort_keys=True)

class RubricEngine:
    def __init__(self):
        self.allowed = Bloom()
        self._exact = set()

    def allow(self, call: dict) -> None:
        s = _sig(call)
        self._exact.add(s)
        self.allowed.add(s)

    def accepts(self, call: dict) -> bool:
        return _sig(call) in self._exact

    def false_accept_rate(self, mutated_calls: Iterable[dict]) -> float:
        mutated = list(mutated_calls)
        if not mutated:
            return 0.0
        fa = sum(1 for c in mutated if self.accepts(c))
        return fa / len(mutated)

def layer1_demo() -> None:
    engine = RubricEngine()
    golden = [
        {'tool': 'read_file', 'args': {'path': 'a.txt'}},
        {'tool': 'web_search', 'args': {'query': 'x'}},
        {'tool': 'terminal', 'args': {'command': 'ls'}},
    ]
    for g in golden:
        engine.allow(g)
    mutated = []
    for g in golden:
        mutated.extend(mutate_call(g))
    while len(mutated) < 500:
        mutated.extend(mutate_call(golden[len(mutated) % 3]))
    mutated = mutated[:500]
    far = engine.false_accept_rate(mutated)
    assert far <= 0.15, far
    assert engine.accepts(golden[0]) is True
    print('[layer1] PASS FAR=%.4f n=%d' % (far, len(mutated)))

def main() -> None:
    pa = argparse.ArgumentParser()
    pa.add_argument('--layer1', action='store_true')
    pa.add_argument('--self-test', action='store_true')
    args = pa.parse_args()
    if args.layer1 or args.self_test:
        layer1_demo()
        return
    print(json.dumps({'ok': True, 'mode': 'noop'}))

if __name__ == '__main__':
    main()
