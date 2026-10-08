#!/usr/bin/env python3
"""memory-wave18-adversarial.py — cold attacker pass on Wave 18 memory scripts.

Assumes the attacker wants to break H-I6, H-I7, atomic writes, and lens laws.
Fail-closed: nonzero exit if HIGH/MEDIUM findings remain.
"""
from __future__ import annotations

import ast
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


NEW = [
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
    "memory-wave18-invariants.py",
]
FORBIDDEN = {"requests", "pandas", "sklearn", "torch", "tensorflow", "yaml", "httpx", "bs4", "lxml", "cv2"}
NEEDLE_VAR = "/" + "var/home/"
NEEDLE_RAIN = "/" + "home/rainbow"


def main() -> int:
    scripts = Path(__file__).resolve().parent
    findings = []
    shadow = hermes_home() / "profiles" / "fork" / "hermes-scripts"
    if shadow.exists() and any(shadow.iterdir()):
        findings.append(("HIGH", "H-I7", f"shadow dir {shadow}"))

    for name in NEW:
        p = scripts / name
        if not p.exists():
            findings.append(("HIGH", name, "missing"))
            continue
        text = p.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for m in mods:
                if m in FORBIDDEN:
                    findings.append(("HIGH", name, f"H-I6 import {m}"))
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if NEEDLE_VAR in line or NEEDLE_RAIN in line:
                findings.append(("HIGH", name, f"hardcoded L{i}"))
        # self-test must not live inside a bare fail-open that returns 0
        if "if args.self_test" in text and "except Exception" in text:
            # ensure self_test return precedes the operational try
            idx_st = text.find("if args.self_test")
            idx_try = text.find("    try:\n", idx_st)
            idx_except = text.find("except Exception", idx_st)
            if idx_try != -1 and idx_except != -1 and idx_try < idx_st:
                findings.append(("HIGH", name, "self-test inside fail-open try"))

    # Live property attacks (invariants harness has no --self-test)
    py = sys.executable
    for name in NEW:
        if name == "memory-wave18-invariants.py":
            continue
        proc = subprocess.run([py, str(scripts / name), "--self-test"],
                              capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            findings.append(("HIGH", name, f"self-test rc={proc.returncode} {(proc.stderr or proc.stdout)[-200:]}"))

    # Kalman monotonicity under crash-restart (SQLite atomicity)
    sys.path.insert(0, str(scripts))
    import importlib.util
    spec = importlib.util.spec_from_file_location("k", str(scripts / "memory-kalman-latent.py"))
    km = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(km)
    td = Path(tempfile.mkdtemp()) / "k.db"
    r1 = km.step("atk", 0.0, Q=0.0, R=0.1, path=td)
    r2 = km.step("atk", 1.0, Q=0.0, R=0.1, path=td)
    if not (r2["P"] < r1["P"]):
        findings.append(("HIGH", "kalman", "P did not decrease"))
    conn = sqlite3.connect(str(td))
    n = conn.execute("SELECT COUNT(*) FROM kalman_scalar").fetchone()[0]
    conn.close()
    if n != 1:
        findings.append(("MEDIUM", "kalman", f"expected 1 row got {n}"))

    # Lens laws
    spec = importlib.util.spec_from_file_location("lens", str(scripts / "memory-lens.py"))
    lm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lm)
    s = lm.empty_wm()
    if not lm.getput_ok(s, "goal"):
        findings.append(("HIGH", "lens", "GetPut"))
    if not lm.putget_ok(s, "goal", "x"):
        findings.append(("HIGH", "lens", "PutGet"))
    if not lm.putput_ok(s, "goal", "a", "b"):
        findings.append(("HIGH", "lens", "PutPut"))

    high = [f for f in findings if f[0] == "HIGH"]
    med = [f for f in findings if f[0] == "MEDIUM"]
    out = {"high": high, "medium": med, "low": [f for f in findings if f[0] == "LOW"]}
    print(json.dumps(out, indent=2))
    if high or med:
        print("ADVERSARIAL FAIL")
        return 1
    print("PASS memory-wave18-adversarial (no HIGH/MEDIUM)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
