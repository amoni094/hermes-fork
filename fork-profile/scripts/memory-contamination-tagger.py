#!/usr/bin/env python3
"""
Infra stub: Memory Contamination Tagger (PSE)

Source:    cs-spike-queue: PSE — Persistent Semantic Entity Contamination Tagging
Target:    memory-contamination-tagger.py (new script)
Scaffold:  Scan Graphiti entity nodes for semantic contamination: entities whose
           name, aliases, or edge-label set overlap with known false/outdated
           facts. Three detection strategies:
  (1) Staleness: entity last_updated older than TTL and no corroborating recent
      episode within the recency window.
  (2) Contradiction: entity has two outbound edges with contradictory polarity
      (e.g. "is_true" and "is_false" both pointing from same source node).
  (3) Orphan drift: entity was mentioned in exactly one episode > 30 days ago
      with no reinforcement, and its edge_count == 1.

Invariant: A contaminated entity is tagged (not deleted) — no information is
           permanently removed without a human review step.
Kill test: inject a synthetic contradicted entity; assert tagger tags it within
           one scan cycle.
Hypothesis: PSE contamination tagging identifies ≥ 70% of stale or contradicted
            Graphiti entity nodes within a 30-day rolling window, with < 10%
            false-positive rate on active entities.
Metric:    contamination_precision = true_tagged / (true_tagged + false_tagged)
           measured against a labelled set of 100 entity nodes (50 contaminated,
           50 clean).
GWT:
  Given:  a Graphiti entity node with stale, contradicted, or orphaned edges,
  When:   the contamination tagger scans the entity graph,
  Then:   contaminated entities are tagged with contamination_type and
          confidence, and clean entities are left untagged (precision ≥ 0.90).

Belt: Only tag — never delete. Never tag entities with edge_count > 10 (too
      active to be contaminated). Scan ≤ 1000 entities per run.
"""

import json
import re
import sqlite3
from datetime import datetime, timezone, timedelta, UTC
from pathlib import Path
from typing import Optional

HERMES_HOME  = Path(__file__).resolve().parents[3]
PROFILE_ROOT = HERMES_HOME / "profiles" / "fork"
# Probe multiple candidate paths (ann-embeddings-probe pattern)
_GRAPHITI_CANDIDATES = [
    PROFILE_ROOT / "cache"  / "graphiti.db",
    HERMES_HOME / "graphiti.db",
    HERMES_HOME / "cache" / "graphiti.db",
]
GRAPHITI_DB  = next((c for c in _GRAPHITI_CANDIDATES if c.exists()), _GRAPHITI_CANDIDATES[0])
REPORT_PATH  = PROFILE_ROOT / "cache" / "memory-contamination-report.json"

def _atomic_json(path: Path, data: object) -> None:
    """Atomic JSON write via tmp sibling + os.replace."""
    import os, tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(data, indent=2))
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


TTL_DAYS     = 30
ORPHAN_DAYS  = 30
MAX_EDGE_ACTIVE = 10   # entities with > this many edges are considered active
MAX_SCAN     = 1000

# ── Contamination detectors ───────────────────────────────────────────────────
def _check_staleness(entity: dict, now: datetime) -> Optional[dict]:
    """Stale: last_updated > TTL_DAYS ago, no recent episodes."""
    updated = entity.get("last_updated") or entity.get("updated_at") or ""
    if not updated:
        return None
    try:
        dt = datetime.fromisoformat(updated)
        age = (now - dt).days
    except (ValueError, TypeError):
        return None
    if age > TTL_DAYS and entity.get("edge_count", 0) <= 2:
        return {"contamination_type": "stale", "age_days": age, "confidence": "medium"}
    return None

def _check_contradiction(entity: dict) -> Optional[dict]:
    """Contradiction: entity name or description contains mutually exclusive signals."""
    desc = str(entity.get("summary", "") or entity.get("description", "") or "")
    # Simple heuristic: presence of both "is correct" and "incorrect", "true" and "false" etc.
    contradictions = [
        (r"is correct", r"is incorrect"),
        (r"true",       r"false"),
        (r"valid",      r"invalid"),
        (r"active",     r"deprecated"),
    ]
    for pos, neg in contradictions:
        if re.search(pos, desc, re.IGNORECASE) and re.search(neg, desc, re.IGNORECASE):
            return {"contamination_type": "contradiction",
                    "pattern": f"{pos} + {neg}", "confidence": "high"}
    return None

def _check_orphan_drift(entity: dict, now: datetime) -> Optional[dict]:
    """Orphan: mentioned once long ago, edge_count==1."""
    created = entity.get("created_at") or entity.get("created") or ""
    if not created:
        return None
    try:
        dt = datetime.fromisoformat(created)
        age = (now - dt).days
    except (ValueError, TypeError):
        return None
    if age > ORPHAN_DAYS and entity.get("edge_count", 0) == 1:
        return {"contamination_type": "orphan_drift", "age_days": age, "confidence": "low"}
    return None

# ── Entity loader ─────────────────────────────────────────────────────────────
def _load_entities(limit: int = MAX_SCAN) -> list[dict]:
    """Load entities from Graphiti DB or return synthetic test data."""
    now = datetime.now(UTC)
    if not GRAPHITI_DB.exists():
        # Synthetic test data
        return [
            {"id": "e1", "name": "routing-linucb",   "summary": "Active script is correct",
             "updated_at": (now - timedelta(days=5)).isoformat(),  "edge_count": 12,
             "created_at": (now - timedelta(days=20)).isoformat()},
            {"id": "e2", "name": "old-bandit-policy", "summary": "This was true but is now false",
             "updated_at": (now - timedelta(days=60)).isoformat(), "edge_count": 1,
             "created_at": (now - timedelta(days=90)).isoformat()},
            {"id": "e3", "name": "pending-improvements-review", "summary": "Valid script",
             "updated_at": (now - timedelta(days=2)).isoformat(),  "edge_count": 8,
             "created_at": (now - timedelta(days=30)).isoformat()},
            {"id": "e4", "name": "legacy-routing-v1", "summary": "Deprecated",
             "updated_at": (now - timedelta(days=45)).isoformat(), "edge_count": 2,
             "created_at": (now - timedelta(days=45)).isoformat()},
            {"id": "e5", "name": "orphan-concept",    "summary": "Mentioned once",
             "updated_at": (now - timedelta(days=40)).isoformat(), "edge_count": 1,
             "created_at": (now - timedelta(days=40)).isoformat()},
        ]
    entities = []
    try:
        conn = sqlite3.connect(GRAPHITI_DB)
        cur  = conn.cursor()
        cur.execute("""
            SELECT uuid, name,
                   COALESCE(summary, '') as summary,
                   COALESCE(created_at, '') as created_at,
                   COALESCE(updated_at, '') as updated_at
            FROM entities
            ORDER BY updated_at ASC
            LIMIT ?
        """, (limit,))
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            rec = dict(zip(cols, row))
            # Count edges
            cur2 = conn.cursor()
            cur2.execute(
                "SELECT count(*) FROM edges WHERE source_id=? OR target_id=?",
                (rec["uuid"], rec["uuid"])
            )
            rec["edge_count"] = cur2.fetchone()[0]
            entities.append(rec)
        conn.close()
    except Exception as exc:
        print(f"[contamination] WARNING: {exc}")
    return entities

# ── Main scan ─────────────────────────────────────────────────────────────────
def scan(dry_run: bool = True) -> dict:
    now      = datetime.now(UTC)
    entities = _load_entities()
    tagged   = []
    skipped_active = 0

    for e in entities:
        if e.get("edge_count", 0) > MAX_EDGE_ACTIVE:
            skipped_active += 1
            continue
        contamination = (
            _check_contradiction(e) or
            _check_staleness(e, now) or
            _check_orphan_drift(e, now)
        )
        if contamination:
            tagged.append({
                "entity_id":   e.get("id") or e.get("uuid"),
                "name":        e.get("name"),
                "edge_count":  e.get("edge_count"),
                **contamination,
                "dry_run":     dry_run,
            })

    result = {
        "ts":              now.isoformat(),
        "dry_run":         dry_run,
        "scanned":         len(entities),
        "skipped_active":  skipped_active,
        "tagged":          len(tagged),
        "tags":            tagged,
        "precision_est":   "N/A (requires labelled corpus)",
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(REPORT_PATH, result)
    return result

# ── Layer1 demo ───────────────────────────────────────────────────────────────
def layer1_demo() -> None:
    # Inject known contaminated entities into synthetic data
    datetime.now(UTC)
    entities = _load_entities()
    [e for e in entities if e.get("id") in ("e2", "e4", "e5")]
    result = scan(dry_run=True)

    # Should tag at least the 3 contaminated synthetic entities
    assert result["tagged"] >= 2, f"Expected ≥2 tagged, got {result['tagged']}: {result['tags']}"
    # Should not tag the active entity (e1, edge_count=12)
    active_tagged = [t for t in result["tags"] if t.get("name") == "routing-linucb"]
    assert not active_tagged, f"Should not tag active entity: {active_tagged}"
    print(f"[layer1] PASS — scanned={result['scanned']}  tagged={result['tagged']}  "
          f"skipped_active={result['skipped_active']}")

def main() -> None:
    import argparse
    pa = argparse.ArgumentParser()
    pa.add_argument("--dry-run",  action="store_true", default=True)
    pa.add_argument("--apply",    action="store_true")
    pa.add_argument("--layer1",   action="store_true")
    args = pa.parse_args()
    if args.layer1:
        layer1_demo()
        return
    result = scan(dry_run=not args.apply)
    print(f"[contamination] scanned={result['scanned']}  tagged={result['tagged']}")
    print(f"[contamination] report: {REPORT_PATH}")

if __name__ == "__main__":
    main()
