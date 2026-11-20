#!/usr/bin/env python3
"""Daily SAM decay pass over skill-strengths.json."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

_TRACKER = Path(__file__).resolve().parent / "skill-strength-tracker.py"


def _load_tracker():
    spec = importlib.util.spec_from_file_location("skill_strength_tracker", _TRACKER)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load " + str(_TRACKER))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SkillStrengthTracker


def main() -> int:
    Tracker = _load_tracker()
    tracker = Tracker()
    summary = tracker.decay_all()
    tracker.save()
    ranked = tracker.get_ranked()
    top = ranked[:5]
    report = {
        "n_skills": summary.get("n_skills", 0),
        "decayed": summary.get("decayed", 0),
        "top": top,
        "store": str(tracker.store_path),
    }
    print("skill-strength-decay SUMMARY " + json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
