#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "usage: $0 <skill-name> [output-dir]" >&2
  exit 2
fi
SKILL="$1"
OUTDIR="${2:-}"
ROOT=/var/home/rainbow/.hermes/integrations/hermes-agent-self-evolution/output/${SKILL}
LINTLANG=/var/home/rainbow/.hermes/integrations/lintlang/.venv/bin/lintlang
REPORT_ROOT=/var/home/rainbow/.hermes/self-evolution/reports/${SKILL}
mkdir -p "$REPORT_ROOT"
if [ -z "$OUTDIR" ]; then
  OUTDIR=$(find "$ROOT" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)
fi
[ -n "$OUTDIR" ] && [ -d "$OUTDIR" ]
METRICS="$OUTDIR/metrics.json"
EVOLVED="$OUTDIR/evolved_skill.md"
BASELINE="$OUTDIR/baseline_skill.md"
python3 - <<'PY' "$METRICS" "$EVOLVED" "$BASELINE" "$REPORT_ROOT"
import json, sys, pathlib, difflib, datetime
metrics = json.loads(pathlib.Path(sys.argv[1]).read_text())
evolved = pathlib.Path(sys.argv[2]).read_text()
baseline = pathlib.Path(sys.argv[3]).read_text()
report_root = pathlib.Path(sys.argv[4])
report_root.mkdir(parents=True, exist_ok=True)
passed = bool(metrics.get('constraints_passed')) and float(metrics.get('improvement', 0)) > 0
stamp = metrics.get('timestamp') or datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
diff = ''.join(difflib.unified_diff(baseline.splitlines(True), evolved.splitlines(True), fromfile='baseline_skill.md', tofile='evolved_skill.md'))
(report_root / f'{stamp}.diff').write_text(diff)
report = {
  'skill_name': metrics.get('skill_name'),
  'timestamp': stamp,
  'baseline_score': metrics.get('baseline_score'),
  'evolved_score': metrics.get('evolved_score'),
  'improvement': metrics.get('improvement'),
  'constraints_passed': metrics.get('constraints_passed'),
  'gate_passed': passed,
  'output_dir': str(pathlib.Path(sys.argv[1]).parent),
}
(report_root / f'{stamp}.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
if not passed:
    raise SystemExit(1)
PY
"$LINTLANG" scan "$EVOLVED"
echo "PASS: evolution review cleared for $OUTDIR"
