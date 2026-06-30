#!/usr/bin/env bash
set -euo pipefail

CONFIG="$HOME/.hermes/config.yaml"
OLLAMA_URL="http://localhost:11434/api/tags"

issues="$(python3 - <<'PY' "$CONFIG"
import sys, yaml, pathlib
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
    import json, urllib.request
    with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=5) as resp:
        data = json.load(resp)
    models = {m.get('name') for m in data.get('models', [])}
    if 'qwen3:8b' not in models:
        errs.append('ollama local model qwen3:8b is missing')
except Exception as e:
    errs.append(f'ollama unreachable: {e}')
print('\n'.join(errs))
PY
)"

if [[ -n "$issues" ]]; then
  printf '%s\n' "$issues"
fi
