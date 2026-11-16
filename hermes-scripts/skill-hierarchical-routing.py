#!/usr/bin/env python3
"""Hierarchical coarse-to-fine skill routing with session trajectory state."""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import sqlite3
import sys
import tempfile
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_raw_home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_base = _raw_home
if _hermes_base.name != ".hermes" and _hermes_base.parent.name == "profiles":
    _hermes_base = _hermes_base.parent.parent
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
if not _hermes_profile and _raw_home.parent.name == "profiles":
    _hermes_profile = _raw_home.name
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
CACHE = _hermes_root / "cache"
LIFECYCLE_DB = _hermes_base / "memory-facts" / "lifecycle.db"
UE_SENTINEL = "ue_blackbox"
EPS = 1e-12


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    tmp = path.with_name(path.name + ".tmp")
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _connect(db: Path):
    conn = sqlite3.connect(str(db), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _iter_jsonl(path: Path, max_rows: int | None = None):
    if not path.exists():
        return
    n = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                yield rec
                n += 1
                if max_rows is not None and n >= max_rows:
                    return
    except OSError:
        return


def _clip01(x: float) -> float:
    if not math.isfinite(x):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


OUT_PATH = CACHE / "skill-trajectory-state.json"
GRAPH = CACHE / "skill-graph.json"
EVENTS = CACHE / "routing-events.jsonl"


def load_graph():
    nodes = []
    edges = []
    if GRAPH.exists():
        try:
            g = json.loads(GRAPH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            g = {}
        raw_n = g.get("nodes") or []
        for n in raw_n:
            if isinstance(n, str):
                nodes.append(n)
            elif isinstance(n, dict):
                name = n.get("id") or n.get("name") or n.get("skill")
                if name:
                    nodes.append(str(name))
        for e in g.get("edges") or []:
            if isinstance(e, dict):
                a = e.get("source") or e.get("src")
                b = e.get("target") or e.get("dst")
                if a and b:
                    edges.append((str(a), str(b)))
    return nodes, edges


def clusters(nodes, edges):
    # union-find on graph, fallback to name prefix
    parent = {n: n for n in nodes}
    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for a, b in edges:
        if a not in parent:
            parent[a] = a
        if b not in parent:
            parent[b] = b
        union(a, b)
    groups = defaultdict(list)
    for n in parent:
        groups[find(n)].append(n)
    # if graph is too fragmented, also tag prefix
    tagged = {}
    for root, members in groups.items():
        pref = members[0].split("-", 1)[0] if members else "other"
        for m in members:
            tagged[m] = pref if len(members) == 1 else ("cc:" + str(root)[:24])
    return tagged, groups


def load_traj():
    traj = []
    for rec in _iter_jsonl(EVENTS):
        s = rec.get("top_skill") or rec.get("skill")
        if s:
            traj.append(str(s))
    db = LIFECYCLE_DB
    if db.exists():
        conn = _connect(db)
        try:
            tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "anytime_eval_log" in tabs:
                rows = conn.execute(
                    "SELECT skill_id FROM anytime_eval_log WHERE skill_id IS NOT NULL "
                    "ORDER BY id DESC LIMIT 200"
                ).fetchall()
                extra = []
                for (skill,) in rows:
                    s = str(skill or "").strip()
                    if s and not s.startswith("audit"):
                        extra.append(s)
                traj = list(reversed(extra)) + traj
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    return traj[-50:]


def route_state(nodes, edges, traj) -> dict:
    if not nodes:
        return {"status": "insufficient_data", "n": 0, "ts": _now()}
    tagged, groups = clusters(nodes, edges)
    n_full = max(len(nodes), 1)
    recent_clusters = []
    for s in traj[-8:]:
        recent_clusters.append(tagged.get(s, s.split("-", 1)[0]))
    # coarse-to-fine candidate cap: members of recent clusters, else 15% of library
    cand = set()
    for c in recent_clusters:
        for n, tag in tagged.items():
            if tag == c:
                cand.add(n)
    cap = max(8, int(0.15 * n_full))
    if len(cand) > cap:
        # keep those appearing in traj first
        prefer = [s for s in traj if s in cand]
        rest = [n for n in cand if n not in prefer]
        cand_list = (prefer + rest)[:cap]
    else:
        cand_list = list(cand)[:cap] if cand else nodes[:cap]
    frac = len(cand_list) / n_full
    return {
        "ts": _now(),
        "status": "ok",
        "n_library": n_full,
        "n_clusters": len(groups),
        "n_candidates": len(cand_list),
        "candidate_frac": frac,
        "kill_test_pass": frac <= 0.70,  # coarse filter must beat full enum
        "recent_trajectory": traj[-8:],
        "recent_clusters": recent_clusters[-8:],
        "candidates": cand_list[:40],
    }


def run(out_path: Path | None = None) -> dict:
    out_path = out_path or OUT_PATH
    nodes, edges = load_graph()
    result = route_state(nodes, edges, load_traj())
    if result.get("status") != "insufficient_data":
        _atomic_write(out_path, result)
    return result


def _self_test() -> int:
    nodes = ["alpha-a", "alpha-b", "beta-a", "beta-b", "gamma-a"]
    edges = [("alpha-a", "alpha-b"), ("beta-a", "beta-b")]
    traj = ["alpha-a", "alpha-b", "alpha-a"]
    r = route_state(nodes, edges, traj)
    assert r["status"] == "ok"
    assert r["n_candidates"] <= r["n_library"]
    empty = route_state([], [], [])
    assert empty["status"] == "insufficient_data"
    tmp = Path(tempfile.mkdtemp()) / ("skill-trajectory-state_" + uuid.uuid4().hex + ".json")
    _atomic_write(tmp, r)
    json.loads(tmp.read_text())
    tmp.unlink(missing_ok=True)
    print("[skill-hierarchical-routing] --self-test PASS cand={}/{}".format(r["n_candidates"], r["n_library"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Hierarchical skill routing")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[skill-hierarchical-routing] --self-test FAIL: {exc}")
            return 1
    try:
        print(json.dumps(run()))
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
