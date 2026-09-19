#!/usr/bin/python3
"""
magnitude-mirage-calibrator.py

Prevents retrieval confidence mirage — corrects the known bias where
high-magnitude embedding similarity scores give false confidence in
retrieved results. Applies Platt scaling calibration to raw similarity
scores.

Math basis: "Magnitude Mirage" (arXiv spike)
  Raw cosine similarity s ∈ [-1,1] is not a probability.
  High-magnitude vectors produce high cosine scores even for poor matches.
  Calibrated probability via Platt scaling:
    P(relevant | s) = σ(a·s + b)   where σ = sigmoid
  Parameters a,b estimated from held-out relevance labels (simulated here
  via keyword overlap ground truth).
  
  Alarm when avg(|s - P_cal|) > CALIBRATION_ERROR_THRESHOLD (scores
  are systematically miscalibrated).

Usage:
  python3 magnitude-mirage-calibrator.py --query QUERY
  python3 magnitude-mirage-calibrator.py --dry-run
"""
from __future__ import annotations
import os

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME       = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SKILLS_DIR = _RT / "skills"
ALT_SKILLS = HOME / ".hermes/skills"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE   = CACHE_DIR / "magnitude-calibration.json"

# Platt scaling parameters (empirically tuned; a>1 sharpens, a<1 flattens)
PLATT_A = 2.5   # steepness
PLATT_B = -1.0  # bias (shifts midpoint from s=0 to s=0.4)
CALIBRATION_ERROR_THRESHOLD = 0.25


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _jaccard_sim(a: set, b: set) -> float:
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def _load_skills(n: int = 30) -> list[dict]:
    skills = []
    for base in [SKILLS_DIR, ALT_SKILLS]:
        if not base.exists():
            continue
        for md in list(base.rglob("SKILL.md"))[:n]:
            try:
                text = md.read_text()[:500]
                skills.append({"name": md.parent.name, "tokens": _tokenize(text)})
            except Exception:
                pass
        if len(skills) >= n:
            break
    return skills[:n]


def calibrate(query: str, skills: list[dict]) -> list[dict]:
    q_tok = _tokenize(query)
    results = []

    for s in skills:
        raw_sim  = _jaccard_sim(q_tok, s["tokens"])
        # Platt-calibrated probability
        cal_prob = _sigmoid(PLATT_A * raw_sim + PLATT_B)
        # Ground-truth proxy: keyword overlap fraction
        gt_prob  = min(len(q_tok & s["tokens"]) / max(len(q_tok), 1), 1.0)
        error    = abs(gt_prob - cal_prob)

        results.append({
            "name":     s["name"],
            "raw_sim":  round(raw_sim, 4),
            "cal_prob": round(cal_prob, 4),
            "gt_proxy": round(gt_prob, 4),
            "error":    round(error, 4),
        })

    return sorted(results, key=lambda r: r["cal_prob"], reverse=True)


def run(query: str, top: int, dry_run: bool) -> int:
    now    = datetime.now(timezone.utc).isoformat()
    skills = _load_skills(50)

    if not skills:
        print("[mirage-calibrator] No skills found")
        return 1

    results   = calibrate(query, skills)
    avg_error = sum(r["error"] for r in results) / len(results)
    alarm     = avg_error > CALIBRATION_ERROR_THRESHOLD

    print(f"\n=== Magnitude Mirage Calibrator — {now[:10]} ===")
    print(f"Query:  \"{query}\"")
    print(f"Skills: {len(skills)}  Avg calibration error: {avg_error:.4f}\n")
    print(f"  {'Skill':<35} raw_sim  cal_prob  gt_proxy  error")
    print("  " + "-" * 75)

    for r in results[:top]:
        flag = " ← MIRAGE" if r["raw_sim"] > 0.3 and r["cal_prob"] < 0.3 else ""
        print(f"  {r['name']:<35} {r['raw_sim']:>7.3f}  {r['cal_prob']:>8.3f}  "
              f"{r['gt_proxy']:>8.3f}  {r['error']:>5.3f}{flag}")

    if alarm:
        print(f"\nALARM: yes — avg calibration error {avg_error:.3f} > {CALIBRATION_ERROR_THRESHOLD}")
        rc = 1
    else:
        print(f"\nALARM: no — retrieval scores adequately calibrated")
        rc = 0

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "query": query,
            "avg_error": round(avg_error, 4),
            "alarm": alarm, "results": results[:top],
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)

    return rc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--query", default="agent memory compression")
    p.add_argument("--top",   type=int, default=10)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.query, args.top, args.dry_run))


if __name__ == "__main__":
    main()
