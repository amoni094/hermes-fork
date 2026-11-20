#!/usr/bin/env python3
"""Verify software-related outputs: parse, safe shell, allowed paths."""
from __future__ import annotations
import argparse, ast, json, os, re, sys, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'software-verifier-result.json'
UNSAFE_SHELL = re.compile(r'\brm\s+-rf\b|\bsudo\b.*\b-S\b|\bsudo\b.*password|curl\s+[^|]*\|\s*sh', re.IGNORECASE)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _allowed():
    return [
        str(_hermes_root),
        str(_hermes_base),
        str(Path.home() / '.hermes'),
        str(CACHE),
    ]


def _extract_code_blocks(text):
    blocks = []
    parts = (text or '').split('```')
    for i, p in enumerate(parts):
        if i % 2 == 0:
            continue
        lines = p.splitlines()
        lang = (lines[0].strip().lower() if lines else '')
        body = '\n'.join(lines[1:] if lang in ('python', 'py', 'bash', 'sh', 'shell', '') else lines)
        if lang in ('python', 'py') or (lang == '' and 'def ' in body):
            blocks.append(('python', body))
        elif lang in ('bash', 'sh', 'shell'):
            blocks.append(('shell', body))
        else:
            blocks.append((lang or 'text', body))
    return blocks


def _path_ok(p):
    s = str(p)
    if s.startswith('/tmp') or s.startswith('/etc') or s.startswith('/root'):
        return False
    return any(s.startswith(a) for a in _allowed()) or not s.startswith('/')


def verify(text):
    issues = []
    blocks = _extract_code_blocks(text)
    if UNSAFE_SHELL.search(text or ''):
        issues.append('unsafe_shell_pattern')
    for kind, body in blocks:
        if kind == 'python':
            try:
                ast.parse(body)
            except SyntaxError as e:
                issues.append('python_syntax:' + str(e.msg))
        if kind in ('shell', 'bash', 'sh') and UNSAFE_SHELL.search(body):
            issues.append('unsafe_shell_block')
    path_re = re.compile(r'(?:/var/home|/home|/etc|/root|/tmp)[^\s\'\"]+')
    for m in path_re.finditer(text or ''):
        pth = m.group(0)
        if not _path_ok(pth):
            issues.append('path_outside_allowed:' + pth[:80])
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'verified_at': _now(),
        'n_blocks': len(blocks),
    }


def _self_test() -> int:
    ok = verify('```python\nprint(1+1)\n```\n')
    assert ok['valid'], ok
    bad = verify('```python\ndef (\n```\nrm -rf /tmp/foo')
    assert not bad['valid']
    assert any('python_syntax' in i or i == 'unsafe_shell_pattern' for i in bad['issues'])
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    _atomic_write(tmp, bad)
    tmp.unlink(missing_ok=True)
    print('[agentic-software-verifier] --self-test PASS')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--text', default='')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[agentic-software-verifier] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        text = args.text or (sys.stdin.read() if not sys.stdin.isatty() else '')
        r = verify(text)
        _atomic_write(OUT_PATH, r)
        print(json.dumps(r))
    except Exception:
        pass


if __name__ == '__main__':
    main()
