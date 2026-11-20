#!/usr/bin/env python3
"""One-time merge of BM25-seeded beta priors into live skill-beta-state.json.
Live entries (real feedback) take precedence over seeded priors."""
import json, os
from pathlib import Path

HERMES_HOME = Path(os.environ.get('HERMES_HOME', Path.home() / '.hermes'))
PROFILE = os.environ.get('HERMES_PROFILE', 'fork')
ROOT = (HERMES_HOME / 'profiles' / PROFILE) if PROFILE and 'profiles' not in str(HERMES_HOME) else HERMES_HOME

SEEDED = ROOT / 'cache' / 'skill-beta-state-seeded.json'
LIVE = ROOT / 'cache' / 'skill-beta-state.json'

seeded = json.loads(SEEDED.read_text()) if SEEDED.exists() else {}
live = json.loads(LIVE.read_text()) if LIVE.exists() else {}

# Nested dump {ts, skills:{...}} vs flat {skill: prior}
if isinstance(seeded, dict) and isinstance(seeded.get('skills'), dict) and 'alpha' not in seeded['skills']:
    seeded = seeded['skills']

# Only add skills that don't already have real feedback
n_added = 0
for skill, prior in seeded.items():
    if isinstance(prior, dict) and skill not in live:
        live[skill] = prior
        n_added += 1

# Write back atomically
tmp = LIVE.with_suffix('.tmp')
tmp.write_text(json.dumps(live, indent=2))
os.replace(tmp, LIVE)
print(json.dumps({'n_added': n_added, 'n_kept': len(live) - n_added, 'n_total': len(live)}))
