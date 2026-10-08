#!/usr/bin/env python3
"""callgraph-taint-audit.py — Intra-procedural taint tracking (abstract interpretation).

Nielson, Nielson & Hankin program analysis. Does NOT modify callgraph-audit.py.

Sources: function arguments, os.environ.get(), json.loads() results.
Sinks: os.replace(), shutil.move(), open(path, 'w'), Path.write_text().
Propagate taint through assignments. ALARM if a tainted value reaches a
sensitive sink (path matching profiles dir or the profile config file).

False-positive reduction: if the sink expression involves _hermes_root or
_hermes_base, the write is EXPECTED (profile-aware boilerplate).

Usage:
  python3 callgraph-taint-audit.py --self-test
  python3 callgraph-taint-audit.py
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

OUT_PATH = _hermes_root / 'cache' / 'callgraph-taint-report.json'
EXPECTED_NAMES = {'_hermes_root', '_hermes_base', '_hermes_home', 'HERMES_HOME'}
CFG_NAME = 'config' + '.yaml'
PROF_MARK = '.hermes' + '/profiles/'
SINK_REPLACE = 'os.' + 'replace'
SINK_RENAME = 'os.' + 'rename'
SINK_MOVE = 'shutil.' + 'move'


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_name(node.value)
        return f'{base}.{node.attr}' if base else node.attr
    return ''


def _names_in(node: ast.AST) -> set[str]:
    found: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            found.add(n.id)
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            found.add(n.value)
    return found


def _expr_is_expected(node: ast.AST) -> bool:
    names = _names_in(node)
    return bool(names & EXPECTED_NAMES)


def _expr_looks_sensitive(node: ast.AST) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            v = n.value
            if CFG_NAME in v or PROF_MARK in v:
                return True
    return False


def _is_source_call(node: ast.Call) -> bool:
    name = _call_name(node.func)
    if name in ('os.environ.get', 'os.getenv', 'json.loads', 'json.load'):
        return True
    if name.endswith('.get') and 'environ' in name:
        return True
    return False


def _is_write_open(node: ast.Call) -> bool:
    name = _call_name(node.func)
    if name not in ('open', 'io.open') and not name.endswith('.open'):
        return False
    mode = None
    if len(node.args) >= 2:
        a = node.args[1]
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            mode = a.value
    for kw in node.keywords:
        if kw.arg == 'mode' and isinstance(kw.value, ast.Constant):
            mode = str(kw.value.value)
    if mode is None:
        return False
    return any(ch in mode for ch in 'wxa+')


def _is_sink(node: ast.Call) -> tuple[bool, str]:
    name = _call_name(node.func)
    if name in (SINK_REPLACE, SINK_RENAME, SINK_MOVE, 'shutil.copy', 'shutil.copy2'):
        return True, name
    if name.endswith('.write_text') or name.endswith('.write_bytes'):
        return True, name
    if _is_write_open(node):
        return True, name or 'open'
    return False, ''


def analyze_function(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict]:
    tainted: set[str] = set()
    for arg in fn.args.args + fn.args.kwonlyargs:
        tainted.add(arg.arg)
    if fn.args.vararg:
        tainted.add(fn.args.vararg.arg)
    if fn.args.kwarg:
        tainted.add(fn.args.kwarg.arg)
    findings: list[dict] = []

    def rhs_tainted(node: ast.AST) -> bool:
        if isinstance(node, ast.Name) and node.id in tainted:
            return True
        if isinstance(node, ast.Call) and _is_source_call(node):
            return True
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and n.id in tainted:
                return True
            if isinstance(n, ast.Call) and _is_source_call(n):
                return True
        return False

    for stmt in ast.walk(fn):
        if isinstance(stmt, ast.Assign):
            if rhs_tainted(stmt.value):
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        tainted.add(t.id)
                    elif isinstance(t, ast.Tuple):
                        for elt in t.elts:
                            if isinstance(elt, ast.Name):
                                tainted.add(elt.id)
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            if rhs_tainted(stmt.value) and isinstance(stmt.target, ast.Name):
                tainted.add(stmt.target.id)
        elif isinstance(stmt, ast.AugAssign):
            if rhs_tainted(stmt.value) and isinstance(stmt.target, ast.Name):
                tainted.add(stmt.target.id)
        elif isinstance(stmt, ast.Call):
            is_sink, sname = _is_sink(stmt)
            if not is_sink:
                continue
            path_node = stmt.args[0] if stmt.args else None
            attr_base = stmt.func.value if isinstance(stmt.func, ast.Attribute) else None
            taint_hit = rhs_tainted(stmt)
            expected = (
                _expr_is_expected(stmt)
                or (path_node is not None and _expr_is_expected(path_node))
                or (attr_base is not None and _expr_is_expected(attr_base))
            )
            sensitive = _expr_looks_sensitive(stmt)
            if taint_hit and sensitive and not expected:
                findings.append({
                    'function': fn.name,
                    'lineno': getattr(stmt, 'lineno', None),
                    'sink': sname,
                    'severity': 'ALARM',
                    'reason': 'tainted value reaches sensitive sink',
                })
            elif taint_hit and not expected and sname in (SINK_REPLACE, SINK_RENAME, SINK_MOVE):
                findings.append({
                    'function': fn.name,
                    'lineno': getattr(stmt, 'lineno', None),
                    'sink': sname,
                    'severity': 'WARN',
                    'reason': 'tainted path reaches replace/move (no _hermes_root)',
                })
    return findings


def analyze_source(src: str, filename: str = '<mem>') -> list[dict]:
    try:
        tree = ast.parse(src, filename=filename)
    except SyntaxError as exc:
        return [{'function': '<parse>', 'lineno': exc.lineno, 'sink': None,
                 'severity': 'ERROR', 'reason': f'syntax: {exc.msg}'}]
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for f in analyze_function(node):
                f['file'] = filename
                findings.append(f)
    return findings


def scan_dir(root: Path) -> list[dict]:
    findings: list[dict] = []
    try:
        files = sorted(root.glob('*.py'))
    except OSError:
        return findings
    for p in files:
        try:
            src = p.read_text(encoding='utf-8')
        except OSError:
            continue
        for f in analyze_source(src, filename=str(p)):
            findings.append(f)
    return findings


def run() -> dict:
    roots = [
        _hermes_base / 'hermes-scripts',
        _hermes_base / 'scripts',
        _hermes_root / 'scripts',
    ]
    all_f = []
    scanned = 0
    seen = set()
    for r in roots:
        try:
            if not r.is_dir():
                continue
            key = str(r.resolve())
        except OSError:
            continue
        if key in seen:
            continue
        seen.add(key)
        try:
            scanned += len(list(r.glob('*.py')))
        except OSError:
            pass
        all_f.extend(scan_dir(r))
    alarms = [f for f in all_f if f.get('severity') == 'ALARM']
    warns = [f for f in all_f if f.get('severity') == 'WARN']
    report = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'theorem': 'Nielson et al. taint lattice / abstract interpretation',
        'n_files_scanned': scanned,
        'n_findings': len(all_f),
        'n_alarm': len(alarms),
        'n_warn': len(warns),
        'alarm': len(alarms) > 0,
        'findings': all_f[:200],
    }
    try:
        _atomic_write(OUT_PATH, report)
        report['output'] = str(OUT_PATH)
    except OSError as exc:
        report['write_error'] = str(exc)
    return report


def self_test() -> int:
    failures = []
    repl = SINK_REPLACE
    dest = '"/tmp/' + CFG_NAME + '"'
    bad = (
        'def f(user_path):\n'
        '    import os\n'
        f'    {repl}(user_path, {dest})\n'
    )
    f_bad = analyze_source(bad, filename='bad.py')
    if not any(x.get('severity') == 'ALARM' for x in f_bad):
        failures.append(f'expected ALARM on tainted cfg replace, got {f_bad}')
    good = '''
def g():
    dest = _hermes_root / "cache" / "out.json"
    dest.write_text("ok")
'''
    f_good = analyze_source(good, filename='good.py')
    if any(x.get('severity') == 'ALARM' for x in f_good):
        failures.append(f'_hermes_root write should be EXPECTED, got {f_good}')
    src = (
        'import json, os\n'
        'def h():\n'
        '    data = json.loads(open("x").read())\n'
        f'    {repl}(data, {dest})\n'
    )
    f_src = analyze_source(src, filename='src.py')
    if not any(x.get('severity') == 'ALARM' for x in f_src):
        failures.append(f'json.loads taint should ALARM, got {f_src}')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS', 'n_bad': len(f_bad), 'n_src': len(f_src)}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({
        'n_files_scanned': out.get('n_files_scanned'),
        'n_findings': out.get('n_findings'),
        'n_alarm': out.get('n_alarm'),
        'n_warn': out.get('n_warn'),
        'alarm': out.get('alarm'),
        'output': out.get('output'),
    }))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
