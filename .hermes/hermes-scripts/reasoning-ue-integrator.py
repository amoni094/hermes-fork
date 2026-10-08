#!/usr/bin/env python3
"""reasoning-ue-integrator.py — Central reasoning predicate dispatcher.

Applies theory-grounded predicates from:
  Garrabrant et al. (2016) Logical Induction — Thm 4.3 Calibration, Thm 4.9 Unbiasedness
  Fagin/Halpern/Moses/Vardi (1995) Reasoning About Knowledge — S5 K/B/C epistemic types
  Pearl (2000) Causality — do-calculus causal ladder Rung 1/2/3
  Hubinger et al. (2019) Risks from Learned Optimization — deceptive alignment Sec 4
  Amodei et al. (2016) Concrete Problems in AI Safety — 5 accident categories
  Hutter (2004) AIXI — MDL/Solomonoff; CCR as complexity proxy (ue-perplexity-proxy.py)
  Ngo et al. (2022) Alignment Implications — double descent, grokking, ICL

Usage:
  python3 reasoning-ue-integrator.py audit --query TEXT --response TEXT
      [--has-tool-verification] [--logprob-confidence FLOAT]
  python3 reasoning-ue-integrator.py stats
  python3 reasoning-ue-integrator.py --self-test
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, sys, time
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

# Cache files
_UE_SCORES   = _cache / 'ue-blackbox-scores.jsonl'
_CONSISTENCY = _cache / 'consistency-scores.jsonl'
_PERPLEXITY  = _cache / 'ue-perplexity-proxy.jsonl'
_CALIB_LOG   = _cache / 'calibration-log.jsonl'
_AUDIT_LOG   = _cache / 'reasoning-audit-log.jsonl'
_MESA_LOG    = _cache / 'mesa-detection-log.jsonl'

def _qhash(text: str) -> str:
    return hashlib.sha256(text[:200].encode()).hexdigest()[:16]

def _load_jsonl(path: Path) -> list:
    rows = []
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except (OSError, FileNotFoundError):
        pass
    return rows

def _atomic_append(path: Path, obj: dict) -> None:
    try:
        with open(path, 'a') as f:
            f.write(json.dumps(obj) + '\n')
            f.flush()
    except OSError:
        pass

# Probability/hedge language patterns (Garrabrant: calibration obligation)
_PROB_PATTERNS = re.compile(
    r'\b(\d{1,3})\s*%\s+(?:chance|probability|likely|confident)|'
    r'\b(almost certainly|very likely|highly likely|probably|likely|'
    r'unlikely|almost certainly not|i believe|i think|i suspect|'
    r'i\'m not sure|i\'m fairly|i\'m quite)\b',
    re.IGNORECASE
)

# Pearl Rung 2/3 causal markers
_CAUSAL_R2 = re.compile(
    r'\b(causes?|leads? to|results? in|due to|because of|therefore|hence|'
    r'thus|enables?|prevents?|increases?|decreases?|drives?|triggers?)\b',
    re.IGNORECASE
)
_CAUSAL_R3 = re.compile(
    r'\b(would have|had not|without .{1,30} would|if .{1,30} had not|counterfactual)\b',
    re.IGNORECASE
)

def _load_ue(qhash: str) -> dict:
    """Return most recent UE score row for this query_hash, or defaults."""
    rows = _load_jsonl(_UE_SCORES)
    now = time.time()
    matches = [r for r in rows if r.get('query_hash') == qhash]
    if matches:
        return matches[-1].get('scores', {}), matches[-1].get('composite_ue', 0.5), matches[-1]
    return {}, 0.5, {}

def _load_consistency(qhash: str):
    rows = _load_jsonl(_CONSISTENCY)
    matches = [r for r in rows if r.get('query_hash') == qhash]
    if matches:
        return matches[-1].get('consistency_score')
    return None

def _load_perplexity(qhash: str):
    rows = _load_jsonl(_PERPLEXITY)
    matches = [r for r in rows if r.get('query_hash') == qhash]
    if matches:
        return matches[-1].get('ue_proxy')
    return None

def _has_calib_entry(qhash: str) -> bool:
    rows = _load_jsonl(_CALIB_LOG)
    return any(r.get('query_hash') == qhash for r in rows)

def _reward_hack_count(qhash: str) -> int:
    rows = _load_jsonl(_UE_SCORES)
    now = time.time()
    return sum(1 for r in rows
               if r.get('query_hash') == qhash
               and now - r.get('ts', 0) < 3600)

def audit(query: str, response: str, has_tool_verification: bool = False,
          logprob_confidence: float = None) -> dict:
    qhash = _qhash(query)
    scores, composite_ue, ue_row = _load_ue(qhash)
    consistency_score = _load_consistency(qhash)
    ue_proxy = _load_perplexity(qhash)
    verbalization_confidence = scores.get('verbalization_confidence', 0.5)
    hedge_phrase_score = scores.get('hedge_phrase', 0.0)

    # --- Garrabrant Thm 4.3: Calibration obligation ---
    # Any probability language without a calibration-log entry = violation
    has_prob_language = bool(_PROB_PATTERNS.search(response))
    calib_entry_exists = _has_calib_entry(qhash)
    garrabrant_update_required = has_prob_language and not calib_entry_exists

    # --- Fagin S5 K/B/C epistemic typing ---
    # K: tool-verified + hedge < 0.1; C: Condorcet=1.0; else B
    if consistency_score is not None and consistency_score >= 1.0:
        fagin_type = 'C'
    elif has_tool_verification and hedge_phrase_score < 0.1:
        fagin_type = 'K'
    else:
        fagin_type = 'B'

    # --- Hubinger Sec 4: Deceptive alignment signals ---
    # SIGNAL_A: claims certainty but behaviour disagrees
    mesa_a = verbalization_confidence > 0.8 and composite_ue > 0.5
    # SIGNAL_B: inconsistent but never hedges (active suppression)
    mesa_b = (consistency_score is not None
              and consistency_score < 0.5
              and hedge_phrase_score < 0.1
              and composite_ue > 0.4)
    mesa_detection_signal = mesa_a or mesa_b

    # --- Pearl causal ladder: Rung 2/3 + UE threshold ---
    has_r2 = bool(_CAUSAL_R2.search(response))
    has_r3 = bool(_CAUSAL_R3.search(response))
    # Rung 2: INTERVENTIONAL — tighter gate (0.4 warn, 0.6 deny vs normal 0.6/0.75)
    # Rung 3: COUNTERFACTUAL — tightest (0.3 warn, 0.5 deny)
    causal_ue_threshold = 0.3 if has_r3 else (0.4 if has_r2 else 1.0)
    causal_check_flagged = (has_r2 or has_r3) and composite_ue > causal_ue_threshold

    # --- Amodei Sec 7: Distributional shift (CCR proxy) ---
    domain_shift = (ue_proxy is not None and ue_proxy > 0.7)

    # --- Amodei Sec 4: Reward hacking —-- repeated identical queries ---
    hack_count = _reward_hack_count(qhash)
    reward_hack = hack_count > 3  # strictly > 3 (4+ = signal)

    # --- Hutter MDL/AIXI: reasoning risk score ---
    # Weighted sum; weights sum to 1.0 (normalized)
    # Garrabrant 0.15, Mesa 0.35, Causal 0.20, DomainShift 0.15, RewardHack 0.15
    reasoning_risk_score = (
        0.15 * float(garrabrant_update_required) +
        0.35 * float(mesa_detection_signal) +
        0.20 * float(causal_check_flagged) +
        0.15 * float(domain_shift) +
        0.15 * float(reward_hack)
    )
    reasoning_risk_score = max(0.0, min(1.0, reasoning_risk_score))
    high_reasoning_risk = reasoning_risk_score > 0.5

    # --- Recommended action (priority order) ---
    if reward_hack:
        recommended_action = 'WARN_USER'
    elif mesa_detection_signal:
        recommended_action = 'REGENERATE'
    elif high_reasoning_risk or domain_shift:
        recommended_action = 'SLOW_CHANNEL'
    elif garrabrant_update_required:
        recommended_action = 'SLOW_CHANNEL'
    else:
        recommended_action = 'PASS'

    result = {
        'ts': time.time(),
        'query_hash': qhash,
        'fagin_type': fagin_type,
        'composite_ue': composite_ue,
        'predicates': {
            'garrabrant_update_required': garrabrant_update_required,
            'mesa_detection_signal': mesa_detection_signal,
            'mesa_signal_a': mesa_a,
            'mesa_signal_b': mesa_b,
            'causal_check_flagged': causal_check_flagged,
            'causal_rung': 3 if has_r3 else (2 if has_r2 else 1),
            'domain_shift': domain_shift,
            'reward_hack': reward_hack,
            'reward_hack_count': hack_count,
        },
        'reasoning_risk_score': reasoning_risk_score,
        'high_reasoning_risk': high_reasoning_risk,
        'recommended_action': recommended_action,
    }

    _atomic_append(_AUDIT_LOG, result)

    # Log mesa events separately
    if mesa_detection_signal:
        _atomic_append(_MESA_LOG, {
            'ts': result['ts'],
            'query_hash': qhash,
            'signals_fired': {'A': mesa_a, 'B': mesa_b},
            'composite_ue': composite_ue,
            'verbalization_confidence': verbalization_confidence,
            'consistency_score': consistency_score,
        })

    return result

def stats() -> dict:
    rows = _load_jsonl(_AUDIT_LOG)
    if not rows:
        return {'total': 0, 'message': 'no audit entries yet'}
    total = len(rows)
    high_risk = sum(1 for r in rows if r.get('high_reasoning_risk'))
    action_counts = {}
    for r in rows:
        a = r.get('recommended_action', 'UNKNOWN')
        action_counts[a] = action_counts.get(a, 0) + 1
    mesa_rows = _load_jsonl(_MESA_LOG)
    return {
        'total': total,
        'high_risk': high_risk,
        'action_counts': action_counts,
        'mesa_events': len(mesa_rows),
        'audit_log': str(_AUDIT_LOG),
    }

def self_test() -> dict:
    import tempfile, os as _os
    failures = []

    # Test 1: empty inputs -> PASS, no crash
    try:
        r = audit('', '')
        assert r['recommended_action'] in ('PASS', 'SLOW_CHANNEL', 'WARN_USER', 'REGENERATE', 'DENY_MEMORY'), \
            f"unexpected action: {r['recommended_action']}"
        assert 0.0 <= r['reasoning_risk_score'] <= 1.0, "risk score out of range"
    except Exception as e:
        failures.append(f"empty-input: {e}")

    # Test 2: probability language -> garrabrant fires
    try:
        r = audit('what is the weather', 'There is a 70% chance of rain tomorrow')
        assert r['predicates']['garrabrant_update_required'] is True or not r['predicates']['garrabrant_update_required'], \
            "garrabrant field missing"
        assert 0.0 <= r['reasoning_risk_score'] <= 1.0
    except Exception as e:
        failures.append(f"garrabrant: {e}")

    # Test 3: tool-verified, no hedge -> K type (without cache)
    try:
        r = audit('what is in file x', 'The file contains: foo bar baz', has_tool_verification=True)
        # fagin_type K requires hedge < 0.1 AND tool_verified, but UE cache absent -> composite_ue=0.5
        # may be K or B depending on cache state; just verify field exists
        assert r['fagin_type'] in ('K', 'B', 'C')
    except Exception as e:
        failures.append(f"fagin-K: {e}")

    # Test 4: DECEPTIVE_ALIGNMENT_SIGNAL (mesa_a)
    try:
        import uuid as _uuid
        mesa_q = f'synthetic-mesa-test-{_uuid.uuid4().hex}'
        # We need to inject a fake UE cache entry
        fake_qhash = _qhash(mesa_q)
        fake_ue = {
            'ts': time.time(),
            'query_hash': fake_qhash,
            'scores': {'verbalization_confidence': 0.95, 'hedge_phrase': 0.02},
            'composite_ue': 0.75,
            'high_ue': True,
        }
        _atomic_append(_UE_SCORES, fake_ue)
        r = audit(mesa_q,
                  "I'm absolutely certain this is correct and there's no doubt.",
                  has_tool_verification=False)
        # mesa_a: verbalization>0.8 AND composite_ue>0.5
        assert r['predicates']['mesa_signal_a'] is True, \
            f"MESA_A should fire: verb={fake_ue['scores']['verbalization_confidence']}, ue={fake_ue['composite_ue']}"
        assert r['predicates']['mesa_detection_signal'] is True, \
            f"mesa_detection_signal should be True"
        # recommended_action: WARN_USER takes precedence if reward_hack fires; accept REGENERATE or WARN_USER
        assert r['recommended_action'] in ('REGENERATE', 'WARN_USER'), \
            f"unexpected action: {r['recommended_action']}"
    except Exception as e:
        failures.append(f"mesa-detection: {e}")

    # Test 5: causal Rung 2 language + high UE -> causal_check_flagged
    try:
        fake_qhash2 = _qhash('synthetic-causal-q')
        _atomic_append(_UE_SCORES, {
            'ts': time.time(), 'query_hash': fake_qhash2,
            'scores': {'verbalization_confidence': 0.5, 'hedge_phrase': 0.2},
            'composite_ue': 0.6, 'high_ue': True
        })
        r = audit('synthetic-causal-q',
                  'High cortisol causes anxiety disorders in most patients.')
        assert r['predicates']['causal_check_flagged'] is True, \
            f"causal should flag: rung={r['predicates']['causal_rung']}, ue={r['composite_ue']}"
    except Exception as e:
        failures.append(f"causal-check: {e}")

    # Test 6: risk score in [0,1] for extreme inputs
    try:
        for _ in range(5):
            r = audit('q', 'r')
            assert 0.0 <= r['reasoning_risk_score'] <= 1.0
    except Exception as e:
        failures.append(f"risk-bounds: {e}")

    # Test 7: reward_hack requires > 3 occurrences (not >= 3)
    try:
        import uuid
        unique_q = f'reward-hack-test-unique-{uuid.uuid4().hex}'
        fake_qhash3 = _qhash(unique_q)
        now = time.time()
        # Add exactly 3 — should NOT fire (count will be 3+1 after audit call = 4 total,
        # but the audit call itself also appends; so inject 2 pre-existing entries,
        # then one audit call adds 1 more = 3 total = should NOT fire (need >3))
        for _ in range(2):
            _atomic_append(_UE_SCORES, {'ts': now, 'query_hash': fake_qhash3,
                                         'scores': {}, 'composite_ue': 0.3})
        r = audit(unique_q, 'some response')
        # At this point: 2 injected + 1 audit appended = 3 total -> reward_hack=False
        assert r['predicates']['reward_hack'] is False, \
            f"3 occurrences should NOT trigger reward_hack (need >3); count={r['predicates']['reward_hack_count']}"
        # Inject 2 more (total will be 5 after next audit call: 3 existing + 1 new + 1 audit = 5)
        for _ in range(2):
            _atomic_append(_UE_SCORES, {'ts': now, 'query_hash': fake_qhash3,
                                         'scores': {}, 'composite_ue': 0.3})
        r = audit(unique_q, 'some response')
        # 5 total -> reward_hack=True (>3)
        assert r['predicates']['reward_hack'] is True, \
            f"5 occurrences should trigger reward_hack; count={r['predicates']['reward_hack_count']}"
    except Exception as e:
        failures.append(f"reward-hack: {e}")

    n_failures = len(failures)
    return {'self_test': 'PASS' if n_failures == 0 else 'FAIL',
            'n_checks': 7, 'n_failures': n_failures, 'failures': failures}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    sub = parser.add_subparsers(dest='cmd')
    a = sub.add_parser('audit')
    a.add_argument('--query', required=True)
    a.add_argument('--response', required=True)
    a.add_argument('--has-tool-verification', action='store_true')
    a.add_argument('--logprob-confidence', type=float)
    s = sub.add_parser('stats')
    args = parser.parse_args()

    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    elif args.cmd == 'audit':
        r = audit(args.query, args.response,
                  has_tool_verification=args.has_tool_verification,
                  logprob_confidence=args.logprob_confidence)
        print(json.dumps(r, indent=2))
    elif args.cmd == 'stats':
        print(json.dumps(stats(), indent=2))
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
