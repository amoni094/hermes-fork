#!/usr/bin/env python3
"""session-phase-complexity.py — Phase-space reflection complexity for context budget.

Theory (3B1B 'Colliding Blocks Compute Pi'; Hamiltonian mechanics):
  In the colliding-blocks problem, the number of collisions (reflections
  in phase space) encodes information about the mass ratio. More reflections
  = more complex trajectory = more information needed to describe the state.

  Hermes application:
    Agent sessions are phase-space trajectories. Each 'reflection'
    (tool call that fails and is retried, an assistant correction, a
    re-plan after a wrong action) adds one unit of complexity.

    Complexity C = log2(1 + N_reflections)   [bits to describe trajectory]

    A high-complexity session is in a 'chaotic' region of state space and
    needs MORE context budget (the agent must track more state to avoid
    getting lost). A low-complexity session is smooth and can tolerate
    aggressive compaction.

Hard cores:
  - C >= 0 always (log2(1) = 0 when no reflections)
  - Monotone: more reflections => higher C
  - Budget multiplier: budget_scale = 1 + alpha * C  (alpha tunable)
  - DPI: compaction ratio cannot go below 1/(1 + C) or we lose trajectory info

Usage:
  python3 session-phase-complexity.py --self-test
  python3 session-phase-complexity.py [--dry-run] [--alpha FLOAT]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'session-phase-complexity.json'
SESSIONS_DIR = _hermes_root / 'sessions'

ALPHA = 0.25  # budget_scale = 1 + alpha * C

# Reflection signals: patterns in messages indicating a correction/retry
REFLECTION_PATTERNS = [
    'let me try again',
    'actually,',
    "i made an error",
    'retry',
    'that was wrong',
    'correction:',
    'exit_code: 1',
    'exit_code":1',
    'error:',
    'traceback',
    'failed',
    'exception',
    'let me reconsider',
    'i was wrong',
    'apologies',
]


def count_reflections(messages: list[dict]) -> int:
    """Count reflection events in a session's message stream."""
    n = 0
    for msg in messages:
        role = msg.get('role', '')
        content = str(msg.get('content', '') or '')
        if isinstance(msg.get('content'), list):
            content = ' '.join(
                c.get('text', '') if isinstance(c, dict) else str(c)
                for c in msg['content']
            )
        content_lower = content.lower()
        if role in ('tool', 'assistant'):
            for pat in REFLECTION_PATTERNS:
                if pat in content_lower:
                    n += 1
                    break  # one per message
    return n


def phase_complexity(n_reflections: int, alpha: float = ALPHA) -> dict:
    """
    C = log2(1 + n_reflections).
    budget_scale = 1 + alpha * C.
    min_keep_ratio = 1 / (1 + C) [DPI floor].
    """
    C = math.log2(1 + n_reflections)
    budget_scale = 1.0 + alpha * C
    min_keep_ratio = 1.0 / (1.0 + C) if C > 0 else 1.0
    return {
        'n_reflections': n_reflections,
        'complexity_bits': round(C, 4),
        'budget_scale': round(budget_scale, 4),
        'min_keep_ratio': round(min_keep_ratio, 4),
        'alpha': alpha,
    }


def _load_latest_session() -> list[dict]:
    sessions = []
    for f in SESSIONS_DIR.glob('*.jsonl'):
        try:
            sessions.append((f.stat().st_mtime, f))
        except Exception:
            pass
    if not sessions:
        return []
    sessions.sort(reverse=True)
    try:
        msgs = []
        for line in sessions[0][1].read_text('utf-8', errors='replace').splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                msgs.append(obj)
        return msgs
    except Exception:
        return []


def _atomic_write(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        pass


def run(dry_run: bool = False, alpha: float = ALPHA) -> dict:
    messages = _load_latest_session()
    n = count_reflections(messages)
    pc = phase_complexity(n, alpha=alpha)
    result = {
        'ts': int(time.time()),
        'n_messages': len(messages),
        **pc,
    }
    if not dry_run:
        _atomic_write(OUT_PATH, result)
    return result


def self_test() -> None:
    # Hard core: C >= 0 always
    assert phase_complexity(0)['complexity_bits'] == 0.0
    assert phase_complexity(1)['complexity_bits'] > 0.0
    assert phase_complexity(10)['complexity_bits'] > phase_complexity(1)['complexity_bits']

    # DPI floor: min_keep_ratio in (0, 1]
    for n in [0, 1, 5, 100]:
        pc = phase_complexity(n)
        assert 0.0 < pc['min_keep_ratio'] <= 1.0, f"min_keep_ratio OOR: {pc}"

    # Budget scale >= 1.0 always
    for n in [0, 3, 50]:
        assert phase_complexity(n)['budget_scale'] >= 1.0

    # Monotone in n_reflections
    pcs = [phase_complexity(n) for n in range(10)]
    for i in range(len(pcs) - 1):
        assert pcs[i]['complexity_bits'] <= pcs[i+1]['complexity_bits']
        assert pcs[i]['budget_scale'] <= pcs[i+1]['budget_scale']

    # count_reflections: synthetic
    msgs = [
        {'role': 'assistant', 'content': 'Let me try again, retrying the approach.'},
        {'role': 'tool', 'content': 'exit_code":1 error: file not found'},
        {'role': 'user', 'content': 'please fix it'},
        {'role': 'assistant', 'content': 'Here is the result.'},
    ]
    n = count_reflections(msgs)
    assert n == 2, f"Expected 2 reflections, got {n}"

    # Zero reflections for clean session
    clean = [
        {'role': 'user', 'content': 'What is 2+2?'},
        {'role': 'assistant', 'content': '4.'},
    ]
    assert count_reflections(clean) == 0

    print("self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--alpha', type=float, default=ALPHA)
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    result = run(dry_run=args.dry_run, alpha=args.alpha)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
