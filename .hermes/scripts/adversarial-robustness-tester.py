#!/usr/bin/python3
"""
adversarial-robustness-tester.py

Enables detection of over-confident, misleading skill responses before
they propagate through multi-agent pipelines — applies adversarial
perturbation probes to skill outputs and measures confidence stability.

Math basis: "Deception Delta" adversarial evaluation
  A response is adversarially fragile if small perturbations of the input
  produce large swings in claimed confidence:
    Δ_deception = |conf(response | perturbed_input) - conf(response | input)|
  High Δ_deception + high initial confidence → likely over-confident/misleading.
  
  Operationally: generate synonym/negation perturbations of the task query,
  re-evaluate skill response overlap, measure confidence swing.

Usage:
  python3 adversarial-robustness-tester.py --response TEXT --query QUERY
  python3 adversarial-robustness-tester.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "adversarial-robustness-report.json"

DECEPTION_THRESHOLD    = 0.35   # alarm if deception delta > 0.35
CONFIDENCE_FLOOR       = 0.50   # only test responses claiming ≥ 50% confidence

# Perturbation strategies
NEGATIONS = {
    "is": "is not", "are": "are not", "can": "cannot", "will": "will not",
    "does": "does not", "has": "has not", "should": "should not",
}
SYNONYMS = {
    "fast": "quick", "large": "big", "small": "tiny", "good": "effective",
    "error": "failure", "correct": "accurate", "best": "optimal",
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def _confidence_proxy(response: str, query_tokens: set[str]) -> float:
    """Estimate response confidence via overlap + certainty language."""
    resp_tokens = _tokenize(response)
    overlap     = len(resp_tokens & query_tokens) / max(len(query_tokens), 1)

    # Certainty boosters
    certain = len(re.findall(
        r"(?i)\b(definitely|certainly|always|guaranteed|precisely|exactly)\b", response
    ))
    # Uncertainty reducers
    uncertain = len(re.findall(
        r"(?i)\b(maybe|perhaps|might|could|possibly|unclear|unsure)\b", response
    ))

    conf = overlap + certain * 0.10 - uncertain * 0.08
    return max(0.0, min(conf, 1.0))


def _perturb(query: str) -> list[str]:
    """Generate adversarial perturbations of the query."""
    perturbed = []

    # Negation perturbation
    neg = query
    for w, neg_w in NEGATIONS.items():
        neg = re.sub(rf"\b{w}\b", neg_w, neg, count=1)
    if neg != query:
        perturbed.append(neg)

    # Synonym swap
    syn = query
    for w, s in SYNONYMS.items():
        syn = re.sub(rf"\b{w}\b", s, syn, count=1, flags=re.IGNORECASE)
    if syn != query:
        perturbed.append(syn)

    # Random word drop (remove every 4th word)
    words  = query.split()
    drop   = " ".join(w for i, w in enumerate(words) if (i + 1) % 4 != 0)
    if drop != query:
        perturbed.append(drop)

    return perturbed or [query + " not"]


def test_robustness(response: str, query: str) -> dict:
    q_tok       = _tokenize(query)
    base_conf   = _confidence_proxy(response, q_tok)

    if base_conf < CONFIDENCE_FLOOR:
        return {
            "query":      query[:60],
            "base_conf":  round(base_conf, 4),
            "note":       f"base confidence {base_conf:.2f} below floor {CONFIDENCE_FLOOR}",
            "fragile":    False,
        }

    perturbations = _perturb(query)
    pert_confs    = [_confidence_proxy(response, _tokenize(p)) for p in perturbations]
    max_delta     = max(abs(base_conf - pc) for pc in pert_confs)
    avg_delta     = sum(abs(base_conf - pc) for pc in pert_confs) / len(pert_confs)

    fragile = max_delta > DECEPTION_THRESHOLD

    return {
        "query":       query[:60],
        "base_conf":   round(base_conf, 4),
        "pert_confs":  [round(pc, 4) for pc in pert_confs],
        "max_delta":   round(max_delta, 4),
        "avg_delta":   round(avg_delta, 4),
        "fragile":     fragile,
        "verdict":     "FRAGILE" if fragile else "ROBUST",
    }


def run(response: str | None, query: str | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    demo_cases = [
        ("The answer is definitely correct and precisely accurate in all cases.",
         "is the result correct and reliable"),
        ("This might work but could have errors depending on context.",
         "will this produce correct results"),
        ("Memory compression always improves performance by exactly 40%.",
         "does memory compression improve performance"),
    ]

    if response and query:
        cases = [(response, query)]
    else:
        cases = demo_cases

    print(f"\n=== Adversarial Robustness Tester — {now[:10]} ===")
    results  = []
    fragile  = 0

    for resp, qry in cases:
        r = test_robustness(resp, qry)
        icon = "✗" if r.get("fragile") else "✓"
        print(f"\n  {icon} Query: \"{r['query']}\"")
        if "note" in r:
            print(f"      {r['note']}")
        else:
            print(f"      base_conf={r['base_conf']:.3f}  "
                  f"max_delta={r['max_delta']:.3f}  verdict={r['verdict']}")
        results.append(r)
        if r.get("fragile"):
            fragile += 1

    print(f"\nFragile responses: {fragile}/{len(results)}")
    if fragile:
        print("ALARM: yes — adversarially fragile responses detected")
    else:
        print("ALARM: no — responses are adversarially robust")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({"ts": now, "results": results}, indent=2))

    return 1 if fragile else 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--response", default=None)
    p.add_argument("--query",    default=None)
    p.add_argument("--dry-run",  action="store_true")
    args = p.parse_args()
    sys.exit(run(args.response, args.query, args.dry_run))


if __name__ == "__main__":
    main()
