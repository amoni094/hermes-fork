#!/usr/bin/env python3
'''Fork profile wrapper: delegates to hermes-scripts implementation.'''
import os
import runpy
import sys
from pathlib import Path

def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p

TARGET = _hermes_home() / "hermes-scripts" / 'memory-wave18-invariants.py'
if not TARGET.exists():
    print("ERROR: target script missing: " + str(TARGET), file=sys.stderr)
    sys.exit(2)
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name="__main__")
