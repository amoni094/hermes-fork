#!/usr/bin/env python3
"""causal-memory-annotator.py — Pearl causal ladder annotation for memory commits.

Theory:
  Pearl (2000/2009) Causality. Three rungs of causal ladder (Pearl & Mackenzie 2018):
    Rung 1 OBSERVATIONAL: P(Y|X) — 'associated with', 'correlated', 'tends to'
    Rung 2 INTERVENTIONAL: P(Y|do(X)) — 'causes', 'leads to', 'results in'
    Rung 3 COUNTERFACTUAL: P(Y_x|X'=x') — 'would have', 'if X had not'
  Shpitser & Pearl (2006): P(Y|do(X)) identifiable from observational data
    iff no unblocked backdoor path in causal graph.
  Confound risk: if context mentions common cause C for both A and B,
    claim A->B requires controlling for C (backdoor criterion).
  UE penalty: higher rungs and confound risk attract uncertainty penalties
    because they make stronger claims from weaker evidence.

Usage:
  python3 causal-memory-annotator.py annotate --content TEXT [--context TEXT] [--query TEXT]
  python3 causal-memory-annotator.py --self-test
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, time
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

_UE_SCORES = _cache / 'ue-blackbox-scores.jsonl'

# Causal marker patterns
_R1_MARKERS = re.compile(
    r'\b(associated with|correlat|related to|tends? to|linked to|'
    r'goes? with|varies? with|co-occurs?)\b', re.IGNORECASE)
_R2_MARKERS = re.compile(
    r'\b(causes?|leads? to|results? in|due to|because of|therefore|hence|'
    r'thus|enables?|prevents?|increases?|decreases?|drives?|triggers?|'
    r'produces?|generates?|induces?|forces?|makes?)\b', re.IGNORECASE)
_R3_MARKERS = re.compile(
    r'\b(would have|had not|without .{1,40} would|if .{1,40} had not|'
    r'counterfactual|but for)\b', re.IGNORECASE)
_CONFOUND_MARKERS = re.compile(
    r'\b(both|common cause|confound|covariate|lurking|third variable|'
    r'common factor|shared cause|mediator|moderator|spurious)\b', re.IGNORECASE)
# Controlled experiment markers (reduce confound concern)
_CONTROL_MARKERS = re.compile(
    r'\b(experiment|controlled|randomize|random assignment|RCT|'
    r'intervention|do\(|placebo|double.blind)\b', re.IGNORECASE)

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

def _get_cached_ue(query: str) -> float:
    if not query:
        return 0.5
    qhash = _qhash(query)
    rows = _load_jsonl(_UE_SCORES)
    matches = [r for r in rows if r.get('query_hash') == qhash]
    if matches:
        return float(matches[-1].get('composite_ue', 0.5))
    return 0.5  # default when no cache

def _split_sentences(text: str) -> list[str]:
    # Split on sentence boundaries; keep non-empty
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 3]

def _classify_sentence(sentence: str, context: str = '') -> dict:
    combined = sentence + ' ' + context
    has_r3 = bool(_R3_MARKERS.search(sentence))
    has_r2 = bool(_R2_MARKERS.search(sentence))
    has_r1 = bool(_R1_MARKERS.search(sentence))
    has_control = bool(_CONTROL_MARKERS.search(combined))
    has_confound = bool(_CONFOUND_MARKERS.search(combined))

    if has_r3:
        rung = 3
        causal_type = 'COUNTERFACTUAL'
        base_penalty = 0.25
    elif has_r2:
        rung = 2
        causal_type = 'INTERVENTIONAL'
        base_penalty = 0.15
    elif has_r1:
        rung = 1
        causal_type = 'OBSERVATIONAL'
        base_penalty = 0.0
    else:
        rung = 0
        causal_type = 'NONE'
        base_penalty = 0.0

    confound_risk = has_confound and not has_control and rung >= 2
    confound_penalty = 0.20 if confound_risk else 0.0
    # Control evidence reduces penalty for Rung 2/3
    control_reduction = 0.10 if has_control and rung >= 2 else 0.0

    ue_penalty = max(0.0, min(0.5, base_penalty + confound_penalty - control_reduction))

    return {
        'text': sentence[:200],
        'rung': rung,
        'causal_type': causal_type,
        'confound_risk': confound_risk,
        'has_control_evidence': has_control,
        'ue_penalty': round(ue_penalty, 3),
    }

def annotate(content: str, context: str = '', query: str = '') -> dict:
    sentences = _split_sentences(content)
    if not sentences:
        return {
            'sentences': [],
            'max_rung': 0,
            'total_ue_penalty': 0.0,
            'composite_ue_adjusted': 0.0,
            'should_gate': False,
            'gate_reason': 'no sentences',
        }

    base_ue = _get_cached_ue(query)
    annotations = [_classify_sentence(s, context) for s in sentences]

    max_rung = max(a['rung'] for a in annotations)
    # Mean penalty, clipped
    penalties = [a['ue_penalty'] for a in annotations if a['rung'] > 0]
    total_ue_penalty = round(min(0.5, sum(penalties) / max(1, len(penalties))), 3)
    composite_ue_adjusted = round(min(1.0, base_ue + total_ue_penalty), 3)

    any_confound = any(a['confound_risk'] for a in annotations)

    # Gate logic (tighter than standard 0.75):
    # Rung 2 gate: warn at 0.4, deny at 0.6
    # Rung 3 gate: warn at 0.3, deny at 0.5
    # Confound: warn at 0.35, deny at 0.55
    gate_warn_thresh = {0: 0.75, 1: 0.75, 2: 0.40, 3: 0.30}
    gate_deny_thresh = {0: 0.90, 1: 0.90, 2: 0.60, 3: 0.50}
    warn_t = gate_warn_thresh.get(max_rung, 0.75)
    deny_t = gate_deny_thresh.get(max_rung, 0.90)
    if any_confound:
        warn_t = min(warn_t, 0.35)
        deny_t = min(deny_t, 0.55)

    should_gate = composite_ue_adjusted > warn_t
    gate_action = 'DENY' if composite_ue_adjusted > deny_t else ('WARN' if should_gate else 'PASS')
    gate_reason = (
        f"max_rung={max_rung} ({annotations[max(range(len(annotations)), key=lambda i: annotations[i]['rung'])]['causal_type']})"
        f" composite_ue_adjusted={composite_ue_adjusted} > threshold={warn_t}"
        if should_gate else 'below threshold'
    )

    return {
        'sentences': annotations,
        'max_rung': max_rung,
        'total_ue_penalty': total_ue_penalty,
        'base_ue': base_ue,
        'composite_ue_adjusted': composite_ue_adjusted,
        'any_confound_risk': any_confound,
        'gate_action': gate_action,
        'should_gate': should_gate,
        'gate_reason': gate_reason,
    }

def self_test() -> dict:
    failures = []

    # Test 1: no causal language -> empty annotations, no gate
    r = annotate('The weather is nice today. Birds are singing.')
    assert r['max_rung'] == 0, f"no causal -> rung 0, got {r['max_rung']}"
    assert r['should_gate'] is False, "no causal should not gate"
    assert r['total_ue_penalty'] == 0.0, f"no causal penalty, got {r['total_ue_penalty']}"

    # Test 2: Rung 1 (observational)
    r = annotate('Smoking is associated with lung cancer.')
    assert any(a['rung'] == 1 for a in r['sentences']), f"R1 not detected: {r['sentences']}"

    # Test 3: Rung 2 (interventional)
    r = annotate('High stress causes heart disease in most adults.')
    assert r['max_rung'] == 2, f"R2 not detected: {r['max_rung']}"
    assert any(a['ue_penalty'] > 0 for a in r['sentences'])

    # Test 4: Rung 3 (counterfactual)
    r = annotate('If Einstein had not published special relativity, physics would have advanced differently.')
    assert r['max_rung'] == 3, f"R3 not detected: {r['max_rung']}"
    assert r['total_ue_penalty'] > 0.0

    # Test 5: confound risk increases penalty
    r_no_confound = annotate('X causes Y.')
    r_confound = annotate('X causes Y. Both X and Y share a common cause Z.')
    assert r_confound['total_ue_penalty'] >= r_no_confound['total_ue_penalty'], \
        "confound should increase penalty"

    # Test 6: controlled experiment reduces penalty for Rung 2
    r_ctrl = annotate('In a randomized controlled experiment, drug X causes recovery.')
    r_no_ctrl = annotate('Drug X causes recovery.')
    # Control should reduce or equal penalty
    max_ctrl = max((a['ue_penalty'] for a in r_ctrl['sentences']), default=0)
    max_no_ctrl = max((a['ue_penalty'] for a in r_no_ctrl['sentences']), default=0)
    assert max_ctrl <= max_no_ctrl, \
        f"controlled experiment should reduce penalty: {max_ctrl} vs {max_no_ctrl}"

    # Test 7: empty string -> graceful, no crash
    r = annotate('')
    assert r['should_gate'] is False
    assert r['sentences'] == []

    # Test 8: composite_ue_adjusted always in [0,1]
    for content in ['X causes Y', '', 'a' * 2000, 'would have been better if not']:
        r = annotate(content)
        assert 0.0 <= r['composite_ue_adjusted'] <= 1.0, \
            f"adjusted UE out of range: {r['composite_ue_adjusted']}"

    return {'self_test': 'PASS' if not failures else 'FAIL',
            'n_checks': 8, 'n_failures': len(failures), 'failures': failures}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    sub = parser.add_subparsers(dest='cmd')
    ann = sub.add_parser('annotate')
    ann.add_argument('--content', required=True)
    ann.add_argument('--context', default='')
    ann.add_argument('--query', default='')
    args = parser.parse_args()

    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    elif args.cmd == 'annotate':
        print(json.dumps(annotate(args.content, args.context, args.query), indent=2))
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
