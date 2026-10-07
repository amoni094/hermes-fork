#!/usr/bin/env python3
"""evograph-with-homology.py — Daily skill health: evograph build + persistent homology gaps.

Combines:
  1. evograph-skill-editor.py --build  (EvoGraph health graph from yield data)
  2. skill-persistent-homology.py gaps  (persistent H0 gaps = isolated skill clusters)
  3. skill-persistent-homology.py redundant  (H1 redundant skill clusters)

Theory:
  - EvoGraph (arXiv:2606.04917): failure-aware insight graph; detects yield < 0.35 skills
  - Persistent homology (Edelsbrunner & Harer, Computational Topology Ch.7):
      H0 gaps = topics with no adjacent skills (coverage gaps)
      H1 short bars = redundant skill clusters (candidates for merging)
  - Ghrist "Elementary Applied Topology" Ch.3: Vietoris-Rips complex over TF-IDF space

Both outputs go to stdout. Exit 0 always (individual failures are advisory only).
"""
from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path

_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "")
_SCRIPTS = _HH / "scripts"
_FORK_SCRIPTS = (_HH / "profiles" / _HP) / "scripts" if _HP else _SCRIPTS
_ENV = {**os.environ, "HERMES_HOME": str(_HH), "HERMES_PROFILE": _HP}


def _run(script: Path, *args: str) -> None:
    """Run a script, print output, swallow errors (advisory)."""
    try:
        cmd = [sys.executable, str(script)] + list(args)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=_ENV)
        if r.stdout:
            print(r.stdout.rstrip())
        if r.stderr:
            print(f"[stderr] {r.stderr.rstrip()[:400]}", file=sys.stderr)
        if r.returncode not in (0, 1):
            print(f"[warning] {script.name} exited {r.returncode}", file=sys.stderr)
    except Exception as exc:
        print(f"[advisory] {script.name} failed: {exc}", file=sys.stderr)


def main() -> None:
    # Step 1: EvoGraph build + report
    evograph = _FORK_SCRIPTS / "evograph-skill-editor.py"
    if not evograph.exists():
        evograph = _SCRIPTS / "evograph-skill-editor.py"
    if evograph.exists():
        print("=== EvoGraph: build ===")
        _run(evograph, "--build")
        print("=== EvoGraph: report ===")
        _run(evograph, "--report")
    else:
        print("[advisory] evograph-skill-editor.py not found", file=sys.stderr)

    # Step 2: Persistent homology gaps (coverage gaps)
    homology = _SCRIPTS / "skill-persistent-homology.py"
    if homology.exists():
        print("\n=== Persistent Homology: coverage gaps (H0) ===")
        _run(homology, "gaps")
        print("\n=== Persistent Homology: redundant clusters (H1) ===")
        _run(homology, "redundant")
        print("\n=== Persistent Homology: summary ===")
        _run(homology, "summary")
    else:
        print("[advisory] skill-persistent-homology.py not found", file=sys.stderr)


if __name__ == "__main__":
    main()
