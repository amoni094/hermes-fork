#!/usr/bin/env python3
"""plugin-pipeline-scan.py — Wave 18 theory checks on fork plugins.

Checks:
  1. H-I6 stdlib-only imports (no requests/numpy/yaml as runtime deps)
  2. H-I7 except Exception (or narrower) — no bare except, no except BaseException
  3. No conversation_history.append/insert (no synthetic messages)
  4. Frame rule: sqlite writes only under plugin_name/*
  5. WAL: sqlite reads must check journal_mode == WAL
  6. ISS small-gain: product of ISS_GAIN on the same hook < 1
  7. Assume/guarantee docstrings present
  8. EPS_DP composition: sum of EPS_DP <= 1.0

Stdlib only. Exit 1 on hard-core violations.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

PLUGIN_ROOT = Path("/var/home/rainbow/.hermes/profiles/fork/plugins")
SKIP = {"hindsight", "orca-status", "__pycache__"}
STDLIB_OK = {
    "abc", "argparse", "ast", "asyncio", "base64", "binascii", "calendar",
    "collections", "contextlib", "copy", "csv", "ctypes", "dataclasses",
    "datetime", "decimal", "difflib", "enum", "errno", "fnmatch", "functools",
    "gc", "getpass", "glob", "hashlib", "hmac", "html", "http", "importlib",
    "inspect", "io", "itertools", "json", "logging", "math", "mmap", "os",
    "pathlib", "pickle", "platform", "pprint", "queue", "random", "re",
    "secrets", "select", "shlex", "shutil", "signal", "socket", "sqlite3",
    "ssl", "stat", "string", "struct", "subprocess", "sys", "tempfile",
    "textwrap", "threading", "time", "tokenize", "traceback", "types",
    "typing", "unicodedata", "urllib", "uuid", "warnings", "weakref",
    "xml", "zipfile", "zoneinfo",
}
# First-party / runtime-provided, not pip
LOCAL_OK = {
    "hermes_cli", "hermes_agent", "hermes_tools", "tool_auth_shim",
}
BANNED = {"requests", "numpy", "yaml", "httpx", "aiohttp", "bs4", "lxml", "pandas", "torch"}
HOOK_RE = re.compile(r'register_hook\(\s*["\']([a-z_]+)["\']')
GAIN_RE = re.compile(r"^ISS_GAIN\s*=\s*([0-9.]+)", re.M)
EPS_RE = re.compile(r"^EPS_DP\s*=\s*([0-9.]+)", re.M)
ASSUME_RE = re.compile(r"ASSUME:", re.I)
GUAR_RE = re.compile(r"GUARANTEE:", re.I)


def plugin_dirs(root: Path) -> list[Path]:
    out = []
    if not root.is_dir():
        return out
    for p in sorted(root.iterdir()):
        if not p.is_dir() or p.name in SKIP or p.name.startswith("."):
            continue
        if (p / "__init__.py").is_file():
            out.append(p)
    return out


def _imports(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def _except_handlers(tree: ast.AST) -> list[ast.ExceptHandler]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]


def _call_names(tree: ast.AST) -> list[ast.Call]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call)]


def check_hi6(path: Path, tree: ast.AST) -> list[str]:
    findings = []
    for name in sorted(_imports(tree)):
        if name in BANNED:
            findings.append(f"H-I6 {path}: banned import {name}")
        elif name not in STDLIB_OK and name not in LOCAL_OK and not name.startswith("_"):
            # allow relative / unknown local modules inside the plugin
            if name not in {path.parent.name.replace("-", "_")}:
                # only flag clearly third-party
                if name in BANNED:
                    findings.append(f"H-I6 {path}: non-stdlib import {name}")
    return findings


def check_hi7(path: Path, tree: ast.AST) -> list[str]:
    findings = []
    for h in _except_handlers(tree):
        if h.type is None:
            findings.append(f"H-I7 {path}: bare except")
            continue
        names = []
        if isinstance(h.type, ast.Name):
            names = [h.type.id]
        elif isinstance(h.type, ast.Tuple):
            names = [e.id for e in h.type.elts if isinstance(e, ast.Name)]
        if "BaseException" in names:
            findings.append(f"H-I7 {path}: except BaseException")
    return findings


def check_synthetic(path: Path, text: str) -> list[str]:
    findings = []
    if re.search(r"conversation_history\s*\.\s*(append|insert)\s*\(", text):
        findings.append(f"SYNTHETIC_MSG {path}: conversation_history.append/insert")
    return findings


def check_frame_and_wal(path: Path, plugin: str, tree: ast.AST, text: str) -> list[str]:
    findings = []
    uses_sqlite = "sqlite3" in _imports(tree) or "sqlite3" in text
    if not uses_sqlite:
        return findings
    # Frame rule: write path should mention plugin namespace
    if re.search(r"\.execute\(\s*['\"](\s*(INSERT|UPDATE|DELETE|REPLACE|DROP|CREATE))", text, re.I):
        if f"{plugin}/" not in text and f"{plugin}_" not in text:
            findings.append(f"FRAME {path}: sqlite write without plugin namespace {plugin}/*")
    if re.search(r"sqlite3\.connect\(", text):
        if "WAL" not in text and "journal_mode" not in text:
            findings.append(f"WAL {path}: sqlite connect without journal_mode WAL check")
    return findings


def require_wal(conn: object) -> str:
    """Runtime helper: plugins that read shared sqlite must call this first."""
    try:
        cur = conn.execute("PRAGMA journal_mode")  # type: ignore[attr-defined]
        row = cur.fetchone()
        mode = str(row[0] if row else "").upper()
        if mode != "WAL":
            return f"stale_risk journal_mode={mode}"
        return "WAL"
    except Exception as exc:
        return f"wal_check_failed {exc}"


def check_assume_guarantee(path: Path, text: str) -> list[str]:
    if ASSUME_RE.search(text) and GUAR_RE.search(text):
        return []
    return [f"AG {path}: missing ASSUME/GUARANTEE"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PLUGIN_ROOT)
    args = parser.parse_args(argv)
    findings: list[str] = []
    gains_by_hook: dict[str, list[tuple[str, float]]] = defaultdict(list)
    eps_sum = 0.0
    scanned = 0
    for d in plugin_dirs(args.root):
        init = d / "__init__.py"
        text = init.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            findings.append(f"SYNTAX {init}: {exc}")
            continue
        scanned += 1
        findings.extend(check_hi6(init, tree))
        findings.extend(check_hi7(init, tree))
        findings.extend(check_synthetic(init, text))
        findings.extend(check_frame_and_wal(init, d.name, tree, text))
        findings.extend(check_assume_guarantee(init, text))
        gm = GAIN_RE.search(text)
        em = EPS_RE.search(text)
        gain = float(gm.group(1)) if gm else 1.0
        eps = float(em.group(1)) if em else 0.0
        eps_sum += eps
        hooks = HOOK_RE.findall(text)
        yaml_p = d / "plugin.yaml"
        json_p = d / "plugin.json"
        for meta in (yaml_p, json_p):
            if meta.is_file():
                try:
                    hooks.extend(re.findall(r"-\s+((?:pre_|post_|on_)[a-z_]+)", meta.read_text()))
                except Exception:
                    pass
        hooks = sorted(set(h.strip("- ").strip() for h in hooks if h))
        if not hooks:
            # still attribute gain to unknown
            hooks = ["unknown"]
        for h in hooks:
            gains_by_hook[h].append((d.name, gain))
        if not gm:
            findings.append(f"ISS {init}: missing ISS_GAIN (treated as 1.0)")

    print("ISS composition by hook:")
    for hook, pairs in sorted(gains_by_hook.items()):
        prod = 1.0
        for name, g in pairs:
            prod *= g
        status = "OK" if prod < 1.0 else "FAIL"
        desc = " * ".join(f"{n}={g}" for n, g in pairs)
        print(f"  {hook}: {desc} => {prod:.6f} {status}")
        if prod >= 1.0:
            findings.append(f"ISS hook={hook} product={prod} >= 1")

    print(f"EPS_DP composition sum={eps_sum} budget=1.0 {'OK' if eps_sum <= 1.0 else 'FAIL'}")
    if eps_sum > 1.0:
        findings.append(f"DP composition {eps_sum} > 1.0")

    print(f"plugin-pipeline-scan plugins={scanned} findings={len(findings)}")
    for f in findings:
        print(f)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
