#!/usr/bin/env python3
"""
################################################################################
# RECOVERED FROM BYTECODE
#
# Source: /var/home/rainbow/.hermes/scripts/__pycache__/l1-extract.cpython-314.pyc
# Recovery method: dis.get_instructions() + marshal.loads() on the .pyc header
# Original file: ~/.hermes/scripts/l1-extract.py (662 lines, 28631 bytes, 2026-09-07 05:26)
# Original wiped by: failed patch-tool write on root-owned path
#
# This file is a readable pseudocode reconstruction of the bytecode. It is NOT
# a byte-for-byte restoration of the original 662-line source. Functions that
# the original source contained beyond the stub shim (the actual L1 extraction
# logic) lived in the bytecode payload loaded via SourcelessFileLoader —
# that payload IS the .pyc itself. The functions below are faithfully
# reconstructed from dis.get_instructions() output.
#
# Status: py_compile-verified stub. Does not re-implement the full 662-line
# L1 extraction logic (which ran inside the loaded module). It documents the
# shim layer exactly, and notes where the original logic resided.
################################################################################
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import struct  # imported at module level in original; used for pyc header parsing in original 662-line body
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Module-level constants (recovered from co_consts and co_names)
# ---------------------------------------------------------------------------

LOCK = Path("~/.hermes/.l1-extract-running").expanduser()
"""Cross-job lock file. l1-promote.py skips a cycle while this lock exists
so promote cannot read a partial YYYY-MM-DD.md while extract is still writing
L1 candidates."""

_HERE = Path(__file__).resolve().parent

_PYC_CANDIDATES = [
    _HERE / "references" / "l1-extract.cpython-314.pyc.bak",
    _HERE / "__pycache__" / "l1-extract.cpython-314.pyc",
]
"""Ordered list of .pyc locations tried at runtime. The .bak copy in
references/ is the primary fallback; __pycache__ is the secondary."""

_SYS_PYTHON = "/usr/bin/python3"
"""System python3 used when re-execing under a different interpreter magic."""


# ---------------------------------------------------------------------------
# _pyc_magic(path: Path) -> bytes
#
# Bytecode summary (cpython-314, line 32):
#   try:
#     return path.read_bytes()[:4]
#   except OSError:
#     return b''
#
# Purpose: Read the 4-byte magic number from a .pyc file.
# Returns b'' on any OSError (missing file, permission denied, etc).
# ---------------------------------------------------------------------------
def _pyc_magic(path: Path) -> bytes:
    """Return first 4 bytes (magic number) of a .pyc file, or b'' on OSError."""
    try:
        return path.read_bytes()[:4]
    except OSError:
        return b""


# ---------------------------------------------------------------------------
# _reexec_if_wrong_python() -> None
#
# Bytecode summary (cpython-314, line 39):
#   pyc = next((p for p in _PYC_CANDIDATES if p.exists() and p.stat().st_size > 0), None)
#   if pyc is None:
#     return
#   pyc_magic = _pyc_magic(pyc)
#   our_magic  = importlib.util.MAGIC_NUMBER
#   if pyc_magic != our_magic and sys.executable != _SYS_PYTHON:
#     os.execv(_SYS_PYTHON, [_SYS_PYTHON] + sys.argv)
#
# Purpose: If the .pyc was compiled for a different CPython version than the
# running interpreter, re-exec the script under the system python3, which is
# expected to match the .pyc magic. Avoids marshal version mismatch errors.
# ---------------------------------------------------------------------------
def _reexec_if_wrong_python() -> None:
    """Re-exec under system python3 if the .pyc magic doesn't match ours."""
    pyc = next((p for p in _PYC_CANDIDATES if p.exists() and p.stat().st_size > 0), None)
    if pyc is None:
        return
    pyc_magic = _pyc_magic(pyc)
    our_magic = importlib.util.MAGIC_NUMBER
    if pyc_magic != our_magic and sys.executable != _SYS_PYTHON:
        os.execv(_SYS_PYTHON, [_SYS_PYTHON] + sys.argv)


# ---------------------------------------------------------------------------
# _load() -> module
#
# Bytecode summary (cpython-314, line 50):
#   pyc = next((p for p in _PYC_CANDIDATES if p.exists() and p.stat().st_size > 0), None)
#   if pyc is None:
#     print("l1-extract bytecode missing — cannot run", file=sys.stderr)
#     sys.exit(1)
#   loader = importlib.machinery.SourcelessFileLoader("l1_extract_restored", str(pyc))
#   spec = importlib.util.spec_from_file_location(
#       "l1_extract_restored", str(pyc), loader=loader)
#   mod = importlib.util.module_from_spec(spec)
#   spec.loader.exec_module(mod)
#   return mod
#
# Purpose: Load the .pyc as a module without a corresponding .py source.
# The loaded module is the REAL l1-extract implementation (662 lines worth).
# It must expose a main() callable.
#
# NOTE: The 662-line original source lived inside the payload of the .pyc.
# That payload included the full L1 extraction pipeline logic (session JSONL
# parsing, candidate scoring, lockfile-guarded writing of YYYY-MM-DD.md, etc).
# Only the shim layer (_pyc_magic, _reexec_if_wrong_python, _load, main) is
# recoverable directly from the outer code object; the inner payload was
# exec'd dynamically and is not separately decompilable from this .pyc without
# a full decompiler (e.g. decompile3 / pycdc).
# ---------------------------------------------------------------------------
def _load():
    """Load the real l1-extract implementation from .pyc bytecode."""
    pyc = next((p for p in _PYC_CANDIDATES if p.exists() and p.stat().st_size > 0), None)
    if pyc is None:
        print("l1-extract bytecode missing — cannot run", file=sys.stderr)
        sys.exit(1)
    loader = importlib.machinery.SourcelessFileLoader("l1_extract_restored", str(pyc))
    spec = importlib.util.spec_from_file_location(
        "l1_extract_restored", str(pyc), loader=loader
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# main() -> int | None
#
# Bytecode summary (cpython-314, line 62):
#   _reexec_if_wrong_python()
#   if "--show" in sys.argv:
#     return _load().main()
#   LOCK.touch()
#   try:
#     return _load().main()
#   finally:
#     LOCK.unlink(missing_ok=True)
#
# Purpose: Entry point. The --show flag bypasses the lockfile (used for
# inspection/debug). Normal runs acquire the cross-job lock, delegate to
# the loaded module's main(), then release the lock in a finally block.
# ---------------------------------------------------------------------------
def main():
    """Entry point: optionally bypass lock (--show), otherwise lock + run."""
    _reexec_if_wrong_python()
    if "--show" in sys.argv:
        return _load().main()
    LOCK.touch()
    try:
        return _load().main()
    finally:
        LOCK.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Module entry
#
# Bytecode summary (cpython-314, module level, line 73):
#   if __name__ == "__main__":
#     raise SystemExit(main() or 0)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    raise SystemExit(main() or 0)
