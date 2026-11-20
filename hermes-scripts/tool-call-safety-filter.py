#!/usr/bin/env python3
"""Pre-execution tool-call safety filter (renamed from deductive-verifier).

Rule table of regex predicates against {tool, args}. Block CRITICAL, warn HIGH.
"""
from __future__ import annotations
import argparse, json, os, re, sqlite3, sys, tempfile, time, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
DB_PATH = CACHE / 'tool-call-safety-filter.db'
RULES_PATH = _hermes_root / 'scripts' / 'deductive-verifier-rules.json'


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))


BUILTIN_RULES = [
    {
        'id': 'R001',
        'desc': 'rm -rf on root/home (/ /* ~ $HOME only, not arbitrary absolute paths)',
        'pattern': {'tool': 'terminal|execute_code',
                    'command_re': r'rm\b.*\s+(?:/[*]?|~|[$]HOME)\s*$'},
        'severity': 'CRITICAL',
    },
    {
        'id': 'R002',
        'desc': 'fork bomb pattern',
        'pattern': {'tool': 'terminal|execute_code', 'command_re': r':\(\)\{.*\}'},
        'severity': 'CRITICAL',
    },
    {
        'id': 'R003',
        'desc': 'write to /etc/passwd or /etc/sudoers',
        'pattern': {'tool': 'terminal|execute_code', 'command_re': r'(>|tee|write|echo)\s.*/etc/(passwd|shadow|sudoers)'},
        'severity': 'CRITICAL',
    },
    {
        'id': 'R004',
        'desc': 'exfiltration via curl/wget to external host with file redirect',
        'pattern': {'tool': 'terminal', 'command_re': r'(curl|wget)\s+.*(-d|--data|--upload-file|--data-binary)'},
        'severity': 'HIGH',
    },
    {
        'id': 'R005',
        'desc': 'batch deletion of hermes skills',
        'pattern': {'tool': 'terminal', 'command_re': r'rm\s+.*skills/.*\.md'},
        'severity': 'CRITICAL',
    },
]


def _match_rule(rule: dict, call: dict) -> bool:
    pat = rule['pattern']
    tool = call.get('tool', '')
    if 'tool' in pat:
        allowed = [t.strip() for t in pat['tool'].split('|')]
        if tool not in allowed:
            return False
    if 'command_re' in pat:
        args = call.get('args', call.get('arguments', {}))
        if not isinstance(args, dict):
            args = {}
        cmd = str(args.get('command', args.get('code', call.get('command', ''))))
        if not re.search(pat['command_re'], cmd, re.IGNORECASE | re.DOTALL):
            return False
    return True


class ToolCallSafetyFilter:
    def __init__(self, rules=None):
        self.rules = list(rules or BUILTIN_RULES)
        extra = []
        if RULES_PATH.exists():
            try:
                extra = json.loads(RULES_PATH.read_text(encoding='utf-8'))
                if isinstance(extra, dict):
                    extra = extra.get('rules') or []
            except (OSError, json.JSONDecodeError):
                extra = []
        if isinstance(extra, list):
            self.rules.extend([r for r in extra if isinstance(r, dict)])

    def check(self, call: dict) -> str:
        worst = 'ALLOW'
        for rule in self.rules:
            try:
                if _match_rule(rule, call):
                    sev = rule.get('severity', 'HIGH')
                    if sev == 'CRITICAL':
                        return 'BLOCK'
                    if sev == 'HIGH':
                        worst = 'WARN'
            except Exception:
                continue
        return worst


def _self_test() -> int:
    v = ToolCallSafetyFilter()
    assert v.check({'tool': 'terminal', 'args': {'command': 'rm -rf /'}}) == 'BLOCK'
    assert v.check({'tool': 'read_file', 'args': {'path': '/tmp/test.txt'}}) == 'ALLOW'
    print('[tool-call-safety-filter] --self-test PASS')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--json', default='')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[tool-call-safety-filter] --self-test FAIL: {exc}')
            return 1
    try:
        raw = args.json
        if not raw and not sys.stdin.isatty():
            raw = sys.stdin.read()
        if raw:
            try:
                call = json.loads(raw)
            except json.JSONDecodeError as e:
                print(json.dumps({'status': 'error', 'error': f'invalid json: {e}', 'decision': None}))
                return 0
            v = ToolCallSafetyFilter()
            decision = v.check(call if isinstance(call, dict) else {})
            print(json.dumps({'status': 'ok', 'decision': decision, 'ts': _now()}))
            return 0
        # default cron run: scan recent session tool-ish lines
        sess = CACHE.parent / 'sessions'
        v = ToolCallSafetyFilter()
        n = n_block = n_warn = 0
        samples = []
        if sess.exists():
            for path in sorted(sess.glob('*.jsonl'))[-6:]:
                try:
                    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
                        try:
                            rec = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if not isinstance(rec, dict):
                            continue
                        tool = rec.get('tool') or rec.get('tool_name') or rec.get('name')
                        if not tool:
                            continue
                        args_d = rec.get('args') or rec.get('arguments') or {}
                        if not isinstance(args_d, dict):
                            args_d = {'command': str(args_d)[:500]}
                        n += 1
                        d = v.check({'tool': tool, 'args': args_d})
                        if d == 'BLOCK':
                            n_block += 1
                            samples.append({'tool': tool, 'decision': d})
                        elif d == 'WARN':
                            n_warn += 1
                except OSError:
                    continue
        out = {
            'status': 'ok' if n else 'insufficient_data',
            'ts': _now(),
            'n': n,
            'n_block': n_block,
            'n_warn': n_warn,
            'samples': samples[:20],
            'decision': None if not n else ('BLOCK' if n_block else ('WARN' if n_warn else 'ALLOW')),
        }
        if n:
            _atomic_write(CACHE / 'tool-call-safety-filter.json', {k: out[k] for k in out if k != 'samples'})
        print(json.dumps({k: out[k] for k in out if k != 'samples'}))
        return 0
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e)}))
        return 0


if __name__ == '__main__':
    sys.exit(main())
