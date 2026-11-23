"""RANSAC memory-commit gate. Fail-open, never raises out of hook."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


def _load_ransac():
    path = _hermes_home() / "hermes-scripts" / "memory-ransac-commit.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("memory_ransac_commit", str(path))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def post_tool_call(tool_name: str, result, **kwargs):
    try:
        text = ""
        if isinstance(result, str):
            text = result[:2000]
        elif isinstance(result, dict):
            text = json.dumps(result)[:2000]
        else:
            text = str(result)[:2000]
        if not text.strip():
            return None
        mod = _load_ransac()
        if mod is None:
            return None
        verdict = mod.is_inlier(text, mod.load_corpus())
        if not verdict.get("inlier"):
            print(
                f"[memory-ransac-gate] outlier residual={verdict.get('residual')} "
                f"thr={verdict.get('threshold')} tool={tool_name}",
                file=sys.stderr,
            )
        return None
    except Exception as exc:
        print(f"[memory-ransac-gate] fail-open: {exc}", file=sys.stderr)
        return None
