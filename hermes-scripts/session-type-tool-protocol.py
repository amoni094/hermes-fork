#!/usr/bin/env python3
"""session-type-tool-protocol.py — Honda session types for tool sequences.

Dual of counterfactual-tool-gate (redundancy). Here a tool whose
preconditions are not yet achieved is a PROTOCOL_VIOLATION.

Usage:
  python3 session-type-tool-protocol.py --self-test
  python3 session-type-tool-protocol.py --sequence patch,write_file
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


def check_protocol(tools: list[str]) -> dict:
    names = [str(t).strip() for t in tools if str(t).strip()]
    achieved: set[str] = set()
    violations = []
    for i, name in enumerate(names):
        spec = REGISTRY.get(name)
        if spec is None:
            continue
        missing = spec['pre'] - achieved
        if missing:
            violations.append({'index': i, 'tool': name, 'missing': sorted(missing)})
        achieved |= spec['post']
        achieved |= spec['pre']
    return {
        'sequence': names,
        'violations': violations,
        'n_violations': len(violations),
        'alarm': len(violations) > 0,
        'theorem': 'Honda session types; linear protocol fidelity of tool pre/post',
    }


def self_test() -> int:
    failures = []
    r = check_protocol(['patch'])
    if not r['alarm'] or r['violations'][0]['tool'] != 'patch':
        failures.append(f'patch without read should violate {r}')
    r2 = check_protocol(['read_file', 'patch'])
    if r2['alarm']:
        failures.append(f'read then patch should be ok {r2}')
    r3 = check_protocol(['browser_click'])
    if not r3['alarm']:
        failures.append('click without snapshot')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS'}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--sequence', default='')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = check_protocol([t for t in args.sequence.split(',') if t.strip()])
    print(json.dumps(out, indent=2))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
