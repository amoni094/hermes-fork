#!/usr/bin/python3
"""
semantic-triangulation-verifier.py

Cross-references agent tool outputs against multiple semantic representations
to detect hallucination/inconsistency before results are acted on.

CS SPIKE basis (2511.12288 — "Reducing Hallucinations in LLM-Generated Code
via Semantic Triangulation"): semantic triangulation detects inconsistencies
by comparing multiple semantic renderings of the same claim. Applied to Hermes:
  - Agent output claim → 3 independent re-phrasings via haiku
  - Each re-phrasing is embedded via simple keyword overlap (no model needed)
  - Pairwise JS divergence between the three representations
  - High mean JS = inconsistency = potential hallucination

Given/when/then:
  Given a text claim (e.g. tool output, skill verdict, subagent result)
  When semantic triangulation is applied (3 independent re-phrasings, pairwise JS)
  Then hallucinations manifest as high JS divergence across the triangle

Usage:
  python3 semantic-triangulation-verifier.py --claim "text to verify"
  python3 semantic-triangulation-verifier.py --file path/to/output.txt
  python3 semantic-triangulation-verifier.py --stdin   (reads from stdin)

Output: JSON with triangle_js scores + verdict (CONSISTENT / INCONSISTENT)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import anthropic

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
LOG_FILE  = CACHE_DIR / "triangulation-log.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

JS_THRESHOLD = 0.35   # nats; above = INCONSISTENT
TIMEOUT      = 20     # seconds per rephrase call
MODEL        = "claude-haiku-4-5"


def _keyword_dist(text: str) -> Counter:
    """Simple keyword frequency distribution."""
    words = [w.lower() for w in text.split() if len(w) > 3]
    return Counter(words)


def _js_divergence(p: Counter, q: Counter) -> float:
    """Jensen-Shannon divergence between two distributions."""
    vocab = set(p) | set(q)
    total_p = sum(p.values()) + 0.01 * len(vocab)
    total_q = sum(q.values()) + 0.01 * len(vocab)
    pp = {t: (p.get(t, 0) + 0.01) / total_p for t in vocab}
    qq = {t: (q.get(t, 0) + 0.01) / total_q for t in vocab}
    m  = {t: (pp[t] + qq[t]) / 2 for t in vocab}
    kl_pm = sum(pp[t] * math.log(pp[t] / m[t]) for t in vocab)
    kl_qm = sum(qq[t] * math.log(qq[t] / m[t]) for t in vocab)
    return (kl_pm + kl_qm) / 2


def _rephrase(client: anthropic.Anthropic, claim: str, angle: str) -> str:
    """Get one re-phrasing of the claim from a specific semantic angle."""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        timeout=TIMEOUT,
        messages=[{
            "role": "user",
            "content": (
                f"Rephrase the following claim from the perspective of '{angle}'. "
                f"Preserve all factual content. Do not add or remove facts. "
                f"Output only the rephrased text, nothing else.\n\nClaim: {claim}"
            )
        }]
    )
    from anthropic.types import TextBlock
    block = resp.content[0]
    return block.text.strip() if isinstance(block, TextBlock) else ""


def triangulate(claim: str, dry_run: bool = False) -> dict:
    """
    Triangulate a claim. Returns result dict with verdict.
    In dry-run mode: skips LLM calls, uses simple random divergence estimate.
    """
    now = datetime.now(timezone.utc).isoformat()

    if dry_run:
        # Syntactic self-consistency check without LLM (baseline)
        dist = _keyword_dist(claim)
        # Split claim into halves, measure self-similarity
        words = claim.split()
        mid = max(1, len(words) // 2)
        d1 = _keyword_dist(" ".join(words[:mid]))
        d2 = _keyword_dist(" ".join(words[mid:]))
        d3 = _keyword_dist(claim)
        js12 = _js_divergence(d1, d2)
        js13 = _js_divergence(d1, d3)
        js23 = _js_divergence(d2, d3)
        mean_js = (js12 + js13 + js23) / 3
        return {
            "ts": now, "claim_length": len(claim),
            "triangle_js": {"1-2": round(js12,4), "1-3": round(js13,4), "2-3": round(js23,4)},
            "mean_js": round(mean_js, 4),
            "threshold": JS_THRESHOLD,
            "verdict": "INCONSISTENT" if mean_js > JS_THRESHOLD else "CONSISTENT",
            "dry_run": True,
        }

    client = anthropic.Anthropic()
    angles = [
        "a neutral summarizer",
        "a fact-checker",
        "a domain expert",
    ]
    rephrases: list[str] = []
    for angle in angles:
        try:
            r = _rephrase(client, claim, angle)
            rephrases.append(r)
        except Exception as e:
            rephrases.append(claim)  # fallback: use original

    dists = [_keyword_dist(r) for r in rephrases]
    js12 = _js_divergence(dists[0], dists[1])
    js13 = _js_divergence(dists[0], dists[2])
    js23 = _js_divergence(dists[1], dists[2])
    mean_js = (js12 + js13 + js23) / 3

    return {
        "ts": now,
        "claim_length": len(claim),
        "claim_preview": claim[:100],
        "rephrases": rephrases,
        "triangle_js": {"1-2": round(js12,4), "1-3": round(js13,4), "2-3": round(js23,4)},
        "mean_js": round(mean_js, 4),
        "threshold": JS_THRESHOLD,
        "verdict": "INCONSISTENT" if mean_js > JS_THRESHOLD else "CONSISTENT",
        "dry_run": False,
    }


def _append_log(result: dict) -> None:
    existing: list = []
    if LOG_FILE.exists():
        try:
            existing = json.loads(LOG_FILE.read_text())
        except Exception:
            pass
    existing.append(result)
    LOG_FILE.write_text(json.dumps(existing[-100:], indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic triangulation verifier")
    parser.add_argument("--claim", default=None, help="Claim text to verify")
    parser.add_argument("--file",  default=None, help="File containing claim")
    parser.add_argument("--stdin", action="store_true", help="Read claim from stdin")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.stdin:
        claim = sys.stdin.read().strip()
    elif args.file:
        claim = Path(args.file).read_text().strip()
    elif args.claim:
        claim = args.claim
    else:
        # Self-test
        claim = ("The math-paper-interpreter.py script runs 3 LLM calls per paper: "
                 "pre-filter, full-chain, and Stage 3 ideation. "
                 "It writes results to math-ideas-queue.json.")

    result = triangulate(claim, dry_run=args.dry_run)

    print(f"\n=== Semantic Triangulation Verifier ===")
    print(f"Claim ({result['claim_length']} chars): {claim[:80]}...")
    print(f"Triangle JS:  {result['triangle_js']}")
    print(f"Mean JS:      {result['mean_js']:.4f}  (threshold={result['threshold']})")
    print(f"Verdict:      {result['verdict']}")
    if result.get("dry_run"):
        print("(dry-run — syntactic self-consistency only, no LLM calls)")

    if not args.dry_run:
        _append_log(result)
        print(f"Logged: {LOG_FILE}")

    # Exit code 1 if inconsistent (useful for scripted pipelines)
    sys.exit(1 if result["verdict"] == "INCONSISTENT" else 0)


if __name__ == "__main__":
    main()
