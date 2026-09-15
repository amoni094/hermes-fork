#!/usr/bin/env python3
"""
memory-zscore-retention.py — Z-score based memory retention policy.

Scores staged memory entries on recency and access frequency, then flags
entries more than threshold sigma below the mean for demotion. Statistically
principled alternative to flat TTL cutoffs.

Weights (revised after adversarial review):
  - recency 55%  — newer entries more valuable; decays over 30 days
  - access  45%  — frequently accessed entries more valuable

Char-entropy removed from composite: high-entropy text (base64, stack traces,
random IDs) would score highly and be retained over low-entropy preferences
like "user prefers X" — exactly backwards.

Z-score threshold: 0.5σ demotes lowest ~31% (conservative default).
Minimum fact count: 8. Below that, std is too unstable to trust.

Usage:
    python3 memory-zscore-retention.py --dry-run
    python3 memory-zscore-retention.py --threshold 1.0
    python3 memory-zscore-retention.py --apply

State:
    Reads  ~/.hermes/memory-facts/staging.md
    Reads  ~/.hermes/memory-facts/lifecycle.db (table: fact_lifecycle)
    Writes atomic tempfile+rename to staging.md on --apply
    Appends to purge_log.jsonl (canonical schema: one record per run)
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

FACTS_DIR    = Path.home() / ".hermes" / "memory-facts"
STAGING_PATH = FACTS_DIR / "staging.md"
LIFECYCLE_DB = FACTS_DIR / "lifecycle.db"
PURGE_LOG    = FACTS_DIR / "purge_log.jsonl"

Z_THRESHOLD_DEFAULT = 0.5
MIN_FACTS_FOR_ZSCORE = 8   # std is unstable below this


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat()


def _split_facts(text: str) -> list[str]:
    """Split staging.md into individual fact blocks (§ separator or blank lines)."""
    if "§" in text:
        chunks = [c.strip() for c in text.split("§")]
    else:
        chunks = [c.strip() for c in re.split(r"\n{2,}", text)]
    return [c for c in chunks if c and len(c) > 10]


def _load_lifecycle_data() -> dict[str, dict]:
    """
    Load lifecycle data keyed by fact_text (first 120 chars, stripped).

    Live schema: fact_lifecycle(memory_id TEXT, fact_text TEXT,
                                valid_from TEXT, access_count INTEGER, ...)
    Returns {fact_key: {valid_from: str, access_count: int}}
    """
    data: dict[str, dict] = {}
    if not LIFECYCLE_DB.exists():
        return data
    try:
        con = sqlite3.connect(str(LIFECYCLE_DB))
        cur = con.cursor()
        cur.execute(
            "SELECT fact_text, valid_from, access_count "
            "FROM fact_lifecycle "
            "WHERE valid_to IS NULL OR valid_to = '' "
            "LIMIT 10000"
        )
        for fact_text, valid_from, access_count in cur.fetchall():
            if fact_text:
                key = fact_text[:120].strip()
                data[key] = {
                    "valid_from":    valid_from or "",
                    "access_count":  int(access_count or 0),
                }
        con.close()
    except Exception:
        # Silently swallow all SQLite errors — missing/corrupt DB is best-effort;
        # facts without lifecycle data get default scores (recency=0.5, access=0).
        pass
    return data


def _lookup(text: str, db_data: dict[str, dict]) -> dict:
    """Match a staged fact to lifecycle DB by text prefix."""
    key = text[:120].strip()
    return db_data.get(key, {})


def _recency_score(row: dict) -> float:
    """Recency [0..1]. 1=just written, decays linearly over 30 days. Default 0.5."""
    vf = row.get("valid_from", "")
    if not vf:
        return 0.5
    try:
        dt = datetime.fromisoformat(vf.replace("Z", "+00:00"))
        age_days = (now_utc() - dt).days
        return max(0.0, 1.0 - age_days / 30.0)
    except Exception:
        return 0.5


def _access_score(row: dict) -> float:
    """Access count [0..1] on log scale, cap at 10 accesses."""
    accesses = int(row.get("access_count", 0))
    return min(1.0, math.log(accesses + 1) / math.log(11))


def score_fact(text: str, db_data: dict[str, dict]) -> float:
    """
    Composite retention score [0..1].
    Weights: recency 55%, access_count 45%.
    No entropy: high-entropy junk (base64, stack traces) must not be preferred.
    """
    row = _lookup(text, db_data)
    r = _recency_score(row)
    a = _access_score(row)
    return 0.55 * r + 0.45 * a


def zscore_analysis(scores: list[float]) -> dict:
    """Compute mean and sample std (N-1). Returns z_scores list."""
    n = len(scores)
    if n == 0:
        return {"mean": 0.0, "std": 1.0, "z_scores": []}
    mean = sum(scores) / n
    if n == 1:
        return {"mean": mean, "std": 1.0, "z_scores": [0.0]}
    variance = sum((s - mean) ** 2 for s in scores) / (n - 1)  # sample variance
    std = math.sqrt(variance) if variance > 0 else 1e-9
    return {
        "mean":    mean,
        "std":     std,
        "z_scores": [(s - mean) / std for s in scores],
    }


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically via tempfile + os.replace."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".zscore-tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise


def _gaussian_pdf(x: float, mu: float, sigma: float) -> float:
    """Gaussian PDF N(mu, sigma) at x."""
    return (
        math.exp(-0.5 * ((x - mu) / sigma) ** 2)
        / (sigma * math.sqrt(2 * math.pi))
    )


def cmd_sprt_check(observations: list[dict]) -> dict:
    """Wald 1945 SPRT — sequential probability ratio test for memory retention.

    H1 (KEEP):    obs ~ N(0.8, 0.1)  — high recency+access scores
    H0 (DISCARD): obs ~ N(0.3, 0.15) — low recency+access scores

    Thresholds (alpha=0.05, beta=0.10):
      KEEP    when LR > beta/(1-alpha) = 0.10/0.95 ≈ 0.1053
      DISCARD when LR < alpha/(1-beta) = 0.05/0.90 ≈ 0.0556
      CONTINUE otherwise (need more observations)

    Each observation is the composite retention score (recency*0.55 + access*0.45).
    """
    ALPHA = 0.05
    BETA  = 0.10
    UPPER = BETA  / (1.0 - ALPHA)   # 0.1053 — KEEP boundary
    LOWER = ALPHA / (1.0 - BETA)    # 0.0556 — DISCARD boundary

    MU_H1, SIGMA_H1 = 0.8, 0.10
    MU_H0, SIGMA_H0 = 0.3, 0.15

    lr = 1.0  # running likelihood ratio
    n = 0

    for obs in observations:
        if not isinstance(obs, dict):
            continue
        # Compute composite score from recency and access fields
        recency = float(obs.get("recency", 0.5))
        access  = float(obs.get("access", 0.5))
        score   = 0.55 * recency + 0.45 * access

        p_h1 = _gaussian_pdf(score, MU_H1, SIGMA_H1)
        p_h0 = _gaussian_pdf(score, MU_H0, SIGMA_H0)

        # Avoid division by zero
        if p_h0 <= 0:
            p_h0 = 1e-300
        lr *= p_h1 / p_h0
        n  += 1

        if lr > UPPER:
            return {"decision": "KEEP",    "lr": round(lr, 6), "n_evaluated": n,
                    "note": "Wald 1945 SPRT, alpha=0.05 beta=0.10: LR > beta/(1-alpha)"}
        if lr < LOWER:
            return {"decision": "DISCARD", "lr": round(lr, 6), "n_evaluated": n,
                    "note": "Wald 1945 SPRT, alpha=0.05 beta=0.10: LR < alpha/(1-beta)"}

    return {"decision": "CONTINUE", "lr": round(lr, 6), "n_evaluated": n,
            "note": "Wald 1945 SPRT, alpha=0.05 beta=0.10: need more observations"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Z-score memory retention policy")
    parser.add_argument("subcommand", nargs="?", default=None,
                        help="Subcommand: sprt-check")
    parser.add_argument("--observations", type=str, default=None,
                        help="JSON list of {recency, access} dicts for sprt-check")
    parser.add_argument("--threshold", type=float, default=Z_THRESHOLD_DEFAULT,
                        help=f"Demote entries >Nσ below mean (default {Z_THRESHOLD_DEFAULT})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report demotions without writing")
    parser.add_argument("--apply", action="store_true",
                        help="Apply demotions (atomic rewrite + purge_log)")
    args = parser.parse_args()

    # Dispatch sprt-check subcommand
    if args.subcommand == "sprt-check":
        if not args.observations:
            print(json.dumps({"error": "--observations is required for sprt-check"}))
            sys.exit(1)
        try:
            obs_list = json.loads(args.observations)
            if not isinstance(obs_list, list):
                raise ValueError("must be a list")
        except (json.JSONDecodeError, ValueError) as e:
            print(json.dumps({"error": f"--observations parse error: {e}"}))
            sys.exit(1)
        print(json.dumps(cmd_sprt_check(obs_list)))
        return

    if not STAGING_PATH.exists():
        print(json.dumps({"error": "staging.md not found", "path": str(STAGING_PATH)}))
        sys.exit(1)

    raw   = STAGING_PATH.read_text(encoding="utf-8", errors="ignore")
    facts = _split_facts(raw)

    if not facts:
        print(json.dumps({"status": "empty", "facts_found": 0}))
        return

    if len(facts) < MIN_FACTS_FOR_ZSCORE:
        print(json.dumps({
            "status": "skipped",
            "reason": f"too few facts for reliable z-score ({len(facts)} < {MIN_FACTS_FOR_ZSCORE})",
            "facts_found": len(facts),
        }))
        return

    db_data  = _load_lifecycle_data()
    scores   = [score_fact(f, db_data) for f in facts]
    analysis = zscore_analysis(scores)
    mean, std = analysis["mean"], analysis["std"]
    z_scores  = analysis["z_scores"]

    keep, demote = [], []
    for i, (fact, score, z) in enumerate(zip(facts, scores, z_scores)):
        entry = {
            "index":   i,
            "preview": fact[:80].replace("\n", " "),
            "score":   round(score, 4),
            "z_score": round(z, 4),
            "action":  "KEEP" if z >= -args.threshold else "DEMOTE",
        }
        (keep if z >= -args.threshold else demote).append(entry)

    result = {
        "total_facts":   len(facts),
        "db_matches":    sum(1 for f in facts if _lookup(f, db_data)),
        "distribution":  {
            "mean_score":      round(mean, 4),
            "std_score":       round(std, 4),
            "threshold_sigma": -args.threshold,
        },
        "keep_count":   len(keep),
        "demote_count": len(demote),
        "demoted":      demote,
        "dry_run":      not args.apply,
    }

    if args.apply and demote:
        demote_indices = {e["index"] for e in demote}
        kept_facts     = [f for i, f in enumerate(facts) if i not in demote_indices]

        # Preserve original separator style
        sep = "\n§\n" if "§" in raw else "\n\n"
        _atomic_write(STAGING_PATH, sep.join(kept_facts))

        # Log in canonical purge_log schema: one record per run
        log_entry = {
            "ts":           now_iso(),
            "purged_count": len(demote),
            "policy":       "zscore_retention_v1",
            "threshold_sigma": -args.threshold,
            "entries": [
                {"preview": e["preview"], "z_score": e["z_score"], "score": e["score"]}
                for e in demote
            ],
        }
        with open(PURGE_LOG, "a", encoding="utf-8") as pf:
            pf.write(json.dumps(log_entry) + "\n")

        result["applied"] = True
    else:
        result["applied"] = False
        if not args.dry_run and not args.apply:
            result["note"] = "Use --dry-run to preview or --apply to execute"

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
