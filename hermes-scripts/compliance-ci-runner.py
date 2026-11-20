#!/usr/bin/env python3
"""Batch runner: extracts compliance scores from compliance-scores.jsonl and
feeds them to safe-compliance-confidence.py as a proper calibration list."""
import json, os, subprocess, sys
from pathlib import Path

def _hermes_home() -> Path:
    env = os.environ.get('HERMES_HOME', '').strip()
    p = Path(env) if env else Path.home() / '.hermes'
    # strip profile subdir if caller passed profiles/fork instead of base
    if p.name != '.hermes' and p.parent.name == 'profiles':
        p = p.parent.parent
    return p

HERMES_HOME = _hermes_home()
PROFILE = os.environ.get('HERMES_PROFILE', 'fork')
cache = HERMES_HOME / 'profiles' / PROFILE / 'cache'
jsonl = cache / 'compliance-scores.jsonl'
out = cache / 'compliance-ci-state.json'

if '--self-test' in sys.argv:
    # Synthetic: 50 scores, mean=0.85
    import random, tempfile
    scores = [round(random.gauss(0.85, 0.07), 3) for _ in range(50)]
    tf = Path(tempfile.mktemp(suffix='.json'))
    tf.write_text(json.dumps(scores), encoding='utf-8')
    r = subprocess.run([sys.executable,
                        str(HERMES_HOME / 'hermes-scripts' / 'safe-compliance-confidence.py'),
                        '--score', '0.85', '--calibration-file', str(tf)],
                       capture_output=True, text=True,
                       env={**os.environ, 'HERMES_HOME': str(HERMES_HOME)})
    tf.unlink(missing_ok=True)
    result = json.loads(r.stdout)
    assert result.get('status') != 'insufficient_data', "insufficient_data with 50 scores"
    assert result.get('lower') is not None and result.get('upper') is not None
    assert result['lower'] <= 0.85 <= result['upper'], f"score not in CI: {result}"
    print(f"[compliance-ci-runner] --self-test PASS n={result['n_calibration']} ci=[{result['lower']:.3f},{result['upper']:.3f}]")
    sys.exit(0)

# --run mode
if not jsonl.exists():
    print(json.dumps({'status': 'no_data', 'ts': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}))
    sys.exit(0)

scores = []
for line in jsonl.open():
    line = line.strip()
    if not line: continue
    try:
        rec = json.loads(line)
        v = rec.get('compliance_score') or rec.get('accuracy') or rec.get('score')
        if v is not None:
            scores.append(float(v))
    except Exception:
        pass

if not scores:
    print(json.dumps({'status': 'no_scores', 'n': 0}))
    sys.exit(0)

import tempfile
tf = Path(tempfile.mktemp(suffix='.json'))
tf.write_text(json.dumps(scores))
mean_score = sum(scores) / len(scores)
r = subprocess.run([sys.executable,
                    str(HERMES_HOME / 'hermes-scripts' / 'safe-compliance-confidence.py'),
                    '--score', str(round(mean_score, 4)),
                    '--calibration-file', str(tf)],
                   capture_output=True, text=True,
                   env={**os.environ, 'HERMES_HOME': str(HERMES_HOME)})
tf.unlink(missing_ok=True)
result = json.loads(r.stdout)
result['n_raw'] = len(scores)
out.parent.mkdir(parents=True, exist_ok=True)
tmp = out.with_suffix('.tmp')
tmp.write_text(json.dumps(result, indent=2) + '\n')
tmp.replace(out)
print(json.dumps(result))
