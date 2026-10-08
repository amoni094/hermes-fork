#!/usr/bin/env python3
"""Fork profile wrapper: delegates to hermes-scripts implementation."""
import runpy
import sys
from pathlib import Path

TARGET = Path('/var/home/rainbow/.hermes/hermes-scripts/progress-mirage-gate.py')
if not TARGET.exists():
    print(f"ERROR: target script missing: {TARGET}", file=sys.stderr)
    sys.exit(2)
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name="__main__")
