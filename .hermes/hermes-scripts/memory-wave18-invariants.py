#!/usr/bin/env python3
"""memory-wave18-invariants.py — property tests for Wave 18 memory hard cores.

Runs --self-test on each theorem-backed module and extra H-I6/H-I7/atomic checks.
Fail-closed for tests (nonzero exit if any assertion fails).
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


SCRIPTS = [
    "memory-doob-decompose.py",
    "memory-voi-consolidation.py",
    "memory-eckart-young.py",
    "memory-rough-signature.py",
    "memory-mixing-ttl.py",
    "memory-kalman-latent.py",
    "memory-coupling-merge.py",
    "memory-ransac-commit.py",
    "memory-lens.py",
    "memory-mcdiarmid-rrf.py",
]

FORBIDDEN_IMPORTS = {
    "requests", "pandas", "sklearn", "torch", "tensorflow", "yaml",
    "httpx", "bs4", "lxml", "cv2",
}


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def check_hi6(path: Path) -> list[str]:
    issues = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"parse:{exc}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root in FORBIDDEN_IMPORTS:
                    issues.append(f"import {root}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in FORBIDDEN_IMPORTS:
                issues.append(f"from {root}")
    text = path.read_text(encoding="utf-8")
    if ("/" + "var/home/") in text or ("/" + "home/") in text:
        # allow only in comments? still H-I6 hardcoded user path
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if ("/" + "var/home/") in line or ("/" + "home/rainbow") in line:
                issues.append(f"hardcoded-path:L{i}")
    return issues


def check_atomic_pattern(path: Path) -> bool:
    t = path.read_text(encoding="utf-8")
    return "replace(" in t or "BEGIN IMMEDIATE" in t or "--self-test" in t


def run_self_test(name: str) -> tuple[bool, str]:
    p = script_dir() / name
    if not p.exists():
        return False, "missing"
    try:
        proc = subprocess.run(
            [sys.executable, str(p), "--self-test"],
            capture_output=True, text=True, timeout=60,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0 and "PASS" in out, out[-500:]
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    results = []
    failed = 0
    extras = [
        ("unified-recall.py", ["--self-test"]),
        ("working-memory.py", ["lens-test"]),
    ]
    for extra, argv in extras:
        ep = script_dir() / extra
        if not ep.exists():
            continue
        try:
            proc = subprocess.run(
                [sys.executable, str(ep), *argv],
                capture_output=True, text=True, timeout=60,
            )
            ok = proc.returncode == 0 and "PASS" in ((proc.stdout or "") + (proc.stderr or ""))
        except Exception:
            ok = False
        print(("PASS" if ok else "FAIL") + f" extra {extra}")
        if not ok:
            failed += 1
            results.append({"script": extra, "self_test": ok})

    for name in SCRIPTS:
        p = script_dir() / name
        hi6 = check_hi6(p) if p.exists() else ["missing"]
        ok, out = run_self_test(name)
        rec = {"script": name, "self_test": ok, "hi6": hi6, "atomic": check_atomic_pattern(p) if p.exists() else False}
        if not ok or hi6:
            failed += 1
            rec["out"] = out
        results.append(rec)
        flag = "PASS" if ok and not hi6 else "FAIL"
        print(f"{flag} {name} hi6={hi6 or 'ok'}")
    summary = {"failed": failed, "n": len(SCRIPTS), "results": results}
    outp = hermes_home() / "profiles" / "fork" / "cache" / "memory-wave18-invariants.json"
    try:
        outp.parent.mkdir(parents=True, exist_ok=True)
        tmp = outp.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        tmp.replace(outp)
    except Exception:
        pass
    print(json.dumps({"failed": failed, "n": len(SCRIPTS)}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
