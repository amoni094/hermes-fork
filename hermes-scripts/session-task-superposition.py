#!/usr/bin/env python3
"""session-task-superposition.py — Pre-collapse task-type mixture for skill preloading.

Theory (quantum superposition): session starts in mixture P(task_type).
Skill preload weight = sum_t P(t) * affinity(skill, t).
First tool call collapses to one task type (measurement).
"""
from __future__ import annotations
import argparse, json, math, os, re, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'session-task-superposition.json'
SESSIONS_DIR = _root / 'sessions'

TASKS = {
    'code':     {'python','debug','patch','test','traceback','error','fix','script','function'},
    'research': {'search','arxiv','paper','cite','web','find','article','read','wiki'},
    'memory':   {'remember','recall','preference','user','profile','note','save','store'},
    'sysadmin': {'cron','systemd','hyprland','dns','vpn','ssh','config','service','daemon'},
    'ops':      {'deploy','build','docker','git','commit','push','pull','merge','release'},
}

TOOL_TO_TASK = {
    'web_search': 'research', 'web_extract': 'research', 'browser_navigate': 'research',
    'terminal': 'ops', 'execute_code': 'code', 'patch': 'code',
    'write_file': 'ops', 'read_file': 'research', 'search_files': 'research',
    'skill_manage': 'memory', 'memory': 'memory',
    'cronjob_manage': 'sysadmin',
}

def posterior(text, tasks=TASKS):
    toks = set(re.findall(r'[a-z0-9]+', text.lower()))
    raw = {t: 1.0 + len(toks & vocab) for t, vocab in tasks.items()}
    z = sum(raw.values())
    return {t: round(v/z, 6) for t, v in raw.items()}

def preload_weights(P, skill_task_affinity):
    """skill_task_affinity: {skill_name: {task: weight}}."""
    return {s: round(sum(P.get(t, 0.0) * w.get(t, 0.0) for t in P), 6)
            for s, w in skill_task_affinity.items()}

def collapse(P, tool_name, tool_to_task=TOOL_TO_TASK):
    t = tool_to_task.get(tool_name)
    if not t: return P, False
    return {u: 1.0 if u == t else 0.0 for u in P}, True

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def _load_latest_session_text():
    files = []
    try:
        for f in SESSIONS_DIR.glob('*.jsonl'):
            try:
                files.append((f.stat().st_mtime, f))
            except Exception:
                pass
    except Exception:
        return None
    if not files:
        return None
    files.sort(reverse=True)
    parts = []
    try:
        for line in files[0][1].read_text('utf-8', errors='replace').splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            if obj.get('role') not in ('user', 'assistant'):
                continue
            c = obj.get('content', '')
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, list):
                for item in c:
                    if isinstance(item, str):
                        parts.append(item)
                    elif isinstance(item, dict) and item.get('type') == 'text':
                        parts.append(item.get('text', ''))
    except Exception:
        return None
    text = ' '.join(parts).strip()
    return text or None


def run(query='', tool=None, dry_run=False):
    text = query
    if not text:
        text = _load_latest_session_text()
        if not text:
            return {'ts': int(time.time()), 'skipped': True}
    P = posterior(text)
    collapsed = False
    if tool:
        P, collapsed = collapse(P, tool)
    result = {'ts': int(time.time()), 'query': text[:200], 'tool': tool,
              'collapsed': collapsed, 'P': P}
    if not dry_run:
        _atomic_write(OUT, result)
    return result

def self_test():
    # Empty query: near-uniform (each > 0.1 for 5 tasks, no task > 2x any other)
    P0 = posterior('')
    assert abs(sum(P0.values()) - 1.0) < 1e-6, f"sum(P)!=1: {P0}"
    assert max(P0.values()) < 2 * min(P0.values()) + 0.01, f"not near-uniform: {P0}"

    # Code-heavy query
    P_code = posterior('debug python traceback error test')
    assert P_code['code'] > P_code['research'], f"code not highest: {P_code}"
    assert P_code['code'] > P_code['sysadmin'], f"code not > sysadmin: {P_code}"
    assert abs(sum(P_code.values()) - 1.0) < 1e-6

    # Collapse: web_search -> research=1
    P_col, collapsed = collapse(P_code, 'web_search')
    assert collapsed
    assert P_col['research'] == 1.0
    assert all(P_col[t] == 0.0 for t in P_col if t != 'research')
    assert abs(sum(P_col.values()) - 1.0) < 1e-6

    # After code collapse: research-only skill has weight 0
    affinity = {'research_skill': {'research': 1.0, 'code': 0.0, 'memory': 0.0, 'sysadmin': 0.0, 'ops': 0.0},
                'code_skill':     {'code': 1.0, 'research': 0.0, 'memory': 0.0, 'sysadmin': 0.0, 'ops': 0.0}}
    P_code_collapse = {t: 1.0 if t == 'code' else 0.0 for t in TASKS}
    weights = preload_weights(P_code_collapse, affinity)
    assert weights['research_skill'] == 0.0, f"research skill should be 0 after code collapse: {weights}"
    assert weights['code_skill'] == 1.0, f"code skill should be 1 after code collapse: {weights}"

    # Unknown tool: no collapse
    P2, c2 = collapse(P_code, 'unknown_tool_xyz')
    assert not c2
    assert P2 == P_code

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--query', type=str, default='')
    p.add_argument('--tool', type=str, default=None)
    args = p.parse_args()
    if args.self_test: self_test(); return
    result = run(args.query, args.tool, args.dry_run)
    if result.get('skipped'):
        return
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
