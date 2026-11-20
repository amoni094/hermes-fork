#!/usr/bin/env python3
"""Route claims by citation confidence. Missing confidence is unmeasured, not a default."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'citation-confidence-router.json'
SILENT, CITE, ABSTAIN = 'silent', 'cite', 'abstain'


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def route(claim: str, source: str = '', confidence=None) -> dict:
    if confidence is None:
        return {
            'generated_at': datetime.now(UTC).isoformat(),
            'claim': (claim or '')[:240],
            'has_source': bool(source),
            'confidence': None,
            'decision': None,
            'status': 'insufficient_data',
            'n': 0,
        }
    try:
        conf = float(confidence)
    except (TypeError, ValueError):
        return {
            'generated_at': datetime.now(UTC).isoformat(),
            'claim': (claim or '')[:240],
            'has_source': bool(source),
            'confidence': None,
            'decision': None,
            'status': 'insufficient_data',
            'n': 0,
        }
    if conf < 0.4:
        decision = ABSTAIN
    elif conf < 0.7 or not source:
        decision = CITE
    else:
        decision = SILENT
    return {
        'generated_at': datetime.now(UTC).isoformat(),
        'claim': (claim or '')[:240],
        'has_source': bool(source),
        'confidence': round(conf, 6),
        'decision': decision,
        'status': 'ok',
        'n': 1,
    }


def self_test() -> dict:
    a = route('x is y', source='paper', confidence=0.9)
    assert a['decision'] == SILENT and a['status'] == 'ok'
    b = route('x is y', source='', confidence=0.5)
    assert b['decision'] == CITE
    c = route('x is y', confidence=0.2)
    assert c['decision'] == ABSTAIN
    d = route('x is y')
    assert d['status'] == 'insufficient_data' and d['decision'] is None and d['n'] == 0
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    _atomic_write(tmp, a)
    try:
        assert tmp.exists()
    finally:
        tmp.unlink(missing_ok=True)
    return {'self_test': 'PASS', 'sample': a}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--claim', default='')
    ap.add_argument('--source', default='')
    ap.add_argument('--confidence', default=None)
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0)
    r = route(args.claim, args.source, args.confidence)
    if r.get('status') != 'insufficient_data':
        try:
            _atomic_write(OUT_PATH, r)
        except Exception:
            pass
    print(json.dumps(r, indent=2))


if __name__ == '__main__':
    main()
