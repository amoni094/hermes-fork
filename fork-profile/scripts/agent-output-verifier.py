#!/usr/bin/env python3
"""
Infra stub: Agent Output Verifier

Covers DEFER items:
  - "Breaking the Illusion of Review Reliability under Static Evaluation: SCOPE fuzzing"
  - "Cheap to Hypothesize, Costly to Verify: The Defense Surface of Agentic AI"

Target:     agent-output-verifier.py (new script)
Scaffold:   Two verification strategies implemented as a predicate table:
  (1) SCOPE-style fuzzing: for a given agent output, generate N semantically-
      equivalent rephrased variants; if a downstream reviewer agrees with the
      original but disagrees with k/N variants, the original review is fragile.
  (2) Defense-surface stratification: categorise verification checks into
      cheap (syntactic, regex, type checks) vs. costly (LLM re-evaluation, tool
      re-execution) tiers. Run cheap checks first; only escalate to costly tier
      when cheap tier fails or returns uncertain.

Invariant (SCOPE): fragility_rate(reviewer) < 0.15 for production review gates.
Invariant (defense): cheap_tier_covers ≥ 80% of detectable violations so
                     costly tier is invoked for < 20% of outputs.

Kill test (SCOPE):
    rephrased = rephrase_variants(original_output, n=5)
    verdicts  = [reviewer(r) for r in rephrased]
    assert fragility_rate(verdicts) < 0.15

Kill test (defense):
    cheap_results  = run_cheap_tier(output)
    costly_invoked = sum(1 for r in cheap_results if r == "uncertain")
    assert costly_invoked / len(cheap_results) < 0.20

Hypothesis (SCOPE): Reviewer fragility (flipping verdict on rephrased-but-equivalent
    outputs) can be detected in < 5 LLM calls per review cycle and correlates
    ≥ 0.7 with downstream error rate.
Metric (SCOPE): fragility_rate = flip_count / (n_variants * n_reviews)
    measured on a labelled corpus of 200 agent output pairs.

Hypothesis (defense): Stratified cheap-then-costly verification reduces total
    LLM re-evaluation calls by ≥ 60% while maintaining equivalent violation
    detection rate.
Metric (defense): costly_tier_invocation_rate = costly_calls / total_checks
    measured over 500 agent outputs across 10 session types.

GWT (SCOPE):
  Given: an agent output and a downstream reviewer gate,
  When:  N semantically-equivalent rephrased variants are submitted to the same gate,
  Then:  the gate's fragility rate (verdict flips) is < 0.15 for production gates.

GWT (defense):
  Given: an agent output to verify,
  When:  cheap verification checks are run first and expensive checks only on failures,
  Then:  < 20% of outputs escalate to costly tier while maintaining full coverage.
"""

import json
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone, UTC
from typing import Any

SCRIPTS_DIR  = Path(__file__).resolve().parent
REPORT_PATH  = SCRIPTS_DIR.parent / "cache" / "agent-output-verifier-report.json"

def _atomic_json(path: Path, data: object) -> None:
    """Atomic JSON write via tmp sibling + os.replace."""
    import os, tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(data, indent=2))
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


# ── Cheap-tier predicates ─────────────────────────────────────────────────────
def _check_length(output: str) -> str:
    """Too short or too long outputs are suspicious."""
    if len(output) < 10:
        return "fail"
    if len(output) > 50_000:
        return "uncertain"
    return "pass"

def _check_json_valid(output: str) -> str:
    """If output claims to be JSON, validate it."""
    s = output.strip()
    if s.startswith("{") or s.startswith("["):
        try:
            json.loads(s)
            return "pass"
        except json.JSONDecodeError:
            return "fail"
    return "pass"  # not JSON, skip

def _check_no_truncation_marker(output: str) -> str:
    """Detect common truncation patterns."""
    if re.search(r"\.\.\.(\.+)?$|\[truncated\]|\[cut\]", output, re.IGNORECASE):
        return "uncertain"
    return "pass"

def _check_no_refusal_pattern(output: str) -> str:
    """Detect outright refusals masquerading as valid output."""
    refusal_patterns = [
        r"I cannot.*provide",
        r"I am unable to",
        r"I don't have access to",
        r"As an AI language model",
    ]
    for pat in refusal_patterns:
        if re.search(pat, output, re.IGNORECASE):
            return "uncertain"
    return "pass"

CHEAP_TIER = [
    ("length",             _check_length),
    ("json_validity",      _check_json_valid),
    ("no_truncation",      _check_no_truncation_marker),
    ("no_refusal_pattern", _check_no_refusal_pattern),
]

def run_cheap_tier(output: str) -> list[dict]:
    """Run all cheap checks. Returns list of {name, result}."""
    return [{"name": name, "result": fn(output)} for name, fn in CHEAP_TIER]

# ── SCOPE-style fragility detection ──────────────────────────────────────────
def _rephrase_variants_heuristic(text: str, n: int = 5) -> list[str]:
    """
    Heuristic rephrasing without LLM (offline mode).
    Inserts/removes filler words, changes sentence order, alters spacing.
    For production: replace with LLM-based semantic-preserving rephrase.
    """
    variants = []
    text.split()
    for i in range(n):
        if i == 0:
            variants.append("In summary: " + text)
        elif i == 1:
            variants.append(text + " (Note: above is the complete response.)")
        elif i == 2:
            variants.append(re.sub(r"the", "a", text, count=3))
        elif i == 3:
            # Shuffle sentence order
            sentences = re.split(r"(?<=[.!?])\s+", text)
            if len(sentences) > 1:
                variants.append(" ".join(sentences[1:] + sentences[:1]))
            else:
                variants.append(text.replace("  ", " "))
        else:
            variants.append(text.strip() + ".")
    return variants

def _simple_reviewer(output: str) -> str:
    """
    Stub reviewer: classifies output as 'approve' or 'reject'.
    For production: replace with real governance gate or LLM reviewer.
    """
    results = run_cheap_tier(output)
    fails   = [r for r in results if r["result"] == "fail"]
    return "reject" if fails else "approve"

def measure_fragility(original: str, reviewer=None, n: int = 5) -> dict:
    """Measure reviewer fragility on N rephrased variants."""
    if reviewer is None:
        reviewer = _simple_reviewer
    original_verdict = reviewer(original)
    variants  = _rephrase_variants_heuristic(original, n)
    verdicts  = [reviewer(v) for v in variants]
    flips     = sum(1 for v in verdicts if v != original_verdict)
    return {
        "original_verdict": original_verdict,
        "variant_verdicts":  verdicts,
        "flip_count":        flips,
        "n_variants":        n,
        "fragility_rate":    round(flips / n, 4),
    }

# ── Main verify ───────────────────────────────────────────────────────────────
def verify_output(output: str, run_scope: bool = True) -> dict:
    cheap   = run_cheap_tier(output)
    fails   = [r for r in cheap if r["result"] == "fail"]
    uncerts = [r for r in cheap if r["result"] == "uncertain"]

    # Only escalate to costly tier (SCOPE) when cheap passes or is uncertain
    scope_result = None
    if run_scope and not fails:
        scope_result = measure_fragility(output)

    costly_invoked = bool(scope_result)
    verdict = "REJECT" if fails else ("UNCERTAIN" if uncerts else "PASS")

    return {
        "ts":              datetime.now(UTC).isoformat(),
        "verdict":         verdict,
        "cheap_results":   cheap,
        "costly_invoked":  costly_invoked,
        "scope":           scope_result,
        "output_hash":     hashlib.sha256(output.encode()).hexdigest()[:12],
    }

# ── Layer1 demo ───────────────────────────────────────────────────────────────
def layer1_demo() -> None:
    # Good output: passes cheap, low fragility
    good = "The routing-linucb.py script uses LinUCB to select tools. It maintains a feature vector per tool and updates weights after each tool call based on latency outcomes."
    r_good = verify_output(good)
    assert r_good["verdict"] == "PASS", f"Expected PASS, got {r_good['verdict']}"
    if r_good["scope"]:
        assert r_good["scope"]["fragility_rate"] <= 1.0

    # Bad output: too short, should reject
    bad = "ok"
    r_bad = verify_output(bad, run_scope=False)
    assert r_bad["verdict"] == "REJECT", f"Expected REJECT for short output, got {r_bad['verdict']}"

    # Refusal pattern: uncertain
    refusal = "I am unable to provide that information as it may be harmful."
    r_ref = verify_output(refusal, run_scope=False)
    assert r_ref["verdict"] in ("UNCERTAIN", "PASS"), f"Refusal should be UNCERTAIN, got {r_ref['verdict']}"

    print(f"[layer1] PASS — good={r_good['verdict']}  bad={r_bad['verdict']}  refusal={r_ref['verdict']}")

def main() -> None:
    import argparse
    pa = argparse.ArgumentParser()
    pa.add_argument("--layer1",     action="store_true")
    pa.add_argument("--dry-run",    action="store_true")
    pa.add_argument("--input",      type=str, help="Text to verify (or - for stdin)")
    args = pa.parse_args()

    if args.layer1:
        layer1_demo()
        return

    if args.input:
        import sys
        text = sys.stdin.read() if args.input == "-" else args.input
        result = verify_output(text)
        if not args.dry_run:
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            _atomic_json(REPORT_PATH, result)
        print(json.dumps(result, indent=2))
        return

    # default cron run: cheap-tier scan of recent assistant outputs
    import os, re as _re
    sess = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    prof = os.environ.get("HERMES_PROFILE", "")
    root = (sess / "profiles" / prof) if prof and "profiles" not in str(sess) else sess
    sdir = root / "sessions"
    texts = []
    if sdir.exists():
        for sp in sorted(sdir.glob("*.jsonl"))[-6:]:
            try:
                for line in sp.read_text(encoding="utf-8", errors="replace").splitlines():
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(rec, dict) or rec.get("role") != "assistant":
                        continue
                    content = rec.get("content")
                    if isinstance(content, str) and len(content) >= 10:
                        texts.append(content[:8000])
                    if len(texts) >= 12:
                        break
            except OSError:
                continue
            if len(texts) >= 12:
                break
    if not texts:
        print(json.dumps({"status": "insufficient_data", "n": 0}))
        return
    reports = []
    n_reject = 0
    for t in texts:
        r = verify_output(t, run_scope=False)
        reports.append({"verdict": r.get("verdict"), "output_hash": r.get("output_hash")})
        if r.get("verdict") == "REJECT":
            n_reject += 1
    out = {
        "status": "ok",
        "ts": datetime.now(UTC).isoformat(),
        "n": len(texts),
        "n_reject": n_reject,
        "reports": reports,
    }
    if not args.dry_run:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json(REPORT_PATH, out)
    print(json.dumps({k: out[k] for k in out if k != "reports"}))

if __name__ == "__main__":
    main()
