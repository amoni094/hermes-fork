#!/usr/bin/env python3
"""Cron wrapper: rebuild skill-router-index unconditionally.
Called by hermes cron scheduler (no args supported) — drives --build logic directly.
"""
import importlib.util, pathlib, sys

_script = pathlib.Path(__file__).parent / "skill-router-index.py"
if not _script.exists():
    print(f"[skill-router-index-rebuild] ERROR: {_script} not found", file=sys.stderr)
    sys.exit(1)
try:
    spec = importlib.util.spec_from_file_location("skill_router_index", _script)
    if spec is None or spec.loader is None:
        raise ImportError(f"spec_from_file_location returned None for {_script}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
except Exception as exc:
    print(f"[skill-router-index-rebuild] ERROR loading {_script}: {exc}", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    mod.cmd_build()
