#!/usr/bin/env python3
"""l1-promote.py — extract-running lock + bytecode restore.

The original 1472-line source (66004 bytes, 2026-09-07 03:52) was zeroed by a
failed patch-tool write on this root-owned path. Runtime is restored from
__pycache__/l1-promote.cpython-314.pyc (compiled 2026-08-29; may lag the
Sep 7 source). A copy also lives at
scripts/references/l1-promote.cpython-314.pyc.bak.

If ~/.hermes/.l1-extract-running exists, exit 0 so this cycle does not race
l1-extract writing memory-facts/YYYY-MM-DD.md.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import math
import os
import sqlite3
import sys
from pathlib import Path

LOCK = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / ".l1-extract-running"
METACOG_DB = Path(
    os.environ.get(
        "MH_DB",
        str(Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "memory-facts" / "metacognitive.db"),
    )
)
_HERE = Path(__file__).resolve().parent
_PYC_CANDIDATES = [
    # cpython-314 first: payload compiled for 3.14, re-exec fires if running 3.11
    _HERE / "__pycache__" / "l1-promote.cpython-314.pyc",
    _HERE.parent.parent.parent / "scripts" / "references" / "l1-promote.cpython-314.pyc.bak",
    _HERE.parent.parent.parent / "scripts" / "__pycache__" / "l1-promote.cpython-314.pyc",
    # cpython-311 last: wrapper fallback (for inspection only, not payload)
    _HERE / "__pycache__" / "l1-promote.cpython-311.pyc",
]

# Resolve python3.14 with fallback to lower versions (fragile if hardcoded; Silverblue
# updates via rpm-ostree can remove 3.14 between rebases). ADV-FIX-2 (2026-09-22).
_SYS_PYTHON = next(
    (_v for _v in ["/usr/bin/python3.14", "/usr/bin/python3.13", "/usr/bin/python3.12"]
     if __import__("os").path.exists(_v)),
    "/usr/bin/python3",  # last resort: system default (may be 3.11)
)


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
        print("l1-promote bytecode missing — cannot run", file=sys.stderr)
        sys.exit(1)
    # Ensure scripts/ dir is on sys.path so the restored bytecode can import
    # siblings (l1-tracegrant, l1-graphiti-write, etc.) without FileNotFoundError.
    scripts_dir = str(_HERE)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    loader = importlib.machinery.SourcelessFileLoader("l1_promote_restored", str(pyc))
    spec = importlib.util.spec_from_file_location("l1_promote_restored", str(pyc), loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _n_star_hoeffding(eps=0.1, alpha=0.05):
    import math
    return math.ceil(math.log(2.0 / alpha) / (2.0 * eps ** 2))


def _underpowered_skip(skill: str) -> bool:
    """SPRT->PAC-Bayes underpowered gate for stable-tier skill promotion.

    Return True if this skill should be skipped (reason=underpowered).
    Fail-open: missing DB, query failure, or any exception → False (do not skip).
    """
    try:
        if not METACOG_DB.exists():
            return False
        conn = sqlite3.connect(str(METACOG_DB))
        try:
            rows = conn.execute(
                "SELECT total, successes FROM skill_profiles WHERE skill=?",
                (skill,),
            ).fetchall()
        finally:
            conn.close()
        sum_total = sum(int(r[0] or 0) for r in rows)
        sum_successes = sum(int(r[1] or 0) for r in rows)
        laplace_rate = (sum_successes + 1) / (sum_total + 2)
        n_star = _n_star_hoeffding(eps=0.1, alpha=0.05)
        if sum_total < n_star:
            print(
                f"WARNING: skip promotion skill={skill!r} reason="
                f"underpowered (Hoeffding eps=0.1 alpha=0.05 n_star={n_star}) "
                f"sum_total={sum_total} laplace_rate={laplace_rate:.4f}",
                file=sys.stderr,
            )
            return True
        return False
    except Exception:
        return False


def _filter_stable_skill_candidates(candidates):
    """Skip underpowered skills before stable-tier promotion. Never raises."""
    kept = []
    try:
        for cand in candidates or []:
            try:
                skill = cand.get("skill") if isinstance(cand, dict) else cand
                if skill is None:
                    kept.append(cand)
                    continue
                if _underpowered_skip(str(skill)):
                    continue
                kept.append(cand)
            except Exception:
                kept.append(cand)
    except Exception:
        return candidates
    return kept


def _install_underpowered_gate(mod) -> None:
    """Attach fail-open underpowered skip at stable-tier promote decision points.

    TODO(COH-6): underpowered gate cannot identify skill at promotion site.
    Restored bytecode promote path (process_date / promote_ripe_activefacts)
    iterates raw facts, not named skills — no skill id is available to pass
    to underpowered_skip(). Gate is advisory only until a skill identifier
    exists on the promote path.
    """
    try:
        mod.underpowered_skip = _underpowered_skip
        cands = getattr(mod, "skill_candidates", None)
        if cands:
            mod.skill_candidates = _filter_stable_skill_candidates(cands)
        orig_process = getattr(mod, "process_date", None)
        orig_ripe = getattr(mod, "promote_ripe_activefacts", None)

        def _gate_named_skill(skill) -> bool:
            """Return True if promotion should skip. Fail-open on any error."""
            try:
                if not skill:
                    return False
                return bool(_underpowered_skip(str(skill)))
            except Exception:
                return False

        if orig_process is not None:
            def process_date_gated(*args, **kwargs):
                try:
                    skill = kwargs.get("skill")
                    if _gate_named_skill(skill):
                        n_star = _n_star_hoeffding(eps=0.1, alpha=0.05)
                        print(
                            f"WARNING: skipping promotion of {skill} — "
                            f"underpowered (n_star={n_star})",
                            file=sys.stderr,
                        )
                        return {"skipped": True, "reason": "underpowered"}
                except Exception:
                    pass
                return orig_process(*args, **kwargs)

            mod.process_date = process_date_gated

        if orig_ripe is not None:
            def promote_ripe_gated(*args, **kwargs):
                try:
                    skill = kwargs.get("skill")
                    if _gate_named_skill(skill):
                        n_star = _n_star_hoeffding(eps=0.1, alpha=0.05)
                        print(
                            f"WARNING: skipping promotion of {skill} — "
                            f"underpowered (n_star={n_star})",
                            file=sys.stderr,
                        )
                        return 0
                except Exception:
                    pass
                return orig_ripe(*args, **kwargs)

            mod.promote_ripe_activefacts = promote_ripe_gated
    except Exception:
        pass


def main():
    _reexec_if_wrong_python()
    if "--show" in sys.argv or "--tracegrant-audit" in sys.argv:
        return _load().main()
    if LOCK.exists():
        print("l1-extract still running — skipping promote this cycle")
        sys.exit(0)
    mod = _load()
    print(
        "WARNING: underpowered gate cannot identify skill at promotion site — gate is advisory only",
        file=sys.stderr,
    )
    try:
        _install_underpowered_gate(mod)
    except Exception:
        pass
    return mod.main()


if __name__ == "__main__":
    raise SystemExit(main() or 0)
