#!/usr/bin/env python3
"""Interprocedural call-graph audit for Hermes fork scripts.

Implements Nielson, Nielson & Hankin, *Principles of Program Analysis* §1–2:
dataflow over a call graph propagating the exit-code lattice
{0=ok, 1=intentional-nonzero, 2=error} through call chains (finding P1).

Also flags HERMES_HOME env reads without a Path.exists()/is_dir() check
in the same function scope (finding P2).
"""
from __future__ import annotations

import ast
import json
import os
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

SCAN_DIRS = [
    Path("/var/home/rainbow/.hermes/scripts"),
    Path("/var/home/rainbow/.hermes/profiles/fork/scripts"),
]
REPORT_PATH = Path("/var/home/rainbow/.hermes/scripts/callgraph-audit-report.json")

SUBPROCESS_FUNCS = {
    "subprocess.run",
    "subprocess.call",
    "subprocess.Popen",
    "subprocess.check_call",
    "subprocess.check_output",
    "os.system",
    "os.popen",
}
EXIT_FUNCS = {"sys.exit", "exit"}
MAX_RISK_PATH_LEN = 8
MAX_RISK_PATHS = 200


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _dotted(node: ast.AST) -> str:
    parts: list[str] = []
    cur: ast.AST = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    if isinstance(cur, ast.Call) and isinstance(cur.func, ast.Name) and cur.func.id == "__import__":
        if cur.args and isinstance(cur.args[0], ast.Constant) and isinstance(cur.args[0].value, str):
            suffix = ".".join(reversed(parts)) if parts else ""
            return f"__import__({cur.args[0].value!r})" + (f".{suffix}" if suffix else "")
    return ""


def _const_str(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _py_basename(s: str) -> Optional[str]:
    s = s.strip().strip("'\"")
    s = s.replace("\\", "/")
    base = os.path.basename(s.split()[-1] if s.split() else s)
    if base.endswith(".py") and "/" not in base:
        return base
    if s.endswith(".py"):
        return os.path.basename(s)
    return None


def _strings_in(node: ast.AST) -> list[str]:
    out: list[str] = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
    return out


def _is_environ_get_hermes(node: ast.AST) -> bool:
    """True if node is os.environ.get('HERMES_HOME') or os.environ['HERMES_HOME']."""
    if isinstance(node, ast.Call):
        name = _dotted(node.func)
        if name.endswith("environ.get") or name.endswith("environ.get"):
            if node.args:
                key = _const_str(node.args[0])
                return key == "HERMES_HOME"
        # os.environ.get via subscript-free alias: getattr patterns skipped
        return False
    if isinstance(node, ast.Subscript):
        val_name = _dotted(node.value)
        if val_name.endswith("environ"):
            sl = node.slice
            return _const_str(sl) == "HERMES_HOME"
    return False


def _enclosing_scope(parents: dict[ast.AST, ast.AST], node: ast.AST) -> ast.AST:
    cur: Optional[ast.AST] = node
    while cur is not None:
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            return cur
        cur = parents.get(cur)
    return node


def _build_parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _is_path_exists_or_isdir(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Attribute) and node.func.attr in {"exists", "is_dir"}:
        return True
    return False


def _mentions_returncode(node: ast.AST) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute) and n.attr == "returncode":
            return True
        if isinstance(n, ast.Name) and n.id in {"returncode", "rc"}:
            return True
    return False


def _is_sys_exit_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    return _dotted(node.func) in EXIT_FUNCS or (
        isinstance(node.func, ast.Name) and node.func.id in {"exit"}
    )


def _exit_literal(node: ast.Call) -> Optional[int]:
    if not node.args:
        return 0
    arg = node.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
        return arg.value
    if isinstance(arg, ast.UnaryOp) and isinstance(arg.op, ast.USub) and isinstance(arg.operand, ast.Constant):
        if isinstance(arg.operand.value, int):
            return -arg.operand.value
    return None


def _keyword_check_true(call: ast.Call) -> bool:
    for kw in call.keywords:
        if kw.arg == "check" and isinstance(kw.value, ast.Constant) and kw.value is not False:
            return bool(kw.value.value)
    return False


def _in_try(parents: dict[ast.AST, ast.AST], node: ast.AST) -> bool:
    cur: Optional[ast.AST] = node
    while cur is not None:
        if isinstance(cur, ast.Try):
            return True
        cur = parents.get(cur)
    return False


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_scripts() -> list[Path]:
    seen: set[tuple[int, int]] = set()
    out: list[Path] = []
    for d in SCAN_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.py")):
            try:
                st = p.stat()
            except OSError:
                continue
            key = (st.st_dev, st.st_ino)
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return out


def script_id(path: Path) -> str:
    return str(path)


# ---------------------------------------------------------------------------
# Per-script analysis
# ---------------------------------------------------------------------------

class ScriptInfo:
    __slots__ = (
        "path",
        "sid",
        "tree",
        "src",
        "callees",
        "handled_callees",
        "exit_literals",
        "has_nonliteral_exit",
        "has_error_prop",
        "label",
        "hermes_unvalidated",
        "local_py_constants",
        "imported_local",
    )

    def __init__(self, path: Path, src: str, tree: ast.AST):
        self.path = path
        self.sid = script_id(path)
        self.tree = tree
        self.src = src
        self.callees: set[str] = set()
        self.handled_callees: set[str] = set()
        self.exit_literals: list[int] = []
        self.has_nonliteral_exit = False
        self.has_error_prop = False
        self.label = "unknown"
        self.hermes_unvalidated = False
        self.local_py_constants: list[str] = []
        self.imported_local: set[str] = set()


def _parse(path: Path) -> Optional[ScriptInfo]:
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        info = ScriptInfo(path, src, ast.parse("pass"))
        info.label = "unknown"
        return info
    return ScriptInfo(path, src, tree)


def _known_by_name(scripts: Iterable[Path]) -> dict[str, str]:
    """basename -> first-seen script id."""
    mapping: dict[str, str] = {}
    for p in scripts:
        mapping.setdefault(p.name, script_id(p))
        mapping.setdefault(p.stem, script_id(p))
    return mapping


def analyse_exits(info: ScriptInfo) -> None:
    parents = _build_parents(info.tree)
    assigned_subproc: set[str] = set()

    for node in ast.walk(info.tree):
        if not isinstance(node, ast.Call):
            continue
        dname = _dotted(node.func)
        if dname in SUBPROCESS_FUNCS or dname.endswith(".run") and "subprocess" in dname:
            parent = parents.get(node)
            if isinstance(parent, ast.Assign):
                for t in parent.targets:
                    if isinstance(t, ast.Name):
                        assigned_subproc.add(t.id)
            elif isinstance(parent, ast.AnnAssign) and isinstance(parent.target, ast.Name):
                assigned_subproc.add(parent.target.id)

    for node in ast.walk(info.tree):
        if isinstance(node, ast.Call) and _is_sys_exit_call(node):
            lit = _exit_literal(node)
            if lit is None:
                info.has_nonliteral_exit = True
            else:
                info.exit_literals.append(lit)

        if isinstance(node, ast.Raise):
            exc = node.exc
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name) and exc.func.id == "SystemExit":
                if exc.args and isinstance(exc.args[0], ast.Constant) and isinstance(exc.args[0].value, int):
                    info.exit_literals.append(exc.args[0].value)
                else:
                    info.has_nonliteral_exit = True

        if isinstance(node, ast.If) and _mentions_returncode(node.test):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and _is_sys_exit_call(inner):
                    lit = _exit_literal(inner)
                    if lit is None or lit != 0:
                        info.has_error_prop = True

        if isinstance(node, ast.Call):
            dname = _dotted(node.func)
            if dname in SUBPROCESS_FUNCS and _keyword_check_true(node):
                if not _in_try(parents, node):
                    info.has_error_prop = True

        if isinstance(node, ast.ExceptHandler):
            # except CalledProcessError: sys.exit(...)
            typ = node.type
            tname = _dotted(typ) if typ is not None else ""
            if "CalledProcessError" in tname:
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Call) and _is_sys_exit_call(inner):
                        info.has_error_prop = True

    # Label (local, before interprocedural join)
    if info.has_error_prop:
        info.label = "error_propagator"
        return
    lits = info.exit_literals
    if info.has_nonliteral_exit and not lits:
        info.label = "unknown"
        return
    if not lits:
        info.label = "ok"
        return
    nonzero = [n for n in lits if n != 0]
    if not nonzero:
        info.label = "ok"
        return
    # CLI-style non-zero (alarms, usage) without child-code propagation
    if all(n in (0, 1) for n in lits) or (1 in nonzero and not info.has_error_prop):
        if info.has_nonliteral_exit:
            info.label = "unknown"
        else:
            info.label = "intentional_nonzero"
        return
    info.label = "unknown"


def analyse_calls(info: ScriptInfo, known: dict[str, str]) -> None:
    parents = _build_parents(info.tree)
    # Collect *.py string constants that name known scripts
    py_consts: list[str] = []
    for s in _strings_in(info.tree):
        base = _py_basename(s)
        if base and base in known:
            py_consts.append(base)
    info.local_py_constants = py_consts

    has_subproc = False
    subproc_nodes: list[ast.Call] = []
    for node in ast.walk(info.tree):
        if isinstance(node, ast.Call) and _dotted(node.func) in SUBPROCESS_FUNCS:
            has_subproc = True
            subproc_nodes.append(node)

    for node in subproc_nodes:
        handled = _in_try(parents, node) or _keyword_check_true(node)
        # returncode inspection in enclosing function
        scope = _enclosing_scope(parents, node)
        if not handled:
            for n in ast.walk(scope):
                if isinstance(n, ast.If) and _mentions_returncode(n.test):
                    handled = True
                    break
                if isinstance(n, ast.Attribute) and n.attr == "returncode":
                    # compared or printed — treat as inspected
                    handled = True
                    break
        names_here: set[str] = set()
        for s in _strings_in(node):
            base = _py_basename(s)
            if base and base in known:
                names_here.add(base)
        # argv list: [sys.executable, str(path), ...] with path from a .py constant elsewhere
        if not names_here and has_subproc:
            # If this call's args mention no .py string, fall back later
            pass
        for base in names_here:
            sid = known[base]
            if sid == info.sid:
                continue
            info.callees.add(sid)
            if handled:
                info.handled_callees.add(sid)

    # monitor-suite pattern: subprocess.run(sys.executable, path) looping a list of .py names
    if has_subproc and py_consts:
        any_direct = bool(info.callees)
        if not any_direct:
            handled_file = False
            for node in subproc_nodes:
                if _in_try(parents, node):
                    handled_file = True
                scope = _enclosing_scope(parents, node)
                for n in ast.walk(scope):
                    if isinstance(n, ast.Attribute) and n.attr == "returncode":
                        handled_file = True
            for base in py_consts:
                sid = known[base]
                if sid == info.sid:
                    continue
                info.callees.add(sid)
                if handled_file:
                    info.handled_callees.add(sid)

    # Direct imports of other scanned modules (underscore names / packages)
    for node in ast.walk(info.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in known and known[root] != info.sid:
                    info.imported_local.add(known[root])
                    info.callees.add(known[root])
                    info.handled_callees.add(known[root])  # import is not subprocess risk
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in known and known[root] != info.sid:
                info.imported_local.add(known[root])
                info.callees.add(known[root])
                info.handled_callees.add(known[root])


def analyse_hermes_home(info: ScriptInfo) -> None:
    tree = info.tree
    parents = _build_parents(tree)
    reads: list[ast.AST] = []
    for node in ast.walk(tree):
        if _is_environ_get_hermes(node):
            reads.append(node)
        # also: os.environ.get via Call where func is Attribute get on environ
    if not reads:
        info.hermes_unvalidated = False
        return

    unvalidated = False
    for read in reads:
        scope = _enclosing_scope(parents, read)
        read_line = getattr(read, "lineno", 0) or 0
        ok = False
        for n in ast.walk(scope):
            if _is_path_exists_or_isdir(n):
                nline = getattr(n, "lineno", 0) or 0
                if nline >= read_line:
                    ok = True
                    break
        if not ok:
            unvalidated = True
            break
    info.hermes_unvalidated = unvalidated


# ---------------------------------------------------------------------------
# Interprocedural lattice propagation
# ---------------------------------------------------------------------------

def propagate_labels(infos: dict[str, ScriptInfo]) -> None:
    """If A calls B via subprocess and B is error_propagator, A inherits
    unless the call site has explicit error handling."""
    changed = True
    guard = 0
    while changed and guard < 64:
        changed = False
        guard += 1
        for info in infos.values():
            if info.label == "error_propagator":
                continue
            for callee in info.callees:
                if callee in info.handled_callees:
                    continue
                other = infos.get(callee)
                if other is None:
                    continue
                if other.label == "error_propagator":
                    info.label = "error_propagator"
                    changed = True
                    break


def risk_paths(infos: dict[str, ScriptInfo]) -> list[list[str]]:
    """Call chains (length >= 2) ending at an error_propagator leaf."""
    graph = {sid: sorted(info.callees) for sid, info in infos.items()}
    leaves = {sid for sid, info in infos.items() if info.label == "error_propagator"}
    paths: list[list[str]] = []

    def dfs(node: str, trail: list[str], seen: set[str]) -> None:
        if len(paths) >= MAX_RISK_PATHS:
            return
        if len(trail) >= MAX_RISK_PATH_LEN:
            return
        for nxt in graph.get(node, []):
            if nxt in seen:
                continue
            new_trail = trail + [nxt]
            if nxt in leaves and len(new_trail) >= 2:
                paths.append(new_trail)
            dfs(nxt, new_trail, seen | {nxt})

    for sid in sorted(infos):
        dfs(sid, [sid], {sid})
        if len(paths) >= MAX_RISK_PATHS:
            break
    # stable unique
    uniq = []
    seen_t = set()
    for p in paths:
        t = tuple(p)
        if t not in seen_t:
            seen_t.add(t)
            uniq.append(p)
    return uniq


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(infos: dict[str, ScriptInfo]) -> dict[str, Any]:
    edges: list[list[str]] = []
    seen_e: set[tuple[str, str]] = set()
    for sid, info in sorted(infos.items()):
        for cal in sorted(info.callees):
            key = (sid, cal)
            if key not in seen_e:
                seen_e.add(key)
                edges.append([sid, cal])
    labels = {sid: info.label for sid, info in sorted(infos.items())}
    unval = sorted(sid for sid, info in infos.items() if info.hermes_unvalidated)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "call_edges": edges,
        "exit_code_labels": labels,
        "risk_paths": risk_paths(infos),
        "hermes_home_unvalidated": unval,
    }


def print_summary(report: dict[str, Any], n_scripts: int) -> None:
    labels = report["exit_code_labels"]
    counts: dict[str, int] = defaultdict(int)
    for lab in labels.values():
        counts[lab] += 1
    print("Call-graph audit — Nielson, Nielson & Hankin PPA §1–2")
    print(f"generated_at: {report['generated_at']}")
    print(f"scripts scanned: {n_scripts}")
    print(f"call edges: {len(report['call_edges'])}")
    print("exit_code_labels:")
    for k in ("ok", "intentional_nonzero", "error_propagator", "unknown"):
        print(f"  {k}: {counts.get(k, 0)}")
    extra = set(counts) - {"ok", "intentional_nonzero", "error_propagator", "unknown"}
    for k in sorted(extra):
        print(f"  {k}: {counts[k]}")
    print(f"risk_paths: {len(report['risk_paths'])}")
    for p in report["risk_paths"][:25]:
        short = " -> ".join(Path(s).name for s in p)
        print(f"  {short}")
    if len(report["risk_paths"]) > 25:
        print(f"  ... {len(report['risk_paths']) - 25} more")
    unval = report["hermes_home_unvalidated"]
    print(f"hermes_home_unvalidated (P2): {len(unval)}")
    for s in unval[:40]:
        print(f"  {Path(s).name}")
    if len(unval) > 40:
        print(f"  ... {len(unval) - 40} more")
    print(f"report: {REPORT_PATH}")


def main() -> int:
    scripts = discover_scripts()
    infos_list: list[ScriptInfo] = []
    for p in scripts:
        info = _parse(p)
        if info is not None:
            infos_list.append(info)
    known = _known_by_name(scripts)
    # also map by full path
    for info in infos_list:
        known[info.sid] = info.sid
        known[info.path.name] = info.sid

    for info in infos_list:
        analyse_exits(info)
        analyse_calls(info, known)
        analyse_hermes_home(info)

    infos = {info.sid: info for info in infos_list}
    propagate_labels(infos)
    report = build_report(infos)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print_summary(report, len(infos_list))
    return 0


if __name__ == "__main__":
    sys.exit(main())
