#!/usr/bin/env python3
"""
memory-ttl-purge.py — TTL enforcement for Hermes staged memories.

GPM (Governed Persistent Memory, arXiv:2608.12476, Aug 2026): memories must have
explicit TTL fields; expired memories must be purged, not just tagged. This script
enforces the expiry discipline that lifecycle.db tracks but doesn't self-enforce.

What this script does:
1. Scans lifecycle.db for entries where:
   - memory_status = 'archived' (superseded) and valid_to < NOW - 7 days
   - memory_status = 'deleted' (retention < 0.05)
   - volatility_class = 'ephemeral' and valid_from < NOW - 1 day
   - volatility_class = 'volatile' and valid_from < NOW - 30 days (14d for preference-type facts)
2. For each expired entry, removes the corresponding line from staging.md
3. Logs the purge to purge_log.jsonl for audit

Sweep 24 additions:
- Type-conditioned volatile TTL: preference-type facts expire at 14d, others at 30d
  (arXiv:2604.20006 Memora/FAMA: stale memory reuse is the dominant failure mode;
   arXiv:2605.17625 Dual Process: message-count cap is more principled than calendar TTL)
- FAMA-style staleness tracking: logs stale-retrieval events to staleness_log.jsonl
  for downstream health metric computation (arXiv:2604.20006)

Usage:
  python3 memory-ttl-purge.py [--dry-run] [--verbose]

Runs safely as a cron job (idempotent, append-only audit log).
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re

FACTS_DIR = Path.home() / ".hermes" / "memory-facts"
LIFECYCLE_DB = FACTS_DIR / "lifecycle.db"
STAGING_PATH = FACTS_DIR / "staging.md"
PURGE_LOG = FACTS_DIR / "purge_log.jsonl"
STALENESS_LOG = FACTS_DIR / "staleness_log.jsonl"  # sweep 24: FAMA-style tracking

# TTL policy per volatility class
# Sweep 24: volatile TTL is now type-conditioned (see TYPE_CONDITIONED_TTL below)
TTL_POLICY = {
    "ephemeral": timedelta(days=1),
    "volatile": timedelta(days=30),      # default; overridden per fact_type below
    "stable": timedelta(days=365 * 10),  # effectively permanent unless superseded
}

# Sweep 24: Type-conditioned volatile TTL (arXiv:2604.20006 Memora/FAMA, arXiv:2608.04746 ScrubJay)
# Preference and user-state facts evolve faster than procedural or env facts.
# 'preference' and 'user_state' types → 14d volatile TTL
# All others keep the default 30d volatile TTL
PREFERENCE_FACT_TYPES = frozenset({"preference", "user_state", "user_preference", "correction", "personal_procedure"})
VOLATILE_PREFERENCE_TTL = timedelta(days=14)
# M2: personal_procedure facts evolve faster than preference (procedures go stale quickly)
PERSONAL_PROCEDURE_TTL = timedelta(days=7)
# M2b: skill_trace facts record which skills fired and with what outcomes — keep longer
# than volatile facts (90d) because they inform retrospective skill improvement sweeps.
SKILL_TRACE_TTL = timedelta(days=90)
# Dual Process (arXiv:2605.17625): calendar TTL is a poor proxy under sparse use.
# If a volatile fact's originating session is older than N later sessions, expire it.
MAX_VOLATILE_SESSIONS = 20
CONSTRAINT_FACT_TYPES = frozenset({"constraint", "must"})
CONSTRAINT_MAX_AGE_DAYS = 90

ARCHIVED_GRACE_PERIOD = timedelta(days=7)  # keep archived (superseded) facts 7 days for audit

# ECHO reuse-weighted TTL extension (arXiv:2606.31650): frequently-retrieved facts earn longer retention
REUSE_TTL_BONUS = timedelta(days=7)
REUSE_TTL_CAP = timedelta(days=28)
REUSE_ACCESS_THRESHOLD = 2



def _load_ttl_config() -> None:
    """Sweep 27: honor config.yaml memory.tier_thresholds caps when present."""
    global MAX_VOLATILE_SESSIONS, CONSTRAINT_MAX_AGE_DAYS
    cfg_path = Path.home() / ".hermes" / "config.yaml"
    try:
        import yaml  # type: ignore
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
        tt = (cfg.get("memory") or {}).get("tier_thresholds") or {}
        if tt.get("max_volatile_sessions") is not None:
            MAX_VOLATILE_SESSIONS = int(tt["max_volatile_sessions"])
        cf = cfg.get("constraint_freshness") or (cfg.get("memory") or {}).get("constraint_freshness") or {}
        if cf.get("max_constraint_age_days") is not None:
            CONSTRAINT_MAX_AGE_DAYS = int(cf["max_constraint_age_days"])
    except Exception:
        pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_expired(conn: sqlite3.Connection) -> list[dict]:
    """Return lifecycle.db rows that are due for purge."""
    now = now_utc().isoformat()
    expired = []

    # 1. Archived (superseded) facts older than grace period
    rows = conn.execute(
        "SELECT memory_id, fact_type, memory_status, volatility_class, valid_to, valid_from "
        "FROM fact_lifecycle "
        "WHERE memory_status IN ('archived', 'deleted')",
    ).fetchall()
    grace_cutoff = (now_utc() - ARCHIVED_GRACE_PERIOD).isoformat()
    for r in rows:
        valid_to = r[4] or ""
        if valid_to and valid_to < grace_cutoff:
            expired.append({
                "memory_id": r[0], "fact_type": r[1], "status": r[2],
                "vc": r[3], "reason": "archived_grace_expired",
                "valid_to": valid_to,
            })

    # 2. Ephemeral/volatile facts past their TTL
    # Sweep 24: type-conditioned volatile TTL — preference-type facts use 14d
    rows2 = conn.execute(
        "SELECT memory_id, fact_type, memory_status, volatility_class, valid_from "
        "FROM fact_lifecycle "
        "WHERE memory_status = 'active' AND volatility_class IN ('ephemeral', 'volatile')"
    ).fetchall()
    for r in rows2:
        vc = r[3] or "stable"
        fact_type = (r[1] or "").lower()
        valid_from_str = r[4] or ""
        if not valid_from_str:
            continue
        try:
            valid_from = datetime.fromisoformat(valid_from_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        # Type-conditioned TTL for volatile preference facts (sweep 24, arXiv:2604.20006)
        if vc == "volatile" and fact_type == "personal_procedure":
            ttl = PERSONAL_PROCEDURE_TTL  # M2: 7d — shorter than preference (14d)
            reason = f"ttl_exceeded_volatile_personal_procedure"
        elif vc == "volatile" and fact_type == "skill_trace":
            ttl = SKILL_TRACE_TTL  # M2b: 90d — keep skill traces for retrospective improvement sweeps
            reason = f"ttl_exceeded_volatile_skill_trace"
        elif vc == "volatile" and fact_type in PREFERENCE_FACT_TYPES:
            ttl = VOLATILE_PREFERENCE_TTL
            reason = f"ttl_exceeded_volatile_preference_{fact_type}"
        else:
            ttl = TTL_POLICY.get(vc, TTL_POLICY["stable"])
            reason = f"ttl_exceeded_{vc}"
        # ECHO reuse-weighted TTL extension (arXiv:2606.31650): frequently-retrieved facts earn longer retention
        fact_text = ""
        try:
            ft_row = conn.execute(
                "SELECT fact_text FROM fact_lifecycle WHERE memory_id=? LIMIT 1", (r[0],)
            ).fetchone()
            fact_text = (ft_row[0] or "") if ft_row else ""
        except Exception:
            pass
        access_count = 0
        try:
            ac_row = conn.execute(
                "SELECT access_count FROM fact_lifecycle WHERE memory_id=? LIMIT 1", (r[0],)
            ).fetchone()
            access_count = int((ac_row[0] or 0)) if ac_row else 0
        except Exception:
            pass
        ttl = ttl + _echo_ttl_extension(access_count)
        if now_utc() - valid_from > ttl:
            expired.append({
                "memory_id": r[0], "fact_type": r[1], "status": r[2],
                "vc": vc, "reason": reason,
                "valid_from": valid_from_str,
            })

    # 3. Dual Process session-count cap (arXiv:2605.17625). Fail-open if session_id empty.
    keep_sessions = _recent_session_ids(conn, MAX_VOLATILE_SESSIONS)
    if keep_sessions:
        for r in rows2:
            vc = r[3] or "stable"
            if vc != "volatile":
                continue
            sid = ""
            try:
                sid = conn.execute(
                    "SELECT session_id FROM fact_lifecycle WHERE memory_id=?",
                    (r[0],),
                ).fetchone()
                sid = (sid[0] if sid else "") or ""
            except Exception:
                continue
            if not sid or sid in keep_sessions:
                continue
            if any(e["memory_id"] == r[0] for e in expired):
                continue
            expired.append({
                "memory_id": r[0], "fact_type": r[1], "status": r[2],
                "vc": vc, "reason": "volatile_session_cap",
                "session_id": sid,
            })

    # Never delete constraint-class rows; freshness check warns only.
    return [
        e for e in expired
        if (e.get("fact_type") or "").lower() not in CONSTRAINT_FACT_TYPES
    ]


def _recent_session_ids(conn: sqlite3.Connection, n: int) -> set[str]:
    try:
        rows = conn.execute(
            "SELECT session_id, MAX(valid_from) AS latest "
            "FROM fact_lifecycle "
            "WHERE IFNULL(session_id,'') != '' "
            "GROUP BY session_id ORDER BY latest DESC"
        ).fetchall()
    except Exception:
        return set()
    return {r[0] for r in rows[:n] if r[0]}


def _echo_ttl_extension(access_count: int) -> timedelta:
    """
    ECHO reuse-weighted TTL extension (arXiv:2606.31650).
    Facts with access_count >= REUSE_ACCESS_THRESHOLD earn +7d per access above threshold,
    capped at +28d extra.
    """
    if access_count < REUSE_ACCESS_THRESHOLD:
        return timedelta(0)
    extra_accesses = access_count - (REUSE_ACCESS_THRESHOLD - 1)
    bonus = REUSE_TTL_BONUS * extra_accesses
    return min(bonus, REUSE_TTL_CAP)


def log_staleness_event(memory_ids: set[str], expired: list[dict]) -> None:
    """
    Sweep 24: FAMA-style staleness tracking (arXiv:2604.20006 Memora).
    Logs which expired memory_ids had non-zero access_count at purge time —
    these were 'stale memories that were still being retrieved', the dominant failure mode.
    Call this BEFORE purging so access_count is still readable from lifecycle.db.
    """
    if not LIFECYCLE_DB.exists():
        return
    stale_reuse = []
    try:
        with sqlite3.connect(str(LIFECYCLE_DB)) as conn:
            conn.row_factory = sqlite3.Row
            for mid in memory_ids:
                row = conn.execute(
                    "SELECT memory_id, fact_type, volatility_class, access_count, "
                    "valid_from, last_accessed FROM fact_lifecycle WHERE memory_id=?",
                    (mid,),
                ).fetchone()
                if row and (row["access_count"] or 0) > 0:
                    # FAMA genGap: age at last retrieval (or now) vs valid_from
                    gen_gap_days = None
                    try:
                        vf = row["valid_from"] or ""
                        la = row["last_accessed"] or now_utc().isoformat()
                        if vf:
                            t0 = datetime.fromisoformat(vf.replace("Z", "+00:00"))
                            t1 = datetime.fromisoformat(la.replace("Z", "+00:00"))
                            gen_gap_days = round((t1 - t0).total_seconds() / 86400.0, 2)
                    except Exception:
                        gen_gap_days = None
                    stale_reuse.append({
                        "memory_id": row["memory_id"],
                        "fact_type": row["fact_type"],
                        "vc": row["volatility_class"],
                        "access_count": row["access_count"],
                        "gen_gap_days": gen_gap_days,  # sweep 27 FAMA
                    })
    except Exception:
        return  # access_count column may not exist in all schema versions

    if stale_reuse:
        event = {
            "ts": now_utc().isoformat(),
            "stale_reuse_count": len(stale_reuse),
            "entries": stale_reuse,
        }
        with open(STALENESS_LOG, "a") as f:
            f.write(json.dumps(event) + "\n")


def remove_from_staging(memory_ids: set[str], dry_run: bool, verbose: bool) -> int:
    """Remove lines containing any of the memory_ids from staging.md. Returns count removed."""
    if not STAGING_PATH.exists():
        return 0

    lines = STAGING_PATH.read_text().splitlines()
    kept = []
    removed = 0
    for line in lines:
        matched_id = None
        for mid in memory_ids:
            if f"[id={mid}]" in line:
                matched_id = mid
                break
        if matched_id:
            removed += 1
            if verbose:
                print(f"  PURGE [{matched_id}]: {line[:80]}")
        else:
            kept.append(line)

    if not dry_run and removed > 0:
        STAGING_PATH.write_text("\n".join(kept) + ("\n" if kept else ""))

    return removed


def mark_purged(conn: sqlite3.Connection, memory_ids: set[str], dry_run: bool):
    """Update lifecycle.db status to 'purged' for removed entries."""
    if dry_run:
        return
    ts = now_utc().isoformat()
    for mid in memory_ids:
        conn.execute(
            "UPDATE fact_lifecycle SET memory_status='purged', valid_to=? WHERE memory_id=?",
            (ts, mid),
        )


def append_purge_log(expired: list[dict], removed_ids: set[str], dry_run: bool):
    """Append purge event to audit log."""
    if dry_run:
        return
    event = {
        "ts": now_utc().isoformat(),
        "purged_count": len(removed_ids),
        "entries": [e for e in expired if e["memory_id"] in removed_ids],
    }
    with open(PURGE_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")


def main():
    _load_ttl_config()
    p = argparse.ArgumentParser(description="TTL purge for Hermes staged memories (GPM pattern)")
    p.add_argument("--dry-run", action="store_true", help="Show what would be purged without removing")
    p.add_argument("--verbose", action="store_true", help="Print each purged line")
    args = p.parse_args()

    if not LIFECYCLE_DB.exists():
        print("[memory-ttl-purge] lifecycle.db does not exist yet — nothing to purge.")
        sys.exit(0)

    with sqlite3.connect(str(LIFECYCLE_DB)) as conn:
        expired = load_expired(conn)
        # Freshness warn runs on every purge, including when no volatiles expired.
        stale_constraints = check_constraint_freshness(
            conn, max_age_days=CONSTRAINT_MAX_AGE_DAYS
        )

    if stale_constraints:
        print(f"[memory-ttl-purge] Stale constraints found: {len(stale_constraints)}")
        for sc in stale_constraints[:5]:
            print(f"  STALE_CONSTRAINT  session={sc.get('session','?')} text={sc.get('text','?')[:60]}")

    if not expired:
        print("[memory-ttl-purge] No expired entries found.")
        print(f"\n=== SUMMARY ===\nExpired: 0 | Staging lines removed: 0 | Stale constraints: {len(stale_constraints)}")
        sys.exit(0)

    expired_ids = {e["memory_id"] for e in expired}
    print(f"[memory-ttl-purge] Found {len(expired_ids)} expired entries ({'DRY RUN' if args.dry_run else 'LIVE'})")

    # Sweep 24: FAMA-style staleness tracking — log before purging (access_count still valid)
    log_staleness_event(expired_ids, expired)

    removed = remove_from_staging(expired_ids, args.dry_run, args.verbose)
    print(f"[memory-ttl-purge] Removed {removed} lines from staging.md")

    with sqlite3.connect(str(LIFECYCLE_DB)) as conn:
        mark_purged(conn, expired_ids, args.dry_run)

    append_purge_log(expired, expired_ids, args.dry_run)

    if not args.dry_run:
        print(f"[memory-ttl-purge] Done. Audit log: {PURGE_LOG}")

    print(f"\n=== SUMMARY ===\nExpired: {len(expired_ids)} | Staging lines removed: {removed} | Stale constraints: {len(stale_constraints)}")


if __name__ == "__main__":
    main()


# ── Stale constraint freshness gate (arXiv:2608.25553) ────────────────────────
# ~75% of stale-consistent decisions fail under a 2-record memory budget.
# Freshness ≠ relevance: a semantically relevant but withdrawn constraint is worse than none.
# Add a freshness timestamp to facts tagged as constraints, and warn on stale reuse.

def check_constraint_freshness(conn: sqlite3.Connection, max_age_days: int = 90) -> list[dict]:
    """
    Identify facts tagged as constraints that are older than max_age_days.
    These need re-validation before being injected into handoffs or working memory.
    Emits a staleness warning for each stale constraint found.
    """
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT memory_id, fact_text, fact_type, valid_from, volatility_class "
            "FROM fact_lifecycle "
            "WHERE fact_type IN ('constraint', 'must') "
            "AND memory_status = 'active' "
            "AND (valid_from IS NULL OR valid_from < ?) "
            "ORDER BY valid_from ASC",
            (cutoff_ts,),
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        return []

    stale = []
    for mid, text, ftype, valid_from, vc in rows:
        stale.append({
            "memory_id": mid,
            "fact_text": (text or "")[:120],
            "fact_type": ftype,
            "valid_from": valid_from,
            "volatility_class": vc,
            "age_warning": f"constraint older than {max_age_days}d — needs re-validation",
        })

    if stale:
        log_path = FACTS_DIR / "stale-constraints.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as f:
            import json as _json
            f.write(_json.dumps({
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "max_age_days": max_age_days,
                "stale_count": len(stale),
                "constraints": stale,
            }) + "\n")
        print(f"[constraint-freshness] {len(stale)} stale constraints logged → {log_path}")
    else:
        print(f"[constraint-freshness] No stale constraints (all < {max_age_days}d old)")
    return stale
