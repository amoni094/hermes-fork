#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "usage: $0 <output-dir>" >&2
  exit 2
fi
OUTDIR=$(realpath "$1")
LINTLANG=/var/home/rainbow/.hermes/integrations/lintlang/.venv/bin/lintlang
QMD=/var/home/rainbow/.hermes/scripts/qmd-local.sh
STATUS=0
check(){ echo "==> $*"; "$@" || STATUS=1; }
check test -d "$OUTDIR"
if [ -f "$OUTDIR/metrics.json" ]; then
  check python3 - <<'PY' "$OUTDIR/metrics.json"
import json, sys
m=json.load(open(sys.argv[1]))
assert m.get('constraints_passed') is True, 'constraints did not pass'
assert float(m.get('improvement', 0)) > 0, 'non-positive improvement'
print('metrics gate ok')
PY
fi
if [ -f "$OUTDIR/evolved_skill.md" ]; then
  if [ -x "$LINTLANG" ]; then
    check "$LINTLANG" scan "$OUTDIR/evolved_skill.md"
  else
    echo "==> WARN: lintlang not found at $LINTLANG; skipping SKILL.md lint (install lintlang to enable)"
  fi
fi
check hermes config check
check "$QMD" doctor --json
if [ $STATUS -ne 0 ]; then
  echo "BLOCKED: candidate failed second-pass gate"
  exit 1
fi
echo "PASS: candidate cleared deterministic second-pass gate"
