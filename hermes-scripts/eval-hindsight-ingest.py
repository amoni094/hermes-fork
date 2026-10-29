#!/usr/bin/env python3
"""Ingest needle lines into local hindsight-episodes.jsonl.

Usage:
  python3 eval-hindsight-ingest.py --source FILE [--needle-pattern REGEX]
  python3 eval-hindsight-ingest.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

DEFAULT_PATTERN = r'NEEDLE_\d+:'
DEFAULT_OUT = _hermes_root / 'cache' / 'hindsight-episodes.jsonl'


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    os.replace(tmp, path)


def _max_episode_id(path: Path) -> int:
    max_id = 0
    if not path.exists():
        return max_id
    try:
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get('episode_id') is not None:
                try:
                    max_id = max(max_id, int(obj['episode_id']))
                except (TypeError, ValueError):
                    continue
    except OSError:
        return max_id
    return max_id


def ingest(source: Path, pattern: str, out: Path) -> dict:
    if not source.exists():
        return {'ok': False, 'error': 'source_missing', 'n_appended': 0}
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return {'ok': False, 'error': f'bad_pattern: {e}', 'n_appended': 0}
    try:
        lines = source.read_text(encoding='utf-8').splitlines()
    except OSError as e:
        return {'ok': False, 'error': str(e), 'n_appended': 0}

    existing = ''
    if out.exists():
        try:
            existing = out.read_text(encoding='utf-8')
        except OSError:
            existing = ''
    n_id = _max_episode_id(out)
    ts = datetime.now(UTC).isoformat()
    appended = []
    for raw in lines:
        if not rx.search(raw):
            continue
        n_id += 1
        rec = {'episode_id': n_id, 'text': raw.rstrip('\n'), 'ts': ts}
        appended.append(rec)
    if not appended:
        return {'ok': True, 'n_appended': 0, 'out': str(out), 'max_id': n_id}

    buf = existing if existing.endswith('\n') or existing == '' else existing + '\n'
    buf += ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in appended)
    _atomic_write_text(out, buf)
    return {'ok': True, 'n_appended': len(appended), 'out': str(out), 'max_id': n_id}


def self_test() -> dict:
    failures = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        src = d / 'needles.txt'
        src.write_text(
            'noise\nNEEDLE_1: alpha=4.2\nskip\nNEEDLE_2: beta=7.7\n',
            encoding='utf-8',
        )
        out = d / 'hindsight-episodes.jsonl'
        r = ingest(src, DEFAULT_PATTERN, out)
        if r.get('n_appended') != 2:
            failures.append(f'append-count: {r}')
        else:
            rows = [json.loads(x) for x in out.read_text().splitlines() if x.strip()]
            if rows[0]['episode_id'] != 1 or 'alpha=4.2' not in rows[0]['text']:
                failures.append(f'row0: {rows[0]}')
            r2 = ingest(src, DEFAULT_PATTERN, out)
            if r2.get('n_appended') != 2:
                failures.append(f'second-append: {r2}')
            rows2 = [json.loads(x) for x in out.read_text().splitlines() if x.strip()]
            if len(rows2) != 4 or rows2[-1]['episode_id'] != 4:
                failures.append(f'ids: {[x.get("episode_id") for x in rows2]}')
        missing = ingest(d / 'nope.txt', DEFAULT_PATTERN, out)
        if missing.get('ok') is not False:
            failures.append(f'missing-source: {missing}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=str, default='')
    ap.add_argument('--needle-pattern', type=str, default=DEFAULT_PATTERN)
    ap.add_argument('--out', type=str, default=str(DEFAULT_OUT))
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r))
        return 0 if r['self_test'] == 'PASS' else 1
    if not args.source:
        print('ERROR: --source FILE required', file=sys.stderr)
        return 2
    r = ingest(Path(args.source), args.needle_pattern, Path(args.out))
    print(json.dumps(r))
    return 0 if r.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
