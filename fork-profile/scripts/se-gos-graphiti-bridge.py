#!/usr/bin/env python3
"""Thin wrapper: SE-GoS lives in the skill scripts/ dir (host scripts/ is root-owned)."""
import runpy, pathlib, sys
TARGET = pathlib.Path('/var/home/rainbow/.hermes/skills/autonomous-ai-agents/autonomous-agent-loop-design/scripts/se-gos-graphiti-bridge.py')
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name='__main__')
