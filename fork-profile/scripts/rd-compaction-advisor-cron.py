#!/usr/bin/env python3
"""Cron wrapper: scheduler does not pass job.argv, so force --from-log."""
import os
import subprocess
import sys
from pathlib import Path

os.environ["HERMES_HOME"] = "/var/home/rainbow/.hermes"
os.environ["HERMES_PROFILE"] = "fork"
target = Path(__file__).with_name("rd-compaction-advisor.py")
r = subprocess.run([sys.executable, str(target), "--from-log"], env=os.environ, check=False)
sys.exit(r.returncode)
