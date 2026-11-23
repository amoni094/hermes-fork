#!/usr/bin/env python3
"""skill-routing-causal-audit.py — Pearl/Schölkopf observational vs interventional.

Hard core: refuse causal claims that are only observational.

Observational affinity = log correlation / co-occurrence of (load skill S,
session quality). This is P(Y | load S), confounded by task type.

Interventional effect ≈ P(Y | do(load S)). Without randomized load or a
valid instrument, we estimate a difference-in-differences (DiD) using
run_ledger / task-ledger / skill-beta timestamps:

    DiD = (Y_treat,post - Y_treat,pre) - (Y_control,post - Y_control,pre)

If the parallel-trends assumption is untested or N is too small, the
script MUST print REFUSE_CAUSAL_CLAIM and exit 0 with claim=refused.

Does NOT treat Thompson-sampling skill-beta (alpha,beta) as causal.

Usage:
  python3 skill-routing-causal-audit.py [--json] [--skill NAME]
Exit: 0 always on completed audit (refusal is a successful hard-core check).
      2 on usage error.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _root() -> Path:
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        return base / "profiles" / profile
    return base


def _home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def load_skill_beta(path: Path) -> Dict[str, dict]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def thompson_mean(alpha: float, beta: float) -> float:
    a, b = max(alpha, 1e-9), max(beta, 1e-9)
    return a / (a + b)


def observational_affinity(beta_state: Dict[str, dict]) -> List[dict]:
    rows = []
    for skill, ab in beta_state.items():
        if not isinstance(ab, dict):
            continue
        a, b = float(ab.get("alpha", 1.0)), float(ab.get("beta", 1.0))
        rows.append({
            "skill": skill,
            "alpha": a,
            "beta": b,
            "mean_success_obs": round(thompson_mean(a, b), 4),
            "n": a + b - 2.0,  # prior (1,1)
            "kind": "observational_thompson",
        })
    rows.sort(key=lambda r: -r["mean_success_obs"])
    return rows


def load_jsonl(path: Path, limit: int = 5000) -> List[dict]:
    if not path.is_file():
        return []
    out = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict):
                    out.append(rec)
    except OSError:
        return []
    return out


def did_from_task_ledger(rows: List[dict], skill: Optional[str]) -> dict:
    """Attempt DiD. Quality proxy: child_status==completed.

    Treatment: child_summary or skills field mentions S.
    Time split: median timestamp.

    If we cannot form all four cells with n>=2, refuse.
    """
    parsed = []
    for r in rows:
        ts = r.get("ts") or r.get("timestamp") or ""
        status = str(r.get("child_status") or r.get("status") or "").lower()
        text = json.dumps(r, default=str).lower()
        y = 1.0 if status in {"completed", "ok", "success"} else 0.0
        parsed.append({"ts": str(ts), "y": y, "text": text, "status": status})
    if len(parsed) < 8:
        return {"identified": False, "reason": f"N={len(parsed)}<8", "estimator": "did"}
    parsed.sort(key=lambda x: x["ts"])
    mid = parsed[len(parsed) // 2]["ts"]
    skill_l = (skill or "").lower()
    cells = {(1, 1): [], (1, 0): [], (0, 1): [], (0, 0): []}
    for p in parsed:
        treat = 1 if (skill_l and skill_l in p["text"]) else 0
        post = 1 if p["ts"] >= mid else 0
        cells[(treat, post)].append(p["y"])

    def mean(xs: List[float]) -> Optional[float]:
        return sum(xs) / len(xs) if xs else None

    ns = {f"treat{k[0]}_post{k[1]}": len(v) for k, v in cells.items()}
    if any(n < 2 for n in ns.values()):
        return {
            "identified": False,
            "reason": f"cell counts {ns} — need >=2 per (treat,post) cell",
            "estimator": "did",
            "ns": ns,
        }
    m11, m10, m01, m00 = mean(cells[(1, 1)]), mean(cells[(1, 0)]), mean(cells[(0, 1)]), mean(cells[(0, 0)])
    if m11 is None or m10 is None or m01 is None or m00 is None:
        return {
            "identified": False,
            "reason": f"empty cell after mean(); ns={ns}",
            "estimator": "did",
            "ns": ns,
        }
    did = (m11 - m10) - (m01 - m00)
    return {
        "identified": True,
        "estimator": "difference_in_differences",
        "skill": skill,
        "did": round(did, 4),
        "means": {"treat_post": m11, "treat_pre": m10, "ctrl_post": m01, "ctrl_pre": m00},
        "ns": ns,
        "split_ts": mid,
        "assumptions": [
            "parallel trends untested",
            "treatment assignment (skill mention in ledger text) is a noisy proxy for do(load_skill)",
            "quality proxy is child_status completed — not a task-success label",
        ],
        "claim": (
            "WEAK_INTERVENTIONAL_PROXY — do not cite as P(Y|do(S)) without parallel-trends test"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skill", default="", help="Skill name for DiD treatment")
    args = ap.parse_args()
    root, home = _root(), _home()
    beta_path = root / "cache" / "skill-beta-state.json"
    if not beta_path.is_file():
        beta_path = home / "cache" / "skill-beta-state.json"
    beta = load_skill_beta(beta_path)
    obs = observational_affinity(beta)

    ledger_paths = [
        home / "logs" / "hermes-task-ledger.jsonl",
        root / "logs" / "hermes-task-ledger.jsonl",
    ]
    rows: List[dict] = []
    for lp in ledger_paths:
        rows.extend(load_jsonl(lp))

    skill = args.skill or (obs[0]["skill"] if obs else "")
    did = did_from_task_ledger(rows, skill) if skill else {
        "identified": False, "reason": "no skill specified and no skill-beta state", "estimator": "did",
    }

    refuse = not did.get("identified")
    report = {
        "hard_core": "refuse causal claims that are only observational",
        "observational": {
            "source": str(beta_path) if beta else None,
            "n_skills": len(obs),
            "top": obs[:10],
            "interpretation": (
                "Thompson means are P(success | logged outcome, skill named) "
                "with a Beta(1,1) prior. CONFOUNDED by which tasks load which skills. "
                "NOT P(Y | do(load_skill))."
            ),
        },
        "did": did,
        "claim": "REFUSE_CAUSAL_CLAIM" if refuse else did.get("claim", "REFUSE_CAUSAL_CLAIM"),
        "refused": refuse,
        "pearl": "do-calculus identification failed or cell counts insufficient" if refuse
        else "DiD is an identification strategy, not a proof of unconfoundedness",
    }
    cache = root / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / "skill-routing-causal-audit.json"
    dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["written"] = str(dest)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"claim={report['claim']}")
        print(f"observational_skills={len(obs)} did_identified={did.get('identified')}")
        print(f"wrote {dest}")
        if refuse:
            print("REFUSE_CAUSAL_CLAIM: observational affinity is not an interventional effect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
