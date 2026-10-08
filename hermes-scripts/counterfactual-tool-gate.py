#!/usr/bin/env python3
"""counterfactual-tool-gate.py — Pearl Rung-3 minimal tool-set gate.

Amodei safety category 3 (minimal footprint). Before multi-tool sequences,
check whether a smaller tool set achieves the same state change.

Tool B is redundant if its postconditions are already achieved by earlier
tools (so later tools' preconditions that B was satisfying are already met).

Usage:
  python3 counterfactual-tool-gate.py --self-test
  python3 counterfactual-tool-gate.py --sequence read_file,read_file,write_file
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

# 20 common tools: (preconditions, postconditions)
REGISTRY: dict[str, dict[str, set[str]]] = {
    'read_file': {'pre': set(), 'post': {'file_content_available'}},
    'search_files': {'pre': set(), 'post': {'pattern_results'}},
    'terminal': {'pre': set(), 'post': {'command_executed'}},
    'write_file': {'pre': set(), 'post': {'file_written'}},
    'patch': {'pre': {'file_content_available'}, 'post': {'file_patched'}},
    'web_search': {'pre': set(), 'post': {'search_results'}},
    'web_extract': {'pre': {'search_results'}, 'post': {'page_content'}},
    'browser_navigate': {'pre': set(), 'post': {'page_loaded'}},
    'browser_snapshot': {'pre': {'page_loaded'}, 'post': {'dom_snapshot'}},
    'browser_click': {'pre': {'dom_snapshot'}, 'post': {'ui_clicked'}},
    'skill_view': {'pre': set(), 'post': {'skill_loaded'}},
    'skill_manage': {'pre': {'skill_loaded'}, 'post': {'skill_mutated'}},
    'execute_code': {'pre': set(), 'post': {'code_executed'}},
    'hermes_web_search': {'pre': set(), 'post': {'search_results'}},
    'tool_describe': {'pre': set(), 'post': {'tool_schema'}},
    'tool_call': {'pre': {'tool_schema'}, 'post': {'tool_invoked'}},
    'vision_analyze': {'pre': set(), 'post': {'image_described'}},
    'todo_list': {'pre': set(), 'post': {'todo_updated'}},
    'session_search': {'pre': set(), 'post': {'session_hits'}},
    'process_manage': {'pre': {'command_executed'}, 'post': {'process_controlled'}},
}

WARN_RATIO = 0.5


def analyze_sequence(tools: list[str]) -> dict:
    names = [str(t).strip() for t in tools if str(t).strip()]
    achieved: set[str] = set()
    redundant: list[dict] = []
    minimal: list[str] = []
    unknown: list[str] = []
    for i, name in enumerate(names):
        spec = REGISTRY.get(name)
        if spec is None:
            unknown.append(name)
            minimal.append(name)
            continue
        post = set(spec['post'])
        if post and post.issubset(achieved):
            redundant.append({
                'index': i,
                'tool': name,
                'already_achieved': sorted(post),
            })
            continue
        minimal.append(name)
        achieved |= post
        achieved |= set(spec['pre'])  # satisfied preconditions also "held"
    total = len(names) if names else 0
    n_red = len(redundant)
    ratio = (n_red / total) if total else 0.0
    alarm = ratio > WARN_RATIO
    return {
        'proposed_tool_sequence': names,
        'redundancy_ratio': ratio,
        'redundant_tools': redundant,
        'minimal_set': minimal,
        'unknown_tools': unknown,
        'alarm': alarm,
        'theorem': 'Pearl Rung 3 counterfactual deletion; Amodei cat.3 minimal footprint',
    }


def self_test() -> int:
    failures = []
    r = analyze_sequence(['read_file', 'read_file', 'write_file'])
    red_names = [x['tool'] for x in r['redundant_tools']]
    if red_names != ['read_file']:
        failures.append(f'expected second read_file redundant, got {r}')
    if r['redundant_tools'][0]['index'] != 1:
        failures.append('read_file[1] should be flagged')
    if r['minimal_set'] != ['read_file', 'write_file']:
        failures.append(f'minimal_set {r["minimal_set"]}')
    # ratio 1/3 = 0.333 not > 0.5
    if r['alarm']:
        failures.append('1/3 should not alarm')
    r2 = analyze_sequence(['read_file', 'read_file', 'read_file'])
    if r2['redundancy_ratio'] < 0.5 or not r2['alarm']:
        failures.append('2/3 redundant should alarm')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS', 'demo': r}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--sequence', default='', help='comma-separated tool names')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    tools = [t.strip() for t in args.sequence.split(',') if t.strip()]
    out = analyze_sequence(tools)
    print(json.dumps(out, indent=2))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
