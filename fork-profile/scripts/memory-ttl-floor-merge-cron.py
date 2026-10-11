#!/usr/bin/env python3
import os, subprocess, sys
from pathlib import Path
os.environ.setdefault('HERMES_HOME', '/var/home/rainbow/.hermes')
os.environ.setdefault('HERMES_PROFILE', 'fork')
target = Path.home() / '.hermes/hermes-scripts/memory-ttl-floor-merge.py'
r = subprocess.run([sys.executable, str(target)], env=os.environ)
sys.exit(r.returncode)
