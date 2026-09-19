#!/usr/bin/env python3
"""
SYNAPSE — Skill Yield Normalization and Adaptive Pruning

Tracks skill execution metrics and computes normalized yield for adaptive pruning.

Usage:
  python3 ~/.hermes/scripts/skill-yield-tracker.py [--audit] [--prune]
  --audit: print yield report
  --prune: deprecate skills with yield < 0.1 for 10+ invocations

Metrics:
  - success_count: number of successful executions
  - failure_count: number of failed executions
  - token_cost: average tokens used per execution
  - time_cost: average time taken per execution (seconds)
  - impact: subjective impact score (1-5)

Yield formula:
  yield = (success_count - failure_count) / total_invocations
  normalized_yield = (success_rate * impact) / (token_cost * time_cost)

Pruning:
  - Skills with yield < 0.1 for 10+ invocations are deprecated
  - Tombstone entry added to skill's ## Deprecation section
  - Replacement skill suggested if available
"""

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# OT utilities (shared; OT-14)
_OT_UTILS_PATH = Path(__file__).parent / "ot_utils.py"
if _OT_UTILS_PATH.exists():
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("ot_utils", _OT_UTILS_PATH)
    _ot_utils = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_ot_utils)  # type: ignore[union-attr]
else:
    _ot_utils = None  # type: ignore[assignment]

# Config — profile-aware paths
import os as _os_syt
_hermes_home_syt = Path(_os_syt.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile_syt = _os_syt.environ.get("HERMES_PROFILE", "")
_hermes_root_syt = (_hermes_home_syt / "profiles" / _hermes_profile_syt) if _hermes_profile_syt and "profiles" not in str(_hermes_home_syt) else _hermes_home_syt
DB_PATH = _hermes_root_syt / "state.db"
SKILLS_DIR = _hermes_root_syt / "skills"
SKILL_YIELD_TABLE = "skill_yield_metrics"
SKILL_INVOCATION_TABLE = "skill_invocations"

# Schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS skill_yield_metrics (
    skill_name TEXT PRIMARY KEY,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    token_cost_sum INTEGER DEFAULT 0,
    time_cost_sum REAL DEFAULT 0.0,
    impact_sum INTEGER DEFAULT 0,
    invocation_count INTEGER DEFAULT 0,
    last_invoked_at TEXT,
    yield REAL DEFAULT 0.0,
    normalized_yield REAL DEFAULT 0.0,
    deprecated INTEGER DEFAULT 0,
    deprecation_reason TEXT,
    replacement_skill TEXT
);

CREATE TABLE IF NOT EXISTS skill_invocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT,
    session_id TEXT,
    timestamp TEXT,
    success INTEGER,
    tokens_used INTEGER,
    time_taken REAL,
    impact_score INTEGER,
    FOREIGN KEY(skill_name) REFERENCES skill_yield_metrics(skill_name)
);
"""

# Yield thresholds
YIELD_THRESHOLD_REVIEW = 0.3
YIELD_THRESHOLD_PRUNE = 0.1
MIN_INVOCATIONS_PRUNE = 10


def init_db():
    """Initialize the database schema."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)


def update_metrics(skill_name: str, success: bool, tokens_used: int, time_taken: float, impact_score: int) -> None:
    """Update skill metrics after an invocation."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Update invocation table
        cursor.execute(
            "INSERT INTO skill_invocations (skill_name, session_id, timestamp, success, tokens_used, time_taken, impact_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (skill_name, os.getenv("HERMES_SESSION_ID", "unknown"), time.strftime("%Y-%m-%dT%H:%M:%S"), int(success), tokens_used, time_taken, impact_score)
        )
        
        # Update metrics table
        cursor.execute(
            "SELECT success_count, failure_count, token_cost_sum, time_cost_sum, impact_sum, invocation_count "
            "FROM skill_yield_metrics WHERE skill_name = ?",
            (skill_name,)
        )
        row = cursor.fetchone()
        
        if row:
            success_count, failure_count, token_cost_sum, time_cost_sum, impact_sum, invocation_count = row
            success_count += int(success)
            failure_count += int(not success)
            token_cost_sum += tokens_used
            time_cost_sum += time_taken
            impact_sum += impact_score
            invocation_count += 1
        else:
            success_count = int(success)
            failure_count = int(not success)
            token_cost_sum = tokens_used
            time_cost_sum = time_taken
            impact_sum = impact_score
            invocation_count = 1
        
        # Compute yield
        total_invocations = success_count + failure_count
        yield_val = (success_count - failure_count) / total_invocations if total_invocations > 0 else 0.0
        
        # Compute normalized yield
        success_rate = success_count / total_invocations if total_invocations > 0 else 0.0
        avg_token_cost = token_cost_sum / invocation_count if invocation_count > 0 else 0.0
        avg_time_cost = time_cost_sum / invocation_count if invocation_count > 0 else 0.0
        avg_impact = impact_sum / invocation_count if invocation_count > 0 else 0.0
        
        normalized_yield = (success_rate * avg_impact) / (avg_token_cost * avg_time_cost) if (avg_token_cost * avg_time_cost) > 0 else 0.0
        
        # Update metrics
        cursor.execute(
            "INSERT OR REPLACE INTO skill_yield_metrics "
            "(skill_name, success_count, failure_count, token_cost_sum, time_cost_sum, impact_sum, invocation_count, last_invoked_at, yield, normalized_yield) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (skill_name, success_count, failure_count, token_cost_sum, time_cost_sum, impact_sum, invocation_count, time.strftime("%Y-%m-%dT%H:%M:%S"), yield_val, normalized_yield)
        )
        
        conn.commit()


def audit_skills() -> List[Dict]:
    """Generate a yield report for all skills."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT skill_name, success_count, failure_count, invocation_count, yield, normalized_yield, deprecated, deprecation_reason, replacement_skill "
            "FROM skill_yield_metrics ORDER BY normalized_yield DESC"
        )
        rows = cursor.fetchall()
        
        report = []
        for row in rows:
            skill_name, success_count, failure_count, invocation_count, yield_val, normalized_yield, deprecated, deprecation_reason, replacement_skill = row
            report.append({
                "skill_name": skill_name,
                "success_count": success_count,
                "failure_count": failure_count,
                "invocation_count": invocation_count,
                "yield": round(yield_val, 3),
                "normalized_yield": round(normalized_yield, 3),
                "deprecated": bool(deprecated),
                "deprecation_reason": deprecation_reason,
                "replacement_skill": replacement_skill
            })
        
        return report


def prune_skills() -> List[Dict]:
    """Deprecate skills with yield < 0.1 for 10+ invocations."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT skill_name, invocation_count, yield FROM skill_yield_metrics "
            "WHERE deprecated = 0 AND invocation_count >= ? AND yield < ?",
            (MIN_INVOCATIONS_PRUNE, YIELD_THRESHOLD_PRUNE)
        )
        rows = cursor.fetchall()
        
        pruned = []
        for skill_name, invocation_count, yield_val in rows:
            # Find replacement skill
            replacement_skill = find_replacement_skill(skill_name)
            
            # Add tombstone to skill file
            add_tombstone(skill_name, yield_val, invocation_count, replacement_skill)
            
            # Update database
            cursor.execute(
                "UPDATE skill_yield_metrics SET deprecated = 1, deprecation_reason = ?, replacement_skill = ? WHERE skill_name = ?",
                (f"Yield < {YIELD_THRESHOLD_PRUNE} ({invocation_count} invocations)", replacement_skill, skill_name)
            )
            
            pruned.append({
                "skill_name": skill_name,
                "yield": yield_val,
                "invocation_count": invocation_count,
                "replacement_skill": replacement_skill
            })
        
        conn.commit()
        return pruned


def find_replacement_skill(skill_name: str) -> Optional[str]:
    """Find a replacement skill for the given skill."""
    # Simple heuristic: look for skills in the same category
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_path.exists():
        return None
    
    # Read category from skill file
    with open(skill_path, 'r') as f:
        for line in f:
            if line.startswith("category:"):
                category = line.split(":")[1].strip()
                break
        else:
            return None
    
    # Find skills in the same category
    candidates = []
    for skill_dir in SKILLS_DIR.glob("*"):
        if skill_dir.is_dir():
            candidate_path = skill_dir / "SKILL.md"
            if candidate_path.exists():
                with open(candidate_path, 'r') as f:
                    for line in f:
                        if line.startswith("category:") and line.split(":")[1].strip() == category:
                            candidates.append(skill_dir.name)
                            break
    
    # Filter out the deprecated skill and sort by normalized yield
    candidates = [c for c in candidates if c != skill_name]
    if not candidates:
        return None
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT skill_name FROM skill_yield_metrics WHERE skill_name IN ({}) ORDER BY normalized_yield DESC".format(
                ",".join(["?"] * len(candidates))
            ),
            candidates
        )
        row = cursor.fetchone()
        return row[0] if row else None


def add_tombstone(skill_name: str, yield_val: float, invocation_count: int, replacement_skill: Optional[str]) -> None:
    """Add a tombstone entry to the skill's ## Deprecation section."""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_path.exists():
        return

    with open(skill_path, 'r') as f:
        content = f.read()

    tombstone = f"\n## Deprecation\n- Date: {time.strftime('%Y-%m-%d')}\n- Reason: Yield < {YIELD_THRESHOLD_PRUNE} ({invocation_count} invocations, yield={yield_val:.3f})\n"
    if replacement_skill:
        tombstone += f"- Replacement: `{replacement_skill}`\n"

    if "## Deprecation" in content:
        # Replace existing deprecation section (preserve everything before first marker)
        content = content.split("## Deprecation")[0] + tombstone
    else:
        # Add new deprecation section
        content += tombstone

    # Atomic write: tmp + replace prevents corruption on kill and concurrent access
    _tmp = skill_path.with_suffix(".md.tmp")
    try:
        _tmp.write_text(content)
        _tmp.replace(skill_path)
    except Exception as _e:
        import sys as _sys_at
        print(f"[skill-yield-tracker] tombstone write failed for {skill_name}: {_e}", file=_sys_at.stderr)
        try:
            _tmp.unlink(missing_ok=True)
        except Exception:
            pass


def confidence_intervals(z: float = 1.96) -> list[dict]:
    """Compute Wilson score confidence intervals for per-skill success rates.

    Reads from metacognitive.db skill_profiles (skill, total, successes).
    Wilson CI: center = (n_s + z^2/2) / (n + z^2)
               half_w = z * sqrt(n_s*(n-n_s)/n + z^2/4) / (n + z^2)
    where z=1.96 for 95% CI.
    """
    hermes_home = Path.home() / ".hermes"
    meta_db_candidates = [
        Path(os.environ["MH_DB"]) if "MH_DB" in os.environ else None,
        Path(os.environ.get("HERMES_HOME", str(hermes_home))) / "memory-facts" / "metacognitive.db",
        hermes_home / "memory-facts" / "metacognitive.db",
    ]
    meta_db = next((p for p in meta_db_candidates if p is not None and p.is_file()), None)
    if meta_db is None:
        return []

    import math as _math

    rows_raw = []
    try:
        conn = sqlite3.connect(f"file:{meta_db}?mode=ro", uri=True)
        try:
            rows_raw = conn.execute(
                "SELECT skill, SUM(total) AS n, SUM(successes) AS n_s "
                "FROM skill_profiles GROUP BY skill"
            ).fetchall()
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return []

    z2 = z * z
    results = []
    for skill, n, n_s in rows_raw:
        n = int(n or 0)
        n_s = int(n_s or 0)
        if n <= 0:
            results.append({
                "skill_name": skill,
                "n_obs": 0,
                "success_rate": None,
                "ci_95_low": None,
                "ci_95_high": None,
            })
            continue
        n_s = max(0, min(n_s, n))
        success_rate = n_s / n
        denom = n + z2
        center = (n_s + z2 / 2.0) / denom
        inner = n_s * (n - n_s) / n + z2 / 4.0
        half_w = z * _math.sqrt(max(0.0, inner)) / denom
        ci_low = max(0.0, center - half_w)
        ci_high = min(1.0, center + half_w)
        results.append({
            "skill_name": skill,
            "n_obs": n,
            "success_rate": round(success_rate, 4),
            "ci_95_low": round(ci_low, 4),
            "ci_95_high": round(ci_high, 4),
        })

    results.sort(key=lambda x: (-(x["n_obs"] or 0), x["skill_name"]))
    return results


def cmd_confidence_intervals(argv=None):
    """confidence-intervals subcommand: Wilson 95% CI per skill."""
    import argparse as _ap
    parser = _ap.ArgumentParser(
        prog="skill-yield-tracker.py confidence-intervals",
        description="Wilson score 95% CI for per-skill success rates (GS-4)",
    )
    parser.add_argument("--z", type=float, default=1.96,
                        help="Z-score for CI (default 1.96 = 95%%)")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output raw JSON in addition to the table")
    args = parser.parse_args(argv)

    rows = confidence_intervals(z=args.z)
    if not rows:
        print("No skill profile data found in metacognitive.db.")
        return

    print(f"\n{'skill_name':<42}  {'n_obs':>5}  {'success_rate':>12}  {'95%_CI_low':>10}  {'95%_CI_high':>11}")
    print(f"{'-'*42}  {'-----':>5}  {'------------':>12}  {'----------':>10}  {'-----------':>11}")
    for row in rows:
        sr = f"{row['success_rate']:.4f}" if row["success_rate"] is not None else "n/a"
        lo = f"{row['ci_95_low']:.4f}" if row["ci_95_low"] is not None else "n/a"
        hi = f"{row['ci_95_high']:.4f}" if row["ci_95_high"] is not None else "n/a"
        print(f"{row['skill_name']:<42}  {row['n_obs']:>5}  {sr:>12}  {lo:>10}  {hi:>11}")

    if args.json_out:
        print("\n--- JSON ---")
        print(json.dumps({
            "method": "wilson_score_ci",
            "z": args.z,
            "ci_pct": round((1 - 2 * (1 - 0.9772)) * 100, 1) if abs(args.z - 1.96) < 0.01 else None,
            "skills": rows,
        }, indent=2))
    else:
        print(json.dumps({
            "method": "wilson_score_ci",
            "z": args.z,
            "skills": rows,
        }, indent=2))


def wilson_ci(n: int, n_success: int, z: float = 1.96) -> tuple:
    """Wilson score interval for a proportion.

    Returns (p_hat, lower, upper) where [lower, upper] is the Wilson CI.
    Wilson CI is preferred over Wald (normal approx) because it remains
    valid at extreme proportions (0 or 1) and small n.

    Formula (from Wilson 1927):
      p_hat = n_success / n
      denom = 1 + z^2/n
      centre = (p_hat + z^2/(2n)) / denom
      half_width = z * sqrt(p_hat*(1-p_hat)/n + z^2/(4n^2)) / denom
    """
    if n == 0:
        return 0.0, 0.0, 1.0
    z2 = z * z
    p_hat = n_success / n
    denom = 1.0 + z2 / n
    centre = (p_hat + z2 / (2 * n)) / denom
    half_width = z * ((p_hat * (1.0 - p_hat) / n + z2 / (4 * n * n)) ** 0.5) / denom
    return p_hat, max(0.0, centre - half_width), min(1.0, centre + half_width)


def cmd_skill_ci(skill_name: Optional[str] = None, success: Optional[bool] = None,
                 prior_estimate: Optional[float] = None) -> None:
    """WALD2-4: Maintain and display Wilson CIs for each skill's success rate.

    If skill_name + success are given, record an observation then show the updated table.
    Otherwise just show the current CI table.

    Shift detection: if a prior_estimate is supplied (or read from DB), flag when
    the Wilson CI no longer contains the prior mean.
    """
    init_db()

    # Optionally record an observation
    if skill_name is not None and success is not None:
        update_metrics(skill_name, success,
                       tokens_used=0, time_taken=0.0, impact_score=3)
        print(f"Recorded: skill={skill_name!r} success={success}\n")

    # Fetch all skill metrics
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT skill_name, success_count, invocation_count "
            "FROM skill_yield_metrics ORDER BY skill_name"
        )
        rows = cursor.fetchall()

    if not rows:
        print("No skill metrics found. Record some observations first.")
        return

    print(f"{'Skill':<40} {'n':>5} {'p_hat':>7} {'CI_lo':>7} {'CI_hi':>7} {'prior':>7} {'shift':>6}")
    print("-" * 85)

    for skill_n, n_success, n_total in rows:
        if n_total == 0:
            continue
        p_hat, lo, hi = wilson_ci(n_total, n_success)
        # Prior estimate: uniform Beta(1,1) mean = 0.5 if no explicit prior given
        prior = prior_estimate if prior_estimate is not None else 0.5
        shift = "YES ⚠" if not (lo <= prior <= hi) else "no"
        print(f"{skill_n:<40} {n_total:>5} {p_hat:>7.3f} {lo:>7.3f} {hi:>7.3f} {prior:>7.3f} {shift:>6}")

    print()
    print("Wilson 95% CI: shift=YES when the prior estimate falls outside [CI_lo, CI_hi].")


def main():
    # GS-4: confidence-intervals subcommand
    if len(sys.argv) > 1 and sys.argv[1] == "confidence-intervals":
        cmd_confidence_intervals(sys.argv[2:])
        return

    # WALD2-4: skill-ci subcommand
    if len(sys.argv) > 1 and sys.argv[1] == "skill-ci":
        import argparse as _ap
        _p = _ap.ArgumentParser(
            prog="skill-yield-tracker.py skill-ci",
            description="WALD2-4: Wilson CI per-skill success rate table with shift detection",
        )
        _p.add_argument("--skill", default=None,
                        help="Skill name to record an observation for")
        _p.add_argument("--outcome", choices=["success", "failure"], default=None,
                        help="Outcome of the invocation (success or failure)")
        _p.add_argument("--prior", type=float, default=None,
                        help="Prior success-rate estimate to test for shift (default 0.5)")
        _sargs = _p.parse_args(sys.argv[2:])
        _success_val = None
        if _sargs.outcome == "success":
            _success_val = True
        elif _sargs.outcome == "failure":
            _success_val = False
        cmd_skill_ci(
            skill_name=_sargs.skill,
            success=_success_val,
            prior_estimate=_sargs.prior,
        )
        return

    init_db()

    if "--audit" in sys.argv:
        report = audit_skills()
        print("Skill Yield Report:")
        print("=" * 80)
        for entry in report:
            status = "DEPRECATED" if entry["deprecated"] else "ACTIVE"
            print(f"{entry['skill_name']:40} | Yield: {entry['yield']:6.3f} | Norm: {entry['normalized_yield']:6.3f} | Invocations: {entry['invocation_count']:4} | {status}")
            if entry["deprecated"]:
                print(f"  Reason: {entry['deprecation_reason']}")
                if entry["replacement_skill"]:
                    print(f"  Replacement: {entry['replacement_skill']}")
        return
    
    if "--prune" in sys.argv:
        pruned = prune_skills()
        if pruned:
            print("Pruned Skills:")
            print("=" * 80)
            for entry in pruned:
                print(f"{entry['skill_name']:40} | Yield: {entry['yield']:.3f} | Invocations: {entry['invocation_count']}")
                if entry["replacement_skill"]:
                    print(f"  Replacement: {entry['replacement_skill']}")
        else:
            print("No skills to prune.")
        return

    # === OT-14: --w1-quality ===
    if "--w1-quality" in sys.argv:
        if _ot_utils is None:
            print("[OT-14] ot_utils not available — cannot compute W1 quality signal.")
            sys.exit(1)
        # Parse --ideal and --actual args (positional after --w1-quality,
        # or via --ideal=<text> / --actual=<text>)
        import argparse as _ap
        _p = _ap.ArgumentParser(prog="skill-yield-tracker.py --w1-quality", add_help=False)
        _p.add_argument("--ideal", required=False, default=None,
                        help="Ideal output template (text string or @filepath)")
        _p.add_argument("--actual", required=False, default=None,
                        help="Actual output sample (text string or @filepath)")
        _p.add_argument("--w1-quality", action="store_true", dest="w1_quality")
        _wargs, _wrest = _p.parse_known_args()

        def _load_text(val: str | None, label: str) -> str:
            if val is None:
                # Try positional remainder: first unused arg = ideal, second = actual
                return ""
            if val.startswith("@"):
                p = Path(val[1:])
                if not p.exists():
                    print(f"[OT-14] {label} file not found: {p}")
                    sys.exit(1)
                return p.read_text(errors="replace")
            return val

        ideal_text = _load_text(_wargs.ideal, "ideal")
        actual_text = _load_text(_wargs.actual, "actual")

        # If neither --ideal nor --actual provided, use _wrest positionals
        if not ideal_text and not actual_text and len(_wrest) >= 2:
            ideal_text = _wrest[0]
            actual_text = _wrest[1]
        elif not ideal_text or not actual_text:
            print("[OT-14] Usage: --w1-quality --ideal <text|@file> --actual <text|@file>")
            print("         or:   --w1-quality '<ideal text>' '<actual text>'")
            sys.exit(1)

        tf_ideal = _ot_utils.build_tf(ideal_text)
        tf_actual = _ot_utils.build_tf(actual_text)
        w1 = _ot_utils.w1_distance(tf_ideal, tf_actual)
        print(f"W1_output_distance (lower=better match to ideal) = {w1:.6f}")
        print(f"  Ideal tokens:  {len(tf_ideal)} unique terms")
        print(f"  Actual tokens: {len(tf_actual)} unique terms")
        if w1 < 0.05:
            print("  Quality signal: excellent — output vocabulary closely matches ideal template.")
        elif w1 < 0.15:
            print("  Quality signal: good — minor vocabulary divergence from ideal.")
        elif w1 < 0.30:
            print("  Quality signal: moderate — notable vocabulary gap; review output.")
        else:
            print("  Quality signal: poor — output vocabulary significantly differs from ideal.")
        print("  Note: non-differentiable W1 signal; use for offline QA, not gradient training.")
        return

    print("Usage:")
    print("  python3 skill-yield-tracker.py --audit   # Generate yield report")
    print("  python3 skill-yield-tracker.py --prune   # Deprecate low-yield skills")
    print("  python3 skill-yield-tracker.py --w1-quality --ideal <text|@file> --actual <text|@file>")
    print("  python3 skill-yield-tracker.py skill-ci [--skill NAME --outcome success|failure] [--prior FLOAT]")


if __name__ == "__main__":
    main()