#!/usr/bin/env python3
"""l1-extract.py — lockfile wrapper + bytecode restore.

The original 662-line source (28631 bytes, 2026-09-07 05:26) was zeroed by a
failed patch-tool write on this root-owned path. Runtime is restored from
__pycache__/l1-extract.cpython-314.pyc (same mtime as the wiped source).
A copy also lives at scripts/references/l1-extract.cpython-314.pyc.bak.

Cross-job lock: ~/.hermes/.l1-extract-running
l1-promote.py skips a cycle while this lock exists so promote cannot read a
partial YYYY-MM-DD.md while extract is still writing L1 candidates.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import struct
import sys
from pathlib import Path

LOCK = Path("~/.hermes/.l1-extract-running").expanduser()
_HERE = Path(__file__).resolve().parent
_PYC_CANDIDATES = [
    _HERE / "references" / "l1-extract.cpython-314.pyc.bak",
    _HERE / "__pycache__" / "l1-extract.cpython-314.pyc",
]

_SYS_PYTHON = "/usr/bin/python3"


def _pyc_magic(path: Path) -> bytes:
    try:
        return path.read_bytes()[:4]
    except OSError:
        return b""


def _reexec_if_wrong_python() -> None:
    """If our pyc is compiled for a different Python, re-exec under system python3."""
    pyc = next((p for p in _PYC_CANDIDATES if p.exists() and p.stat().st_size > 0), None)
    if pyc is None:
        return
    pyc_magic = _pyc_magic(pyc)
    our_magic = importlib.util.MAGIC_NUMBER
    if pyc_magic != our_magic and sys.executable != _SYS_PYTHON:
        os.execv(_SYS_PYTHON, [_SYS_PYTHON] + sys.argv)


def _load():
    pyc = next((p for p in _PYC_CANDIDATES if p.exists() and p.stat().st_size > 0), None)
    if pyc is None:
        print("l1-extract bytecode missing — cannot run", file=sys.stderr)
        sys.exit(1)
    loader = importlib.machinery.SourcelessFileLoader("l1_extract_restored", str(pyc))
    spec = importlib.util.spec_from_file_location("l1_extract_restored", str(pyc), loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    _reexec_if_wrong_python()
    if "--show" in sys.argv:
        return _load().main()
    LOCK.touch()
    try:
        return _load().main()
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main() or 0)
