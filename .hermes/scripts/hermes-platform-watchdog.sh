#!/usr/bin/env bash
set -euo pipefail

HERMES_HOME=${HERMES_HOME:-/var/home/rainbow/.hermes}
CONFIG="$HERMES_HOME/config.yaml"
LINTLANG="$HERMES_HOME/integrations/lintlang/.venv/bin/lintlang"
QMD=/var/home/rainbow/.hermes/scripts/qmd-local.sh
OUT=$(mktemp)
TMP=$(mktemp)
trap 'rm -f "$OUT" "$TMP"' EXIT

record_failure() {
  local section=$1
  local command=$2
  printf '\n[%s]\n' "$section" >> "$OUT"
  printf 'command: %s\n' "$command" >> "$OUT"
  cat "$TMP" >> "$OUT"
}

run_capture() {
  : > "$TMP"
  if ! "$@" >"$TMP" 2>&1; then
    return 1
  fi
}

: > "$TMP"
python3 - "$CONFIG" >"$TMP" 2>&1 <<'PY' || record_failure "config invariants / local model presence" "python3 inline watchdog probe"
import json, pathlib, sys, urllib.request
import yaml

path = pathlib.Path(sys.argv[1])
cfg = yaml.safe_load(path.read_text())
errs = []
if not cfg.get('compression', {}).get('abort_on_summary_failure', False):
    errs.append('compression.abort_on_summary_failure is false')
rf = cfg.get('display', {}).get('runtime_footer', {})
if not rf.get('enabled', False):
    errs.append('display.runtime_footer.enabled is false')
for key in ('triage_specifier', 'title_generation', 'profile_describer', 'curator'):
    aux = cfg.get('auxiliary', {}).get(key, {})
    if aux.get('provider') != 'custom:local' or aux.get('model') != 'qwen3:8b':
        errs.append(f'auxiliary.{key} is not pinned to custom:local/qwen3:8b')
try:
    with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=5) as resp:
        data = json.load(resp)
    models = {m.get('name') for m in data.get('models', [])}
    if 'qwen3:8b' not in models:
        errs.append('ollama local model qwen3:8b is missing')
except Exception as e:
    errs.append(f'ollama unreachable: {e}')
if errs:
    print('\n'.join(errs))
    raise SystemExit(1)
PY

if ! run_capture hermes config check; then
  record_failure "hermes config check" "hermes config check"
fi

if ! run_capture hermes memory status; then
  record_failure "hermes memory status" "hermes memory status"
fi

for target in \
  "$HERMES_HOME/config.yaml" \
  "$HERMES_HOME/skills/autonomous-ai-agents/hermes-acp-routing/SKILL.md" \
  "$HERMES_HOME/skills/autonomous-ai-agents/hermes-role-pipelines/SKILL.md"
do
  if ! run_capture "$LINTLANG" scan "$target"; then
    record_failure "lintlang scan" "$LINTLANG scan $target"
  elif grep -Eq 'FAIL|CRITICAL' "$TMP"; then
    record_failure "lintlang scan" "$LINTLANG scan $target"
  fi
done

if run_capture "$QMD" doctor --json; then
  if ! python3 - <<'PY' "$TMP" >"$TMP.check" 2>&1
import json, sys
obj = json.load(open(sys.argv[1]))
ready = str(obj.get('readiness', ''))
if not ready.startswith('ready'):
    raise SystemExit(f'QMD readiness is {ready or "missing"}')
PY
  then
    cat "$TMP.check" >> "$TMP"
    record_failure "qmd readiness" "$QMD doctor --json"
  fi
  rm -f "$TMP.check"
else
  record_failure "qmd readiness" "$QMD doctor --json"
fi

if [ -s "$OUT" ]; then
  sed '/^$/N;/^\n\[/D' "$OUT"
fi
