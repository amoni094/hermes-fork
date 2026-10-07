#!/usr/bin/env python3
"""
hermes_paths.py — Profile-aware path resolution for Hermes fork scripts.

Usage in any script:
    from hermes_paths import hermes_cache, hermes_root, hermes_scripts

HERMES_HOME env var overrides the base (set to ~/.hermes/profiles/fork for fork profile).
HERMES_PROFILE env var selects a sub-profile under ~/.hermes/profiles/.
When neither is set, defaults to ~/.hermes (default profile behaviour).
"""
from __future__ import annotations
import os
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
if not Path(_hermes_base).is_dir():
    print(f'ERROR: HERMES_HOME={_hermes_base} does not exist or is not a directory',
          file=sys.stderr)
    sys.exit(2)
_hermes_profile = os.environ.get("HERMES_PROFILE", "")

if _hermes_profile and "profiles" not in str(_hermes_base):
    hermes_root: Path = _hermes_base / "profiles" / _hermes_profile
else:
    hermes_root = _hermes_base

hermes_cache: Path = hermes_root / "cache"
hermes_scripts: Path = Path(__file__).parent  # always the scripts dir itself


def cache(subpath: str) -> Path:
    """Return a profile-aware cache path and ensure its parent directory exists."""
    p = hermes_cache / subpath
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def state_db() -> Path:
    """Return the profile-aware state.db path."""
    return hermes_root / "state.db"


__all__ = ["hermes_root", "hermes_cache", "hermes_scripts", "cache", "state_db"]