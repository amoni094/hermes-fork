#!/usr/bin/env python3
import os, subprocess, sys
from pathlib import Path
# Finding 9 fix: default HERMES_HOME to the fork profile so memory-staleness.py
# reads FORK/memories/MEMORY.md, not root ~/memories/MEMORY.md.
os.environ.setdefault('HERMES_HOME', '/var/home/rainbow/.hermes/profiles/fork')
os.environ.setdefault('HERMES_PROFILE', 'fork')
target = Path.home() / '.hermes/hermes-scripts/memory-staleness.py'
r = subprocess.run([sys.executable, str(target)], env=os.environ)
sys.exit(r.returncode)
