#!/usr/bin/python3
"""
skill-ranker.py

Reduces oracle (LLM agent rollout) evaluations needed to evolve skills
by using a Plackett-Luce ranking model to predict relative skill quality
from observable features — without calling an LLM for each candidate.

Research basis (skill ranking via feature-based preference learning):
  Given M skill candidates and N evaluations (oracle calls), learn a
  ranking function f(skill_features) that predicts oracle preference.
  Uses pair-wise comparison data to fit a Bradley-Terry model:
    P(skill_i > skill_j) = exp(β·φ(i)) / (exp(β·φ(i)) + exp(β·φ(j)))

  Observable features (no LLM required):
    - Description length (detail proxy)
    - Number of `Use when` trigger phrases (specificity)
    - Age in days (staleness)
    - Number of tool references (implementation depth)
    - Number of pitfall entries (robustness)

Outputs ranked skill list + predicted quality scores, saving oracle calls
by filtering obvious low-quality candidates before evaluation.

Usage:
  python3 skill-ranker.py                    # rank all loaded skills
  python3 skill-ranker.py --top 20           # show top 20
  python3 skill-ranker.py --category devops  # filter by category
  python3 skill-ranker.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME       = Path.home()
SKILLS_DIR = HOME / ".hermes/skills"
FORK_SKILLS = HOME / ".hermes/profiles/fork/skills"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE   = CACHE_DIR / "skill-rankings.json"

now_ts = time.time()


def _extract_features(skill_path: Path) -> dict:
    """Extract observable features from SKILL.md without LLM."""
    text = ""
    md = skill_path / "SKILL.md"
    if md.exists():
        text = md.read_text(errors="replace")

    # Feature: description length
    m = re.search(r"description:\s*['\"]?(.+?)(?:['\"]?\n|$)", text)
    desc = m.group(1).strip() if m else ""
    desc_len = len(desc)

    # Feature: trigger specificity (count of "Use when" phrases)
    triggers = len(re.findall(r"(?i)use when", text))

    # Feature: age in days from last modification
    try:
        age_days = (now_ts - md.stat().st_mtime) / 86400.0
    except Exception:
        age_days = 365.0

    # Feature: tool references (implementation depth)
    tool_refs = len(re.findall(r"(?i)\b(terminal|execute_code|write_file|patch|web_search|browser_exec|skill_manage|delegate_task)\b", text))

    # Feature: pitfall/lesson entries
    pitfalls = len(re.findall(r"(?i)\b(pitfall|lesson|warning|note:|do not|never|avoid)\b", text))

    # Feature: total content length (richness proxy)
    content_len = len(text)

    return {
        "desc_len":    desc_len,
        "triggers":    triggers,
        "age_days":    age_days,
        "tool_refs":   tool_refs,
        "pitfalls":    pitfalls,
        "content_len": content_len,
    }


def _feature_vector(f: dict) -> np.ndarray:
    """Normalise and return feature vector for Bradley-Terry scoring."""
    return np.array([
        min(f["desc_len"] / 200.0, 1.0),       # description richness
        min(f["triggers"] / 5.0, 1.0),          # trigger specificity
        max(0.0, 1.0 - f["age_days"] / 180.0),  # recency (fresher = better)
        min(f["tool_refs"] / 10.0, 1.0),         # implementation depth
        min(f["pitfalls"] / 8.0, 1.0),           # robustness
        min(f["content_len"] / 3000.0, 1.0),     # overall richness
    ])


# Bradley-Terry weights (uniform prior — no oracle data yet; update with oracle pairs)
BT_WEIGHTS = np.array([0.25, 0.20, 0.15, 0.20, 0.10, 0.10])


def _bt_score(fv: np.ndarray) -> float:
    """Predicted Bradley-Terry log-odds score."""
    return float(np.dot(BT_WEIGHTS, fv))


def load_oracle_pairs() -> list[tuple[str, str, int]]:
    """
    Load oracle comparison pairs from cache file (if any).
    Format: [(winner_name, loser_name, weight), ...]
    Used to update BT_WEIGHTS via gradient descent (future: online learning).
    """
    pairs_file = CACHE_DIR / "skill-oracle-pairs.json"
    if not pairs_file.exists():
        return []
    try:
        return [tuple(p) for p in json.loads(pairs_file.read_text())]  # type: ignore
    except Exception:
        return []


def rank_skills(category: str | None, top: int) -> list[dict]:
    skills: list[dict] = []

    for skill_dir in list(SKILLS_DIR.rglob("SKILL.md")) + list(FORK_SKILLS.rglob("SKILL.md")):
        parent = skill_dir.parent
        cat = parent.parent.name  # category/skill_name/SKILL.md
        name = parent.name

        if category and category.lower() not in cat.lower():
            continue

        feats = _extract_features(parent)
        fv    = _feature_vector(feats)
        score = _bt_score(fv)

        skills.append({
            "name":        name,
            "category":    cat,
            "score":       round(score, 4),
            "desc_len":    feats["desc_len"],
            "triggers":    feats["triggers"],
            "age_days":    round(feats["age_days"], 1),
            "tool_refs":   feats["tool_refs"],
            "pitfalls":    feats["pitfalls"],
            "content_len": feats["content_len"],
        })

    # Sort by BT score descending
    skills.sort(key=lambda x: -x["score"])
    return skills[:top]


def run(category: str | None, top: int, dry_run: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    ranked = rank_skills(category, top)

    cat_label = f" (category={category})" if category else ""
    print(f"\n=== Skill Ranker — {now[:10]}{cat_label} ===")
    print(f"Ranked {len(ranked)} skills by predicted quality (Bradley-Terry model)")
    print(f"\n  {'Rank':<5} {'Score':<7} {'Triggers':<9} {'Age(d)':<8} {'Tools':<7} {'Pitfalls':<9} Skill")
    print("  " + "-" * 80)
    for i, s in enumerate(ranked, 1):
        print(f"  {i:<5} {s['score']:<7.4f} {s['triggers']:<9} {s['age_days']:<8.0f} "
              f"{s['tool_refs']:<7} {s['pitfalls']:<9} {s['category']}/{s['name']}")

    if len(ranked) >= 5:
        bottom_5 = ranked[-5:]
        print(f"\n  Low-quality candidates (oracle filter targets):")
        for s in bottom_5:
            print(f"    {s['score']:.4f}  {s['category']}/{s['name']} "
                  f"(age={s['age_days']:.0f}d, pitfalls={s['pitfalls']})")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now, "category": category, "top": top, "skills": ranked,
        }, indent=2))
        print(f"\nWritten: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--category", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(category=args.category, top=args.top, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
