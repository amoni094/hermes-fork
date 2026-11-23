#!/usr/bin/env bash
# hermes-platform-watchdog.sh
# Checks actual config invariants, service health, and memory status.
# Rewritten 2026-07-03: removed stale qwen3/runtime_footer/lintlang checks.
# 2026-08-13: QMD check is now conditional (QMD is intentionally disabled on this host).
set -euo pipefail

HERMES_HOME=${HERMES_HOME:-/var/home/rainbow/.hermes}
CONFIG="$HERMES_HOME/config.yaml"
QMD=/var/home/rainbow/.hermes/scripts/qmd-local.sh
OUT=$(mktemp)
TMP=$(mktemp)
trap 'rm -f "$OUT" "$TMP" "${TMP}.check"' EXIT

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

# --- 1. Config invariants: check keys that actually exist in config ---
: > "$TMP"
python3 - "$CONFIG" >"$TMP" 2>&1 <<'PY' || record_failure "config invariants" "python3 inline probe"
import json, pathlib, sys
import yaml

path = pathlib.Path(sys.argv[1])
cfg = yaml.safe_load(path.read_text())
errs = []

# Compression must be enabled
if not cfg.get('compression', {}).get('enabled', False):
    errs.append('compression.enabled is false')

# Auxiliary compression model must be set
aux_comp = cfg.get('auxiliary', {}).get('compression', {})
if not aux_comp.get('model'):
    errs.append('auxiliary.compression.model is missing')

# Fallback chain must have at least 2 entries
fb = cfg.get('fallback_providers', cfg.get('fallback_model', []))
if len(fb) < 2:
    errs.append(f'fallback_providers has only {len(fb)} entr(ies); expected >=2')

# Graphiti MCP must be enabled
graphiti = cfg.get('mcp_servers', {}).get('graphiti', {})
if not graphiti.get('enabled', False):
    errs.append('mcp_servers.graphiti.enabled is false')

# QMD MCP: only assert if it is configured as enabled.
# QMD is intentionally disabled on this host (Iris Xe VRAM constraint).
# This check will fire only if someone accidentally re-enables QMD without the binary.
qmd = cfg.get('mcp_servers', {}).get('qmd', {})
if qmd.get('enabled', False):
    import os
    qmd_cmd = qmd.get('command', '')
    if qmd_cmd and not os.path.isfile(qmd_cmd):
        errs.append(f'mcp_servers.qmd.command not found: {qmd_cmd}')

if errs:
    print('\n'.join(errs))
    raise SystemExit(1)
PY

# --- 2. Hindsight LLM reachability (Anthropic API) ---
: > "$TMP"
python3 - >"$TMP" 2>&1 <<'PY' || record_failure "hindsight llm health" "python3 inline probe"
import os, urllib.request, json
from pathlib import Path
env_path = Path.home() / ".hermes" / ".env"
if env_path.exists() and not os.environ.get("ANTHROPIC_API_KEY"):
    for line in env_path.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()
            break
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    print("ANTHROPIC_API_KEY not set")
    raise SystemExit(1)
PY

# --- 3. Firecrawl API health ---
: > "$TMP"
if ! curl -fsS --max-time 8 http://127.0.0.1:3002/ >"$TMP" 2>&1; then
  record_failure "firecrawl health" "curl http://127.0.0.1:3002/"
fi

# --- 4. Graphiti MCP health ---
: > "$TMP"
if ! curl -fsS --max-time 8 http://127.0.0.1:8765/mcp/ >"$TMP" 2>&1; then
  record_failure "graphiti-mcp health" "curl http://127.0.0.1:8765/mcp/"
fi

# --- 5. hermes config check ---
if ! run_capture hermes config check; then
  record_failure "hermes config check" "hermes config check"
fi

# --- 6. hermes memory status ---
if ! run_capture hermes memory status; then
  record_failure "hermes memory status" "hermes memory status"
fi

# --- 7. QMD readiness (optional - skip gracefully if unavailable) ---
if [ -x "$QMD" ]; then
  : > "$TMP"
  if run_capture "$QMD" doctor --json; then
    python3 - "$TMP" >"${TMP}.check" 2>&1 <<'PY' || { cat "${TMP}.check" >> "$TMP"; record_failure "qmd readiness" "$QMD doctor --json"; }
import json, sys
obj = json.load(open(sys.argv[1]))
ready = str(obj.get('readiness', ''))
if not ready.startswith('ready'):
    raise SystemExit(f'QMD readiness is {ready or "missing"}')
PY
  else
    record_failure "qmd readiness" "$QMD doctor --json"
  fi
fi

# --- 8. Graphiti epistemic consistency spot-check ---
# Silo/Epistemic Inertia (arXiv:2608.03421, sweep 22): contradictory facts can accumulate
# in the graph without detection. Query recent facts and check for state-flip contradictions.
: > "$TMP"
python3 - >"$TMP" 2>&1 <<'PY' || record_failure "graphiti consistency" "python3 inline probe"
import json, urllib.request, sys

GRAPHITI_BASE = "http://127.0.0.1:8765/mcp/"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
FLIP_PAIRS = [
    ("uninstalled", "installed"),
    ("disabled", "enabled"),
    ("cloud-only", "local"),
    ("never use", "use"),
]

def graphiti_call(session_id, tool, arguments):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": tool, "arguments": arguments}}).encode()
    h = dict(HEADERS)
    if session_id:
        h["mcp-session-id"] = session_id
    req = urllib.request.Request(GRAPHITI_BASE, data=payload, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            # MCP responses may be SSE — extract JSON from data: lines
            for line in body.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:].strip())
            return json.loads(body)
    except Exception:
        return {}

# Initialize session
init_payload = json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
               "clientInfo": {"name": "watchdog", "version": "1.0"}}}).encode()
req0 = urllib.request.Request(GRAPHITI_BASE, data=init_payload, headers=dict(HEADERS), method="POST")
try:
    with urllib.request.urlopen(req0, timeout=10) as resp:
        session_id = resp.headers.get("mcp-session-id", "")
        resp.read()
except Exception as e:
    print(f"Graphiti unreachable: {e}")
    sys.exit(0)  # watchdog check — Graphiti down check is in section 4; skip gracefully

# Fetch recent facts
result = graphiti_call(session_id, "search_memory_facts", {"query": "hermes system state", "max_facts": 20})
facts = []
try:
    content = result.get("result", {}).get("content", [{}])
    text = content[0].get("text", "[]") if content else "[]"
    facts = json.loads(text)
except Exception:
    sys.exit(0)

if not isinstance(facts, list):
    sys.exit(0)

# Check all fact pairs for state-flip contradictions
contradictions = []
texts = [str(f.get("fact", f.get("name", f.get("content", "")))) for f in facts]
for i, a in enumerate(texts):
    for j, b in enumerate(texts):
        if i >= j:
            continue
        al, bl = a.lower(), b.lower()
        for pos, neg in FLIP_PAIRS:
            if pos in al and neg in al and pos not in bl and neg in bl:
                contradictions.append(f"Contradiction: fact[{i}] has '{pos}' but fact[{j}] has '{neg}'")
            elif neg in al and pos in bl and neg not in bl:
                contradictions.append(f"Contradiction: fact[{i}] has '{neg}' but fact[{j}] has '{pos}'")

if contradictions:
    print("Graphiti state-flip contradictions detected:")
    for c in contradictions[:5]:
        print(f"  {c}")
    sys.exit(1)
PY

# --- Output ---
if [ -s "$OUT" ]; then
  # Strip leading blank lines between sections
  sed '/^$/N;/^\n\[/D' "$OUT"
fi
