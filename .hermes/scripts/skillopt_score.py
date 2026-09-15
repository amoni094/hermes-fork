#!/usr/bin/env python3
"""
skillopt_score.py — SkillOpt-inspired skill quality scorer for Hermes.

Adapted from SkillOpt (arXiv:2605.23904, Microsoft Research).
SkillOpt uses a trained optimizer model to propose bounded edits to skill docs
and accept/reject via held-out validation. This script implements the SCORING
and DIAGNOSIS half of that loop — it evaluates skills against quality criteria
without requiring a training loop.

Usage:
  python3 ~/.hermes/scripts/skillopt_score.py [skill_path]
  python3 ~/.hermes/scripts/skillopt_score.py ~/.hermes/skills/research/academic-literature-review/SKILL.md
  python3 ~/.hermes/scripts/skillopt_score.py --all         # score all skills
  python3 ~/.hermes/scripts/skillopt_score.py --top 10      # show bottom 10 (most fixable)

Scoring criteria (deterministic, no LLM needed):
  1. Has triggers section       (20pts) — ensures skill is discovered correctly
  2. Has pitfalls section       (20pts) — encodes hard-won lessons
  3. Has verification steps     (15pts) — evidence-grounded completion
  4. Commands are exact/runnable (15pts) — no vague "run X" without a real command
  5. Description length          (10pts) — too short = underspecified, too long = bloated
  6. Version/metadata present    (10pts) — enables tracking
  7. Related skills linked       (10pts) — enables routing

Total: 100pts. Threshold for "needs improvement": < 60.

This is NOT a replacement for human review. It surfaces candidates for the
skill curator (hermes-skill-library-consolidation-audit) to focus on.

References:
  SkillOpt: arXiv:2605.23904 (Microsoft Research, +19.1pp Claude Code)
  CoALA:    arXiv:2309.02427 (Princeton, TMLR 2024) — procedural memory = skills
  ExpeL:    arXiv:2308.10144 (Tsinghua LeapLab, AAAI 2024) — extractive insight distillation
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any


SKILLS_ROOT = Path.home() / ".hermes" / "skills"

# Minimum/maximum description lengths for the scoring gate
MIN_DESC_WORDS = 10
MAX_DESC_WORDS = 80

# Floor score below which a skill is flagged as a priority fix
PRIORITY_THRESHOLD = 60


def clopper_pearson_lower(k, n, alpha=0.05):
    """Exact Clopper-Pearson 95% lower confidence bound on binomial proportion.
    Source: generalization_theory primer. At n<50, Hoeffding half-width ~0.55 = uninformative.
    Returns 0.0 for n==0 or k==0. Returns 1.0 for k==n.
    """
    import math
    if n == 0 or k == 0:
        return 0.0
    if k == n:
        # H2 fix: exact lower bound at perfect score is (alpha/2)^(1/n), not 1.0
        return (alpha / 2) ** (1.0 / n)

    def _betainc(a, b, x, tol=1e-10):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        if x > (a + 1) / (a + b + 2):
            return 1.0 - _betainc(b, a, 1.0 - x)
        lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
        front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
        f, C, D, TINY = 1.0, 1.0, 0.0, 1e-30
        for m in range(1, 201):
            for step in (0, 1):
                if step == 0:
                    d = m * (b - m) * x / ((a + 2*m - 1) * (a + 2*m))
                else:
                    d = -(a + m) * (a + b + m) * x / ((a + 2*m) * (a + 2*m + 1))
                D = 1.0 / max(abs(1.0 + d * D), TINY) * (1 if (1.0 + d * D) >= 0 else -1)
                C = max(abs(1.0 + d / C), TINY) * (1 if (1.0 + d / C) >= 0 else -1)
                delta = C * D
                f *= delta
                if abs(delta - 1.0) < tol:
                    break
        return front * (f - 1.0)

    def _beta_ppf(p, a, b):
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if _betainc(a, b, mid) < p:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    return _beta_ppf(alpha / 2, k, n - k + 1)


def score_skill(path: Path) -> dict[str, Any]:
    """Score a single SKILL.md file against quality criteria."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return {"path": str(path), "error": str(e), "total": 0, "breakdown": {}}

    scores: dict[str, int] = {}
    notes: list[str] = []

    # --- 1. Triggers (20 pts) ---
    has_triggers = bool(re.search(r"triggers\s*:", text, re.IGNORECASE))
    trigger_count = len(re.findall(r"^\s*-\s+.+", text, re.MULTILINE))
    if has_triggers and trigger_count >= 3:
        scores["triggers"] = 20
    elif has_triggers:
        scores["triggers"] = 10
        notes.append(f"triggers: only {trigger_count} entries — add more (aim for 4+)")
    else:
        scores["triggers"] = 0
        notes.append("missing triggers: section — skill won't be auto-loaded correctly")

    # --- 2. Pitfalls (20 pts) ---
    has_pitfalls = bool(re.search(r"pitfall|gotcha|warning|avoid|caution", text, re.IGNORECASE))
    pitfall_section = bool(re.search(r"#+\s*(pitfall|gotcha|warning|avoid|caution)", text, re.IGNORECASE))
    if pitfall_section:
        scores["pitfalls"] = 20
    elif has_pitfalls:
        scores["pitfalls"] = 10
        notes.append("pitfall content exists but not in a dedicated section — extract to ## Pitfalls")
    else:
        scores["pitfalls"] = 0
        notes.append("no pitfalls section — add hard-won lessons here")

    # --- 3. Verification steps (15 pts) ---
    has_verify = bool(re.search(
        r"verif|check\s+with|confirm|assert|test\s+with|prove|run.*--dry|expected\s+output",
        text, re.IGNORECASE
    ))
    if has_verify:
        scores["verification"] = 15
    else:
        scores["verification"] = 0
        notes.append("no verification steps — add 'how to confirm it worked'")

    # --- 4. Runnable commands (15 pts) ---
    # Look for backtick code blocks with actual commands
    code_blocks = re.findall(r"```[^\n]*\n(.*?)```", text, re.DOTALL)
    inline_cmds = re.findall(r"`[^`]{4,60}`", text)
    has_commands = bool(code_blocks or len(inline_cmds) >= 3)
    # Check for vague placeholder commands (no real commands)
    vague = bool(re.search(r"run\s+X|run\s+the\s+command|execute\s+this", text, re.IGNORECASE))
    if has_commands and not vague:
        scores["commands"] = 15
    elif has_commands:
        scores["commands"] = 7
        notes.append("has commands but some appear vague — replace placeholders with real commands")
    else:
        scores["commands"] = 0
        notes.append("no concrete commands — add exact runnable shell/python commands")

    # --- 5. Description length (10 pts) ---
    desc_match = re.search(r"description\s*:\s*[\"']?(.+?)[\"']?\s*(?:\n|$)", text, re.IGNORECASE)
    desc_words = len(desc_match.group(1).split()) if desc_match else 0
    if MIN_DESC_WORDS <= desc_words <= MAX_DESC_WORDS:
        scores["description"] = 10
    elif desc_words < MIN_DESC_WORDS:
        scores["description"] = 3
        notes.append(f"description too short ({desc_words} words) — expand to {MIN_DESC_WORDS}+ words")
    else:
        scores["description"] = 5
        notes.append(f"description very long ({desc_words} words) — aim for ≤{MAX_DESC_WORDS}")

    # --- 6. Version/metadata (10 pts) ---
    has_version = bool(re.search(r"version\s*:", text, re.IGNORECASE))
    has_frontmatter = text.strip().startswith("---")
    if has_version and has_frontmatter:
        scores["metadata"] = 10
    elif has_frontmatter:
        scores["metadata"] = 5
        notes.append("has frontmatter but no version — add 'version: 1.0.0'")
    else:
        scores["metadata"] = 0
        notes.append("no YAML frontmatter — skill may not parse correctly")

    # --- 7. Related skills (10 pts) ---
    has_related = bool(re.search(r"related.skills\s*:|related_skills\s*:", text, re.IGNORECASE))
    if has_related:
        scores["related_skills"] = 10
    else:
        scores["related_skills"] = 0
        notes.append("no related_skills — link to complementary skills for better routing")

    total = sum(scores.values())
    priority = total < PRIORITY_THRESHOLD
    n_dims = len(scores)
    n_pass_dims = sum(1 for s in scores.values() if s > 0)  # any points = partial pass
    frac = total / 100.0  # normalise to [0,1]
    k_equiv = round(frac * n_dims)  # equivalent passes
    cp_lb = clopper_pearson_lower(k_equiv, n_dims)

    return {
        "path": str(path),
        "name": path.parent.name,
        "total": total,
        "breakdown": scores,
        "notes": notes,
        "priority_fix": priority,
        "cp_lower_95": round(cp_lb, 3),
    }


def find_all_skills() -> list[Path]:
    """Recursively find all SKILL.md files under SKILLS_ROOT."""
    return sorted(SKILLS_ROOT.rglob("SKILL.md"))


def print_report(result: dict[str, Any], verbose: bool = True) -> None:
    """Print a single skill's score report."""
    name = result.get("name", Path(result["path"]).parent.name)
    total = result["total"]
    flag = " [PRIORITY FIX]" if result.get("priority_fix") else ""
    print(f"\n{'='*60}")
    print(f"Skill: {name}  Score: {total}/100{flag}")
    print(f"Path:  {result['path']}")
    if "error" in result:
        print(f"ERROR: {result['error']}")
        return
    if verbose:
        print("\nBreakdown:")
        for criterion, pts in result["breakdown"].items():
            max_pts = {"triggers": 20, "pitfalls": 20, "verification": 15,
                       "commands": 15, "description": 10, "metadata": 10,
                       "related_skills": 10}[criterion]
            bar = "█" * (pts // 5) + "░" * ((max_pts - pts) // 5)
            print(f"  {criterion:15s} {bar} {pts}/{max_pts}")
        if result.get("notes"):
            print("\nImprovement suggestions:")
            for note in result["notes"]:
                print(f"  • {note}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score Hermes SKILL.md files against quality criteria (SkillOpt-inspired)"
    )
    parser.add_argument("path", nargs="?", help="Path to a SKILL.md (or omit for --all)")
    parser.add_argument("--all", action="store_true", help="Score all skills")
    parser.add_argument("--top", type=int, default=0,
                        help="Show N lowest-scoring skills (most in need of improvement)")
    parser.add_argument("--threshold", type=int, default=PRIORITY_THRESHOLD,
                        help=f"Priority-fix threshold (default: {PRIORITY_THRESHOLD})")
    parser.add_argument("--quiet", action="store_true",
                        help="Only show total score per skill, no breakdown")
    args = parser.parse_args()

    if args.path:
        p = Path(args.path)
        if not p.exists():
            print(f"ERROR: {p} does not exist", file=sys.stderr)
            sys.exit(1)
        result = score_skill(p)
        print_report(result, verbose=not args.quiet)
        return

    if args.all or args.top:
        skills = find_all_skills()
        if not skills:
            print(f"No SKILL.md files found under {SKILLS_ROOT}", file=sys.stderr)
            sys.exit(1)
        results = [score_skill(s) for s in skills]
        results.sort(key=lambda r: r["total"])

        if args.top:
            results = results[: args.top]

        print(f"\nSkillOpt Score Report — {len(results)} skills")
        print(f"Priority threshold: {args.threshold}/100\n")
        print(f"{'Name':<40} {'Score':>6}  {'Priority Fix'}")
        print("-" * 65)
        for r in results:
            flag = "YES" if r.get("priority_fix") else ""
            print(f"{r.get('name', '?'):<40} {r['total']:>6}  {flag}")

        priority_count = sum(1 for r in results if r.get("priority_fix"))
        print(f"\n{priority_count}/{len(results)} skills below threshold ({args.threshold}/100)")

        if not args.quiet:
            print("\nDetailed reports for priority-fix skills:")
            for r in results:
                if r.get("priority_fix"):
                    print_report(r, verbose=True)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
