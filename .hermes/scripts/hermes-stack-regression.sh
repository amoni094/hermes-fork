#!/usr/bin/env bash
set -euo pipefail
HERMES_HOME=${HERMES_HOME:-/var/home/rainbow/.hermes}
LINTLANG=/var/home/rainbow/.hermes/integrations/lintlang/.venv/bin/lintlang
QMD=/var/home/rainbow/.hermes/scripts/qmd-local.sh
OUT=$(mktemp)
TMP=$(mktemp)
trap 'rm -f "$OUT" "$TMP"' EXIT

record_failure() {
  printf '\n[%s]\n' "$1" >> "$OUT"
  cat "$TMP" >> "$OUT"
}

run_quiet() {
  : > "$TMP"
  if ! "$@" >"$TMP" 2>&1; then
    record_failure "$*"
    return 1
  fi
}

run_quiet hermes config check || true
run_quiet hermes memory status || true

for target in \
  "$HERMES_HOME/config.yaml" \
  "$HERMES_HOME/skills/autonomous-ai-agents/hermes-acp-routing/SKILL.md" \
  "$HERMES_HOME/skills/autonomous-ai-agents/hermes-role-pipelines/SKILL.md"
  do
  : > "$TMP"
  if ! "$LINTLANG" scan "$target" >"$TMP" 2>&1; then
    record_failure "lintlang scan $target"
  elif grep -Eq 'FAIL|CRITICAL' "$TMP"; then
    record_failure "lintlang scan $target"
  fi
done

if run_quiet "$QMD" doctor --json; then
  if ! python3 - <<'PY' "$TMP"; then
import json, sys
obj=json.load(open(sys.argv[1]))
ready=str(obj.get('readiness',''))
if not ready.startswith('ready'):
    raise SystemExit(1)
PY
    record_failure "$QMD doctor --json"
  fi
else
  true
fi

if [ -s "$OUT" ]; then
  cat "$OUT"
fi
