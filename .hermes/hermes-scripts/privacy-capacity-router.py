#!/usr/bin/python3
"""
privacy-capacity-router.py

Enables Hermes to delegate sensitive multi-step tasks across agent pools
without leaking sensitive context — routes via privacy-capacity trade-off.

Math basis: Privacy-capacity region (information-theoretic)
  The privacy-capacity region defines achievable (rate, privacy) pairs:
    C_priv(ε) = max I(X;Y) s.t. I(X;Z) ≤ ε
  where X=task, Y=result, Z=leaked context to adversarial observer.
  
  Operationally: each routing option has an estimated information rate
  (capability) and an estimated leakage (privacy cost). We select the
  route that maximises rate subject to leakage ≤ ε_budget.
  
  Leakage estimated by: fraction of sensitive tokens in context that
  would be included in the delegated message to the route.

Usage:
  python3 privacy-capacity-router.py --task TASK [--budget 0.2]
  python3 privacy-capacity-router.py --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = _HH / "cache" / "monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "privacy-capacity-routing.json"

import json

DEFAULT_BUDGET = 0.20   # max tolerated leakage fraction

# Sensitive token patterns (information that shouldn't reach untrusted routes)
SENSITIVE_PATTERNS = [
    r"(?i)\b(password|secret|token|api.?key|credential|auth)\b",
    r"(?i)\b(private|confidential|internal|pii|ssn|dob)\b",
    r"(?i)\b(salary|revenue|financial|banking|credit.?card)\b",
    r"(?i)\b(medical|health|diagnosis|patient|prescription)\b",
    r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b",  # card-like
    r"\b\d{3}-\d{2}-\d{4}\b",                       # SSN-like
]

# Route definitions: (name, capability, context_fraction_sent)
# context_fraction: what fraction of the full context this route receives
ROUTES = [
    {"name": "local_direct",    "capability": 0.60, "ctx_fraction": 0.00},  # no delegation
    {"name": "trusted_subagent","capability": 0.85, "ctx_fraction": 0.30},  # partial context
    {"name": "external_api",    "capability": 0.92, "ctx_fraction": 0.80},  # most context
    {"name": "full_delegation", "capability": 0.98, "ctx_fraction": 1.00},  # full context
]


def _sensitive_fraction(text: str) -> float:
    """Fraction of words that match sensitive patterns."""
    words = re.findall(r"\S+", text)
    if not words:
        return 0.0
    sensitive = sum(
        1 for w in words
        if any(re.search(pat, w) for pat in SENSITIVE_PATTERNS)
    )
    return sensitive / len(words)


def route(task: str, context: str, epsilon: float) -> dict:
    """Select route maximising capability subject to leakage ≤ epsilon."""
    sens_frac = _sensitive_fraction(task + " " + context)

    candidates = []
    for r in ROUTES:
        leakage = sens_frac * r["ctx_fraction"]
        feasible = leakage <= epsilon
        candidates.append({
            "name":       r["name"],
            "capability": r["capability"],
            "leakage":    round(leakage, 4),
            "feasible":   feasible,
        })

    feasible = [c for c in candidates if c["feasible"]]
    if feasible:
        chosen = max(feasible, key=lambda c: c["capability"])
        blocked = False
    else:
        # All routes leak too much — fall back to local_direct (zero leakage)
        chosen  = candidates[0]
        blocked = True

    return {
        "task":         task[:80],
        "sens_frac":    round(sens_frac, 4),
        "epsilon":      epsilon,
        "chosen_route": chosen["name"],
        "capability":   chosen["capability"],
        "leakage":      chosen["leakage"],
        "blocked":      blocked,
        "all_routes":   candidates,
    }


def run(task: str, context: str, epsilon: float, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    demos = [
        ("Summarise the quarterly report", "Revenue was $4.2M, salary pool $1.1M"),
        ("Debug the authentication module", "API key: sk-abc123, password check fails"),
        ("Fetch latest arXiv papers on RL", "Search arxiv for reinforcement learning"),
        ("Draft a generic email template", "Dear user, please find attached..."),
        (task, context),
    ] if task == "route this task" else [(task, context)]

    print(f"\n=== Privacy-Capacity Router — {now[:10]} ===")
    print(f"ε_budget={epsilon} (max leakage)\n")
    print(f"  {'Task':<45} {'Sens':>5}  {'Route':<20} {'Cap':>5} {'Leak':>5}")
    print("  " + "-" * 85)

    results = []
    blocked_count = 0
    for t, ctx in demos:
        r = route(t, ctx, epsilon)
        icon = "✗" if r["blocked"] else "✓"
        print(f"  {icon} {r['task'][:44]:<45} {r['sens_frac']:>5.3f}"
              f"  {r['chosen_route']:<20} {r['capability']:>5.3f} {r['leakage']:>5.3f}")
        results.append(r)
        if r["blocked"]:
            blocked_count += 1

    print(f"\nRouted: {len(results) - blocked_count}  Blocked to local: {blocked_count}")
    print("ALARM: no — privacy-capacity routing complete")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "results": results}, indent=2))
        _tmp_out_file.replace(OUT_FILE)
    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task",    default="route this task")
    p.add_argument("--context", default="")
    p.add_argument("--budget",  type=float, default=DEFAULT_BUDGET)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.task, args.context, args.budget, args.dry_run))


if __name__ == "__main__":
    main()
