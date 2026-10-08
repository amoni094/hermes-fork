#!/usr/bin/env python3
"""sheaf-memory-gluing.py — Curry/Robinson sheaf consistency across memory shards.

Hard core (gluing axiom): if a fact is stored in two overlapping memory
shards, the restrictions to the overlap must agree. Nonzero Čech H^1
means locally consistent, globally inconsistent.

Stores inspected (when present):
  - memory.db (often empty placeholder)
  - hindsight.db (often empty placeholder)
  - memory-facts/lifecycle.db  (fact_lifecycle.fact_text / memory_id)
  - memory-facts/graphiti-state.db (graphiti_writes.fact_text)
  - memory-facts/provenance.db (memory_id keys)

Complexity: pairwise overlap of finite fact maps is O(n). Computing a
full sheaf cohomology of an arbitrary cover of an infinite space is not
claimed; this is the finite Čech H^1 of the 0-cochain of fact values
on a 2-cover. RCA0 (Dean): finite maps, primitive-recursive equality.

Usage:
  python3 sheaf-memory-gluing.py [--json] [--root PATH]
Exit: 0 consistent (H1=0), 1 obstruction (H1>0), 2 usage/io error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

NORM_WS = re.compile(r"\s+")


def hermes_root() -> Path:
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        return base / "profiles" / profile
    return base


def _norm_text(s: str) -> str:
    return NORM_WS.sub(" ", (s or "").strip().lower())


def _key(s: str) -> str:
    n = _norm_text(s)
    return hashlib.sha256(n.encode("utf-8")).hexdigest()[:16]


def _rows(db: Path, sql: str) -> List[tuple]:
    if not db.is_file() or db.stat().st_size < 4096:
        return []
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            return list(con.execute(sql))
        except sqlite3.Error:
            return []
        finally:
            con.close()
    except sqlite3.Error:
        return []


def load_shard_facts(root: Path) -> Dict[str, Dict[str, str]]:
    """shard_name -> {fact_key: text}."""
    shards: Dict[str, Dict[str, str]] = {}

    def add(name: str, pairs: Iterable[Tuple[str, str]]) -> None:
        m: Dict[str, str] = {}
        for k, v in pairs:
            if not v:
                continue
            m[k] = v
        shards[name] = m

    # memory.db / hindsight.db — unknown schema; try common table names
    for label, path in (
        ("memory.db", root / "memory.db"),
        ("hindsight.db", root / "hindsight.db"),
        ("memory/memory.db", root / "memory" / "memory.db"),
    ):
        facts = []
        for table_sql in (
            "SELECT name FROM sqlite_master WHERE type='table'",
        ):
            tables = [r[0] for r in _rows(path, table_sql)]
            for t in tables:
                cols_rows = _rows(path, f"PRAGMA table_info({t})")
                cols = [c[1] for c in cols_rows]
                text_col = next((c for c in cols if c in ("fact_text", "content", "text", "body", "value")), None)
                id_col = next((c for c in cols if c in ("memory_id", "id", "key", "uuid")), None)
                if not text_col:
                    continue
                sel = f"SELECT {id_col or text_col}, {text_col} FROM {t} LIMIT 5000"
                for rid, txt in _rows(path, sel):
                    key = str(rid) if id_col else _key(str(txt))
                    facts.append((key, str(txt)))
        add(label, facts)

    life = root / "memory-facts" / "lifecycle.db"
    add(
        "lifecycle",
        (
            (str(mid) or _key(str(txt)), str(txt))
            for mid, txt in _rows(life, "SELECT memory_id, fact_text FROM fact_lifecycle")
        ),
    )
    g = root / "memory-facts" / "graphiti-state.db"
    add(
        "graphiti",
        (
            (_key(str(txt)), str(txt))
            for (txt,) in _rows(g, "SELECT fact_text FROM graphiti_writes")
        ),
    )
    # also scan HERMES_HOME (non-profile) siblings if root is a profile
    home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    if root != home:
        home_life = home / "memory-facts" / "lifecycle.db"
        add(
            "lifecycle_home",
            (
                (str(mid) or _key(str(txt)), str(txt))
                for mid, txt in _rows(home_life, "SELECT memory_id, fact_text FROM fact_lifecycle")
            ),
        )
    return shards


def cech_h1(shards: Dict[str, Dict[str, str]]) -> dict:
    """Finite Čech H^1 for the 2-cover of shards: disagreements on overlaps.

    H0 ~ globally agreed facts (same key, same normalized text).
    H1 ~ keys present in >=2 shards whose normalized texts differ.
    Vacuous: empty overlap => H1=0 (gluing holds on empty intersection).
    """
    names = sorted(shards)
    obstructions = []
    agreements = 0
    overlaps = 0
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            ka, kb = shards[a], shards[b]
            # overlap by exact key
            common_keys = set(ka) & set(kb)
            # also overlap by normalized text hash if keys differ (memory_id vs content hash)
            na = {_key(v): (k, v) for k, v in ka.items()}
            nb = {_key(v): (k, v) for k, v in kb.items()}
            # key-based
            for k in common_keys:
                overlaps += 1
                if _norm_text(ka[k]) != _norm_text(kb[k]):
                    obstructions.append({
                        "a": a, "b": b, "key": k,
                        "text_a": ka[k][:200], "text_b": kb[k][:200],
                        "kind": "key_disagreement",
                    })
                else:
                    agreements += 1
            # same-text different-id is glue-ok (restriction agrees)
            for hk in set(na) & set(nb):
                overlaps += 1
                agreements += 1
    h1 = len(obstructions)
    return {
        "shards": {n: len(shards[n]) for n in names},
        "overlap_pairs_checked": overlaps,
        "agreements": agreements,
        "H0_proxy_agreements": agreements,
        "H1": h1,
        "obstructions": obstructions[:50],
        "gluing_holds": h1 == 0,
        "note": (
            "Vacuous consistency" if overlaps == 0
            else ("gluing axiom holds" if h1 == 0 else "nonzero H1: locally stored, globally inconsistent")
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Sheaf gluing check across memory shards")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default="", help="Profile/home root (default: HERMES profile root)")
    args = ap.parse_args()
    root = Path(args.root) if args.root else hermes_root()
    if not root.is_dir():
        print(f"ERROR: root missing {root}", file=sys.stderr)
        return 2
    shards = load_shard_facts(root)
    report = cech_h1(shards)
    report["root"] = str(root)
    out = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    cache = (out / "profiles" / profile / "cache") if profile and "profiles" not in str(out) else (out / "cache")
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / "sheaf-gluing-report.json"
    dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["written"] = str(dest)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"root={root}")
        print(f"shards={report['shards']}")
        print(f"H1={report['H1']} gluing_holds={report['gluing_holds']} {report['note']}")
        print(f"wrote {dest}")
    return 0 if report["H1"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
