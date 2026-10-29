#!/usr/bin/env python3
"""governance-falsifiability-lint.py — Popper/Critch failure_observable gate.

Every improvement proposal must name a failure_observable (a non-empty string
describing what observation would falsify the claim). Missing or trivial
observables are WARN. Deployed proposals older than 7 days without an
observable are HIGH alarm.

Usage:
  python3 governance-falsifiability-lint.py --self-test
  python3 governance-falsifiability-lint.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

OUT_PATH = _hermes_root / 'cache' / 'governance-falsifiability-report.json'
MIN_CHARS = 20
DEPLOYED_STATES = {
    'deployed', 'implemented', 'approved', 'shipped', 'live', 'promoted',
}
STALE_DAYS = 7

# Substrings from improvement_governance._default_failure_observable() templates.
# Match case-insensitive; a proposal whose only FO is one of these is WARN, not PASS/HIGH.
BOILERPLATE_PATTERNS = [
    'raises unhandled exception or breaks a downstream monitor within 14 days',
    'causes alarm rate to increase >20% vs baseline in the 7-day post-deploy window',
    'fails to produce expected output or writes stale data for 2+ consecutive runs',
    'produces measurable regression in quality or stability metrics within 14 days',
    'causes regressions in eval suite or produces incorrect outputs on 3+ test cases',
]


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _parse_dt(v) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(float(v), tz=UTC)
        except (OSError, ValueError, OverflowError):
            return None
    if isinstance(v, str):
        s = v.replace('Z', '+00:00')
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            return None
    return None


def _is_boilerplate_fo(raw: str) -> bool:
    s = raw.lower()
    return any(pat.lower() in s for pat in BOILERPLATE_PATTERNS)


def lint_proposal(rec: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    pid = rec.get('id') or rec.get('proposal_id') or rec.get('name') or '?'
    raw = rec.get('failure_observable')
    boilerplate = False
    if raw is None:
        status = 'WARN'
        reason = 'missing failure_observable'
    elif not isinstance(raw, str) or not raw.strip():
        status = 'WARN'
        reason = 'empty failure_observable'
    elif len(raw.strip()) <= MIN_CHARS:
        status = 'WARN'
        reason = f'trivial failure_observable (len={len(raw.strip())} <= {MIN_CHARS})'
    elif _is_boilerplate_fo(raw):
        status = 'WARN'
        boilerplate = True
        reason = 'boilerplate/template failure_observable'
    else:
        status = 'PASS'
        reason = 'non-trivial failure_observable'
    state = str(rec.get('state') or rec.get('status') or '').lower()
    deployed = state in DEPLOYED_STATES or rec.get('deployed') is True
    deployed_at = _parse_dt(rec.get('deployed_at') or rec.get('approved_at') or rec.get('updated_at'))
    alarm = None
    # Boilerplate-only FOs stay WARN even after deploy>7d (not HIGH, not PASS).
    if deployed and status != 'PASS' and deployed_at is not None:
        if now - deployed_at > timedelta(days=STALE_DAYS):
            if boilerplate:
                status = 'WARN'
                reason = 'deployed >7d with boilerplate failure_observable'
            else:
                status = 'HIGH'
                alarm = 'HIGH'
                reason = 'deployed >7d without non-trivial failure_observable'
    severity = 'HIGH' if status == 'HIGH' else ('WARN' if status == 'WARN' else 'PASS')
    return {
        'id': pid,
        'status': status,
        'severity': severity,
        'reason': reason,
        'alarm': alarm,
        'deployed': deployed,
        'state': state,
        'boilerplate': boilerplate,
    }


def load_proposals() -> list[dict]:
    paths = [
        _hermes_base / 'logs' / 'improvement-proposals.jsonl',
        _hermes_root / 'logs' / 'improvement-proposals.jsonl',
        _hermes_base / 'cache' / 'improvement-proposals.jsonl',
    ]
    rows: list[dict] = []
    seen = set()
    for p in paths:
        try:
            if not p.is_file():
                continue
            key = str(p.resolve())
        except OSError:
            continue
        if key in seen:
            continue
        seen.add(key)
        try:
            text = p.read_text(encoding='utf-8')
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def run(rows: list[dict] | None = None) -> dict:
    now = datetime.now(UTC)
    rows = rows if rows is not None else load_proposals()
    latest: dict[str, dict] = {}
    for rec in rows:
        pid = str(rec.get('id') or rec.get('proposal_id') or id(rec))
        latest[pid] = rec
    lints = [lint_proposal(rec, now=now) for rec in latest.values()]
    n_high = sum(1 for x in lints if x['status'] == 'HIGH')
    n_warn = sum(1 for x in lints if x['status'] == 'WARN')
    n_pass = sum(1 for x in lints if x['status'] == 'PASS')
    report = {
        'ts': now.isoformat(),
        'theorem': 'Popper falsifiability; Critch ARCHES failure-observable requirement',
        'n_proposals': len(lints),
        'n_pass': n_pass,
        'n_warn': n_warn,
        'warn_count': n_warn,
        'n_high': n_high,
        'alarm': n_high > 0,
        'lints': lints,
    }
    try:
        _atomic_write(OUT_PATH, report)
        report['output'] = str(OUT_PATH)
    except OSError as exc:
        report['write_error'] = str(exc)
    return report


def self_test() -> int:
    failures = []
    now = datetime.now(UTC)
    missing = lint_proposal({'id': 'a'}, now=now)
    if missing['status'] != 'WARN':
        failures.append('missing should WARN')
    empty = lint_proposal({'id': 'b', 'failure_observable': ''}, now=now)
    if empty['status'] != 'WARN':
        failures.append('empty should WARN')
    trivial = lint_proposal({'id': 'c', 'failure_observable': 'too short'}, now=now)
    if trivial['status'] != 'WARN':
        failures.append('trivial should WARN')
    good = lint_proposal({
        'id': 'd',
        'failure_observable': 'mean_score drops below 3.0 for 7 consecutive days',
    }, now=now)
    if good['status'] != 'PASS':
        failures.append('non-trivial should PASS')
    old = now - timedelta(days=10)
    high = lint_proposal({
        'id': 'e',
        'state': 'deployed',
        'deployed_at': old.isoformat(),
        'failure_observable': '',
    }, now=now)
    if high['status'] != 'HIGH' or high['alarm'] != 'HIGH':
        failures.append(f'deployed stale should HIGH, got {high}')
    bp_deployed = lint_proposal({
        'id': 'f',
        'state': 'deployed',
        'deployed_at': old.isoformat(),
        'failure_observable': (
            "Script/plugin 'X' raises unhandled exception or breaks a "
            "downstream monitor within 14 days of deployment."
        ),
    }, now=now)
    if bp_deployed['status'] != 'WARN' or bp_deployed.get('severity') != 'WARN':
        failures.append(f'deployed boilerplate should WARN not HIGH, got {bp_deployed}')
    if bp_deployed.get('alarm') == 'HIGH':
        failures.append(f'deployed boilerplate must not set HIGH alarm, got {bp_deployed}')
    bp_pending = lint_proposal({
        'id': 'g',
        'state': 'pending_review',
        'failure_observable': (
            "Change 'X' produces measurable regression in quality or "
            "stability metrics within 14 days."
        ),
    }, now=now)
    if bp_pending['status'] != 'WARN' or bp_pending.get('severity') != 'WARN':
        failures.append(f'pending boilerplate should WARN, got {bp_pending}')
    for pat in BOILERPLATE_PATTERNS:
        hit = lint_proposal({
            'id': 'bp-' + pat[:12],
            'failure_observable': 'PREFIX ' + pat + ' SUFFIX extra context here',
        }, now=now)
        if hit['status'] != 'WARN' or not hit.get('boilerplate'):
            failures.append(f'pattern not rejected: {pat!r} -> {hit}')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS'}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({
        'n_proposals': out.get('n_proposals'),
        'n_pass': out.get('n_pass'),
        'n_warn': out.get('n_warn'),
        'warn_count': out.get('warn_count'),
        'n_high': out.get('n_high'),
        'alarm': out.get('alarm'),
        'output': out.get('output'),
    }))
    return 1 if out.get('write_error') else 0  # ADV2-017: alarm is not a process failure


if __name__ == '__main__':
    sys.exit(main())
