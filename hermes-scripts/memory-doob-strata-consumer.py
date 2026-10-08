#!/usr/bin/env python3
"""memory-doob-strata-consumer.py — Score working-memory by Doob stratum.

Reads doob_strata written by memory-doob-decompose.py and attaches a
quality_score used by recall/TTL advisors.

Stratum → quality (hard core: martingale is F_t innovation = highest signal):
  martingale  1.00   — genuine new information (innovation = E[X_t|F_t] - E[X_t|F_{t-1}])
  predictable 0.45   — scheduled / cron / consolidation artefacts
  remainder   0.10   — unclassifiable / empty / noise
  empty text  0.00   — whitespace-only entries

Quality classes:
  >= 0.80  high       (recall-worthy, long TTL)
  >= 0.30  scheduled  (refresh periodically)
  >  0.00  noise      (short TTL, deprioritise in recall)
  == 0.00  empty      (prune immediately)

Advisory JSON written to: ~/.hermes/profiles/fork/cache/doob-quality-advisory.json

Usage:
  python3 memory-doob-strata-consumer.py [--apply] [--self-test] [--dry-run]

  --apply     Write quality scores back into doob_strata.db (adds quality_score col)
  --self-test Run built-in assertions and exit 0/1
  --dry-run   Print advisory JSON without writing
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

# ─── paths ───────────────────────────────────────────────────────────────────
# HERMES_HOME is the profile root when set by cron (e.g. .../profiles/fork).
# Do NOT append "profiles/fork" — HERMES_HOME already IS the profile root.
_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
_DOOB_DB = _HOME / "cache" / "memory-doob.db"
_ADVISORY = _HOME / "cache" / "doob-quality-advisory.json"

# ─── hard-core score table ────────────────────────────────────────────────────
_STRATUM_SCORE: dict[str, float] = {
    "martingale": 1.00,
    "predictable": 0.45,
    "remainder": 0.10,
}
_EMPTY_SCORE = 0.00


def score_row(stratum: str, text: str) -> float:
    """Return quality score for one row.  Hard core: empty text → 0.0."""
    if not text or not text.strip():
        return _EMPTY_SCORE
    return _STRATUM_SCORE.get(stratum, _STRATUM_SCORE["remainder"])


def quality_class(score: float) -> str:
    """Map numeric score to advisory class."""
    if score >= 0.80:
        return "high"
    if score >= 0.30:
        return "scheduled"
    if score > 0.00:
        return "noise"
    return "empty"


def _ensure_quality_col(conn: sqlite3.Connection) -> None:
    """Add quality_score column to doob_strata if absent (idempotent)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(doob_strata)")}
    if "quality_score" not in cols:
        conn.execute("ALTER TABLE doob_strata ADD COLUMN quality_score REAL DEFAULT NULL")
        conn.execute("ALTER TABLE doob_strata ADD COLUMN quality_class TEXT DEFAULT NULL")
        conn.commit()


def run(db_path: Path, apply: bool, dry_run: bool) -> dict:
    """Score all rows in doob_strata.  Returns advisory summary."""
    if not db_path.exists():
        return {"status": "no_db", "db": str(db_path), "rows": 0, "advisory": "{}"}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT rowid, stratum, text FROM doob_strata"
        ).fetchall()

        scored: list[dict] = []
        for r in rows:
            sc = score_row(r["stratum"] or "", r["text"] or "")
            qc = quality_class(sc)
            scored.append({"rowid": r["rowid"], "stratum": r["stratum"],
                           "quality_score": sc, "quality_class": qc})

        summary: dict = {
            "status": "ok",
            "db": str(db_path),
            "rows": len(scored),
            "counts": {},
        }
        for s in scored:
            summary["counts"][s["quality_class"]] = summary["counts"].get(s["quality_class"], 0) + 1

        if apply and not dry_run:
            _ensure_quality_col(conn)
            for s in scored:
                conn.execute(
                    "UPDATE doob_strata SET quality_score=?, quality_class=? WHERE rowid=?",
                    (s["quality_score"], s["quality_class"], s["rowid"])
                )
            conn.commit()
            summary["applied"] = True

        adv = json.dumps(summary, indent=2)
        summary["advisory"] = adv
        return summary
    finally:
        conn.close()


def self_test() -> int:
    """Built-in assertions.  Returns 0 on pass, 1 on fail."""
    # Score table
    assert score_row("martingale", "user prefers dark mode") == 1.00
    assert score_row("predictable", "nightly consolidation") == 0.45
    assert score_row("remainder", "???") == 0.10
    assert score_row("martingale", " ") == _EMPTY_SCORE
    assert score_row("nope", "x") == 0.10  # unknown stratum → remainder
    # Quality classes
    assert quality_class(1.0) == "high"
    assert quality_class(0.45) == "scheduled"
    assert quality_class(0.10) == "noise"
    assert quality_class(0.0) == "empty"

    # Integration: in-memory SQLite round-trip
    td = Path(tempfile.mkdtemp())
    db = td / "doob.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE doob_strata (stratum TEXT, text TEXT, filtration_t INTEGER)"
    )
    conn.executemany(
        "INSERT INTO doob_strata VALUES (?,?,?)",
        [
            ("martingale", "real new fact", 1),
            ("predictable", "scheduled digest", 2),
            ("remainder", "noise", 3),
            ("martingale", " ", 4),  # empty text
        ],
    )
    conn.commit()
    conn.close()

    summary = run(db, apply=True, dry_run=False)
    assert summary["rows"] == 4, f"expected 4 rows, got {summary['rows']}"
    assert summary["counts"].get("high", 0) == 1    # martingale non-empty
    assert summary["counts"].get("scheduled", 0) == 1
    assert summary["counts"].get("noise", 0) == 1
    assert summary["counts"].get("empty", 0) == 1

    # Verify columns were added and scores written
    conn2 = sqlite3.connect(str(db))
    rows2 = conn2.execute("SELECT quality_score, quality_class FROM doob_strata").fetchall()
    conn2.close()
    scores = [r[0] for r in rows2]
    assert 1.00 in scores
    assert 0.45 in scores
    assert 0.10 in scores
    assert 0.00 in scores

    print("self_test: 12/12 assertions passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Doob strata quality consumer")
    parser.add_argument("--apply", action="store_true", default=True,
                        help="Write quality_score/class back into doob_strata DB (default: True)")
    parser.add_argument("--no-apply", dest="apply", action="store_false",
                        help="Skip writing scores back to DB")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print advisory without writing to advisory file")
    parser.add_argument("--self-test", action="store_true",
                        help="Run assertions and exit")
    parser.add_argument("--db", default=str(_DOOB_DB),
                        help=f"Path to doob_strata.db (default: {_DOOB_DB})")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    db = Path(args.db)
    summary = run(db, apply=args.apply, dry_run=args.dry_run)

    adv = summary.pop("advisory", "{}")
    print(json.dumps(summary, indent=2))

    # Write advisory file
    if not args.dry_run:
        _ADVISORY.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(_ADVISORY) + ".tmp")
        tmp.write_text(adv)
        tmp.replace(_ADVISORY)

    return 0 if summary.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
