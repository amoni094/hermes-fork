#!/usr/bin/env python3
"""epistemic-state-tracker.py — K/B/C epistemic state table.

Based on Fagin, Halpern, Moses, Vardi (1995) Reasoning About Knowledge.
  S5 axioms: K(phi)->phi (K implies truth); K(phi)->KK(phi) (positive introspection)
  K = knowledge: true in ALL accessible worlds. Requires tool verification.
  B = belief: true in MOST accessible worlds. Hedged; decays over time.
  C = common knowledge: fixed point of mutual knowledge. Requires Condorcet=1.0.

Epistemic regression (K->B, C->B) is always logged — never silent.
B-type confidence decays exponentially (info half-life model).
K and C are stable until contradicted.

Usage:
  python3 epistemic-state-tracker.py update --domain TEXT --type K|B|C --confidence FLOAT [--evidence TEXT]
  python3 epistemic-state-tracker.py query --domain TEXT
  python3 epistemic-state-tracker.py decay --hours FLOAT
  python3 epistemic-state-tracker.py stats
  python3 epistemic-state-tracker.py --self-test
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, sys, time
from pathlib import Path

# --- Profile awareness ---
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)
_cache = _hermes_root / 'cache'
_cache.mkdir(parents=True, exist_ok=True)

_STATE_FILE   = _cache / 'epistemic-state.json'
_REGRESS_LOG  = _cache / 'epistemic-regressions.jsonl'
_CONSIST      = _cache / 'consistency-scores.jsonl'

def _dhash(text: str) -> str:
    return hashlib.sha256(text[:300].encode()).hexdigest()[:12]

def _load_state() -> dict:
    try:
        raw = _STATE_FILE.read_text()
        d = json.loads(raw)
        return d if isinstance(d, dict) else {'domains': {}}
    except (OSError, json.JSONDecodeError):
        return {'domains': {}}

def _save_state(state: dict) -> None:
    tmp = _STATE_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, indent=2))
    os.replace(tmp, _STATE_FILE)

def _atomic_append(path: Path, obj: dict) -> None:
    try:
        with open(path, 'a') as f:
            f.write(json.dumps(obj) + '\n')
            f.flush()
    except OSError:
        pass

def _get_consistency_for_domain(dhash: str) -> float | None:
    """Check consistency-scores.jsonl for a domain_hash match."""
    try:
        lines = _CONSIST.read_text().splitlines()
    except (OSError, FileNotFoundError):
        return None
    for line in reversed(lines):
        try:
            r = json.loads(line)
            if r.get('domain_hash') == dhash or r.get('query_hash') == dhash:
                return float(r.get('consistency_score', 0.0))
        except (json.JSONDecodeError, ValueError):
            pass
    return None

def update(domain: str, ep_type: str, confidence: float,
           evidence: str = '', has_tool_verification: bool = False) -> dict:
    ep_type = ep_type.upper()
    if ep_type not in ('K', 'B', 'C'):
        return {'error': f'invalid type {ep_type!r}, must be K, B, or C'}

    confidence = max(0.0, min(1.0, float(confidence)))
    dhash = _dhash(domain)
    state = _load_state()
    domains = state.setdefault('domains', {})
    existing = domains.get(dhash)
    now = time.time()

    # --- Hard cores ---
    # K requires tool verification or evidence string containing 'tool:'
    if ep_type == 'K':
        k_evidence_ok = has_tool_verification or 'tool:' in evidence
        if not k_evidence_ok:
            return {
                'error': 'K-type requires tool-verified evidence (pass --has-tool-verification or include "tool:" in --evidence)',
                'dhash': dhash,
                'domain': domain[:80],
            }

    # C requires Condorcet=1.0 from consistency-scores.jsonl
    if ep_type == 'C':
        cs = _get_consistency_for_domain(dhash)
        if cs is None or cs < 1.0:
            return {
                'error': f'C-type requires consistency_score=1.0 in cache; found={cs}',
                'dhash': dhash,
                'domain': domain[:80],
            }

    # --- Regression detection ---
    regression = None
    if existing is not None:
        old_type = existing.get('type', 'B')
        # K->B or C->B is a regression
        if (old_type in ('K', 'C')) and ep_type == 'B':
            regression = {
                'ts': now,
                'dhash': dhash,
                'domain': domain[:80],
                'old_type': old_type,
                'new_type': 'B',
                'old_confidence': existing.get('confidence', 0.0),
                'new_confidence': confidence,
                'reason': evidence or 'unspecified',
            }
            _atomic_append(_REGRESS_LOG, regression)

    # Build evidence list
    ev_list = existing.get('evidence', []) if existing else []
    if evidence:
        ev_list = ev_list[-9:]  # keep last 10
        ev_list.append(evidence)

    domains[dhash] = {
        'domain': domain[:80],
        'type': ep_type,
        'confidence': confidence,
        'last_updated': now,
        'evidence': ev_list,
        'update_count': (existing.get('update_count', 0) + 1) if existing else 1,
    }
    _save_state(state)

    result = {
        'dhash': dhash,
        'domain': domain[:80],
        'type': ep_type,
        'confidence': confidence,
        'regression': regression is not None,
    }
    return result

def query(domain: str) -> dict:
    dhash = _dhash(domain)
    state = _load_state()
    entry = state.get('domains', {}).get(dhash)
    if entry is None:
        return {'dhash': dhash, 'type': 'UNKNOWN', 'confidence': 0.0, 'exists': False}
    return {**entry, 'dhash': dhash, 'exists': True}

def decay(hours: float) -> dict:
    """Decay B-type confidences: conf_new = conf_old * exp(-0.05 * hours).
    Derives from Ebbinghaus forgetting curve generalisation; half-life ~14h at rate 0.05.
    K and C are stable (knowledge does not decay absent contradiction).
    Remove B entries with confidence < 0.01.
    """
    hours = max(0.0, float(hours))
    state = _load_state()
    domains = state.get('domains', {})
    rate = 0.05
    decay_factor = math.exp(-rate * hours)
    decayed = removed = untouched = 0
    to_delete = []
    for dhash, entry in domains.items():
        if entry.get('type') == 'B':
            new_conf = entry['confidence'] * decay_factor
            if new_conf < 0.01:
                to_delete.append(dhash)
                removed += 1
            else:
                entry['confidence'] = round(new_conf, 6)
                decayed += 1
        else:
            untouched += 1
    for d in to_delete:
        del domains[d]
    _save_state(state)
    return {'decayed_B': decayed, 'removed_below_threshold': removed,
            'untouched_K_C': untouched, 'hours': hours, 'decay_factor': round(decay_factor, 6)}

def stats() -> dict:
    state = _load_state()
    domains = state.get('domains', {})
    counts = {'K': 0, 'B': 0, 'C': 0, 'UNKNOWN': 0}
    for e in domains.values():
        counts[e.get('type', 'UNKNOWN')] = counts.get(e.get('type', 'UNKNOWN'), 0) + 1

    regressions = []
    try:
        for line in _REGRESS_LOG.read_text().splitlines()[-10:]:
            try:
                regressions.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except (OSError, FileNotFoundError):
        pass

    return {
        'total_domains': len(domains),
        'type_counts': counts,
        'recent_regressions': len(regressions),
        'state_file': str(_STATE_FILE),
        'regression_log': str(_REGRESS_LOG),
    }

def self_test() -> dict:
    import tempfile, shutil
    failures = []
    # Use a temp dir to isolate state
    td = Path(tempfile.mkdtemp())
    orig_state = _STATE_FILE
    orig_regress = _REGRESS_LOG
    orig_consist = _CONSIST

    # Monkey-patch paths for test
    # Test via direct function calls with temp state, patching module globals
    import sys as _sys
    mod = _sys.modules[__name__]
    old_state = mod._STATE_FILE
    old_regress = mod._REGRESS_LOG
    old_consist = mod._CONSIST
    mod._STATE_FILE = td / 'epistemic-state.json'
    mod._REGRESS_LOG = td / 'epistemic-regressions.jsonl'
    mod._CONSIST = td / 'consistency-scores.jsonl'

    try:
        # Test 1: K without tool verification -> error
        r = update('the sky is blue', 'K', 0.9, evidence='just trust me')
        assert 'error' in r, f"K without tool-verify should error; got {r}"

        # Test 2: K with tool verification -> success
        r = update('the sky is blue', 'K', 0.9, evidence='tool:read_file /etc/os-release', has_tool_verification=True)
        assert r.get('type') == 'K', f"K update failed: {r}"
        assert not r.get('regression'), "fresh K should not be regression"

        # Test 3: K -> B downgrade = regression logged
        r = update('the sky is blue', 'B', 0.4, evidence='cloud cover today')
        assert r.get('regression') is True, "K->B downgrade should log regression"
        regress_lines = (td / 'epistemic-regressions.jsonl').read_text().strip().splitlines()
        assert len(regress_lines) >= 1, "regression not logged"
        reg = json.loads(regress_lines[-1])
        assert reg['old_type'] == 'K' and reg['new_type'] == 'B'

        # Test 4: C upgrade without consistency_score -> error
        r = update('all agents agree', 'C', 0.95)
        assert 'error' in r, f"C without Condorcet=1.0 should error; got {r}"

        # Test 5: C upgrade with consistency_score=1.0 -> success
        dhash_c = _dhash('all agents agree on this fact')
        (td / 'consistency-scores.jsonl').write_text(
            json.dumps({'domain_hash': dhash_c, 'consistency_score': 1.0}) + '\n'
        )
        r = update('all agents agree on this fact', 'C', 0.99)
        assert r.get('type') == 'C', f"C upgrade should succeed: {r}"

        # Test 6: decay only touches B-type
        # Set up one K and one B
        update('k-claim', 'K', 0.9, has_tool_verification=True)
        update('b-claim', 'B', 0.8)
        before_state = _load_state()
        k_conf_before = before_state['domains'][_dhash('k-claim')]['confidence']
        decay(10.0)
        after_state = _load_state()
        k_conf_after = after_state['domains'][_dhash('k-claim')]['confidence']
        b_conf_after = after_state['domains'].get(_dhash('b-claim'), {}).get('confidence', 0.0)
        assert k_conf_after == k_conf_before, f"K confidence should not decay: {k_conf_before} -> {k_conf_after}"
        assert b_conf_after < 0.8, f"B confidence should decay: got {b_conf_after}"

        # Test 7: query unknown domain -> UNKNOWN
        r = query('totally unknown domain xyz123')
        assert r['type'] == 'UNKNOWN', f"unknown domain should return UNKNOWN: {r}"

    except Exception as e:
        failures.append(str(e))
    finally:
        mod._STATE_FILE = old_state
        mod._REGRESS_LOG = old_regress
        mod._CONSIST = old_consist
        shutil.rmtree(td, ignore_errors=True)

    return {'self_test': 'PASS' if not failures else 'FAIL',
            'n_checks': 7, 'n_failures': len(failures), 'failures': failures}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    sub = parser.add_subparsers(dest='cmd')

    upd = sub.add_parser('update')
    upd.add_argument('--domain', required=True)
    upd.add_argument('--type', required=True, dest='ep_type')
    upd.add_argument('--confidence', type=float, required=True)
    upd.add_argument('--evidence', default='')
    upd.add_argument('--has-tool-verification', action='store_true')

    qry = sub.add_parser('query')
    qry.add_argument('--domain', required=True)

    dec = sub.add_parser('decay')
    dec.add_argument('--hours', type=float, required=True)

    sub.add_parser('stats')
    args = parser.parse_args()

    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    elif args.cmd == 'update':
        print(json.dumps(update(args.domain, args.ep_type, args.confidence,
                                args.evidence, args.has_tool_verification), indent=2))
    elif args.cmd == 'query':
        print(json.dumps(query(args.domain), indent=2))
    elif args.cmd == 'decay':
        print(json.dumps(decay(args.hours), indent=2))
    elif args.cmd == 'stats':
        print(json.dumps(stats(), indent=2))
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
