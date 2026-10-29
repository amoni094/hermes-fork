#!/usr/bin/env python3
"""0-CFA callgraph (Nielson Ch 3) over Python AST.

Handles FunctionDef, Lambda, Assign, Call, runpy.run_path, getattr.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from nielson_solver import scc_solve


def _name_of(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _name_of(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def emit_constraints(tree: ast.AST) -> dict:
    """Emit 0-CFA subset/implication constraints from a module AST."""
    edges: list[tuple[str, str]] = []
    impls = []
    lambdas: dict[str, ast.Lambda] = {}
    fns: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    assigns: list[tuple[str, str]] = []
    calls: list[tuple[str | None, ast.Call]] = []
    runpy_sites: list[str] = []
    getattr_sites: list[tuple[str, str]] = []

    class Collector(ast.NodeVisitor):
        def __init__(self):
            self.fn_stack: list[str] = []

        def visit_FunctionDef(self, node):
            fns[node.name] = node
            self.fn_stack.append(node.name)
            self.generic_visit(node)
            self.fn_stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, node):
            lid = f"_lambda_{node.lineno}"
            lambdas[lid] = node
            self.fn_stack.append(lid)
            self.generic_visit(node)
            self.fn_stack.pop()

        def visit_Assign(self, node):
            src = _name_of(node.value)
            dest_names = []
            for t in node.targets:
                dst = _name_of(t)
                if src and dst:
                    assigns.append((src, dst))
                    edges.append((f"val:{src}", f"val:{dst}"))
                if dst:
                    dest_names.append(dst)
            if isinstance(node.value, ast.Lambda):
                lid = f"_lambda_{node.value.lineno}"
                for dst in dest_names:
                    edges.append((f"lam:{lid}", f"val:{dst}"))
                    lambdas[dst] = node.value
            if isinstance(node.value, ast.Name) and node.value.id in fns:
                for dst in dest_names:
                    edges.append((f"fn:{node.value.id}", f"val:{dst}"))
            # Bound name sits under the lambda so recursive `f = lambda: f()`
            # records caller `f` as well as `_lambda_{lineno}`.
            for dst in dest_names:
                if isinstance(node.value, ast.Lambda):
                    self.fn_stack.append(dst)
            self.generic_visit(node)
            if isinstance(node.value, ast.Lambda):
                for _dst in dest_names:
                    if self.fn_stack:
                        self.fn_stack.pop()

        def visit_Call(self, node):
            caller = self.fn_stack[-1] if self.fn_stack else "<module>"
            for name in reversed(self.fn_stack):
                if not str(name).startswith("_lambda_"):
                    caller = name
                    break
            calls.append((caller, node))
            fname = _name_of(node.func)
            if fname in ("runpy.run_path", "runpy.run_module"):
                runpy_sites.append(caller)
            if isinstance(node.func, ast.Call) and _name_of(node.func.func) == "getattr":
                getattr_sites.append((caller, ast.dump(node.func)))
            if isinstance(node.func, ast.Name) and node.func.id == "getattr":
                getattr_sites.append((caller, ast.dump(node)))
            self.generic_visit(node)

    Collector().visit(tree)

    # Direct calls: if f in val:x then call x → f
    for caller, call in calls:
        fname = _name_of(call.func)
        if fname and fname in fns:
            edges.append((f"fn:{fname}", f"call:{caller}->{fname}"))
        elif fname:
            # x() where x may hold a function
            def _mk(fname=fname, caller=caller):
                def premise(A):
                    return True

                def adder(A):
                    extra = []
                    bucket = A.get(f"val:{fname}", frozenset())
                    for lam in bucket:
                        extra.append((str(lam), f"call:{caller}->{fname}"))
                    return extra

                return premise, adder

            impls.append(_mk())

    vars_ = set()
    for a, b in edges:
        vars_.add(a)
        vars_.add(b)
    for name in fns:
        vars_.add(f"fn:{name}")
        vars_.add(f"val:{name}")
        edges.append((f"fn:{name}", f"val:{name}"))
    for lid in lambdas:
        vars_.add(f"lam:{lid}")
    for src, dst in assigns:
        vars_.add(f"val:{src}")
        vars_.add(f"val:{dst}")
    for caller, call in calls:
        fname = _name_of(call.func)
        if fname:
            vars_.add(f"call:{caller}->{fname}")
    if runpy_sites:
        vars_.add("dyn:runpy")
        for c in runpy_sites:
            edges.append(("dyn:runpy", f"call:{c}->runpy"))
            vars_.add(f"call:{c}->runpy")
    if getattr_sites:
        vars_.add("dyn:getattr")
        for c, _d in getattr_sites:
            edges.append(("dyn:getattr", f"call:{c}->getattr"))
            vars_.add(f"call:{c}->getattr")

    return {
        "vars": sorted(vars_),
        "edges": edges,
        "impls": impls,
        "fns": sorted(fns),
        "lambdas": sorted(lambdas),
        "runpy": runpy_sites,
        "getattr": getattr_sites,
        "calls": [(c, _name_of(call.func)) for c, call in calls],
    }


def solve_0cfa(cs: dict) -> dict:
    bot = frozenset()

    def join(a, b):
        return frozenset(a or ()) | frozenset(b or ())

    seeded_edges = list(cs.get("edges") or [])
    # seed each fn:name with itself
    A_init_edges = seeded_edges
    sol = scc_solve(cs.get("vars") or [], A_init_edges, impls=cs.get("impls") or [], join=join, bot=bot)
    # overlay seeds
    out = dict(sol)
    for fn in cs.get("fns") or []:
        key = f"fn:{fn}"
        out[key] = frozenset({key}) | frozenset(out.get(key) or ())
        val = f"val:{fn}"
        out[val] = out[key] | frozenset(out.get(val) or ())
    for lam in cs.get("lambdas") or []:
        key = f"lam:{lam}"
        out[key] = frozenset({key}) | frozenset(out.get(key) or ())
    # re-flow seeds along edges
    changed = True
    guard = 0
    while changed and guard < max(8, len(out) * 4):
        guard += 1
        changed = False
        for u, v in seeded_edges:
            j = join(out.get(v, bot), out.get(u, bot))
            if j != out.get(v, bot):
                out[v] = j
                changed = True
    return out


def materialise_callgraph(caches: dict) -> dict[str, set[str]]:
    """caches: var -> set of lam/fn labels. Return caller -> callees."""
    graph: dict[str, set[str]] = defaultdict(set)
    for var, vals in (caches or {}).items():
        if not str(var).startswith("call:"):
            continue
        rest = str(var)[5:]
        if "->" in rest:
            caller, callee = rest.split("->", 1)
        else:
            caller, callee = rest, rest
        graph[caller].add(callee)
        for v in vals or ():
            s = str(v)
            if s.startswith("fn:"):
                graph[caller].add(s[3:])
            elif s.startswith("lam:"):
                graph[caller].add(s)
    return {k: set(vs) for k, vs in graph.items()}


def analyse_source(src: str) -> dict:
    tree = ast.parse(src)
    cs = emit_constraints(tree)
    caches = solve_0cfa(cs)
    graph = materialise_callgraph(caches)
    return {
        "fns": cs["fns"],
        "lambdas": cs["lambdas"],
        "runpy": cs["runpy"],
        "getattr": cs["getattr"],
        "calls": cs["calls"],
        "graph": {k: sorted(v) for k, v in graph.items()},
    }


def _self_test() -> int:
    src = '''
import runpy
def f(x):
    return g(x)
def g(x):
    return x
h = f
def k():
    h(1)
    getattr(f, "__call__")
    runpy.run_path("x.py")
m = lambda y: y
'''
    r = analyse_source(src)
    assert "f" in r["fns"] and "g" in r["fns"]
    assert r["lambdas"]
    assert r["runpy"]
    assert r["getattr"]
    graph = r["graph"]
    # f calls g
    callees_f = set()
    for caller, callees in graph.items():
        if caller == "f":
            callees_f |= set(callees)
    assert "g" in callees_f or any("g" in vs for vs in graph.values()), graph
    print(json.dumps({"ok": True, "fns": r["fns"], "graph": r["graph"], "runpy": r["runpy"]}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="0-CFA callgraph")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("path", nargs="?")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    if args.path:
        src = Path(args.path).read_text(encoding="utf-8", errors="replace")
        print(json.dumps(analyse_source(src), indent=2))
        return 0
    print(json.dumps({"ok": True, "usage": "--self-test | PATH"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
