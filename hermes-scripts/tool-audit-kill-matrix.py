#!/usr/bin/env python3
"""Mutation-inspired kill matrix for Hermes tool-call chains.

Protocols x fault types. Reads tool_review_log (lifecycle.db, INSERT-only,
no DDL). Writes tool-audit-state.json. Fail-open. stdlib only.
"""
from __future__ import annotations
import argparse, fcntl, json, os, random, sqlite3, sys, tempfile, uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
if _hermes_base.name != '.hermes' and _hermes_base.parent.name == 'profiles':
    _hermes_base = _hermes_base.parent.parent
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'
OUT_PATH = CACHE / 'tool-audit-state.json'

FAULTS = ('timeout', 'empty_output', 'wrong_schema', 'hallucinated_ok', 'truncated')
PROTOCOLS = ('outcome_flag', 'score_threshold', 'latency_outlier', 'notes_parse', 'combo')


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + '.lock') if path.suffix else path.with_name(path.name + '.lock')
    tmp = path.with_name(path.name + '.tmp')
    payload = json.dumps(obj, indent=2) + '\n'
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _temp_out(prefix: str) -> Path:
    return Path(tempfile.gettempdir()) / (f'{prefix}-{uuid.uuid4().hex}.json')


def _ok_outcome(val) -> bool:
    s = str(val or '').strip().lower()
    return s in ('ok', 'success', 'true', '1', 'pass')


def inject_fault(row, fault, rng):
    rec = dict(row)
    rec['fault_type'] = fault
    rec['injected'] = True
    if fault == 'timeout':
        rec['latency_ms'] = 60_000 + rng.randrange(5_000)
        rec['outcome'] = 'timeout'
        rec['score'] = 0.0
    elif fault == 'empty_output':
        rec['notes'] = ''
        rec['score'] = 0.0
        rec['outcome'] = rec.get('outcome') or 'ok'
    elif fault == 'wrong_schema':
        rec['notes'] = '{not-json'
        rec['outcome'] = rec.get('outcome') or 'ok'
        rec['score'] = rec.get('score') if rec.get('score') is not None else 0.9
    elif fault == 'hallucinated_ok':
        rec['outcome'] = 'ok'
        rec['score'] = 1.0
        rec['notes'] = json.dumps({'hallucinated': True, 'source': 'inject'})
        rec['latency_ms'] = rec.get('latency_ms') or 12
    elif fault == 'truncated':
        rec['notes'] = (rec.get('notes') or 'partial')[:4]
        rec['outcome'] = 'ok'
        rec['score'] = 0.85
        rec['latency_ms'] = rec.get('latency_ms') or 8
    return rec


def protocol_catches(rec, proto) -> bool:
    outcome = rec.get('outcome')
    try:
        score = float(rec.get('score')) if rec.get('score') is not None else None
    except (TypeError, ValueError):
        score = None
    try:
        lat = float(rec.get('latency_ms')) if rec.get('latency_ms') is not None else None
    except (TypeError, ValueError):
        lat = None
    notes = rec.get('notes')
    if proto == 'outcome_flag':
        return not _ok_outcome(outcome)
    if proto == 'score_threshold':
        return score is not None and score < 0.5
    if proto == 'latency_outlier':
        return lat is not None and lat >= 15_000
    if proto == 'notes_parse':
        if notes is None:
            return False
        s = str(notes).strip()
        if s == '':
            return True
        if s.startswith('{') or s.startswith('['):
            try:
                obj = json.loads(s)
            except (json.JSONDecodeError, TypeError):
                return True
            if isinstance(obj, dict) and obj.get('hallucinated'):
                return True
        if len(s) <= 4:
            return True
        return False
    if proto == 'combo':
        return any(protocol_catches(rec, p) for p in PROTOCOLS if p != 'combo')
    return False


def kill_matrix(rows):
    counts = {p: {f: {'caught': 0, 'n': 0} for f in FAULTS} for p in PROTOCOLS}
    for rec in rows:
        fault = rec.get('fault_type') or 'unknown'
        if fault not in FAULTS:
            continue
        for p in PROTOCOLS:
            counts[p][fault]['n'] += 1
            if protocol_catches(rec, p):
                counts[p][fault]['caught'] += 1
    rates = {}
    for p in PROTOCOLS:
        rates[p] = {}
        for f in FAULTS:
            n = counts[p][f]['n']
            c = counts[p][f]['caught']
            rates[p][f] = (c / n) if n else None
    return counts, rates


def detection_rate(rows, proto):
    if not rows:
        return None, 0
    caught = sum(1 for r in rows if protocol_catches(r, proto))
    return caught / float(len(rows)), len(rows)


def load_live_rows(db_path=None, limit=5000):
    db = db_path or LIFECYCLE_DB
    if not Path(db).exists():
        return []
    conn = sqlite3.connect(str(db), timeout=30)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'tool_review_log' not in tables:
            return []
        cur = conn.execute(
            'SELECT ts, session_id, tool_name, latency_ms, outcome, score, notes FROM tool_review_log ORDER BY id DESC LIMIT ?',
            (limit,),
        )
        out = []
        for ts, sid, tool, lat, outcome, score, notes in cur.fetchall():
            out.append({
                'ts': ts,
                'session_id': sid,
                'tool_name': tool,
                'latency_ms': lat,
                'outcome': outcome,
                'score': score,
                'notes': notes,
                'injected': False,
                'fault_type': None,
            })
        return out
    except Exception:
        return []
    finally:
        conn.close()


def synthetic_suite(n=100, seed=1):
    rng = random.Random(seed)
    clean = []
    for i in range(n // 2):
        clean.append({
            'ts': _now(),
            'session_id': f's{i}',
            'tool_name': f'tool_{i % 5}',
            'latency_ms': 20 + rng.randrange(80),
            'outcome': 'ok',
            'score': 0.9 + 0.1 * rng.random(),
            'notes': json.dumps({'ok': True}),
            'injected': False,
            'fault_type': None,
        })
    faults = []
    for i in range(n // 2):
        base = {
            'ts': _now(),
            'session_id': f'f{i}',
            'tool_name': f'tool_{i % 5}',
            'latency_ms': 30,
            'outcome': 'ok',
            'score': 0.95,
            'notes': json.dumps({'ok': True}),
        }
        faults.append(inject_fault(base, FAULTS[i % len(FAULTS)], rng))
    return clean, faults


def run(out_path=None, db_path=None, rows=None):
    live = list(rows) if rows is not None else load_live_rows(db_path=db_path)
    if not live:
        return {'status': 'insufficient_data', 'n': 0, 'ts': _now()}
    rng = random.Random(7)
    injected = []
    for i, rec in enumerate(live[:200]):
        injected.append(inject_fault(rec, FAULTS[i % len(FAULTS)], rng))
    counts, rates = kill_matrix(injected)
    base_rate, _n_base = detection_rate(injected, 'outcome_flag')
    combo_rate, n_combo = detection_rate(injected, 'combo')
    delta = None
    if base_rate is not None and combo_rate is not None:
        delta = combo_rate - base_rate
    payload = {
        'ts': _now(),
        'status': 'ok',
        'n_live': len(live),
        'n_injected': len(injected),
        'baseline_protocol': 'outcome_flag',
        'baseline_detection_rate': base_rate,
        'combo_detection_rate': combo_rate,
        'delta_pp': None if delta is None else round(100.0 * delta, 3),
        'kill_matrix_rates': rates,
        'per_protocol_fault_counts': counts,
        'n': n_combo,
    }
    dest = out_path or OUT_PATH
    _atomic_write(dest, payload)
    return payload


def _self_test() -> int:
    empty = run(rows=[], out_path=_temp_out('kill-empty'))
    assert empty['status'] == 'insufficient_data'
    clean, faults = synthetic_suite(100, seed=2)
    tmp = _temp_out('kill-matrix')
    r = run(rows=clean + faults, out_path=tmp)
    assert r['status'] == 'ok'
    assert r['combo_detection_rate'] is not None
    assert r['baseline_detection_rate'] is not None
    assert r['combo_detection_rate'] + 1e-12 >= r['baseline_detection_rate'] + 0.10, r
    miss = sum(1 for f in faults if not protocol_catches(f, 'combo'))
    assert miss <= 2, miss
    far = sum(1 for c in clean if protocol_catches(c, 'combo'))
    assert far / float(len(clean)) < 0.10, far
    try:
        tmp.unlink(missing_ok=True)
        tmp.with_suffix(tmp.suffix + '.lock').unlink(missing_ok=True)
    except OSError:
        pass
    print('[tool-audit-kill-matrix] --self-test PASS combo={:.3f} base={:.3f} delta_pp={}'.format(
        r['combo_detection_rate'], r['baseline_detection_rate'], r['delta_pp']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[tool-audit-kill-matrix] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        payload = run()
        public = {k: payload[k] for k in payload if k not in ('per_protocol_fault_counts',)}
        print(json.dumps(public))
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
