#!/usr/bin/env python3
"""
skill_prune_audit.py — AutoRefine-inspired skill library health check.

AutoRefine (arXiv:2601.22758, 2026): without periodic prune+merge cycles,
skill repositories bloat 4.5x while utilization drops from 0.71 to 0.08.

This script:
1. Reads ~/.hermes/skills/.usage.json for usage counts and last_activity_at
2. Identifies never-used skills (0 invocations in 60+ days)
3. Computes cosine similarity between skill descriptions to find merge candidates
4. Prints a compact report: PRUNE candidates, MERGE candidates, HEALTHY skills

Four-Tier Pruning Decision Matrix (ToolScope arXiv:2510.20036 + SkillsVote arXiv:2605.18401):
  Archive       — zero invocations 90d AND semantic substitute exists (cos > 0.80)  → Disable
  ACTIVE_DORMANT — zero invocations BUT no semantic substitute                        → Preserve with keyword triggers
  Merge         — two skills with cos_sim > 0.92 on descriptions                    → LLM-audited merge proposal
  Delete        — semantic duplicate AND outcome-weighted usage is negative           → Hard delete

Capability guard (ToolScope): never disable a skill if no substitute exists with cos_sim > 0.80.

Usage:
  python3 skill_prune_audit.py              # 60-day window
  python3 skill_prune_audit.py --days 30    # 30-day window
  python3 skill_prune_audit.py --json       # machine-readable output

Output: plain text report to stdout.
Cron delivery: the output becomes the cron message body.
If nothing needs attention, prints nothing (SILENT for no_agent cron pattern).
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# OT utilities (shared; OT-4)
_OT_UTILS_PATH = Path(__file__).parent / "ot_utils.py"
if _OT_UTILS_PATH.exists():
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("ot_utils", _OT_UTILS_PATH)
    _ot_utils = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_ot_utils)  # type: ignore[union-attr]
else:
    _ot_utils = None  # type: ignore[assignment]

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
SKILLS_DIR = HERMES_HOME / "skills"
USAGE_JSON = SKILLS_DIR / ".usage.json"
ARCHIVE_DIR = SKILLS_DIR / ".archive"

# Similarity thresholds (ToolScope arXiv:2510.20036):
#   >0.92 → strong merge candidate (LLM-audited merge proposal)
#   >0.80 → semantic substitute exists (capability guard — safe to Archive)
#   >0.55 → weaker overlap worth surfacing (original threshold, kept as INFO)
MERGE_SIM_THRESHOLD = 0.55       # surface in report
MERGE_SIM_STRONG = 0.92          # four-tier Merge tier: LLM-audited merge required
SUBSTITUTE_SIM = 0.80            # capability guard: Archive is safe when sub exists at this level
# Days without activity before flagging as stale
DEFAULT_STALE_DAYS = 60
ARCHIVE_DAYS = 90                # four-tier Archive tier: 90d zero-activity


def load_usage() -> dict:
    if not USAGE_JSON.exists():
        return {}
    try:
        return json.loads(USAGE_JSON.read_text())
    except Exception:
        return {}


def find_active_skills() -> list[Path]:
    """Return all SKILL.md files not under .archive/."""
    skills = []
    for skill_md in SKILLS_DIR.rglob("SKILL.md"):
        if ".archive" in skill_md.parts:
            continue
        skills.append(skill_md)
    return skills


def extract_description(skill_md: Path) -> str:
    """Extract description: field from SKILL.md frontmatter."""
    try:
        text = skill_md.read_text(errors="replace")
        m = re.search(r"^description:\s*[\"']?(.*?)[\"']?\s*$", text, re.MULTILINE)
        if m:
            return m.group(1).strip().rstrip("'\"")
        # Also try multi-line description with >
        m2 = re.search(r"^description:\s*>\s*\n((?:  .+\n?)+)", text, re.MULTILINE)
        if m2:
            return " ".join(m2.group(1).split())
    except Exception:
        pass
    return ""


def skill_name_from_path(skill_md: Path) -> str:
    """Derive skill name from directory name."""
    return skill_md.parent.name


def bag_of_words(text: str) -> dict[str, int]:
    words = re.findall(r"[a-z]{3,}", text.lower())
    bow = {}
    for w in words:
        bow[w] = bow.get(w, 0) + 1
    return bow


def cosine_sim(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def parse_last_activity(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        # ISO format with optional Z
        ts_str = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_str)
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser(description="Skill library prune+merge audit")
    p.add_argument("--days", type=int, default=DEFAULT_STALE_DAYS,
                   help=f"Days without activity before flagging stale (default: {DEFAULT_STALE_DAYS})")
    p.add_argument("--json", action="store_true", dest="json_out",
                   help="Machine-readable JSON output")
    p.add_argument("--merge-suggest", action="store_true", dest="merge_suggest",
                   help="OT-4: for pairs with cosine overlap > 0.65, output merge candidates as JSON "
                        "with overlap score and heuristic barycenter description suggestion")
    args = p.parse_args()

    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=args.days)

    usage = load_usage()
    skills = find_active_skills()

    if not skills:
        # No output = SILENT (no_agent cron pattern)
        return

    # Build skill inventory
    inventory = []
    for skill_md in skills:
        name = skill_name_from_path(skill_md)
        info = usage.get(name, {})
        use_count = info.get("use_count", 0)
        view_count = info.get("view_count", 0)
        last_activity = parse_last_activity(info.get("last_activity_at"))
        created_by = info.get("created_by", "unknown")
        state = info.get("state", "active")
        pinned = info.get("pinned", False)

        # Skip archived/pinned
        if state in ("archived",) or pinned:
            continue

        description = extract_description(skill_md)
        bow = bag_of_words(description + " " + name)

        inventory.append({
            "name": name,
            "path": str(skill_md),
            "use_count": use_count,
            "view_count": view_count,
            "last_activity": last_activity,
            "created_by": created_by,
            "description": description[:120],
            "bow": bow,
        })

    # === Pairwise cosine similarity matrix (one pass) ===
    # Used for both merge detection and capability-guard checks.
    pair_sims: dict[tuple[str, str], float] = {}
    for i in range(len(inventory)):
        for j in range(i + 1, len(inventory)):
            a, b = inventory[i], inventory[j]
            sim = cosine_sim(a["bow"], b["bow"])
            if sim >= MERGE_SIM_THRESHOLD:
                pair_sims[(a["name"], b["name"])] = sim

    def has_substitute(name: str, sim_floor: float = SUBSTITUTE_SIM) -> bool:
        """Return True if any other skill has cosine >= sim_floor against `name`."""
        for (a, b), sim in pair_sims.items():
            if (a == name or b == name) and sim >= sim_floor:
                return True
        return False

    # === Four-Tier classification (ToolScope + SkillsVote) ===
    archive_cutoff = now - timedelta(days=ARCHIVE_DAYS)
    prune_candidates = []   # ACTIVE_DORMANT: stale but no substitute → preserve, flag
    archive_candidates = [] # Archive tier: stale + substitute ≥ 0.80 exists
    strong_merge_pairs = [] # Merge tier: cos ≥ 0.92
    merge_pairs = []        # INFO: cos 0.55–0.91

    for s in inventory:
        total_activity = s["use_count"] + s["view_count"]
        last = s["last_activity"]
        stale_60 = (last is None or last < stale_cutoff) and total_activity == 0
        stale_90 = (last is None or last < archive_cutoff) and total_activity == 0

        if stale_90:
            # Capability guard: only Archive if a substitute exists
            if has_substitute(s["name"], SUBSTITUTE_SIM):
                archive_candidates.append(s)
            else:
                # ACTIVE_DORMANT — no substitute, must preserve
                s["_dormant"] = True
                prune_candidates.append(s)
        elif stale_60:
            # Under 90 days but stale — surface as watch candidates
            s["_dormant"] = False
            prune_candidates.append(s)

    for (a_name, b_name), sim in sorted(pair_sims.items(), key=lambda x: -x[1]):
        a_desc = next((s["description"][:80] for s in inventory if s["name"] == a_name), "")
        b_desc = next((s["description"][:80] for s in inventory if s["name"] == b_name), "")
        entry = (sim, a_name, b_name, a_desc, b_desc)
        if sim >= MERGE_SIM_STRONG:
            strong_merge_pairs.append(entry)
        else:
            merge_pairs.append(entry)

    # === Find OVERSIZED skills (inline bloat) ===
    # Skills over 50KB risk hitting the 100KB write limit as they accumulate patches.
    # Extract self-contained knowledge banks / code blocks to references/ files.
    SIZE_WARN_KB = 50
    SIZE_URGENT_KB = 80
    oversized = []
    for skill_md in skills:
        try:
            sz = skill_md.stat().st_size
            if sz >= SIZE_WARN_KB * 1024:
                name = skill_name_from_path(skill_md)
                tier = "URGENT" if sz >= SIZE_URGENT_KB * 1024 else "WARN"
                oversized.append((sz, tier, name, str(skill_md)))
        except OSError:
            pass
    oversized.sort(reverse=True)

    # === OT-4: --merge-suggest ===
    # For pairs with cosine overlap > 0.65, output merge candidates with
    # heuristic W2-barycenter description suggestion.
    if args.merge_suggest:
        OT_MERGE_THRESHOLD = 0.65
        candidates = []
        for (a_name, b_name), sim in sorted(pair_sims.items(), key=lambda x: -x[1]):
            if sim < OT_MERGE_THRESHOLD:
                continue
            a_item = next((s for s in inventory if s["name"] == a_name), None)
            b_item = next((s for s in inventory if s["name"] == b_name), None)
            if not a_item or not b_item:
                continue
            # Build TF dicts for both descriptions
            desc_a = a_item.get("description", "") or ""
            desc_b = b_item.get("description", "") or ""
            # Heuristic barycenter: merge word sets, keep high-frequency shared terms first
            if _ot_utils is not None:
                tf_a = _ot_utils.build_tf(desc_a)
                tf_b = _ot_utils.build_tf(desc_b)
                # Shared tokens (appear in both) => core meaning
                shared = sorted(
                    set(tf_a) & set(tf_b),
                    key=lambda t: tf_a[t] + tf_b[t],
                    reverse=True,
                )[:8]
                # Unique-to-A and unique-to-B sorted by frequency
                only_a = sorted(set(tf_a) - set(tf_b), key=lambda t: tf_a[t], reverse=True)[:4]
                only_b = sorted(set(tf_b) - set(tf_a), key=lambda t: tf_b[t], reverse=True)[:4]
                merged_terms = shared + only_a + only_b
                barycenter_hint = (
                    "midpoint description would reduce routing ambiguity; "
                    f"suggested merged terms: [{', '.join(merged_terms[:12])}]. "
                    f"(heuristic suggestion — not an actual OT barycenter)"
                )
            else:
                barycenter_hint = (
                    "midpoint description would reduce routing ambiguity. "
                    "(heuristic suggestion — ot_utils not available)"
                )
            candidates.append({
                "skill_a": a_name,
                "skill_b": b_name,
                "cosine_overlap": round(sim, 4),
                "desc_a": desc_a[:120],
                "desc_b": desc_b[:120],
                "barycenter_suggestion": barycenter_hint,
                "note": "heuristic suggestion",
            })
        print(json.dumps({"merge_candidates": candidates}, indent=2))
        return

    # === Output ===
    if not prune_candidates and not archive_candidates and not strong_merge_pairs and not merge_pairs and not oversized:
        # SILENT — nothing to report
        return

    if args.json_out:
        out = {
            "generated": now.isoformat(),
            "stale_days": args.days,
            "total_active_skills": len(inventory),
            "archive_candidates": [
                {"name": s["name"], "use_count": s["use_count"],
                 "view_count": s["view_count"],
                 "tier": "Archive",
                 "note": "Substitute exists (cos>=0.80) — safe to disable",
                 "last_activity": s["last_activity"].isoformat() if s["last_activity"] else None}
                for s in archive_candidates
            ],
            "active_dormant": [
                {"name": s["name"], "use_count": s["use_count"],
                 "view_count": s["view_count"],
                 "tier": "ACTIVE_DORMANT",
                 "note": "No substitute — MUST preserve with keyword triggers",
                 "last_activity": s["last_activity"].isoformat() if s["last_activity"] else None}
                for s in prune_candidates if s.get("_dormant")
            ],
            "watch_stale": [
                {"name": s["name"], "use_count": s["use_count"],
                 "view_count": s["view_count"],
                 "last_activity": s["last_activity"].isoformat() if s["last_activity"] else None}
                for s in prune_candidates if not s.get("_dormant")
            ],
            "strong_merge_candidates": [
                {"similarity": round(sim, 3), "skill_a": a, "skill_b": b,
                 "tier": "Merge", "note": "cos>=0.92 — LLM-audited merge required"}
                for sim, a, b, _, _ in strong_merge_pairs
            ],
            "merge_candidates": [
                {"similarity": round(sim, 3), "skill_a": a, "skill_b": b}
                for sim, a, b, _, _ in merge_pairs[:10]
            ],
            "oversized_skills": [
                {"name": name, "size_kb": round(sz / 1024, 1), "tier": tier}
                for sz, tier, name, _ in oversized
            ],
        }
        print(json.dumps(out, indent=2))
        return

    # Human-readable report
    lines = [
        f"SKILL LIBRARY AUDIT — {now.strftime('%Y-%m-%d')}",
        f"Active skills: {len(inventory)}  |  Stale threshold: {args.days}d  |  Archive threshold: {ARCHIVE_DAYS}d",
        "",
    ]

    if oversized:
        lines.append(f"OVERSIZED SKILLS ({len(oversized)} — inline bloat risks write failures at 100KB limit):")
        for sz, tier, name, path in oversized:
            label = "[URGENT >80KB]" if tier == "URGENT" else "[WARN >50KB]"
            lines.append(f"  {label} [{name}] {sz // 1024}KB")
        lines.append("  Fix: extract knowledge banks / code blocks to references/ files.")
        lines.append("  See hermes-skill-library-consolidation-audit for extraction rules.")
        lines.append("")

    if strong_merge_pairs:
        lines.append(f"MERGE TIER — cos>=0.92 ({len(strong_merge_pairs)} pairs — LLM-audited merge required):")
        for sim, a, b, da, db in strong_merge_pairs:
            lines.append(f"  {sim:.2f}  [{a}] vs [{b}]")
            lines.append(f"         A: {da}")
            lines.append(f"         B: {db}")
        lines.append("  Action: consolidate content then delete weaker with absorbed_into= set.")
        lines.append("")

    if archive_candidates:
        lines.append(f"ARCHIVE TIER — {ARCHIVE_DAYS}d stale + substitute exists ({len(archive_candidates)} skills — safe to disable):")
        for s in sorted(archive_candidates, key=lambda x: x["name"]):
            last_str = s["last_activity"].strftime("%Y-%m-%d") if s["last_activity"] else "never"
            lines.append(f"  [Archive] [{s['name']}] last={last_str} use={s['use_count']} view={s['view_count']}")
            if s["description"]:
                lines.append(f"    {s['description'][:100]}")
        lines.append("  Action: hermes curator archive <name> (safe — substitute covers capability).")
        lines.append("")

    dormant = [s for s in prune_candidates if s.get("_dormant")]
    watch = [s for s in prune_candidates if not s.get("_dormant")]

    if dormant:
        lines.append(f"ACTIVE_DORMANT — {ARCHIVE_DAYS}d stale, NO substitute ({len(dormant)} skills — CAPABILITY GUARD: do not delete):")
        for s in sorted(dormant, key=lambda x: x["name"]):
            last_str = s["last_activity"].strftime("%Y-%m-%d") if s["last_activity"] else "never"
            lines.append(f"  [DORMANT] [{s['name']}] last={last_str} use={s['use_count']} view={s['view_count']}")
            if s["description"]:
                lines.append(f"    {s['description'][:100]}")
        lines.append("  Action: add keyword triggers to description so future queries can find it.")
        lines.append("")

    if watch:
        lines.append(f"WATCH — stale 60-89d ({len(watch)} skills):")
        for s in sorted(watch, key=lambda x: x["name"]):
            last_str = s["last_activity"].strftime("%Y-%m-%d") if s["last_activity"] else "never"
            lines.append(f"  [watch] [{s['name']}] last={last_str} use={s['use_count']} view={s['view_count']}")
        lines.append("")

    if merge_pairs:
        shown = merge_pairs[:8]
        lines.append(f"MERGE INFO — cos 0.55-0.91 (top {len(shown)} similar pairs):")
        for sim, a, b, da, db in shown:
            lines.append(f"  {sim:.2f}  [{a}] vs [{b}]")
            lines.append(f"         A: {da}")
            lines.append(f"         B: {db}")
        lines.append("")

    # WikiSkill prune (arXiv:2608.27454): sweep entries older than 90d without access
    import subprocess
    wiki_prune = subprocess.run(
        ["python3", "/var/home/rainbow/.hermes/scripts/skill-wiki.py", "prune", "--days", "90"],
        capture_output=True, text=True,
    )
    if wiki_prune.stdout.strip():
        lines.append("WIKI-PRUNE:")
        for wl in wiki_prune.stdout.strip().splitlines():
            lines.append(f"  {wl}")
        lines.append("")

    # skill-state GC: remove completed states older than 24h
    skill_state_gc = subprocess.run(
        ["python3", "/var/home/rainbow/.hermes/scripts/skill-state.py", "gc"],
        capture_output=True, text=True,
    )
    if skill_state_gc.stdout.strip():
        lines.append("SKILL-STATE GC:")
        lines.append(f"  {skill_state_gc.stdout.strip()[:120]}")
        lines.append("")

    lines.append("Reference: agent-skill-management-research-2026.md (ToolScope arXiv:2510.20036, SkillsVote arXiv:2605.18401)")
    lines.append("Action: review and run `hermes curator archive` (Archive tier) or `skill_manage(action='delete')` (confirmed duplicates).")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
