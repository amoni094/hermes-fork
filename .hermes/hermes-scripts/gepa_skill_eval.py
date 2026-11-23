#!/usr/bin/env python3
"""
GEPA Skill Evaluation Harness
==============================
Standalone evaluation harness for Hermes skill optimization via GEPA/omni.

Usage:
  python3 gepa_skill_eval.py --skill ~/.hermes/skills/my-skill/SKILL.md
  python3 gepa_skill_eval.py --skill ... --optimize          # run GEPA optimization
  python3 gepa_skill_eval.py --skill ... --optimize --omni   # use omni meta-optimizer
  python3 gepa_skill_eval.py --skill ... --baseline          # just score, no optimize

This implements the EDD + GEPA bridge described in evaluation-driven-development
and gepa-omni-optimization skills.

Architecture:
  1. Load test cases from gepa_eval_cases.json (or specify via --cases)
  2. For each test case: run a simulated task check (fast heuristics + keyword checks)
  3. Score the skill's trigger clarity, coverage, pitfall completeness, step quality
  4. Return (score, diagnostic_dict) for GEPA's ASI feedback loop
  5. Optionally: run GEPA optimization and write best candidate back to a temp file

Score dimensions (each 0-1.0, averaged):
  - trigger_coverage: do triggers cover the stated test query types?
  - pitfall_completeness: are common failure modes documented?
  - step_actionability: are steps concrete (commands/code) vs vague instructions?
  - example_quality: do code examples include imports and run independently?
  - metadata_integrity: frontmatter has required fields, no placeholders

Requires: pip install gepa (for --optimize mode; baseline mode has no deps)
"""

import sys
import re
import json
import argparse
from pathlib import Path

# ── Default test cases (intrinsic skill quality checks) ─────────────────────

DEFAULT_EVAL_CASES = [
    {
        "id": "trigger_specificity",
        "description": "Triggers should be specific enough to distinguish from adjacent skills",
        "check": "trigger_specificity",
    },
    {
        "id": "pitfall_count",
        "description": "At least 3 documented pitfalls",
        "check": "pitfall_count",
        "min_count": 3,
    },
    {
        "id": "has_code_examples",
        "description": "At least one code example with imports",
        "check": "code_example_imports",
    },
    {
        "id": "step_concreteness",
        "description": "Steps include commands or code, not just vague verbs",
        "check": "step_concreteness",
    },
    {
        "id": "frontmatter_complete",
        "description": "Required frontmatter fields present: name, description, triggers, version",
        "check": "frontmatter_fields",
        "required": ["name", "description", "triggers", "version"],
    },
    {
        "id": "no_placeholders",
        "description": "No bare placeholders like YYYY-MM-DD or <YOUR_VALUE>",
        "check": "no_placeholders",
    },
    {
        "id": "trigger_count",
        "description": "At least 4 trigger entries",
        "check": "trigger_count",
        "min_count": 4,
    },
]


# ── Score functions ──────────────────────────────────────────────────────────

def extract_frontmatter(skill_md: str) -> dict:
    """Extract YAML frontmatter as raw text + parse key lists."""
    parts = skill_md.split("---")
    if len(parts) < 3:
        return {}
    fm_text = parts[1]
    result = {}
    # Simple extraction — not full YAML parse to avoid deps
    for line in fm_text.splitlines():
        m = re.match(r'^(\w[\w-]*):\s*(.*)', line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    # Extract trigger list
    triggers = []
    in_triggers = False
    for line in fm_text.splitlines():
        if re.match(r'^triggers:', line):
            in_triggers = True
            continue
        if in_triggers:
            m = re.match(r'^\s+[-]\s+"?(.+?)"?\s*$', line)
            if m:
                triggers.append(m.group(1))
            elif line.strip() and not line.startswith(' '):
                in_triggers = False
    result['_triggers'] = triggers
    return result


def score_trigger_specificity(skill_md: str) -> tuple[float, str]:
    fm = extract_frontmatter(skill_md)
    triggers = fm.get('_triggers', [])
    if not triggers:
        return 0.0, "No triggers found in frontmatter"
    # Penalise overly generic triggers
    generic = ["use this", "when you need", "how to", "help with"]
    vague_count = sum(1 for t in triggers if any(g in t.lower() for g in generic))
    score = 1.0 - (vague_count / max(len(triggers), 1)) * 0.5
    return score, f"{len(triggers)} triggers, {vague_count} vague"


def score_pitfall_count(skill_md: str, min_count: int = 3) -> tuple[float, str]:
    body = skill_md.split("---", 2)[-1] if skill_md.count("---") >= 2 else skill_md
    # Count pitfall bullet points under a Pitfalls section
    in_pitfalls = False
    count = 0
    for line in body.splitlines():
        if re.match(r'^#+\s+[Pp]itfall', line):
            in_pitfalls = True
            continue
        if in_pitfalls and re.match(r'^#+', line) and 'pitfall' not in line.lower():
            in_pitfalls = False
        if in_pitfalls and re.match(r'^-\s+\*\*', line):
            count += 1
    score = min(1.0, count / min_count)
    return score, f"{count}/{min_count} pitfalls documented"


def score_code_example_imports(skill_md: str) -> tuple[float, str]:
    code_blocks = re.findall(r'```python(.*?)```', skill_md, re.DOTALL)
    if not code_blocks:
        return 0.0, "No Python code blocks found"
    with_imports = sum(1 for b in code_blocks if 'import ' in b)
    score = min(1.0, with_imports / max(len(code_blocks), 1))
    return score, f"{with_imports}/{len(code_blocks)} code blocks have imports"


def score_step_concreteness(skill_md: str) -> tuple[float, str]:
    body = skill_md.split("---", 2)[-1] if skill_md.count("---") >= 2 else skill_md
    numbered_steps = re.findall(r'^\d+\.\s+(.+)', body, re.MULTILINE)
    if not numbered_steps:
        return 0.5, "No numbered steps found (may be fine for reference skills)"
    # Steps with commands/code markers
    concrete = sum(1 for s in numbered_steps if
                   any(c in s for c in ['`', 'run', 'call', 'execute', 'install', 'pip', 'hermes', '>>>']))
    score = concrete / max(len(numbered_steps), 1)
    return score, f"{concrete}/{len(numbered_steps)} steps are concrete"


def score_frontmatter_fields(skill_md: str, required: list) -> tuple[float, str]:
    fm = extract_frontmatter(skill_md)
    missing = [f for f in required if f not in fm]
    score = 1.0 - len(missing) / max(len(required), 1)
    return score, f"Missing fields: {missing}" if missing else "All required fields present"


def score_no_placeholders(skill_md: str) -> tuple[float, str]:
    placeholders = re.findall(r'YYYY-MM-DD|<YOUR_VALUE>|<REPLACE_ME>|\[TOPIC\]|\[DATE\]', skill_md)
    if not placeholders:
        return 1.0, "No bare placeholders"
    return max(0.0, 1.0 - len(placeholders) * 0.2), f"Found placeholders: {placeholders[:5]}"


def score_trigger_count(skill_md: str, min_count: int = 4) -> tuple[float, str]:
    fm = extract_frontmatter(skill_md)
    triggers = fm.get('_triggers', [])
    score = min(1.0, len(triggers) / min_count)
    return score, f"{len(triggers)}/{min_count} triggers"


CHECK_DISPATCH = {
    "trigger_specificity": lambda md, tc: score_trigger_specificity(md),
    "pitfall_count": lambda md, tc: score_pitfall_count(md, tc.get("min_count", 3)),
    "code_example_imports": lambda md, tc: score_code_example_imports(md),
    "step_concreteness": lambda md, tc: score_step_concreteness(md),
    "frontmatter_fields": lambda md, tc: score_frontmatter_fields(md, tc.get("required", [])),
    "no_placeholders": lambda md, tc: score_no_placeholders(md),
    "trigger_count": lambda md, tc: score_trigger_count(md, tc.get("min_count", 4)),
}


# ── Main evaluator ───────────────────────────────────────────────────────────

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
        # e.g. n=7, k=7, alpha=0.05 → ~0.59; CP lower is never 1.0 without infinite data
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


def evaluate_skill(skill_md: str, cases: list | None = None) -> tuple[float, dict]:
    """
    Evaluate a skill SKILL.md string.
    Returns (score 0-1.0, diagnostic dict).
    """
    if cases is None:
        cases = DEFAULT_EVAL_CASES

    results = {}
    total = 0.0
    failures = []

    for tc in cases:
        check_fn = CHECK_DISPATCH.get(tc["check"])
        if check_fn is None:
            continue
        try:
            score, detail = check_fn(skill_md, tc)
        except Exception as e:
            score, detail = 0.0, f"ERROR: {e}"
        results[tc["id"]] = {"score": round(score, 3), "detail": detail}
        total += score
        if score < 0.8:
            failures.append(f"{tc['id']} ({score:.2f}): {detail}")

    avg = round(total / max(len(cases), 1), 3)
    n_checks = len(cases)
    n_pass = sum(1 for r in results.values() if r["score"] >= 0.8)
    cp_lower = clopper_pearson_lower(n_pass, n_checks)
    return avg, {
        "avg_score": avg,
        "cp_lower_95": round(cp_lower, 3),
        "n_pass": n_pass,
        "n_checks": n_checks,
        "per_check": results,
        "failures": failures,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GEPA Skill Evaluation Harness")
    parser.add_argument("--skill", required=True, help="Path to SKILL.md")
    parser.add_argument("--cases", help="Path to JSON test cases file")
    parser.add_argument("--optimize", action="store_true", help="Run GEPA optimization")
    parser.add_argument("--omni", action="store_true", help="Use omni meta-optimizer (requires --optimize)")
    parser.add_argument("--budget", type=float, default=5.0, help="Token cost budget in USD for optimization")
    parser.add_argument("--output", help="Write optimized skill to this path")
    args = parser.parse_args()

    skill_path = Path(args.skill).expanduser()
    if not skill_path.exists():
        print(f"ERROR: skill file not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    skill_md = skill_path.read_text()
    cases = DEFAULT_EVAL_CASES
    if args.cases:
        cases = json.loads(Path(args.cases).expanduser().read_text())

    # Baseline evaluation
    score, info = evaluate_skill(skill_md, cases)
    print(f"\nBaseline score: {score:.3f}")
    print(f"Per-check results:")
    for check_id, res in info["per_check"].items():
        marker = "OK" if res["score"] >= 0.8 else "!!"
        print(f"  [{marker}] {check_id}: {res['score']:.2f} — {res['detail']}")
    if info["failures"]:
        print(f"\nFailures ({len(info['failures'])}):")
        for f in info["failures"]:
            print(f"  - {f}")

    if not args.optimize:
        sys.exit(0)

    # GEPA optimization
    try:
        import gepa.optimize_anything as oa
    except ImportError:
        print("\nERROR: gepa not installed. Run: pip install gepa", file=sys.stderr)
        sys.exit(1)

    print(f"\nRunning GEPA optimization (budget=${args.budget:.1f})...")
    cases_copy = cases  # capture for closure

    def evaluator(candidate: str) -> tuple[float, dict]:
        s, info_d = evaluate_skill(candidate, cases_copy)
        oa.log(f"Score: {s:.3f} | Failures: {info_d['failures'][:3]}")
        return s, info_d

    if args.omni:
        from gepa.optimize_anything import optimize_anything, OptimizeAnythingConfig
        phase_budget = args.budget / 3.0

        print("  Phase 1: parallel exploration (GEPA + AutoResearch + Meta-Harness)...")
        r_gepa = optimize_anything(skill_md, evaluator=evaluator,
                                   objective="Improve this Hermes skill: clearer triggers, concrete steps, more pitfalls, better examples.",
                                   config=OptimizeAnythingConfig(engine="gepa", max_token_cost=phase_budget))
        r_auto = optimize_anything(skill_md, evaluator=evaluator,
                                   objective="Improve this Hermes skill: clearer triggers, concrete steps, more pitfalls, better examples.",
                                   config=OptimizeAnythingConfig(engine="autoresearch", max_token_cost=phase_budget))
        r_meta = optimize_anything(skill_md, evaluator=evaluator,
                                   objective="Improve this Hermes skill: clearer triggers, concrete steps, more pitfalls, better examples.",
                                   config=OptimizeAnythingConfig(engine="meta_harness", max_token_cost=phase_budget))

        best_r = max([r_gepa, r_auto, r_meta], key=lambda r: r.best_score)
        print(f"  Phase 1 best: {best_r.best_score:.3f} (via {best_r.engine})")
        print(f"  Phase 2: continuing with fresh GEPA engine (budget=${phase_budget:.1f})...")
        # Phase 2 budget: give the plateau-breaker the same budget as each Phase 1 engine.
        # Total spend: 4 * (budget/3) = 4/3 * budget. This matches the omni paper's pattern
        # where phase 2 gets the remaining allocation after phase 1 parallel exploration.
        # Do NOT use (args.budget - 3 * phase_budget) which equals 0.
        result = optimize_anything(best_r.best_candidate, evaluator=evaluator,
                                   config=OptimizeAnythingConfig(engine="gepa", max_token_cost=phase_budget))
    else:
        from gepa.optimize_anything import optimize_anything, OptimizeAnythingConfig
        result = optimize_anything(
            seed_candidate=skill_md,
            evaluator=evaluator,
            objective="Improve this Hermes skill: clearer triggers, concrete steps, more pitfalls, better examples.",
            config=OptimizeAnythingConfig(max_token_cost=args.budget),
        )

    final_score, final_info = evaluate_skill(result.best_candidate, cases)
    print(f"\nOptimized score: {final_score:.3f} (was {score:.3f}, delta +{final_score - score:.3f})")

    out_path = args.output or str(skill_path.parent / "SKILL_optimized.md")
    Path(out_path).write_text(result.best_candidate)
    print(f"Optimized skill written to: {out_path}")
    print("Review and copy to SKILL.md if satisfied.")


if __name__ == "__main__":
    main()
