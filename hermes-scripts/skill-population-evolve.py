#!/usr/bin/env python3
"""CyberEvolver-style skill scaffold population (local variants, no live skill writes)."""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import random
import sqlite3
import statistics
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
_lifecycle_home = _hermes_base.parent.parent if _hermes_base.parent.name == "profiles" else _hermes_base
LIFECYCLE_DB = _lifecycle_home / "memory-facts" / "lifecycle.db"
CACHE = _hermes_root / "cache"

OUT_PATH = CACHE / "skill-population-state.json"
VARIANTS_DB = CACHE / "skill-variants.db"

def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    tmp = path.with_name(path.name + ".tmp")
    payload = json.dumps(obj, indent=2) + "\n"
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _connect(db: Path):
    conn = sqlite3.connect(str(db), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


SCHEMA = (
    "CREATE TABLE IF NOT EXISTS variants ("
    "variant_id TEXT PRIMARY KEY, skill_id TEXT, prompt_text TEXT, tool_order TEXT, "
    "mutated_at TEXT, success_count INT, failure_count INT, last_active_epoch INT)"
)


def _open_variants(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def hamming(a: str, b: str) -> float:
    n = max(len(a), len(b), 1)
    m = min(len(a), len(b))
    mism = sum(1 for i in range(m) if a[i] != b[i]) + abs(len(a) - len(b))
    return mism / n


def mutate_order(order: str, rng) -> str:
    parts = [p for p in order.split(",") if p]
    if len(parts) < 2:
        parts = parts + ["read_file", "terminal"]
    i, j = rng.randrange(len(parts)), rng.randrange(len(parts))
    parts[i], parts[j] = parts[j], parts[i]
    return ",".join(parts)


def seed_from_logs(conn, db_path: Path, epoch: int):
    if not db_path.exists():
        return 0
    lc = _connect(db_path)
    try:
        rows = lc.execute(
            "SELECT tool_name, outcome FROM tool_review_log ORDER BY id DESC LIMIT 2000"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        lc.close()
    counts = defaultdict(lambda: [0, 0])
    for name, outcome in rows:
        if not name or name == "ue_blackbox":
            continue
        ok = str(outcome).lower() in ("ok", "success", "true", "1", "pass")
        if ok:
            counts[str(name)][0] += 1
        else:
            counts[str(name)][1] += 1
    n = 0
    for skill, (s, f) in counts.items():
        vid = skill + ":base"
        conn.execute(
            "INSERT OR REPLACE INTO variants(variant_id, skill_id, prompt_text, tool_order, "
            "mutated_at, success_count, failure_count, last_active_epoch) VALUES (?,?,?,?,?,?,?,?)",
            (vid, skill, "", skill, _now(), int(s), int(f), int(epoch)),
        )
        n += 1
    conn.commit()
    return n


def evolve(conn, epoch: int, rng=None):
    rng = rng or random.Random(epoch)
    rows = conn.execute(
        "SELECT variant_id, skill_id, tool_order, success_count, failure_count FROM variants"
    ).fetchall()
    if not rows:
        return 0
    by_skill = defaultdict(list)
    for vid, sid, order, s, f in rows:
        tot = (s or 0) + (f or 0)
        rate = (s or 0) / tot if tot else 0.0
        by_skill[sid].append((rate, vid, order or sid, s or 0, f or 0))
    created = 0
    for sid, items in by_skill.items():
        items.sort(reverse=True)
        best = items[0]
        if best[0] < 0.1:
            continue
        new_order = mutate_order(best[2], rng)
        vid = sid + ":e" + str(epoch) + ":" + uuid.uuid4().hex[:8]
        conn.execute(
            "INSERT OR REPLACE INTO variants(variant_id, skill_id, prompt_text, tool_order, "
            "mutated_at, success_count, failure_count, last_active_epoch) VALUES (?,?,?,?,?,?,?,?)",
            (vid, sid, "", new_order, _now(), 0, 0, int(epoch)),
        )
        created += 1
    conn.commit()
    return created


def diversity(conn) -> float:
    orders = [r[0] or "" for r in conn.execute("SELECT tool_order FROM variants").fetchall()]
    if len(orders) < 2:
        return 0.0
    acc = 0.0
    n = 0
    for i in range(len(orders)):
        for j in range(i + 1, len(orders)):
            acc += hamming(orders[i], orders[j])
            n += 1
    return acc / n if n else 0.0


def snapshot(conn, epoch: int) -> dict:
    rows = conn.execute(
        "SELECT skill_id, variant_id, success_count, failure_count, tool_order FROM variants"
    ).fetchall()
    pop = defaultdict(list)
    for sid, vid, s, f, order in rows:
        tot = (s or 0) + (f or 0)
        rate = (s or 0) / tot if tot else 0.0
        pop[sid].append({"variant_id": vid, "rate": rate, "n": tot, "tool_order": order})
    best = {}
    for sid, items in pop.items():
        items.sort(key=lambda x: x["rate"], reverse=True)
        best[sid] = items[0]
    if not pop:
        return {"ts": _now(), "status": "insufficient_data", "epoch": epoch, "n_skills": 0, "diversity": 0.0}
    return {
        "ts": _now(),
        "status": "ok",
        "epoch": epoch,
        "n_skills": len(pop),
        "n_variants": sum(len(v) for v in pop.values()),
        "diversity": diversity(conn),
        "best": best,
        "note": "Variants live in cache DB only; live SKILL.md files are never written.",
    }


def run(out_path=None, variants_db=None, lifecycle=None, epoch=None):
    dest = out_path or OUT_PATH
    vdb = variants_db or VARIANTS_DB
    lc = lifecycle or LIFECYCLE_DB
    ep = int(epoch if epoch is not None else datetime.now(UTC).timestamp() // 3600)
    try:
        conn = _open_variants(vdb)
        try:
            seed_from_logs(conn, lc, ep)
            evolve(conn, ep)
            report = snapshot(conn, ep)
        finally:
            conn.close()
        _atomic_write_json(dest, report)
        return report
    except Exception as exc:
        err = {"ts": _now(), "status": "error", "error": str(exc)}
        try:
            _atomic_write_json(dest, err)
        except Exception:
            pass
        return err


def _self_test():
    tmp = Path(tempfile.mkdtemp(prefix="evo-"))
    out = tmp / ("skill-population-state_test_" + uuid.uuid4().hex + ".json")
    vdb = tmp / "skill-variants.db"
    conn = _open_variants(vdb)
    conn.execute(
        "INSERT INTO variants VALUES (?,?,?,?,?,?,?,?)",
        ("t:base", "t", "", "a,b,c", _now(), 10, 1, 1),
    )
    conn.commit()
    n = evolve(conn, 2, rng=random.Random(0))
    assert n >= 1
    d = diversity(conn)
    assert d >= 0.0
    conn.close()
    r = run(out_path=out, variants_db=vdb, lifecycle=tmp / "no.db", epoch=3)
    assert out.exists()
    json.loads(out.read_text())
    print("[skill-population-evolve] --self-test PASS diversity={:.3f} status={}".format(d, r.get("status")))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print("[skill-population-evolve] --self-test FAIL:", exc)
            return 1
    report = run()
    print(json.dumps({"status": report.get("status"), "n_skills": report.get("n_skills"), "diversity": report.get("diversity")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
