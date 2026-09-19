#!/usr/bin/env python3
"""
omni_skill_scan.py — Scheduled GEPA Omni continuous improvement driver.

Two modes:
  1. SCAN (default): score all skills, write report + patch queue
  2. OPTIMIZE (--optimize): run GEPA omni on queued skills (requires gepa installed)

Cron invocation:
  python3 ~/.hermes/scripts/omni_skill_scan.py
  python3 ~/.hermes/scripts/omni_skill_scan.py --optimize --budget 3.0

Output:
  ~/.hermes/omni/scan-YYYY-MM-DD.md   — full report
  ~/.hermes/omni/patch-queue.json     — skills below threshold, sorted by score
  ~/.hermes/omni/candidates/          — GEPA-optimized SKILL_candidate.md files (optimize mode)

The patch queue is the human review surface. No SKILL.md is ever auto-patched.
"""

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SKILLS_ROOT = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "skills"
OMNI_DIR = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "omni"
QUEUE_PATH = OMNI_DIR / "patch-queue.json"
THRESHOLD = 0.65   # skills scoring below this are queued for optimization
MAX_OPTIMIZE = 3   # max skills to optimize per cron run (cost control)
SCORE_HISTORY_PATH = OMNI_DIR / "score-history.json"
HISTORY_WINDOW = 5  # number of past scans to track per skill
HIGH_VARIANCE_THRESHOLD = 0.15  # score spread above this = high-variance / fragile skill


def load_score_history() -> dict:
    """Load per-skill score history. Returns {skill_name: [score, ...]} (oldest first)."""
    if SCORE_HISTORY_PATH.exists():
        try:
            return json.loads(SCORE_HISTORY_PATH.read_text())
        except Exception as e:
            import sys as _s
            print(f"[omni_skill_scan] score-history.json corrupt ({e}), resetting", file=_s.stderr)
            return {}
    return {}


def update_score_history(results: list[dict]) -> dict:
    """Append this run's scores to history. Prune to HISTORY_WINDOW."""
    history = load_score_history()
    for r in results:
        name = r["name"]
        history.setdefault(name, [])
        history[name].append(round(r["score"], 3))
        history[name] = history[name][-HISTORY_WINDOW:]
    _sh_tmp = SCORE_HISTORY_PATH.with_suffix(".tmp")
    _sh_tmp.write_text(json.dumps(history, indent=2))
    _sh_tmp.replace(SCORE_HISTORY_PATH)
    return history


def classify_skill_trajectory(history: list[float]) -> str:
    """D2ACCI Promote/FeatureFlag/Reject + EvoTS fragility flag.

    Returns one of: 'Promote', 'FeatureFlag', 'Reject', 'HighVariance', 'Insufficient'
    - Promote:      score consistently improving (last > first by >0.05, monotone trend)
    - FeatureFlag:  flat (spread <0.10) but above threshold
    - Reject:       declining (last < first by >0.05) or consistently below threshold
    - HighVariance: spread > HIGH_VARIANCE_THRESHOLD — fragile by EvoTS/arXiv:2608.18066 criteria
    - Insufficient: fewer than 2 data points
    """
    if len(history) < 2:
        return "Insufficient"
    spread = max(history) - min(history)
    if spread >= HIGH_VARIANCE_THRESHOLD:
        return "HighVariance"
    delta = history[-1] - history[0]
    if delta > 0.05:
        return "Promote"
    if delta < -0.05:
        return "Reject"
    return "FeatureFlag"


# ── Quality scoring (mirrors gepa_skill_eval.py) ─────────────────────────

def extract_frontmatter(skill_md: str) -> dict:
    parts = skill_md.split("---")
    if len(parts) < 3:
        return {"_triggers": []}
    fm_text = parts[1]
    result = {}
    for line in fm_text.splitlines():
        m = re.match(r'^(\w[\w-]*):\s*(.*)', line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    triggers = []
    in_triggers = False
    for line in fm_text.splitlines():
        if re.match(r'^triggers:', line):
            in_triggers = True
            continue
        if in_triggers:
            m = re.match(r'^(\s*)- (.+)', line)  # match both indented and unindented YAML bullets
            if m:
                triggers.append(m.group(2).strip().strip('"'))
            elif line.strip() and not line.startswith(' '):
                break
    result['_triggers'] = triggers
    return result


def parse_related_skills(skill_md: str) -> list[str]:
    """Parse related_skills from SKILL.md frontmatter (inline list or YAML bullets)."""
    parts = skill_md.split("---")
    if len(parts) < 3:
        return []
    fm_text = parts[1]
    names: list[str] = []
    for m in re.finditer(r"related_skills:\s*\[([^\]]*)\]", fm_text):
        for item in m.group(1).split(","):
            item = item.strip().strip('"').strip("'")
            if item:
                names.append(item)
    in_list = False
    for line in fm_text.splitlines():
        if re.match(r"^\s*related_skills:\s*$", line):
            in_list = True
            continue
        if in_list:
            m = re.match(r"^\s*-\s+(.+)", line)
            if m:
                item = m.group(1).strip().strip('"').strip("'")
                if item:
                    names.append(item)
                continue
            if re.match(r"^\s*\w[\w-]*:", line):
                in_list = False
            elif line.strip() and not line[:1].isspace():
                in_list = False
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def score_skill(skill_md: str) -> tuple[float, dict]:
    fm = extract_frontmatter(skill_md)
    body = skill_md.split("---", 2)[-1] if skill_md.count("---") >= 2 else skill_md

    checks = {}

    # 1. Trigger count (min 4)
    n_triggers = len(fm.get('_triggers', []))
    checks['trigger_count'] = min(1.0, n_triggers / 4)

    # 2. Trigger specificity (penalise vague)
    generic = ["use this", "when you need", "how to", "help with"]
    triggers = fm.get('_triggers', [])
    vague = sum(1 for t in triggers if any(g in t.lower() for g in generic))
    checks['trigger_specificity'] = 1.0 - (vague / max(len(triggers), 1)) * 0.5 if triggers else 0.0

    # 3. Pitfall completeness (min 3)
    in_pf = False
    pf_count = 0
    for line in body.splitlines():
        if re.match(r'^#+\s+[Pp]itfall', line):
            in_pf = True
            continue
        if in_pf and re.match(r'^#+', line) and 'pitfall' not in line.lower():
            in_pf = False
        if in_pf and re.match(r'^-\s+', line):
            pf_count += 1
    checks['pitfall_count'] = min(1.0, pf_count / 3)

    # 4. Step concreteness
    numbered = re.findall(r'^\d+\.\s+(.+)', body, re.MULTILINE)
    if numbered:
        concrete = sum(1 for s in numbered if any(
            c in s for c in ['`', 'run', 'call', 'execute', 'install', 'pip', 'hermes', '>>>']
        ))
        checks['step_concreteness'] = concrete / len(numbered)
    else:
        checks['step_concreteness'] = 0.5  # neutral for reference skills

    # 5. Has version field
    checks['has_version'] = 1.0 if 'version' in fm else 0.0

    # 6. No bare placeholders
    placeholders = re.findall(r'YYYY-MM-DD|<YOUR_VALUE>|<REPLACE_ME>|\[TOPIC\]|\[DATE\]', skill_md)
    checks['no_placeholders'] = max(0.0, 1.0 - len(placeholders) * 0.25)

    # 7. Has description field
    checks['has_description'] = 1.0 if fm.get('description', '').strip() else 0.0

    avg = sum(checks.values()) / len(checks)
    return round(avg, 3), checks


def scan_all_skills() -> list[dict]:
    results = []
    # Skill categories that are command/plugin handlers, not workflow guides.
    # These have intentionally minimal structure — scoring them against the same
    # quality dimensions as full workflow skills produces false negatives.
    SKIP_CATEGORIES = {"ouroboros"}

    for skill_md_path in sorted(SKILLS_ROOT.glob("**/SKILL.md")):
        try:
            content = skill_md_path.read_text()
            name = skill_md_path.parent.name
            category = skill_md_path.parent.parent.name if skill_md_path.parent.parent != SKILLS_ROOT else "root"
            if category in SKIP_CATEGORIES:
                continue
            score, checks = score_skill(content)
            results.append({
                "name": name,
                "category": category,
                "path": str(skill_md_path),
                "score": score,
                "checks": checks,
                "related_skills": parse_related_skills(content),
            })
        except Exception as e:
            results.append({
                "name": skill_md_path.parent.name,
                "category": "error",
                "path": str(skill_md_path),
                "score": 0.0,
                "checks": {},
                "error": str(e),
                "related_skills": [],
            })
    return sorted(results, key=lambda r: r['score'])


# ── Report writer ─────────────────────────────────────────────────────────

def write_report(results: list[dict], report_path: Path):
    today = datetime.now().strftime("%Y-%m-%d")
    total = len(results)
    below = [r for r in results if r['score'] < THRESHOLD]
    above = [r for r in results if r['score'] >= THRESHOLD]
    avg = round(sum(r['score'] for r in results) / max(total, 1), 3)

    lines = [
        f"# GEPA Omni Skill Quality Scan — {today}",
        f"",
        f"**Total skills:** {total} | **Avg score:** {avg:.3f} | **Below threshold ({THRESHOLD}):** {len(below)}",
        f"",
        f"## Skills below threshold (optimization candidates)",
        f"",
        f"| Rank | Name | Category | Score | Weak checks |",
        f"|------|------|----------|-------|-------------|",
    ]
    for i, r in enumerate(below[:20], 1):
        weak = [k for k, v in r.get('checks', {}).items() if v < 0.6]
        lines.append(f"| {i} | {r['name']} | {r['category']} | {r['score']:.3f} | {', '.join(weak[:3])} |")

    lines += [
        f"",
        f"## All skills (sorted by score)",
        f"",
        f"| Name | Category | Score |",
        f"|------|----------|-------|",
    ]
    for r in results:
        marker = " ⚠" if r['score'] < THRESHOLD else ""
        lines.append(f"| {r['name']}{marker} | {r['category']} | {r['score']:.3f} |")

    lines += [
        f"",
        f"## Check dimension averages",
        f"",
    ]
    all_checks = {}
    for r in results:
        for k, v in r.get('checks', {}).items():
            all_checks.setdefault(k, []).append(v)
    for k, vals in sorted(all_checks.items()):
        avg_dim = sum(vals) / len(vals)
        lines.append(f"- **{k}**: {avg_dim:.3f} avg (n={len(vals)})")

    lines += [
        f"",
        f"---",
        f"",
        f"Generated by `~/.hermes/scripts/omni_skill_scan.py`.",
        f"Review `~/.hermes/omni/patch-queue.json` for optimization candidates.",
        f"To run GEPA optimization on queued skills (requires `pip install gepa`):",
        f"  python3 ~/.hermes/scripts/omni_skill_scan.py --optimize --budget 3.0",
    ]

    _rp_tmp = report_path.with_suffix(".tmp")
    _rp_tmp.write_text("\n".join(lines))
    _rp_tmp.replace(report_path)
    return len(below)


def analyze_skill_connectivity(results: list[dict]) -> dict:
    """Stdlib Fiedler-style proxy: degrees + weakly-connected components.

    Full algebraic connectivity (Fiedler eigenvalue) needs numpy. Here:
      in-degree  = how many skills list this skill in related_skills
      out-degree = how many related_skills this skill lists
      isolated   = in_degree == 0 AND out_degree == 0
    """
    names = [r["name"] for r in results]
    name_set = set(names)
    related = {r["name"]: list(r.get("related_skills") or []) for r in results}

    in_degree = {n: 0 for n in names}
    out_degree = {n: len(related.get(n, [])) for n in names}
    undirected: dict[str, set[str]] = {n: set() for n in names}

    for src, targets in related.items():
        for tgt in targets:
            if tgt in in_degree:
                in_degree[tgt] += 1
            if tgt in name_set and src in name_set:
                undirected[src].add(tgt)
                undirected[tgt].add(src)

    isolated = sorted(
        n for n in names if in_degree[n] == 0 and out_degree[n] == 0
    )

    seen: set[str] = set()
    components: list[list[str]] = []
    for n in names:
        if n in seen:
            continue
        stack = [n]
        seen.add(n)
        comp: list[str] = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in undirected.get(u, ()):
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        components.append(sorted(comp))

    linked_score = {n: in_degree[n] + out_degree[n] for n in names}
    hubs = sorted(names, key=lambda n: (-linked_score[n], n))[:5]
    hubs_detail = [
        {
            "name": n,
            "in_degree": in_degree[n],
            "out_degree": out_degree[n],
            "degree": linked_score[n],
        }
        for n in hubs
        if linked_score[n] > 0
    ]

    return {
        "isolated": isolated,
        "n_isolated": len(isolated),
        "n_clusters": len(components),
        "n_nontrivial_clusters": sum(1 for c in components if len(c) > 1),
        "hubs": hubs_detail,
        "in_degree": in_degree,
        "out_degree": out_degree,
    }


def format_connectivity_section(conn: dict) -> list[str]:
    isolated = conn["isolated"]
    hubs = conn["hubs"]
    iso_preview = isolated[:40]
    iso_note = ""
    if len(isolated) > 40:
        iso_note = f" (showing 40 of {len(isolated)})"
    lines = [
        "",
        "## CONNECTIVITY (Fiedler proxy — stdlib)",
        "",
        "Algebraic connectivity approximated without numpy: undirected weakly-connected",
        "components of the `related_skills` graph, plus in/out degree.",
        "",
        f"- **Skills:** {len(conn['in_degree'])}",
        f"- **Weakly-connected clusters:** {conn['n_clusters']}",
        f"- **Non-trivial clusters (size>1):** {conn['n_nontrivial_clusters']}",
        f"- **Isolated nodes (in=0 and out=0):** {conn['n_isolated']}",
        "",
        "### Top-5 most-linked skills (hubs)",
        "",
    ]
    if hubs:
        lines.append("| Rank | Name | In-degree | Out-degree | Degree |")
        lines.append("|------|------|-----------|------------|--------|")
        for i, h in enumerate(hubs, 1):
            lines.append(
                f"| {i} | {h['name']} | {h['in_degree']} | {h['out_degree']} | {h['degree']} |"
            )
    else:
        lines.append("_No related_skills links found._")
    lines += [
        "",
        f"### Isolated skills{iso_note}",
        "",
    ]
    if iso_preview:
        for n in iso_preview:
            lines.append(f"- {n}")
    else:
        lines.append("_None._")
    lines.append("")
    return lines


def append_connectivity_report(report_path: Path, conn: dict) -> None:
    """Append CONNECTIVITY section to the existing markdown scan report."""
    section = "\n".join(format_connectivity_section(conn))
    with report_path.open("a", encoding="utf-8") as fh:
        fh.write(section)


def print_connectivity(conn: dict) -> None:
    print("\n--- CONNECTIVITY ---")
    print(f"  Weakly-connected clusters: {conn['n_clusters']}")
    print(f"  Non-trivial clusters:      {conn['n_nontrivial_clusters']}")
    print(f"  Isolated skills:           {conn['n_isolated']}")
    if conn["hubs"]:
        print("  Hubs (top-5 most-linked):")
        for h in conn["hubs"]:
            print(
                f"    {h['degree']:3d}  {h['name']}  (in={h['in_degree']} out={h['out_degree']})"
            )
    if conn["isolated"]:
        preview = conn["isolated"][:15]
        extra = f" (+{len(conn['isolated']) - 15} more)" if len(conn["isolated"]) > 15 else ""
        print(f"  Isolated: {', '.join(preview)}{extra}")


def write_queue(results: list[dict], history: dict | None = None):
    history = history or {}
    below = [
        {
            "name": r['name'],
            "category": r['category'],
            "path": r['path'],
            "score": r['score'],
            "weak_checks": [k for k, v in r.get('checks', {}).items() if v < 0.6],
            # D2ACCI trajectory classification + EvoTS variance flag (Aug 2026)
            "trajectory": classify_skill_trajectory(history.get(r['name'], [])),
            "score_history": history.get(r['name'], []),
        }
        for r in results if r['score'] < THRESHOLD
    ]
    # Also flag high-variance skills even if above threshold
    high_variance = [
        {
            "name": r['name'],
            "category": r['category'],
            "path": r['path'],
            "score": r['score'],
            "weak_checks": [],
            "trajectory": "HighVariance",
            "score_history": history.get(r['name'], []),
        }
        for r in results
        if r['score'] >= THRESHOLD
        and classify_skill_trajectory(history.get(r['name'], [])) == "HighVariance"
    ]
    queue = {"candidates": below, "high_variance": high_variance}
    _q_tmp = QUEUE_PATH.with_suffix(".tmp")
    _q_tmp.write_text(json.dumps(queue, indent=2))
    _q_tmp.replace(QUEUE_PATH)
    return below


# ── GEPA optimize pass ────────────────────────────────────────────────────

def optimize_queued(budget_per_skill: float, max_skills: int):
    if not QUEUE_PATH.exists():
        print("No patch queue found — run scan first.")
        return

    queue = json.loads(QUEUE_PATH.read_text())
    if not queue:
        print("Queue is empty — all skills meet threshold.")
        return

    try:
        from gepa.optimize_anything import optimize_anything, OptimizeAnythingConfig
    except ImportError:
        print("ERROR: gepa not installed. Run: pip install gepa")
        print(f"Queue has {len(queue)} candidates waiting. Re-run with gepa installed.")
        sys.exit(1)

    candidates_dir = OMNI_DIR / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    # Import the evaluator from gepa_skill_eval
    eval_script = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "scripts" / "gepa_skill_eval.py"
    import importlib.util
    spec = importlib.util.spec_from_file_location("gepa_skill_eval", eval_script)
    if spec is None or spec.loader is None:
        print(f"ERROR: could not load {eval_script}", file=sys.stderr)
        sys.exit(1)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    processed = 0
    for item in queue.get("candidates", queue)[:max_skills]:
        skill_path = Path(item['path'])
        if not skill_path.exists():
            continue
        skill_md = skill_path.read_text()
        baseline, _ = mod.evaluate_skill(skill_md)
        print(f"\nOptimizing: {item['name']} (baseline={baseline:.3f}, weak={item['weak_checks']})")

        # Omni: parallel GEPA + AutoResearch + Meta-Harness, then handoff
        phase_budget = budget_per_skill / 3.0
        objective = (
            f"Improve this Hermes skill named '{item['name']}'. "
            f"Weak dimensions: {item['weak_checks']}. "
            "Make triggers more specific and numerous (target 8+), "
            "add concrete numbered steps with commands, "
            "add pitfall entries for real failure modes, "
            "add at least one code example with imports. "
            "Do not change the skill's fundamental purpose or remove existing correct content."
        )

        evaluator = lambda c: mod.evaluate_skill(c)

        r_gepa = optimize_anything(skill_md, evaluator=evaluator, objective=objective,
                                   config=OptimizeAnythingConfig(engine="gepa", max_token_cost=phase_budget))
        r_auto = optimize_anything(skill_md, evaluator=evaluator, objective=objective,
                                   config=OptimizeAnythingConfig(engine="autoresearch", max_token_cost=phase_budget))
        r_meta = optimize_anything(skill_md, evaluator=evaluator, objective=objective,
                                   config=OptimizeAnythingConfig(engine="meta_harness", max_token_cost=phase_budget))

        best_r = max([r_gepa, r_auto, r_meta], key=lambda r: r.best_score)
        result = optimize_anything(best_r.best_candidate, evaluator=evaluator, objective=objective,
                                   config=OptimizeAnythingConfig(engine="gepa", max_token_cost=phase_budget))

        final_score, _ = mod.evaluate_skill(result.best_candidate)
        delta = final_score - baseline
        print(f"  Result: {final_score:.3f} (delta +{delta:.3f})")

        if delta > 0.02:
            out_path = candidates_dir / f"{item['name']}_candidate.md"
            out_path.write_text(result.best_candidate)
            print(f"  Candidate written: {out_path}")
            print(f"  Review and copy to {item['path']} if satisfied.")
        else:
            print(f"  No meaningful improvement (delta={delta:.3f}) — skipping.")

        processed += 1

    print(f"\nOptimization pass complete. {processed} skills processed.")
    print(f"Candidates in: {candidates_dir}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GEPA Omni continuous skill improvement driver")
    parser.add_argument("--optimize", action="store_true", help="Run GEPA optimization on queued skills")
    parser.add_argument("--budget", type=float, default=2.0, help="USD budget per skill (optimize mode)")
    parser.add_argument("--max", type=int, default=MAX_OPTIMIZE, help="Max skills to optimize per run")
    args = parser.parse_args()

    OMNI_DIR.mkdir(parents=True, exist_ok=True)

    if args.optimize:
        optimize_queued(args.budget, args.max)
        return

    # Scan mode (default)
    print(f"Scanning skills under {SKILLS_ROOT} ...")
    results = scan_all_skills()
    print(f"Found {len(results)} skills.")

    # Update score history and classify trajectories (D2ACCI + EvoTS, Aug 2026)
    history = update_score_history(results)

    today = datetime.now().strftime("%Y-%m-%d")
    report_path = OMNI_DIR / f"scan-{today}.md"
    n_below = write_report(results, report_path)
    conn = analyze_skill_connectivity(results)
    append_connectivity_report(report_path, conn)
    below = write_queue(results, history)

    # Count high-variance skills for summary
    n_hv = sum(
        1 for r in results
        if classify_skill_trajectory(history.get(r['name'], [])) == "HighVariance"
    )

    print(f"\nScan complete.")
    print(f"  Report:      {report_path}")
    print(f"  History:     {SCORE_HISTORY_PATH}")
    print(f"  Queue:       {QUEUE_PATH} ({n_below} candidates, {n_hv} high-variance)")
    print_connectivity(conn)

    if n_below == 0 and n_hv == 0:
        print("  All skills above threshold and low-variance. Nothing to optimize.")
    else:
        print(f"\nTop 5 candidates for optimization:")
        for item in below[:5]:
            traj = item.get("trajectory", "?")
            print(f"  {item['score']:.3f}  [{traj}]  {item['name']}  ({', '.join(item['weak_checks'][:3])})")
        if n_hv > 0:
            print(f"\nHigh-variance skills (fragile — require multi-run validation before promoting):")
            queue_data = json.loads(QUEUE_PATH.read_text())
            for item in queue_data.get("high_variance", [])[:5]:
                hist = item.get("score_history", [])
                print(f"  {item['score']:.3f}  {item['name']}  history={hist}")
        print(f"\nTo optimize (requires gepa installed):")
        print(f"  python3 ~/.hermes/scripts/omni_skill_scan.py --optimize --budget 2.0")

    # SkillRouter overlap check (Sweep 21 — detects routing-confusing skill pairs)
    import subprocess as _sp
    _router = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "scripts" / "skill-router-index.py"
    if _router.exists():
        print(f"\n--- SkillRouter: rebuilding index ---")
        _result = _sp.run(["python3", str(_router), "--build"], capture_output=True)
        if _result.returncode != 0:
            print(f"[omni_skill_scan] skill-router-index --build failed (rc={_result.returncode})", file=sys.stderr)
        _chk = _sp.run(["python3", str(_router), "--check"], capture_output=True, text=True)
        if _chk.stdout.strip():
            print(_chk.stdout.strip())

    # Pending trace2skill candidates
    _pending = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "cache" / "pending-improvements"
    _candidates = list(_pending.glob("skill-candidate-*.md")) if _pending.exists() else []
    if _candidates:
        print(f"\n--- Pending trace2skill candidates ({len(_candidates)}) ---")
        for p in sorted(_candidates)[-5:]:
            print(f"  {p.name}")
        print(f"  Review with: ls -lt {_pending}/")
        print(f"  Promote with: skill_manage(action='create', ...)")

    # Skill yield audit (SYNAPSE tracker — shows metrics for skills with recorded invocations)
    _yield_tracker = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "scripts" / "skill-yield-tracker.py"
    if _yield_tracker.exists():
        _yt = _sp.run(["python3", str(_yield_tracker), "--audit"], capture_output=True, text=True)
        if _yt.stdout.strip():
            print(f"\n--- Skill Yield Tracker (SYNAPSE) ---")
            print(_yt.stdout.strip())

    # Print summary for cron delivery
    avg = round(sum(r['score'] for r in results) / max(len(results), 1), 3)
    print(f"\n=== SUMMARY ===")
    print(f"Skills: {len(results)} | Avg quality: {avg:.3f} | Below threshold: {n_below} | High-variance: {n_hv}")
    if below:
        worst = below[0]
        print(f"Lowest: {worst['name']} ({worst['score']:.3f}) — weak: {', '.join(worst['weak_checks'][:3])}")


if __name__ == "__main__":
    main()
