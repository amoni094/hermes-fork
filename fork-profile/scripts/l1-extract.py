#!/usr/bin/env python3
"""l1-extract.py — lockfile wrapper + bytecode restore.

The original 662-line source (28631 bytes, 2026-09-07 05:26) was zeroed by a
failed patch-tool write on this root-owned path. Runtime is restored from
__pycache__/l1-extract.cpython-314.pyc (same mtime as the wiped source).
A copy also lives at scripts/references/l1-extract.cpython-314.pyc.bak.

Cross-job lock: ~/.hermes/profiles/fork/cache/.l1-extract-running
l1-promote.py skips a cycle while this lock exists so promote cannot read a
partial YYYY-MM-DD.md while extract is still writing L1 candidates.
"""
from __future__ import annotations

import glob
import importlib.machinery
import importlib.util
import os
import struct
import sys
from pathlib import Path


def _bind_profile_home() -> Path:
    """Bind HERMES_HOME to the active profile data root before loading bytecode.

    Inner payload uses HERMES_HOME/memory-facts and HERMES_HOME/state.db with no
    HERMES_PROFILE join. Cron sets HERMES_HOME=~/.hermes and HERMES_PROFILE=fork;
    without this, fork jobs read/write the default profile.
    """
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        bound = base / "profiles" / profile
        os.environ["HERMES_HOME"] = str(bound)
        return bound
    return base


_HERMES_HOME = _bind_profile_home()
LOCK = _HERMES_HOME / "cache" / ".l1-extract-running"
_HERE = Path(__file__).resolve().parent
_PYC_CANDIDATES = [
    # Direct references/ in same scripts dir (works for both default and fork profile paths)
    _HERE / "references" / "l1-extract.cpython-314.pyc.bak",
    # Default profile scripts/references (absolute fallback)
    Path.home() / ".hermes" / "scripts" / "references" / "l1-extract.cpython-314.pyc.bak",
    # Legacy: 3 parents up (correct for default profile, wrong for fork)
    _HERE.parent.parent.parent / "scripts" / "references" / "l1-extract.cpython-314.pyc.bak",
    _HERE.parent.parent.parent / "scripts" / "__pycache__" / "l1-extract.cpython-314.pyc",
    # cpython-311 last: wrapper fallback (for inspection only, not payload)
    _HERE / "__pycache__" / "l1-extract.cpython-311.pyc",
]

def _find_py() -> str:
    for _p in glob.glob("/var/home/rainbow/.hermes/tools/python-3.14.9+*/bin/python3"):
        return os.path.realpath(_p)
    for _p in ["/usr/bin/python3.14", "/usr/bin/python3.13", "/usr/bin/python3.12"]:
        if os.path.exists(_p):
            return _p
    return "/usr/bin/python3"


_SYS_PYTHON = _find_py()
del _find_py


def _pyc_magic(path: Path) -> bytes:
    try:
        return path.read_bytes()[:4]
    except OSError:
        return b""


def _reexec_if_wrong_python() -> None:
    """If our pyc is compiled for a different Python, re-exec under the matching interpreter.

    In the openshell sandbox, sys.executable is /usr/bin/python3 (system python).
    _SYS_PYTHON resolves to the hermes python 3.14 binary.  When the pyc magic
    mismatches, we re-exec under _SYS_PYTHON (3.14) so it can load the 3.14 bytecode.
    If _SYS_PYTHON is not executable here (sandbox restriction), os.execv raises
    PermissionError which is caught and re-raised with a clearer message.
    """
    pyc = next((p for p in _PYC_CANDIDATES if p.exists() and p.stat().st_size > 20000), None)
    if pyc is None:
        return
    pyc_magic = _pyc_magic(pyc)
    our_magic = importlib.util.MAGIC_NUMBER
    if pyc_magic != our_magic and sys.executable != _SYS_PYTHON:
        try:
            os.execv(_SYS_PYTHON, [_SYS_PYTHON] + sys.argv)
        except (PermissionError, OSError) as exc:
            print(
                f"l1-extract: pyc magic mismatch (pyc={pyc_magic!r} this={our_magic!r}) "
                f"and re-exec to {_SYS_PYTHON!r} failed: {exc}. "
                "Add the hermes python binary to the openshell sandbox policy (binaries + read_only).",
                file=sys.stderr,
            )
            sys.exit(1)


def _load():
    pyc = next((p for p in _PYC_CANDIDATES if p.exists() and p.stat().st_size > 20000), None)
    if pyc is None:
        print("l1-extract bytecode missing — cannot run", file=sys.stderr)
        sys.exit(1)
    pyc_magic = _pyc_magic(pyc)
    our_magic = importlib.util.MAGIC_NUMBER
    if pyc_magic != our_magic:
        print(
            f"l1-extract: pyc magic mismatch — pyc={pyc_magic!r} this interpreter={our_magic!r}. "
            f"Expected _reexec_if_wrong_python() to have switched to the matching python. "
            f"Current interpreter: {sys.executable!r}. Target: {_SYS_PYTHON!r}.",
            file=sys.stderr,
        )
        sys.exit(1)
    loader = importlib.machinery.SourcelessFileLoader("l1_extract_restored", str(pyc))
    spec = importlib.util.spec_from_file_location("l1_extract_restored", str(pyc), loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _inject_api_key() -> None:
    """Load ANTHROPIC_API_KEY from ~/.hermes/.env if not already in the environment.

    The openshell sandbox strips host environment variables, so scripts that call
    the Anthropic API directly need the key re-injected from the secrets file.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env_path = Path.home() / ".hermes" / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY=") and "=" in line:
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    os.environ["ANTHROPIC_API_KEY"] = key
                    return
    except OSError:
        pass


def main():
    _reexec_if_wrong_python()
    _inject_api_key()
    if "--show" in sys.argv:
        return _load().main()
    LOCK.touch()
    try:
        return _load().main()
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main() or 0)