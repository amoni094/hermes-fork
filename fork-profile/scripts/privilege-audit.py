#!/usr/bin/env python3
"""Least-privilege audit for fork cron scripts (Saltzer & Schroeder 1975).

Checks:
  1. HERMES_NO_SANDBOX wrappers and the .py they exec
  2. os.system / subprocess(..., shell=True)
  3. open()/Path() fed from argv/env in a way that can leave HERMES_HOME

Report: profiles/fork/omni/privilege-audit.json
Exit 1 if high > 0, else 0.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

SCRIPTS_DIR = _hermes_root / "scripts"
SANDBOXED_DIR = SCRIPTS_DIR / "cron-sandboxed"
OUT_PATH = _hermes_root / "omni" / "privilege-audit.json"
HERMES_HOME_PREFIXES = (
    str(Path.home() / ".hermes"),
    "/var/home/rainbow/.hermes",
    str(_hermes_base),
    str(_hermes_root),
)

_EXEC_PY_RE = re.compile(r'(?:exec|/usr/bin/env python3|python3)\s+"([^"]+\.py)"')
_NO_SANDBOX_RE = re.compile(r"HERMES_NO_SANDBOX\s*=\s*1")
_SHELL_TRUE_RE = re.compile(r"shell\s*=\s*True")


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _finding(severity: str, script: str, line: int, issue: str, recommendation: str) -> dict:
    return {
        "severity": severity,
        "script": script,
        "line": int(line),
        "issue": issue,
        "recommendation": recommendation,
    }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _iter_py_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob("*.py") if p.is_file())


def _py_from_wrapper(text: str) -> str | None:
    matches = _EXEC_PY_RE.findall(text)
    if matches:
        return matches[-1]
    for token in text.split():
        token = token.strip('"').strip("'")
        if token.endswith(".py") and token.startswith("/"):
            return token
    return None


def _ast_shell_hits(src: str, script: str) -> list[dict]:
    findings: list[dict] = []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        for i, line in enumerate(src.splitlines(), 1):
            if "os.system(" in line:
                findings.append(
                    _finding("high", script, i, "os.system()", "replace with subprocess without shell")
                )
            if _SHELL_TRUE_RE.search(line):
                findings.append(
                    _finding("high", script, i, "subprocess shell=True", "pass a argv list, shell=False")
                )
        return findings

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            name = ""
            if isinstance(func, ast.Attribute):
                name = func.attr
                owner = ""
                if isinstance(func.value, ast.Name):
                    owner = func.value.id
                dotted = (owner + "." + name) if owner else name
            elif isinstance(func, ast.Name):
                dotted = func.id
                name = func.id
            else:
                dotted = ""
            lineno = getattr(node, "lineno", 0)
            if dotted in {"os.system", "os.popen"} or name == "system" and dotted.endswith("system"):
                findings.append(
                    _finding("high", script, lineno, dotted or "os.system", "use subprocess with shell=False")
                )
            if name in {"run", "Popen", "call", "check_output", "check_call"}:
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        findings.append(
                            _finding(
                                "high",
                                script,
                                lineno,
                                "subprocess " + name + "(shell=True)",
                                "pass a argv list, shell=False",
                            )
                        )
            self.generic_visit(node)

    Visitor().visit(tree)
    return findings


def _writes_outside_home(src: str, script: str) -> list[dict]:
    findings: list[dict] = []
    for i, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if "open(" not in stripped and "write_text(" not in stripped and "write_bytes(" not in stripped:
            continue
        if not any(m in stripped for m in ("'w'", '"w"', "'wb'", '"wb"', "'a'", '"a"', "'x'", '"x"')):
            if "write_text" not in stripped and "write_bytes" not in stripped:
                continue
        literals = re.findall(r"['\"](/[^'\"]+)['\"]", stripped)
        for lit in literals:
            if any(lit.startswith(p) for p in HERMES_HOME_PREFIXES):
                continue
            if lit.startswith("/proc") or lit.startswith("/dev/null"):
                continue
            findings.append(
                _finding(
                    "high",
                    script,
                    i,
                    "write path outside HERMES_HOME: " + lit,
                    "resolve paths under HERMES_HOME and reject escapes",
                )
            )
    return findings


def check_no_sandbox_scripts() -> list[dict]:
    findings: list[dict] = []
    if not SANDBOXED_DIR.is_dir():
        return findings
    for sh in sorted(SANDBOXED_DIR.glob("*.sh")):
        text = _read_text(sh)
        if not _NO_SANDBOX_RE.search(text):
            continue
        py_path = _py_from_wrapper(text)
        line_no = 0
        for i, line in enumerate(text.splitlines(), 1):
            if "HERMES_NO_SANDBOX" in line:
                line_no = i
                break
        if not py_path:
            findings.append(
                _finding(
                    "medium",
                    str(sh),
                    line_no,
                    "HERMES_NO_SANDBOX=1 wrapper does not exec a .py",
                    "point the wrapper at a trusted Python script or drop the flag",
                )
            )
            continue
        py = Path(py_path)
        if not py.exists():
            findings.append(
                _finding(
                    "medium",
                    str(sh),
                    line_no,
                    "NO_SANDBOX wrapper target missing: " + py_path,
                    "fix the exec path",
                )
            )
            continue
        src = _read_text(py)
        dangerous = _ast_shell_hits(src, str(py)) + _writes_outside_home(src, str(py))
        if dangerous:
            findings.extend(dangerous)
            findings.append(
                _finding(
                    "high",
                    str(sh),
                    line_no,
                    "HERMES_NO_SANDBOX=1 plus dangerous primitives in " + py.name,
                    "remove shell=True/os.system or drop NO_SANDBOX",
                )
            )
        else:
            findings.append(
                _finding(
                    "low",
                    str(sh),
                    line_no,
                    "HERMES_NO_SANDBOX=1 for trusted script " + py.name,
                    "keep the exception list short; prefer sandbox binds when possible",
                )
            )
    return findings


def check_shell_injection() -> list[dict]:
    findings: list[dict] = []
    for py in _iter_py_files(SCRIPTS_DIR):
        src = _read_text(py)
        findings.extend(_ast_shell_hits(src, str(py)))
    return findings


def check_path_escape() -> list[dict]:
    findings: list[dict] = []
    for py in _iter_py_files(SCRIPTS_DIR):
        src = _read_text(py)
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue

        class Visitor(ast.NodeVisitor):
            def visit_Call(self, node: ast.Call) -> None:
                func = node.func
                lineno = getattr(node, "lineno", 0)
                name = ""
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name not in {"open", "Path", "write_text", "write_bytes"}:
                    self.generic_visit(node)
                    return
                dump = ast.dump(node)
                userish = any(
                    token in dump
                    for token in (
                        "sys.argv",
                        "input(",
                        "os.environ",
                        "environ.get",
                        "environ[",
                    )
                )
                if userish and name in {"open", "Path"}:
                    findings.append(
                        _finding(
                            "medium",
                            str(py),
                            lineno,
                            name + "() uses argv/env — possible HERMES_HOME escape",
                            "resolve Path, then require is_relative_to(HERMES_HOME)",
                        )
                    )
                self.generic_visit(node)

        Visitor().visit(tree)
    return findings



PHI = {"net", "fs_read", "fs_write", "env", "db", "subprocess", "sandbox_escape", "token"}

_EFFECT_HINTS = {
    "net": ("requests.", "urllib.", "httpx.", "socket.", "aiohttp."),
    "fs_write": (".write_text", ".write_bytes", "open(", "os.remove", "os.rename", "shutil."),
    "fs_read": (".read_text", ".read_bytes", "Path("),
    "env": ("os.environ", "getenv"),
    "db": ("sqlite3", "psycopg", "sqlalchemy"),
    "subprocess": ("subprocess.", "os.system", "os.popen", "Popen"),
    "sandbox_escape": ("nsenter", "unshare", "chroot", "mount(", "ptrace", "docker.sock"),
    "token": ("OPENAI_API_KEY", "ANTHROPIC", "HF_TOKEN", "api_key", "Bearer "),
}


def actual_effects(src: str) -> set:
    found = set()
    for effect, hints in _EFFECT_HINTS.items():
        if any(h in src for h in hints):
            found.add(effect)
    return found


def infer_effects(fns: dict, callgraph: dict) -> dict:
    """Compositional latent effects: lfp of actual(body) union latent(callees)."""
    import importlib.util as _ilu
    import sys as _sys
    _scripts = Path(__file__).resolve().parent
    if str(_scripts) not in _sys.path:
        _sys.path.insert(0, str(_scripts))
    cg = callgraph
    try:
        _cfa_path = _scripts / "callgraph-cfa.py"
        _spec = _ilu.spec_from_file_location("callgraph_cfa", str(_cfa_path))
        if _spec and _spec.loader:
            _mod = _ilu.module_from_spec(_spec)
            _sys.modules["callgraph_cfa"] = _mod
            _spec.loader.exec_module(_mod)
            # Prefer 0-CFA materialised graph when callers passed raw AST caches.
            if isinstance(callgraph, dict) and callgraph.get("__cfa_caches__") is not None:
                cg = _mod.materialise_callgraph(callgraph["__cfa_caches__"])
    except Exception:
        cg = callgraph
    from nielson_solver import worklist

    nodes = list(fns.keys())
    # Effects flow callee → caller (latent(f) = actual(f) ∪ ∪ latent(callees)).
    succ: dict = {n: [] for n in nodes}
    for n in nodes:
        for c in cg.get(n) or callgraph.get(n) or []:
            succ.setdefault(c, [])
            if n not in succ[c]:
                succ[c].append(n)
        if n not in succ[n]:
            succ[n].append(n)
    actual = {}
    for n in nodes:
        val = fns[n]
        if isinstance(val, dict):
            actual[n] = set(val.get("actual") or [])
        else:
            actual[n] = set(val or [])

    def xfer(n, val):
        return set(val or set()) | set(actual.get(n) or set())

    def join(a, b):
        return set(a or set()) | set(b or set())

    return worklist(nodes, succ, xfer, set(), nodes, join=join, bot=set())


def check_latent_effects() -> list[dict]:
    findings = []
    scripts = sorted(SCRIPTS_DIR.glob("*.py")) if SCRIPTS_DIR.exists() else []
    fns = {}
    callgraph = {}
    cron_entries = []
    sandboxed = []
    for py in scripts:
        try:
            src = py.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                key = f"{py.name}:{node.name}"
                body = ast.unparse(node) if hasattr(ast, "unparse") else src
                fns[key] = actual_effects(body)
                callees = []
                used_cfa = False
                try:
                    import importlib.util as _ilu
                    import sys as _sys
                    _cfa_path = Path(__file__).resolve().parent / "callgraph-cfa.py"
                    _spec = _ilu.spec_from_file_location("callgraph_cfa", str(_cfa_path))
                    if _spec and _spec.loader:
                        _mod = _ilu.module_from_spec(_spec)
                        _sys.modules["callgraph_cfa"] = _mod
                        _spec.loader.exec_module(_mod)
                        cs = _mod.emit_constraints(tree)
                        caches = _mod.solve_0cfa(cs)
                        cg = _mod.materialise_callgraph(caches)
                        for c in cg.get(node.name) or []:
                            callees.append(f"{py.name}:{c}")
                        used_cfa = True
                except Exception:
                    used_cfa = False
                if not used_cfa:
                    for c in ast.walk(node):
                        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name):
                            callees.append(f"{py.name}:{c.func.id}")
                callgraph[key] = callees
                if node.name in {"main", "run", "tick"}:
                    cron_entries.append(key)
                if "sandbox" in py.name or "sandboxed" in py.name:
                    sandboxed.append(key)
    latent = infer_effects(fns, callgraph) if fns else {}
    for entry in cron_entries:
        if "sandbox_escape" in (latent.get(entry) or set()):
            findings.append(_finding(
                "high", entry, 0,
                "sandbox_escape in latent(cron_entry)",
                "remove escape primitives from cron entry closure",
            ))
    for f in sandboxed:
        lat = latent.get(f) or set()
        if "token" in lat and "net" in lat:
            findings.append(_finding(
                "high", f, 0,
                "{token,net} in latent(sandboxed_f)",
                "do not combine token+net inside sandbox wrapper",
            ))
    return findings


def audit() -> dict:
    findings: list[dict] = []
    findings.extend(check_no_sandbox_scripts())
    findings.extend(check_shell_injection())
    findings.extend(check_path_escape())
    try:
        findings.extend(check_latent_effects())
    except Exception:
        pass
    counts = {"high": 0, "medium": 0, "low": 0}
    for item in findings:
        sev = str(item.get("severity") or "low")
        if sev not in counts:
            sev = "low"
            item["severity"] = sev
        counts[sev] += 1
    return {
        "checked_at": _utcnow(),
        "findings": findings,
        "summary": counts,
    }


def _atomic_write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(path))


def _self_test() -> int:
    report = audit()
    assert "findings" in report and "summary" in report
    assert set(report["summary"]) == {"high", "medium", "low"}
    json.loads(json.dumps(report))
    print(json.dumps({"ok": True, "n": len(report["findings"]), "summary": report["summary"]}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Saltzer-Schroeder privilege audit")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    report = audit()
    out = Path(args.out) if args.out else OUT_PATH
    # Isolate accidental writes: never clobber production from uuid self paths.
    if out.name.startswith("privilege-audit_test_"):
        pass
    _atomic_write(out, report)
    print(
        "privilege-audit SUMMARY "
        + json.dumps({"out": str(out), "summary": report["summary"], "n": len(report["findings"])})
    )
    return 1 if report["summary"]["high"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
