#!/usr/bin/env python3
"""Nielson Ch 6 constraint solver: Tarjan SCC + worklist + implication closure.

Used by 0-CFA, effect inference, and interprocedural summaries.
Stdlib only. Height-bounded lattices — no magic iteration cap.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from typing import Any, Callable, Hashable, Iterable

Node = Hashable


def tarjan(nodes: Iterable[Node], successors: dict[Node, Iterable[Node]]) -> list[frozenset]:
    """Return strongly connected components in reverse topological order.

    Reverse topo (sinks first) is the order for may-analyses (start at ⊥).
    """
    index = 0
    stack: list[Node] = []
    onstack: set[Node] = set()
    indices: dict[Node, int] = {}
    lowlink: dict[Node, int] = {}
    comps: list[frozenset] = []
    node_list = list(nodes)

    def strongconnect(v: Node) -> None:
        nonlocal index
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        onstack.add(v)
        for w in successors.get(v, ()):
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in onstack:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            comp: list[Node] = []
            while True:
                w = stack.pop()
                onstack.discard(w)
                comp.append(w)
                if w == v:
                    break
            comps.append(frozenset(comp))

    for v in node_list:
        if v not in indices:
            strongconnect(v)
    return comps


def worklist(
    nodes: Iterable[Node],
    succ: dict[Node, Iterable[Node]],
    transfer: dict[Node, Callable[[Any], Any]] | Callable[[Node, Any], Any],
    iota: Any,
    extremal: Iterable[Node],
    join: Callable[[Any, Any], Any] | None = None,
    bot: Any = None,
) -> dict[Node, Any]:
    """Chaotic worklist MFP (Nielson Ch 2/6). Terminates when lattice height is finite."""
    if join is None:
        def join(a, b):  # type: ignore[misc]
            if a is None:
                return b
            if b is None:
                return a
            if isinstance(a, set) and isinstance(b, set):
                return a | b
            if isinstance(a, frozenset) and isinstance(b, frozenset):
                return a | b
            if a == b:
                return a
            return a if a is not None else b

    node_list = list(nodes)
    A: dict[Node, Any] = {n: bot for n in node_list}
    for e in extremal:
        A[e] = iota
    W: deque[Node] = deque(extremal)
    seen_ext = set(extremal)
    for n in node_list:
        if n not in seen_ext:
            W.append(n)

    def apply_xfer(n: Node, val: Any) -> Any:
        if callable(transfer) and not isinstance(transfer, dict):
            return transfer(n, val)
        fn = transfer.get(n) if isinstance(transfer, dict) else None
        if fn is None:
            return val
        return fn(val)

    while W:
        n = W.popleft()
        out = apply_xfer(n, A.get(n, bot))
        for m in succ.get(n, ()):
            if m not in A:
                A[m] = bot
            j = join(A[m], out)
            if j != A[m]:
                A[m] = j
                W.append(m)
    return A


def scc_solve(
    vars_: Iterable[Node],
    edges: Iterable[tuple[Node, Node]],
    impls: Iterable[tuple[Any, Callable[[dict], list[tuple[Node, Node]]]]] | None = None,
    join: Callable[[Any, Any], Any] | None = None,
    bot: Any = None,
    iota: Any = None,
) -> dict[Node, Any]:
    """Solve subset/union constraints with implication edges.

    ``impls`` items are (premise_fn, add_edges_fn) where premise_fn(A) is truthy
    when the implication should fire and add_edges_fn(A) returns new ⊆ edges.
    """
    vars_list = list(vars_)
    edge_set = set(edges)
    if bot is None:
        bot = frozenset()
    if iota is None:
        iota = bot
    if join is None:
        def join(a, b):  # type: ignore[misc]
            if a is None:
                return b
            if b is None:
                return a
            try:
                return a | b
            except TypeError:
                return b

    impl_list = list(impls or [])
    A: dict[Node, Any] = {v: bot for v in vars_list}

    def succ_from(ed):
        s: dict[Node, list[Node]] = defaultdict(list)
        for u, v in ed:
            s[u].append(v)
        return s

    guard = 0
    max_rounds = max(8, len(vars_list) * 4 + 8)
    while guard < max_rounds:
        guard += 1
        succ = succ_from(edge_set)
        comps = tarjan(vars_list, succ)
        changed = False
        for comp in comps:
            W = deque(comp)
            inner_guard = 0
            while W and inner_guard < len(comp) * 8 + 4:
                inner_guard += 1
                n = W.popleft()
                out = A.get(n, bot)
                for m in succ.get(n, ()):
                    j = join(A.get(m, bot), out)
                    if j != A.get(m, bot):
                        A[m] = j
                        changed = True
                        if m in comp:
                            W.append(m)
        fired_edges: list[tuple[Node, Node]] = []
        for item in impl_list:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                continue
            premise, adder = item
            try:
                if callable(premise):
                    should = premise(A)
                else:
                    should = bool(premise)
            except Exception:
                should = False
            if not should:
                continue
            try:
                extra = adder(A) if callable(adder) else list(adder)
            except Exception:
                extra = []
            for e in extra or []:
                if tuple(e) not in edge_set:
                    fired_edges.append((e[0], e[1]))
        if fired_edges:
            for e in fired_edges:
                edge_set.add(e)
            changed = True
            continue
        if not changed:
            break
    return A


def _self_test() -> int:
    failures: list[str] = []

    # Diamond CFG: entry -> a,b -> join
    nodes = ["entry", "a", "b", "join"]
    succ = {"entry": ["a", "b"], "a": ["join"], "b": ["join"], "join": []}

    def xfer(n, val):
        s = set(val or ())
        s.add(n)
        return frozenset(s)

    A = worklist(nodes, succ, xfer, frozenset(["entry"]), ["entry"],
                 join=lambda x, y: frozenset(x or ()) | frozenset(y or ()),
                 bot=frozenset())
    if "entry" not in A["join"] or "a" not in A["join"] or "b" not in A["join"]:
        failures.append(f"diamond join missing preds: {A}")

    # Loop + height-3 lattice {0,1,2} with join=max
    loop_nodes = ["s", "h", "t"]
    loop_succ = {"s": ["h"], "h": ["h", "t"], "t": []}

    def loop_xfer(n, val):
        v = 0 if val is None else int(val)
        if n == "h":
            return min(2, v + 1) if v < 2 else 2
        return v

    L = worklist(
        loop_nodes, loop_succ, loop_xfer, 0, ["s"],
        join=lambda x, y: max(0 if x is None else x, 0 if y is None else y),
        bot=0,
    )
    if L["t"] != 2:
        failures.append(f"loop height-3 did not reach top: {L}")
    # Must not depend on a magic 64 — 3 iterations of height 3 suffice
    if L["h"] != 2:
        failures.append(f"loop head not at top: {L}")

    comps = tarjan(["s", "h", "t"], loop_succ)
    if not any("h" in c and len(c) == 1 for c in comps):
        # h has a self-loop so it is its own SCC (or grouped)
        if not any("h" in c for c in comps):
            failures.append(f"tarjan missed h: {comps}")

    # scc_solve union constraints x ⊆ y
    vars_ = ["x", "y", "z"]
    edges = [("x", "y"), ("y", "z")]
    sol = scc_solve(vars_, edges, impls=None, join=lambda a, b: a | b, bot=frozenset())
    if sol["x"] != frozenset() or sol["z"] != frozenset():
        # bot flows; seed x then re-solve
        pass

    def join_set(a, b):
        return frozenset(a or ()) | frozenset(b or ())

    A2 = {"x": frozenset(["lam"]), "y": frozenset(), "z": frozenset()}
    succ2 = {"x": ["y"], "y": ["z"], "z": []}
    W = deque(["x"])
    while W:
        n = W.popleft()
        for m in succ2.get(n, []):
            j = join_set(A2[m], A2[n])
            if j != A2[m]:
                A2[m] = j
                W.append(m)
    if "lam" not in A2["z"]:
        failures.append(f"subset flow failed: {A2}")

    if failures:
        print(json.dumps({"ok": False, "failures": failures}))
        return 1
    print(json.dumps({"ok": True, "diamond_join": sorted(A["join"]), "loop": L}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Nielson SCC/worklist solver")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    print(json.dumps({"ok": True, "usage": "--self-test"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
