#!/usr/bin/env bash
# cron-sandbox-wrapper.sh — run a Hermes cron command inside NVIDIA OpenShell.
#
# Usage:
#   cron-sandbox-wrapper.sh SCRIPT [ARGS...]
#   cron-sandbox-wrapper.sh -- SCRIPT [ARGS...]
#
# Host fallback is allowed ONLY when the openshell binary is missing from PATH
# AND HERMES_OPENSHELL_FALLBACK is unset or 1. When FALLBACK=0, missing binary
# and sandbox create failure both exit 1 (fail-closed). Policy denial, timeout
# (124/137), and any other sandbox failure never re-exec on the host.
set -u
HERMES_OPENSHELL_FALLBACK="${HERMES_OPENSHELL_FALLBACK:-}"

_log() {
  local ts
  ts="$(date -Iseconds 2>/dev/null || date)"
  printf '%s %s\n' "$ts" "$*" >>"$VIOLATION_LOG" 2>/dev/null || true
  printf '%s\n' "$*" >&2
}

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_PROFILE="${HERMES_PROFILE:-fork}"
if [[ "$HERMES_HOME" == */profiles/* ]]; then
  PROFILE_ROOT="$HERMES_HOME"
else
  PROFILE_ROOT="$HERMES_HOME/profiles/$HERMES_PROFILE"
fi
export HERMES_HOME HERMES_PROFILE PATH

CACHE_DIR="$PROFILE_ROOT/cache"
mkdir -p "$CACHE_DIR" 2>/dev/null || true
VIOLATION_LOG="${HERMES_OPENSHELL_VIOLATION_LOG:-$CACHE_DIR/openshell-violations.log}"
SCRATCH_DIR="${HERMES_OPENSHELL_CWD:-$CACHE_DIR/scratch}"
mkdir -p "$SCRATCH_DIR" 2>/dev/null || true
if ! cd "$SCRATCH_DIR"; then
  _log "ERROR: cannot cd to scratch dir: $SCRATCH_DIR"
  exit 2
fi
export TMPDIR="$SCRATCH_DIR"
POLICY="${OPENSHELL_SANDBOX_POLICY:-$PROFILE_ROOT/openshell-policy.yaml}"
if [[ -z "${OPENSHELL_BIN:-}" ]]; then
  if [[ -x "$HOME/.local/bin/openshell" ]]; then
    OPENSHELL_BIN="$HOME/.local/bin/openshell"
  else
    OPENSHELL_BIN="$(command -v openshell 2>/dev/null || true)"
  fi
fi

if [[ "${1:-}" == "--" ]]; then
  shift
fi

if [[ $# -lt 1 ]]; then
  _log "ERROR: script path required"
  exit 2
fi

SCRIPT="$1"
shift

if [[ ! -e "$SCRIPT" ]]; then
  _log "ERROR: script path does not exist: $SCRIPT"
  exit 2
fi

# Capture job-provided HERMES_PYTHON BEFORE stripping env so it survives the unset.
# Jobs can set HERMES_PYTHON in their env dict to force a specific interpreter
# (e.g. to work around openshell's stale PM-venv python resolution).
_JOB_HERMES_PYTHON="${HERMES_PYTHON:-}"

# Strip host interpreter / preload leakage so command -v python3 below uses
# the clean PATH, not the daemon's PATH which may have a stale venv prepended.
unset PYTHONPATH VIRTUAL_ENV LD_PRELOAD LD_LIBRARY_PATH HERMES_PYTHON
export PATH="/usr/local/bin:/usr/bin:/var/home/rainbow/.local/bin"

# Resolve interpreter for the inner script.
INNER=()
if [[ -x "$SCRIPT" ]] && [[ "$SCRIPT" != *.py ]]; then
  INNER=("$SCRIPT")
elif [[ "$SCRIPT" == *.py ]]; then
  PY="${_JOB_HERMES_PYTHON:-}"
  if [[ -z "$PY" ]]; then
    PY="$(command -v python3 2>/dev/null || true)"
  fi
  if [[ -z "$PY" ]]; then
    _log "ERROR: python3 not found for $SCRIPT"
    exit 2
  fi
  INNER=("$PY" "$SCRIPT")
else
  INNER=("$SCRIPT")
fi

# HERMES_NO_SANDBOX=1: bypass openshell and run directly on host.
# Use for scripts that need access to paths outside the sandbox (e.g. SecondBrain vault).
if [[ "${HERMES_NO_SANDBOX:-}" == "1" ]]; then
  _log "NO_SANDBOX: running on host (HERMES_NO_SANDBOX=1)"
  exec "${INNER[@]}" "$@"
fi

if [[ -z "${OPENSHELL_BIN:-}" || ! -x "$OPENSHELL_BIN" ]]; then
  if [[ "$HERMES_OPENSHELL_FALLBACK" == "0" ]]; then
    _log "ERROR: openshell not installed and HERMES_OPENSHELL_FALLBACK=0"
    exit 1
  fi
  # Host fallback only when FALLBACK is unset or 1.
  _log "FALLBACK: openshell not installed"
  exec "${INNER[@]}" "$@"
fi

if [[ ! -f "$POLICY" ]]; then
  _log "ERROR: policy file missing: $POLICY"
  exit 2
fi

ENV_FROM=()
for _k in HERMES_HOME HERMES_PROFILE HERMES_CRON_SESSION HOME PATH TMPDIR; do
  if [[ -n "${!_k:-}" ]]; then
    ENV_FROM+=(--env-from "$_k")
  fi
done
ENV_FROM+=(--env HERMES_OPENSHELL=1)

# Source API keys from .env files (profile .env overrides root .env).
# Keys are passed explicitly as --env so the sandbox never inherits the full
# host environment — only the declared set crosses the sandbox boundary.
_API_KEYS=(
  ANTHROPIC_API_KEY ANTHROPIC_TOKEN
  OPENAI_API_KEY
  XAI_API_KEY
  MISTRAL_API_KEY
  DEEPSEEK_API_KEY
  OPENROUTER_API_KEY
)
declare -A _ENV_VALS=()
for _dotenv in "$HERMES_HOME/.env" "$PROFILE_ROOT/.env"; do
  if [[ -f "$_dotenv" ]]; then
    while IFS= read -r _line || [[ -n "$_line" ]]; do
      # Skip comments and blank lines
      [[ "$_line" =~ ^[[:space:]]*# ]] && continue
      [[ -z "${_line// }" ]] && continue
      _k="${_line%%=*}"
      _v="${_line#*=}"
      for _want in "${_API_KEYS[@]}"; do
        if [[ "$_k" == "$_want" ]]; then
          _ENV_VALS["$_k"]="$_v"
          break
        fi
      done
    done < "$_dotenv"
  fi
done
for _k in "${_API_KEYS[@]}"; do
  # Prefer live env (already exported by daemon) over .env file value
  _live="${!_k:-}"
  if [[ -n "$_live" ]]; then
    ENV_FROM+=(--env "$_k=$_live")
  elif [[ -n "${_ENV_VALS[$_k]:-}" ]]; then
    ENV_FROM+=(--env "$_k=${_ENV_VALS[$_k]}")
  fi
done
unset _dotenv _line _k _v _want _live _API_KEYS _ENV_VALS

# OpenShell filesystem_policy is Landlock inside the container; host paths are
# attached only as bind mounts. Restrict mounts to the policy-declared set.
_json_escape() {
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  printf '%s' "$s"
}
declare -A _SEEN_MOUNTS=()
_add_bind() {
  local src=$1 ro=$2 resolved
  [[ -e "$src" ]] || return 0
  resolved="$(realpath "$src" 2>/dev/null || true)"
  [[ -n "$resolved" ]] || resolved="$src"
  if [[ -n "${_SEEN_MOUNTS[$resolved]+x}" ]]; then
    return 0
  fi
  _SEEN_MOUNTS[$resolved]=1
  if [[ -n "${_MOUNTS:-}" ]]; then
    _MOUNTS+=","
  fi
  _MOUNTS+=$(printf '{"type":"bind","source":"%s","target":"%s","read_only":%s}' \
    "$(_json_escape "$src")" "$(_json_escape "$src")" "$ro")
}
_MOUNTS=""
_add_bind /usr true
_add_bind /lib true
_add_bind /lib64 true
_add_bind "$HOME/.local/bin" true
# W7-H1: always bind the unwrapped canonical scripts dir. When HERMES_HOME
# is a profile root (…/profiles/fork), $HERMES_HOME/hermes-scripts does not
# exist and fork wrappers cannot runpy the canonical scripts.
_add_bind "$HOME/.hermes/hermes-scripts" true
_add_bind "$HOME/.hermes/scripts" true
_add_bind "$PROFILE_ROOT/scripts" true
_add_bind "$PROFILE_ROOT/skills" true
_add_bind "$PROFILE_ROOT/hooks" true
_add_bind "$PROFILE_ROOT/sessions" true
_add_bind "$HERMES_HOME/sessions" true
# logs must be RW (cron scripts write to logs/); RW bind is added below — no RO bind here.
_add_bind "$HERMES_HOME/logs" true
_add_bind "$PROFILE_ROOT/cron" true
_add_bind "$PROFILE_ROOT/state.db" true
_add_bind "$PROFILE_ROOT/state.db-wal" true
_add_bind "$PROFILE_ROOT/state.db-shm" true
_add_bind "$HOME/.hermes/memories" true
_add_bind "$PROFILE_ROOT/memories" true
_add_bind "$PROFILE_ROOT/cache" false
_add_bind "$PROFILE_ROOT/memory-facts" false
_add_bind "$HERMES_HOME/memory-facts" false
_add_bind "$PROFILE_ROOT/logs" false
_add_bind "$HERMES_HOME/omni" false
_add_bind "$PROFILE_ROOT/omni" false
_add_bind "$HOME/Documents" true
_add_bind "$HOME/Documents/SecondBrain" true
DRIVER_JSON="{\"podman\":{\"mounts\":[${_MOUNTS}]}}"

CMD=(
  "$OPENSHELL_BIN" sandbox create
  --policy "$POLICY"
  --no-keep
  --no-auto-providers
  --no-tty
  --no-credential-warnings
  --driver-config-json "$DRIVER_JSON"
  "${ENV_FROM[@]}"
  --
  /bin/bash -c 'cd "$1" || exit 2; shift; exec "$@"' _
  "$SCRATCH_DIR"
  "${INNER[@]}"
  "$@"
)

TIMEOUT_SEC="${HERMES_OPENSHELL_TIMEOUT:-180}"
set +e
if command -v timeout >/dev/null 2>&1; then
  timeout --signal=TERM --kill-after=10 "$TIMEOUT_SEC" "${CMD[@]}"
  rc=$?
else
  "${CMD[@]}"
  rc=$?
fi
set -euo pipefail

if [[ $rc -eq 0 ]]; then
  exit 0
fi

# Timeouts/kills must never re-exec on the host (double side effects).
if [[ $rc -eq 124 || $rc -eq 137 ]]; then
  _log "ERROR: sandbox timeout/killed rc=$rc for $SCRIPT — not re-executing on host"
  exit "$rc"
fi

_log "ERROR: SANDBOX_FAIL openshell exit $rc for $SCRIPT — not re-executing on host"
if [[ "$HERMES_OPENSHELL_FALLBACK" == "0" ]]; then
  exit 1
fi
exit "$rc"
