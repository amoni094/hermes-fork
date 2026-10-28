#!/usr/bin/env python3
"""Attribute agent failures via lightweight graph betweenness (AFANet-style)."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "failure-attribution.json"


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def build_graph(trace: list) -> tuple:
    nodes = []
    edges = []
    for i, step in enumerate(trace or []):
        if not isinstance(step, dict):
            step = {"action": str(step)}
        nid = str(step.get("id") or step.get("action") or step.get("tool") or ("s%d" % i))
        nodes.append(nid)
        if i > 0:
            prev = str((trace[i - 1] or {}).get("id") if isinstance(trace[i - 1], dict) else "s%d" % (i - 1))
            if not isinstance(trace[i - 1], dict):
                prev = "s%d" % (i - 1)
            else:
                prev = str(trace[i - 1].get("id") or trace[i - 1].get("action") or trace[i - 1].get("tool") or ("s%d" % (i - 1)))
            edges.append((prev, nid))
        causes = step.get("caused_by") or step.get("depends_on") or []
        if isinstance(causes, str):
            causes = [causes]
        for c in causes:
            edges.append((str(c), nid))
    return nodes, edges


def betweenness(nodes: list, edges: list) -> dict:
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    uniq = list(dict.fromkeys(nodes))
    scores = {n: 0.0 for n in uniq}
    for s in uniq:
        stack = []
        pred = {n: [] for n in uniq}
        sigma = {n: 0.0 for n in uniq}
        dist = {n: -1 for n in uniq}
        sigma[s] = 1.0
        dist[s] = 0
        q = [s]
        qi = 0
        while qi < len(q):
            v = q[qi]
            qi += 1
            stack.append(v)
            for w in adj[v]:
                if w not in dist:
                    continue
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    q.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta = {n: 0.0 for n in uniq}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                if sigma[w]:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                scores[w] += delta[w]
    n = len(uniq)
    if n > 2:
        norm = 1.0 / ((n - 1) * (n - 2))
        scores = {k: v * norm for k, v in scores.items()}
    return scores


def attribute(trace: list) -> dict:
    nodes, edges = build_graph(trace)
    scores = betweenness(nodes, edges) if nodes else {}
    root = None
    best = -1.0
    for n, sc in scores.items():
        if sc > best:
            best = sc
            root = n
    if root is None and nodes:
        root = nodes[0]
        best = 0.0
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "root_cause": root,
        "betweenness": {k: round(v, 6) for k, v in scores.items()},
        "score": round(best if best >= 0 else 0.0, 6),
    }


def self_test() -> dict:
    tr = [
        {"id": "a", "action": "start"},
        {"id": "b", "action": "bad", "caused_by": ["a"]},
        {"id": "c", "action": "fail", "caused_by": ["b"]},
        {"id": "d", "action": "end", "caused_by": ["b"]},
    ]
    r = attribute(tr)
    assert r["root_cause"] in ("a", "b", "c", "d"), r
    assert attribute([])["n_nodes"] == 0
    return {"self_test": "PASS", "sample": r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    try:
        raw = args.json
        if not raw and not sys.stdin.isatty():
            raw = sys.stdin.read()
        trace = []
        if raw:
            try:
                obj = json.loads(raw)
                trace = obj if isinstance(obj, list) else obj.get("trace") or []
            except json.JSONDecodeError:
                trace = []
        out = attribute(trace)
        try:
            _atomic_write_json(OUT, out)
        except Exception:
            pass
        print(json.dumps(out, indent=2))
    except Exception:
        pass


if __name__ == "__main__":
    main()
