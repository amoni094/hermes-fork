#!/usr/bin/env python3
"""
critique-bank.py — CritICL critique bank for inference-time failure conditioning.

arXiv:2608.27455 (CritICL): Build an offline CritBank from cheap-model failures.
At inference time, inject 1-3 failure-mode critique cards instead of extra samples.
ICL-from-failures — not verifier loops. No extra generations.

Card schema:
  {query, wrong_trace, failure_mode, critique, created_at, source_session, source_model}

Failure modes (Hermes-specific clustering):
  - constraint_skip: agent ignored an active must-constraint
  - unverified_final: agent claimed done without verification step
  - stale_assumption: agent acted on outdated fact (no freshness check)
  - tool_injection: tool output caused a state change the agent didn't authorise
  - scope_creep: agent took actions outside the stated task boundary
  - context_drop: agent forgot a key goal mid-task (Paritok failure mode)
  - retry_loop: agent retried same action >= 3 times without progress (SLO violation)
  - false_attribution: agent attributed a cause to an observation without testing alternatives

Usage:
  critique-bank.py add --session SESSION --failure-mode FAILURE_MODE --critique TEXT [--query Q]
  critique-bank.py match --query QUERY [--top N]
  critique-bank.py list [--failure-mode FAILURE_MODE]
  critique-bank.py inject --query QUERY [--top N]   # prints injection cards for system prompt
  critique-bank.py hypothesize --observation TEXT --context TEXT [--candidates JSON] [--top N] [--session SID]
  critique-bank.py false-attribution --claim TEXT --context TEXT
  critique-bank.py stats
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

BANK_PATH = Path.home() / ".hermes/cache/critique-bank.jsonl"
FAILURE_MODES = [
    "constraint_skip",
    "unverified_final",
    "stale_assumption",
    "tool_injection",
    "scope_creep",
    "context_drop",
    "retry_loop",
    "false_attribution",
    "other",
]


def _load_bank() -> list[dict]:
    if not BANK_PATH.exists():
        return []
    entries = []
    with BANK_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def _save_entry(entry: dict) -> None:
    BANK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BANK_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _simple_overlap(a: str, b: str) -> float:
    """Jaccard overlap on word sets — fast, no ML required."""
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def cmd_add(args: argparse.Namespace) -> int:
    entry = {
        "query": (args.query or "").strip(),
        "wrong_trace": (args.wrong_trace or "").strip(),
        "failure_mode": args.failure_mode,
        "critique": args.critique.strip(),
        "source_session": args.session,
        "source_model": getattr(args, "source_model", "unknown"),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rule": (args.rule or "").strip(),
        "outcome": (args.outcome or "").strip(),
    }
    _save_entry(entry)
    print(json.dumps({"ok": True, "entry": entry}, indent=2))
    return 0


def cmd_match(args: argparse.Namespace) -> int:
    bank = _load_bank()
    if not bank:
        print("[]")
        return 0
    query = args.query.strip()
    scored = []
    for e in bank:
        score = _simple_overlap(query, e.get("query", "") + " " + e.get("critique", ""))
        scored.append((score, e))
    scored.sort(key=lambda x: -x[0])
    top = scored[: args.top]
    results = []
    for s, card in top:
        results.append({"score": round(s, 3), **card})
    print(json.dumps(results, indent=2))
    # H4 fix: [RULE] is now inside the JSON object, not pre-printed to stdout
    # (pre-printing broke any json.loads consumer of this command's output)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    bank = _load_bank()
    if args.failure_mode:
        bank = [e for e in bank if e.get("failure_mode") == args.failure_mode]
    print(json.dumps(bank, indent=2))
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    """
    Print critique cards formatted for system prompt injection.
    arXiv:2608.27455: inject as ICL examples, not as extra generation.
    Prepend 1-3 cards before the task description.
    """
    bank = _load_bank()
    if not bank:
        print("# [CritICL] No critique bank entries yet.")
        return 0
    query = args.query.strip()
    scored = []
    for e in bank:
        score = _simple_overlap(query, e.get("query", "") + " " + e.get("critique", ""))
        scored.append((score, e))
    scored.sort(key=lambda x: -x[0])
    top = scored[: args.top]
    if not top or top[0][0] < 0.05:
        print("# [CritICL] No relevant critiques found for this query.")
        return 0
    lines = ["## Failure Critiques (CritICL — arXiv:2608.27455)", ""]
    lines.append("Before starting, review these past failure modes relevant to this task:")
    lines.append("")
    for i, (score, e) in enumerate(top, 1):
        lines.append(f"**Critique {i}** [{e.get('failure_mode', 'other')}] (relevance: {score:.2f})")
        if e.get("query"):
            lines.append(f"  Task context: {e['query'][:120]}")
        lines.append(f"  What went wrong: {e.get('critique', '')[:300]}")
        lines.append("")
    lines.append("Avoid repeating these failure patterns in your current task.")
    print("\n".join(lines))
    return 0


def _wm_must_texts(session_id: str | None) -> list[str]:
    if not session_id:
        return []
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:120]
    path = Path.home() / ".hermes" / "cache" / "working-memory" / f"{safe}.json"
    if not path.exists():
        return []
    try:
        doc = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    texts = []
    for c in doc.get("constraints") or []:
        if (c.get("binding") or "").lower() == "must" and c.get("text"):
            texts.append(str(c["text"]))
    return texts


def _observation_clauses(observation: str) -> list[str]:
    parts = []
    for chunk in observation.replace(";", ".").split("."):
        t = chunk.strip()
        if t:
            parts.append(t)
    return parts or [observation.strip() or "the observation"]


def cmd_hypothesize(args: argparse.Namespace) -> int:
    """Abductive best-explanation hypotheses for an observation (Peirce / arXiv:2505.21935)."""
    observation = (args.observation or "").strip()
    context = (args.context or "").strip()
    top_n = max(1, int(args.top))
    if not observation:
        print(json.dumps({"error": "--observation is required", "hypotheses": []}))
        return 2

    raw_cands = getattr(args, "candidates", None)
    if raw_cands is not None and str(raw_cands).strip() != "":
        try:
            cands = json.loads(raw_cands)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"malformed --candidates JSON: {e}", "hypotheses": []}))
            return 2
        if not isinstance(cands, list):
            print(json.dumps({"error": "--candidates must be a JSON list", "hypotheses": []}))
            return 2
        if len(cands) == 0:
            print(json.dumps({"error": "--candidates is empty; nothing to rank", "hypotheses": []}))
            return 2
        clauses = _observation_clauses(observation)
        scored = []
        for c in cands:
            text = str(c).strip()
            if not text:
                continue
            plaus = 0.5 + 0.2 * _simple_overlap(observation + " " + context, text)
            scored.append({
                "hypothesis": text,
                "plausibility": round(max(0.0, min(1.0, plaus)), 3),
                "test_to_confirm": f"Discriminate '{text[:80]}' against rivals with a falsifying test.",
                "would_explain": clauses[:1],
            })
        if not scored:
            print(json.dumps({"error": "--candidates contained no non-empty items", "hypotheses": []}))
            return 2
        scored.sort(key=lambda x: -x["plausibility"])
        print(json.dumps({"hypotheses": scored[:top_n]}, indent=2, ensure_ascii=False))
        return 0

    clauses = _observation_clauses(observation)
    focus = clauses[0][:160]
    combined = f"{observation} {context}".strip()
    wm_must = _wm_must_texts(getattr(args, "session", None))

    templates = [
        {
            "hypothesis": f"The observation is produced by a primary fault matching '{focus}'.",
            "base": 0.72,
            "test_to_confirm": f"Isolate and reproduce '{focus}' with a minimal test that holds context fixed.",
            "would_explain": list(clauses),
        },
        {
            "hypothesis": "A transient environmental or timing condition produced the observation (not a durable code fault).",
            "base": 0.58,
            "test_to_confirm": "Retry the same operation unchanged; if it does not recur, prefer transient over structural cause.",
            "would_explain": clauses[:1],
        },
        {
            "hypothesis": "A tool, dependency, or permission failure independent of the first suspected cause produced the observation.",
            "base": 0.54,
            "test_to_confirm": "Check exit codes, logs, and auth/permissions separately from the suspected primary component.",
            "would_explain": list(clauses),
        },
        {
            "hypothesis": "Stale context or an outdated assumption (false reading of current state) produced the observation.",
            "base": 0.50,
            "test_to_confirm": "Re-read live state instead of prior traces; confirm freshness before attributing cause.",
            "would_explain": clauses[:1],
        },
        {
            "hypothesis": "The agent incorrectly attributed a cause without testing alternatives (false_attribution).",
            "base": 0.46,
            "test_to_confirm": "Enumerate at least two rival causes and run a discriminating test that would falsify the first guess.",
            "would_explain": ["why a single-cause story looked convincing", *clauses[:1]],
        },
        {
            "hypothesis": "An operator/agent write immediately before the observation is the actual cause.",
            "base": 0.42,
            "test_to_confirm": "Diff recent writes against the observation timestamp; revert the last write and re-observe.",
            "would_explain": list(clauses),
        },
    ]

    scored = []
    for t in templates:
        plaus = float(t["base"])
        # Prefer explanations that cover more observation clauses (best explanation).
        plaus += 0.04 * min(3, len(t["would_explain"]))
        # Prefer simpler hypotheses (fewer words).
        words = len(t["hypothesis"].split())
        plaus += 0.06 if words <= 18 else 0.0
        # Overlap with observation+context.
        plaus += 0.08 * _simple_overlap(combined, t["hypothesis"] + " " + t["test_to_confirm"])
        # Consistency with WM must-constraints.
        hypo_l = t["hypothesis"].lower()
        for ct in wm_must:
            cl = ct.lower()
            if any(p in hypo_l for p in ("do not", "don't", "never")):
                continue
            if any(tok in hypo_l for tok in cl.split() if len(tok) > 4):
                # overlapping content: slight boost if not obviously contradicting
                if any(prefix in cl for prefix in ("do not ", "don't ", "never ", "must not ")):
                    banned = cl
                    for prefix in ("do not ", "don't ", "never ", "must not "):
                        if prefix in cl:
                            banned = cl.split(prefix, 1)[1]
                            break
                    if banned.strip() and banned.strip() in hypo_l:
                        plaus -= 0.18
                    else:
                        plaus += 0.05
                else:
                    plaus += 0.05
        plaus = max(0.0, min(1.0, plaus))
        scored.append({
            "hypothesis": t["hypothesis"],
            "plausibility": round(plaus, 3),
            "test_to_confirm": t["test_to_confirm"],
            "would_explain": t["would_explain"],
        })

    scored.sort(key=lambda x: -x["plausibility"])
    hypotheses = scored[:top_n]
    print(json.dumps({"hypotheses": hypotheses}, indent=2, ensure_ascii=False))
    return 0


def cmd_false_attribution(args: argparse.Namespace) -> int:
    """Check a causal claim for false-attribution risk.

    Exit 0 = LOW risk (claim plausible, context supports it)
    Exit 1 = MEDIUM risk (possible but alternatives not ruled out)
    Exit 2 = HIGH risk (claim unsupported or alternatives explain it better)
    """
    claim = (args.claim or "").strip()
    context = (getattr(args, "context", None) or "").strip()
    if not claim:
        print(json.dumps({"error": "claim is required", "exit_code": 2}))
        return 2

    cl = claim.lower()
    ctx = context.lower()

    def _has_word(text: str, word: str) -> bool:
        return bool(re.search(rf"\b{re.escape(word)}\b", text))

    def _has_any(text: str, words: list[str]) -> bool:
        return any(_has_word(text, w) for w in words)

    # "no evidence" / "without evidence" must not count as supporting evidence.
    evidence_denied = bool(re.search(
        r"\b(no|without|lacking|not enough|absence of)\s+evidence\b",
        ctx + " " + cl,
    )) or bool(re.search(r"\b(unverified|untested|speculative)\b", ctx + " " + cl))

    # Strong causal-evidence signals — sufficient on their own to lower risk
    strong_evidence_words = [
        "rct", "randomized", "controlled trial", "p<", "p <", "p=0.", "p = 0.",
        "confidence interval", "odds ratio", "effect size", "replicated",
        "peer.reviewed", "meta.analysis", "systematic review",
    ]
    has_strong_evidence = any(
        re.search(rf"\b{re.escape(w)}\b" if " " not in w else re.escape(w), cl + " " + ctx, re.IGNORECASE)
        for w in strong_evidence_words
    )

    support_words = [
        "because", "evidence", "verified", "verify", "test", "tests",
        "passed", "pass", "ruled", "alternative", "alternatives", "bisect",
        "reproduc",
    ]
    # Check both claim and context for supporting language
    has_support = (not evidence_denied) and (
        has_strong_evidence or _has_any(ctx, support_words)
    )
    causal_assert = _has_any(cl, ["caused", "fixed", "attributed"]) or "due to" in cl
    hedged = _has_any(cl, ["might", "may", "could", "possibly", "perhaps"])
    correlated_only = _has_word(ctx, "correlated") and not has_support

    high_signals = [
        causal_assert and len(context) < 20 and not has_support,
        causal_assert and not has_support and not hedged,
        causal_assert and evidence_denied,
        _has_word(cl, "fixed") and not _has_any(ctx, ["test", "tests", "verify", "verified", "pass", "passed"]),
    ]
    medium_signals = [
        hedged,
        correlated_only or _has_word(ctx, "correlated"),
        causal_assert and len(context) < 50 and not has_support,
    ]

    if sum(1 for x in high_signals if x) >= 2:
        risk, reason, rc = "HIGH", "Asserts causation without evidence of alternative elimination.", 2
    elif sum(1 for x in high_signals if x) == 1 or sum(1 for x in medium_signals if x) >= 2:
        risk, reason, rc = "MEDIUM", "Plausible but alternatives not explicitly ruled out.", 1
    else:
        risk, reason, rc = "LOW", "Claim appears grounded; context suggests alternatives considered.", 0

    print(json.dumps({
        "claim": claim,
        "claim_chars": len(claim),
        "risk": risk,
        "reason": reason,
        "exit_code": rc,
    }, indent=2, ensure_ascii=False))
    return rc


def cmd_stats(args: argparse.Namespace) -> int:
    bank = _load_bank()
    from collections import Counter
    counts = Counter(e.get("failure_mode", "other") for e in bank)
    print(json.dumps({
        "total": len(bank),
        "by_failure_mode": dict(counts.most_common()),
    }, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="CritICL critique bank for Hermes (arXiv:2608.27455)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Record a failure critique")
    p_add.add_argument("--session", "-s", required=True, help="Session ID where failure occurred")
    p_add.add_argument("--failure-mode", required=True, choices=FAILURE_MODES)
    p_add.add_argument("--critique", required=True, help="What went wrong + how to avoid")
    p_add.add_argument("--query", default="", help="Task description at time of failure")
    p_add.add_argument("--wrong-trace", default="", help="Brief description of wrong steps taken")
    p_add.add_argument("--source-model", default="unknown", help="Model that failed")
    p_add.add_argument("--rule", default="", help="Corrective rule: what to do differently next time")
    p_add.add_argument("--outcome", default="", help="What actually happened due to this failure")
    p_add.set_defaults(func=cmd_add)

    p_match = sub.add_parser("match", help="Find relevant critiques for a query")
    p_match.add_argument("--query", required=True)
    p_match.add_argument("--top", type=int, default=3)
    p_match.set_defaults(func=cmd_match)

    p_list = sub.add_parser("list", help="List all critiques")
    p_list.add_argument("--failure-mode", choices=FAILURE_MODES, default=None)
    p_list.set_defaults(func=cmd_list)

    p_inject = sub.add_parser("inject", help="Print injection cards for system prompt")
    p_inject.add_argument("--query", required=True)
    p_inject.add_argument("--top", type=int, default=3)
    p_inject.set_defaults(func=cmd_inject)

    p_stats = sub.add_parser("stats", help="Show bank statistics")
    p_stats.set_defaults(func=cmd_stats)

    p_hyp = sub.add_parser("hypothesize", help="Abductive hypotheses for an observation")
    p_hyp.add_argument("--observation", required=True, help="What was observed")
    p_hyp.add_argument("--context", default="", help="Surrounding context")
    p_hyp.add_argument("--candidates", default=None,
                       help="JSON list of competing hypotheses to rank. Empty list → exit 2.")
    p_hyp.add_argument("--top", type=int, default=3, help="Number of hypotheses to generate (default 3)")
    p_hyp.add_argument("--session", "-s", default=None, help="Optional WM session for constraint consistency")
    p_hyp.set_defaults(func=cmd_hypothesize)

    p_fa = sub.add_parser("false-attribution", help="Check a causal claim for false-attribution risk")
    p_fa.add_argument("--claim", required=True, help="The causal claim to check (e.g. 'X caused Y')")
    p_fa.add_argument("--context", default="", help="Supporting evidence context")
    p_fa.set_defaults(func=cmd_false_attribution)

    args = ap.parse_args()
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
