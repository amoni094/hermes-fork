#!/usr/bin/env python3
"""ACES-style Skill Lift: with-skill vs without-skill mean UE difference."""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import tempfile
import uuid
from collections import defaultdict
from pathlib import Path

_HH = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_HP = os.environ.get('HERMES_PROFILE', 'fork')
_PROFILE_ROOT = _HH if (_HP and _HH.name == _HP and _HH.parent.name == 'profiles') else ((_HH / 'profiles' / _HP) if _HP else _HH)
_HH_BASE = _HH if _HH.name == '.hermes' else (_HH.parent.parent if _HH.parent.name == 'profiles' else _HH)
CALIB_LOG = _PROFILE_ROOT / 'cache' / 'calibration-log.jsonl'
# Fallback: base hermes calibration-log may have real scope entries when fork log has none
CALIB_LOG_FALLBACK = _HH_BASE / 'cache' / 'calibration-log.jsonl'
BETA_STATE = _PROFILE_ROOT / 'cache' / 'skill-beta-state.json'

Z_95 = 1.96
PASS_LIFT = 0.05
MIN_N = 5
SKIP_SCOPES = frozenset({'MISSING', 'ue_blackbox', 'L2', 'L3'})


def _finite_unit(x: float):
    if x != x or x in (float('inf'), float('-inf')):
        return None
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _as_ue(rec: dict):
    v = rec.get('ue_score')
    if v is not None and v != '':
        try:
            return _finite_unit(float(v))
        except (TypeError, ValueError):
            return None
    pc = rec.get('predicted_confidence')
    if pc is not None and pc != '':
        try:
            c = float(pc)
        except (TypeError, ValueError):
            return None
        if c != c or c in (float('inf'), float('-inf')):
            return None
        return _finite_unit(1.0 - c)
    return None


def load_beta_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {}
    return obj if isinstance(obj, dict) else {}


def load_entries(path: Path) -> list:
    if not path.exists() or not path.is_file():
        return []
    out = []
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                scope = rec.get('scope')
                if scope is None or scope == '':
                    continue
                scope = str(scope)
                if scope in SKIP_SCOPES:
                    continue
                sid = rec.get('session_id')
                if sid is None or sid == '':
                    continue
                ue = _as_ue(rec)
                if ue is None:
                    continue
                out.append((str(sid), scope, ue))
    except OSError:
        return []
    return out


def _mean(xs: list) -> float:
    if not xs:
        return 0.0
    return sum(xs) / float(len(xs))


def _sample_var(xs: list) -> float:
    if len(xs) < 2:
        return 0.0
    return statistics.variance(xs)


def verdict_for(lift: float, ci_lo: float, n_with: int, n_without: int) -> str:
    if n_with < MIN_N or n_without < MIN_N:
        return 'INSUFFICIENT'
    if lift > PASS_LIFT and ci_lo > 0:
        return 'PASS'
    if lift > 0:
        return 'NEUTRAL'
    return 'FAIL'


def compute_lifts(entries: list) -> dict:
    sess_ues = defaultdict(list)
    sess_scopes = defaultdict(set)
    skills = set()
    for sid, scope, ue in entries:
        sess_ues[sid].append(ue)
        sess_scopes[sid].add(scope)
        skills.add(scope)
    all_sids = list(sess_ues.keys())
    sess_mean = {sid: _mean(vs) for sid, vs in sess_ues.items()}
    results = {}
    for skill in skills:
        with_s = [sid for sid in all_sids if skill in sess_scopes[sid]]
        without_s = [sid for sid in all_sids if skill not in sess_scopes[sid]]
        n_with = len(with_s)
        n_without = len(without_s)
        with_entries = []
        for sid in with_s:
            with_entries.extend(sess_ues[sid])
        without_entries = []
        for sid in without_s:
            without_entries.extend(sess_ues[sid])
        mean_with = _mean(with_entries)
        mean_without = _mean(without_entries)
        lift = mean_without - mean_with
        var_w = _sample_var([sess_mean[s] for s in with_s])
        var_wo = _sample_var([sess_mean[s] for s in without_s])
        if n_with > 0 and n_without > 0:
            se = math.sqrt(var_w / n_with + var_wo / n_without)
            # SE floor: prevent zero-variance collapse producing false PASS at n=MIN_N.
            # Minimum SE treated as if one unit of variance across all n samples.
            se_floor = math.sqrt(1.0 / n_with + 1.0 / n_without) / (n_with + n_without)
            se = max(se, se_floor)
        else:
            se = 0.0
        ci_lo = lift - Z_95 * se
        ci_hi = lift + Z_95 * se
        results[skill] = {
            'lift': lift,
            'ci_lo': ci_lo,
            'ci_hi': ci_hi,
            'n_with': n_with,
            'n_without': n_without,
            'mean_ue_with': mean_with,
            'mean_ue_without': mean_without,
            'verdict': verdict_for(lift, ci_lo, n_with, n_without),
        }
    return results


def filter_skill(results: dict, skill_name):
    if not skill_name:
        return results
    if skill_name in results:
        return {skill_name: results[skill_name]}
    return {}


def print_json(results: dict) -> None:
    print(json.dumps(results, indent=2, sort_keys=True))


def print_report(results: dict) -> None:
    rows = sorted(results.items(), key=lambda kv: kv[1].get('lift', 0.0), reverse=True)
    if not rows:
        return
    hdr = (
        'skill', 'lift', 'ci_lo', 'ci_hi', 'n_with', 'n_without',
        'mean_ue_with', 'mean_ue_without', 'verdict',
    )
    print('\t'.join(hdr))
    for name, r in rows:
        print('\t'.join([
            str(name),
            '{:.6f}'.format(float(r['lift'])),
            '{:.6f}'.format(float(r['ci_lo'])),
            '{:.6f}'.format(float(r['ci_hi'])),
            str(int(r['n_with'])),
            str(int(r['n_without'])),
            '{:.6f}'.format(float(r['mean_ue_with'])),
            '{:.6f}'.format(float(r['mean_ue_without'])),
            str(r['verdict']),
        ]))


def self_test() -> int:
    failures = []

    missing = compute_lifts(load_entries(Path('/tmp/skill-lift-tracker-no-such-' + uuid.uuid4().hex + '.jsonl')))
    if missing != {}:
        failures.append('missing-log')

    tmpdir = tempfile.TemporaryDirectory(prefix='skill-lift-')
    log = Path(tmpdir.name) / 'calibration-log.jsonl'
    records = []
    for i in range(8):
        records.append({
            'session_id': 'help-%d' % i,
            'scope': 'helpful-skill',
            'ue_score': 0.08,
            'ts': '2026-01-01T00:00:00Z',
        })
        records.append({
            'session_id': 'help-%d' % i,
            'scope': 'helpful-skill',
            'ue_score': 0.12,
            'ts': '2026-01-01T00:00:01Z',
        })
    for i in range(8):
        records.append({
            'session_id': 'hurt-%d' % i,
            'scope': 'unhelpful-skill',
            'ue_score': 0.82,
            'ts': '2026-01-01T00:00:00Z',
        })
        records.append({
            'session_id': 'hurt-%d' % i,
            'scope': 'unhelpful-skill',
            'ue_score': 0.88,
            'ts': '2026-01-01T00:00:01Z',
        })
    for i in range(8):
        records.append({
            'session_id': 'base-%d' % i,
            'scope': 'baseline-skill',
            'ue_score': 0.40,
            'ts': '2026-01-01T00:00:00Z',
        })
    for i in range(3):
        records.append({
            'session_id': 'tiny-%d' % i,
            'scope': 'rare-skill',
            'ue_score': 0.20,
            'ts': '2026-01-01T00:00:00Z',
        })
    records.append({
        'session_id': 'miss-1',
        'scope': 'MISSING',
        'ue_score': 0.99,
        'ts': '2026-01-01T00:00:00Z',
    })
    records.append({
        'session_id': 'nosc-1',
        'ue_score': 0.50,
        'ts': '2026-01-01T00:00:00Z',
    })
    records.append({
        'session_id': 'pc-1',
        'scope': 'pc-skill',
        'predicted_confidence': 0.9,
        'ts': '2026-01-01T00:00:00Z',
    })

    body_lines = [json.dumps(r) for r in records]
    body_lines.append('{not json')
    body_lines.append('not-json')
    log.write_text(chr(10).join(body_lines) + chr(10), encoding='utf-8')

    results = compute_lifts(load_entries(log))
    if 'MISSING' in results:
        failures.append('missing-scope-leaked')
    help_r = results.get('helpful-skill')
    hurt_r = results.get('unhelpful-skill')
    rare_r = results.get('rare-skill')
    pc_r = results.get('pc-skill')
    if not help_r:
        failures.append('helpful-missing')
    else:
        if help_r['n_with'] != 8:
            failures.append('helpful-n_with')
        if help_r['n_without'] < 5:
            failures.append('helpful-n_without')
        if help_r['lift'] <= PASS_LIFT:
            failures.append('helpful-lift')
        if help_r['ci_lo'] <= 0:
            failures.append('helpful-ci')
        if help_r['verdict'] != 'PASS':
            failures.append('helpful-verdict:{}'.format(help_r['verdict']))
        if not (help_r['mean_ue_with'] < help_r['mean_ue_without']):
            failures.append('helpful-means')
    if not hurt_r:
        failures.append('unhelpful-missing')
    else:
        if hurt_r['lift'] > 0:
            failures.append('unhelpful-lift')
        if hurt_r['verdict'] != 'FAIL':
            failures.append('unhelpful-verdict:{}'.format(hurt_r['verdict']))
    if not rare_r:
        failures.append('rare-missing')
    elif rare_r['verdict'] != 'INSUFFICIENT':
        failures.append('rare-verdict:{}'.format(rare_r['verdict']))
    if pc_r is not None:
        if abs(pc_r['mean_ue_with'] - 0.1) > 1e-9:
            failures.append('pc-fallback')
    empty = filter_skill(results, 'no-such-skill')
    if empty != {}:
        failures.append('unknown-skill-filter')

    load_beta_state(Path('/tmp/skill-lift-no-beta-' + uuid.uuid4().hex + '.json'))
    junk_beta = Path(tmpdir.name) / 'skill-beta-state.json'
    junk_beta.write_text('not-json', encoding='utf-8')
    if load_beta_state(junk_beta) != {}:
        failures.append('beta-malformed')

    tmpdir.cleanup()
    if failures:
        print('SELF-TEST FAIL: ' + ', '.join(failures), file=sys.stderr)
        return 1
    print('SELF-TEST PASS')
    return 0


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='ACES-style skill lift from calibration-log.jsonl')
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--report', action='store_true', help='human-readable table sorted by lift desc')
    p.add_argument('--json', action='store_true', help='JSON to stdout')
    p.add_argument('--skill', default='', help='restrict output to SKILL_NAME')
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return self_test()
    load_beta_state(BETA_STATE)
    # Use primary calibration-log; fall back to base-hermes log if primary has 0 usable entries
    calib_path = CALIB_LOG
    entries = load_entries(calib_path)
    if not entries and CALIB_LOG_FALLBACK != CALIB_LOG and CALIB_LOG_FALLBACK.exists():
        calib_path = CALIB_LOG_FALLBACK
        entries = load_entries(calib_path)
    results = compute_lifts(entries)
    skill = (args.skill or '').strip()
    results = filter_skill(results, skill if skill else None)
    if args.report and not args.json:
        print_report(results)
    else:
        print_json(results)
    return 0


if __name__ == '__main__':
    sys.exit(main())
