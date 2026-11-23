#!/usr/bin/env python3
"""memory-doob-decompose.py — Doob decomposition of working-memory entries.

Williams, Probability with Martingales: every integrable adapted process X
admits a unique decomposition X = M + A where M is a martingale and A is
predictable (A_t is F_{t-1}-measurable). Remainder absorbs non-integrable
or unclassifiable mass.

Strata:
  predictable — cron-scheduled / consolidation writes (A_t known before t)
  martingale  — innovation at t, computed from F_t only (no future peeking)
  remainder   — unsigned, untimestamped, or unclassifiable

Hard core: the martingale stratum is F_t-measurable. Classification of an
entry at filtration time t never reads rows with ts > t.

Store: <profile-or-home>/cache/memory-doob.db  (WAL)

Usage:
  python3 memory-doob-decompose.py --scan
  python3 memory-doob-decompose.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PREDICTABLE_SOURCES = frozenset({
    "cron", "gmemory", "consolidation", "ttl-purge", "buffer-flush",
    "l1-gmemory", "nightly", "scheduled",
})


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def profile_root() -> Path:
    hh = hermes_home()
    hp = os.environ.get("HERMES_PROFILE", "").strip()
    return (hh / "profiles" / hp) if hp else hh


def cache_dir() -> Path:
    d = profile_root() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return cache_dir() / "memory-doob.db"


def wm_dir() -> Path:
    # Match working-memory.py: HERMES_HOME/cache/working-memory
    return hermes_home() / "cache" / "working-memory"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS doob_strata (
            memory_id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            text TEXT,
            martingale TEXT,
            predictable TEXT,
            remainder TEXT,
            stratum TEXT NOT NULL CHECK(stratum IN ('martingale','predictable','remainder')),
            filtration_t TEXT NOT NULL,
            source TEXT
        )
        """
    )
    return conn


def _entry_ts(entry: dict[str, Any], fallback: str) -> str:
    for k in ("ts", "updated_at", "created_at", "timestamp"):
        v = entry.get(k)
        if isinstance(v, str) and v:
            return v
        if isinstance(v, (int, float)) and v > 0:
            return datetime.fromtimestamp(float(v), tz=timezone.utc).isoformat()
    return fallback


def _source_blob(entry: dict[str, Any]) -> str:
    parts = []
    for k in ("source", "src", "origin", "authority", "type"):
        v = entry.get(k)
        if v:
            parts.append(str(v).lower())
    text = str(entry.get("text") or entry.get("content") or entry.get("goal") or "")
    parts.append(text.lower()[:200])
    return " ".join(parts)


def is_predictable_source(blob: str) -> bool:
    b = blob.lower()
    return any(tok in b for tok in PREDICTABLE_SOURCES)


def filtration_at(entries: list[dict[str, Any]], t: str) -> list[dict[str, Any]]:
    """F_t: entries with ts <= t. Hard core — no future peeking."""
    out = []
    for e in entries:
        ts = str(e.get("_ts") or "")
        if ts <= t:
            out.append(e)
    return out


def classify_one(entry: dict[str, Any], past: list[dict[str, Any]]) -> str:
    """Classify using only F_t = past (ts <= entry ts)."""
    blob = _source_blob(entry)
    if is_predictable_source(blob):
        return "predictable"
    text = str(entry.get("text") or entry.get("content") or entry.get("goal") or "").strip()
    if not text and not entry.get("progress") and not entry.get("beliefs"):
        return "remainder"
    # Innovation: content not already present in F_{t-}
    prior_texts = set()
    for p in past:
        if p is entry:
            continue
        prior_texts.add(str(p.get("text") or p.get("content") or p.get("goal") or "").strip())
    if text and text in prior_texts:
        return "predictable"
    if text or entry.get("beliefs") or entry.get("progress"):
        return "martingale"
    return "remainder"


def flatten_wm_doc(doc: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    sid = str(doc.get("session_id") or path.stem)
    ts = _entry_ts(doc, now_iso())
    rows: list[dict[str, Any]] = []
    base = {
        "session_id": sid,
        "source": "working-memory",
        "_ts": ts,
        "updated_at": doc.get("updated_at"),
    }
    rows.append({**base, "memory_id": f"wm:{sid}:goal", "text": str(doc.get("goal") or ""), "type": "goal"})
    for i, item in enumerate(doc.get("progress") or []):
        rows.append({**base, "memory_id": f"wm:{sid}:progress:{i}", "text": str(item), "type": "progress"})
    for i, item in enumerate(doc.get("constraints") or []):
        rows.append({
            **base,
            "memory_id": f"wm:{sid}:constraint:{i}",
            "text": json.dumps(item, sort_keys=True) if not isinstance(item, str) else item,
            "type": "constraint",
            "source": str((item or {}).get("authority") if isinstance(item, dict) else "working-memory"),
        })
    beliefs = doc.get("beliefs") or {}
    if isinstance(beliefs, dict):
        for k, v in beliefs.items():
            text = v.get("text") if isinstance(v, dict) else str(v)
            src = v.get("source") if isinstance(v, dict) else "belief"
            bts = v.get("created_at") if isinstance(v, dict) else ts
            rows.append({
                **base,
                "memory_id": f"wm:{sid}:belief:{k}",
                "text": str(text or ""),
                "type": "belief",
                "source": str(src or "belief"),
                "_ts": str(bts or ts),
            })
    return rows


def load_wm_entries() -> list[dict[str, Any]]:
    d = wm_dir()
    if not d.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for p in sorted(d.glob("*.json")):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(doc, dict):
                entries.extend(flatten_wm_doc(doc, p))
        except Exception:
            continue
    return entries


def decompose(entries: list[dict[str, Any]], filtration_t: str | None = None) -> list[dict[str, Any]]:
    """Doob-decompose. Martingale labels use only F_t (ts <= filtration_t or entry ts)."""
    t = filtration_t or now_iso()
    dated = []
    for e in entries:
        e = dict(e)
        e["_ts"] = _entry_ts(e, t)
        dated.append(e)
    dated.sort(key=lambda x: x["_ts"])
    out = []
    for i, e in enumerate(dated):
        if e["_ts"] > t:
            # Not in F_t — remainder until observed
            local_t = t
            past = filtration_at(dated, t)
            stratum = "remainder"
        else:
            local_t = e["_ts"]
            past = filtration_at(dated[: i + 1], local_t)
            # Hard core: never include future
            if any(p["_ts"] > local_t for p in past):
                raise AssertionError("future peeking in filtration")
            stratum = classify_one(e, past)
        text = str(e.get("text") or "")
        rec = {
            "memory_id": str(e.get("memory_id") or f"anon:{i}"),
            "ts": e["_ts"],
            "text": text,
            "martingale": text if stratum == "martingale" else "",
            "predictable": text if stratum == "predictable" else "",
            "remainder": text if stratum == "remainder" else "",
            "stratum": stratum,
            "filtration_t": local_t,
            "source": str(e.get("source") or ""),
        }
        out.append(rec)
    return out


def persist(rows: list[dict[str, Any]], path: Path | None = None) -> int:
    conn = _connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        n = 0
        for r in rows:
            conn.execute(
                """
                INSERT INTO doob_strata
                  (memory_id, ts, text, martingale, predictable, remainder, stratum, filtration_t, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(memory_id) DO UPDATE SET
                  ts=excluded.ts, text=excluded.text, martingale=excluded.martingale,
                  predictable=excluded.predictable, remainder=excluded.remainder,
                  stratum=excluded.stratum, filtration_t=excluded.filtration_t, source=excluded.source
                """,
                (r["memory_id"], r["ts"], r["text"], r["martingale"], r["predictable"],
                 r["remainder"], r["stratum"], r["filtration_t"], r["source"]),
            )
            n += 1
        conn.commit()
        return n
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def property_no_future_peek(rows: list[dict[str, Any]]) -> None:
    for r in rows:
        if r["stratum"] == "martingale" and r["ts"] > r["filtration_t"]:
            raise AssertionError(f"martingale used future: {r['memory_id']}")
        if r["filtration_t"] < r["ts"] and r["stratum"] == "martingale":
            raise AssertionError("filtration_t before observation for martingale")


def property_partition(rows: list[dict[str, Any]]) -> None:
    for r in rows:
        filled = sum(1 for k in ("martingale", "predictable", "remainder") if r.get(k))
        if r.get("text") and filled != 1:
            raise AssertionError(f"not a partition: {r['memory_id']} filled={filled}")
        if r["stratum"] not in ("martingale", "predictable", "remainder"):
            raise AssertionError("bad stratum")


def self_test() -> int:
    # Synthetic timeline: cron at t1, user innovation at t2, duplicate at t3
    entries = [
        {"memory_id": "a", "ts": "2026-01-01T00:00:00+00:00", "text": "nightly consolidation insight", "source": "cron"},
        {"memory_id": "b", "ts": "2026-01-01T01:00:00+00:00", "text": "user prefers dark mode", "source": "user"},
        {"memory_id": "c", "ts": "2026-01-01T02:00:00+00:00", "text": "user prefers dark mode", "source": "tool"},
        {"memory_id": "d", "ts": "2026-01-01T03:00:00+00:00", "text": "", "source": ""},
        {"memory_id": "future", "ts": "2099-01-01T00:00:00+00:00", "text": "should not leak into past", "source": "user"},
    ]
    # Classify at t = t2: future must be excluded from past of b
    t2 = "2026-01-01T01:00:00+00:00"
    dated = []
    for e in entries:
        e = dict(e)
        e["_ts"] = e["ts"]
        dated.append(e)
    past = filtration_at(dated, t2)
    ids = {p["memory_id"] for p in past}
    assert "future" not in ids, "F_t peeked into future"
    assert "a" in ids and "b" in ids
    rows = decompose(entries, filtration_t="2026-01-01T03:00:00+00:00")
    by = {r["memory_id"]: r["stratum"] for r in rows if r["memory_id"] != "future"}
    assert by["a"] == "predictable", by
    assert by["b"] == "martingale", by
    assert by["c"] == "predictable", by  # already in F_{t-}
    assert by["d"] == "remainder", by
    property_no_future_peek(rows)
    property_partition([r for r in rows if r["memory_id"] != "future"])
    # Isolated DB
    import tempfile
    td = Path(tempfile.mkdtemp())
    persist(rows, td / "doob.db")
    conn = sqlite3.connect(str(td / "doob.db"))
    n = conn.execute("SELECT COUNT(*) FROM doob_strata").fetchone()[0]
    conn.close()
    assert n == len(rows)
    print("PASS memory-doob-decompose self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", action="store_true", help="Scan working-memory JSON and persist strata")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        entries = load_wm_entries()
        rows = decompose(entries)
        n = persist(rows) if args.scan else 0
        summary = {
            "n": len(rows),
            "persisted": n,
            "counts": {
                "martingale": sum(1 for r in rows if r["stratum"] == "martingale"),
                "predictable": sum(1 for r in rows if r["stratum"] == "predictable"),
                "remainder": sum(1 for r in rows if r["stratum"] == "remainder"),
            },
            "db": str(db_path()),
        }
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"[doob] {summary['n']} entries → {summary['counts']} db={summary['db']}")
        return 0
    except Exception as exc:
        print(f"[doob] fail-open: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
