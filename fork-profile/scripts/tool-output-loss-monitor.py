#!/usr/bin/env python3
'''Fork profile wrapper: delegates to hermes-scripts implementation.'''
import json, os, runpy, sys
from pathlib import Path

def _scripts_dir() -> Path:
    here = Path(__file__).resolve()
    name = here.name
    cands = []
    if len(here.parents) >= 4:
        cands.append(here.parents[3] / "hermes-scripts")
    cands.append(Path.home() / ".hermes" / "hermes-scripts")
    env = os.environ.get("HERMES_HOME", "").strip()
    if env:
        p = Path(env)
        if p.name != ".hermes" and p.parent.name == "profiles":
            p = p.parent.parent
        cands.append(p / "hermes-scripts")
    for d in cands:
        if (d / name).is_file():
            return d
    return cands[0]

TARGET = _scripts_dir() / Path(__file__).name
if not TARGET.exists():
    print(json.dumps({"status": "error", "reason": "target_missing", "target": str(TARGET)}))
    sys.exit(0)
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name="__main__")
