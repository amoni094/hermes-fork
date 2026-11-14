#!/usr/bin/env bash
# cron-sandbox-wrapper.sh — run a Hermes cron command inside NVIDIA OpenShell.
#
# Usage:
#   cron-sandbox-wrapper.sh SCRIPT [ARGS...]
#   cron-sandbox-wrapper.sh -- SCRIPT [ARGS...]
#
# Host fallback is allowed ONLY when the openshell binary is missing from PATH
# AND HERMES_OPENSHELL_FALLBACK=1. Default is deny (FALLBACK=0). Policy denial,
# timeout (124/137), and any other sandbox failure never re-exec on the host.
set -u
HERMES_OPENSHELL_FALLBACK="${HERMES_OPENSHELL_FALLBACK:-0}"

_log() {
  local ts
  ts="$(date -Iseconds 2>/dev/null || date)"
  printf '%s %s\n' "$ts" "$*" >>"$VIOLATION_LOG" 2>/dev/null || true
  printf '%s\n' "$*" >&2
}

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_PROFILE="${HERMES_PROFILE:-fork}"
_hh="${HERMES_HOME%/}"
if [[ "${_hh%/*}" == */profiles ]]; then
  PROFILE_ROOT="$_hh"
  HERMES_PROFILE="${_hh##*/}"
  # Cron contract: HERMES_HOME is the unwrapped base, never the profile root.
  HERMES_HOME="${_hh%/*}"
  HERMES_HOME="${HERMES_HOME%/*}"
else
  PROFILE_ROOT="$HERMES_HOME/profiles/$HERMES_PROFILE"
fi
unset _hh
export HERMES_HOME HERMES_PROFILE PATH

CACHE_DIR="$PROFILE_ROOT/cache"
mkdir -p "$CACHE_DIR" 2>/dev/null || true
VIOLATION_LOG="${HERMES_OPENSHELL_VIOLATION_LOG:-$CACHE_DIR/openshell-violations.log}"
SCRATCH_DIR="${HERMES_OPENSHELL_CWD:-$CACHE_DIR/scratch}"
mkdir -p "$SCRATCH_DIR" 2>/dev/null || true
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

# Resolve SCRIPT against the caller's cwd BEFORE cd'ing into scratch.
if [[ "$SCRIPT" != /* ]]; then
  SCRIPT="$(pwd)/$SCRIPT"
fi
if [[ ! -e "$SCRIPT" ]]; then
  _log "ERROR: script path does not exist: $SCRIPT"
  exit 2
fi
SCRIPT="$(realpath "$SCRIPT" 2>/dev/null || readlink -f "$SCRIPT" 2>/dev/null || printf '%s' "$SCRIPT")"

# Overlap lock: a timed-out job must not start a second copy while the first
# wrapper (or its timeout child) still holds the lock.
_LOCK_DIR="$CACHE_DIR/cron-sandbox-locks"
mkdir -p "$_LOCK_DIR" 2>/dev/null || true
_LOCK_NAME="$(printf '%s' "$SCRIPT" | sha256sum 2>/dev/null | awk '{print $1}')"
_LOCK_FILE="$_LOCK_DIR/${_LOCK_NAME:-wrapper}.lock"
if command -v flock >/dev/null 2>&1; then
  if exec 9>"$_LOCK_FILE"; then
    if ! flock -n 9; then
      _log "ERROR: overlapping invocation for $SCRIPT — not starting a second copy"
      exit 75
    fi
  fi
fi

if ! cd "$SCRATCH_DIR"; then
  _log "ERROR: cannot cd to scratch dir: $SCRATCH_DIR"
  exit 2
fi
export TMPDIR="$SCRATCH_DIR"

# Capture job-provided HERMES_PYTHON BEFORE stripping env so it survives the unset.
# Jobs can set HERMES_PYTHON in their env dict to force a specific interpreter
# (e.g. to work around openshell's stale PM-venv python resolution).
_JOB_HERMES_PYTHON="${HERMES_PYTHON:-}"

# Strip host interpreter / preload leakage so command -v python3 below uses
# the clean PATH, not the daemon's PATH which may have a stale venv prepended.
unset PYTHONPATH VIRTUAL_ENV LD_PRELOAD LD_LIBRARY_PATH HERMES_PYTHON
export PATH="/usr/local/bin:/usr/bin:/var/home/rainbow/.local/bin"

# Set PYTHONPATH to user site-packages so python3 inside the sandbox finds anthropic
# etc. even when the sandbox overrides HOME. Must be set before ENV_FROM is built.
_PYVER="$(/usr/bin/python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
export PYTHONPATH="${HOME}/.local/lib/python${_PYVER}/site-packages:${PROFILE_ROOT}/lib/python"
unset _PYVER

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

# Laptop energy/load gate (fail-open). 75 = skip this fire without failure_streak.
_GATE_PY="$PROFILE_ROOT/scripts/laptop-cron-governor.py"
if [[ -f "$_GATE_PY" ]]; then
  _GATE_RC=0
  /usr/bin/python3 "$_GATE_PY" --check "$SCRIPT" >/dev/null 2>>"$VIOLATION_LOG" || _GATE_RC=$?
  if [[ "$_GATE_RC" -eq 75 ]]; then
    _log "LAPTOP_CRON_SKIP: $SCRIPT"
    exit 0
  fi
  unset _GATE_RC
fi
unset _GATE_PY

# HERMES_NO_SANDBOX=1: bypass openshell and run directly on host.
# Use for scripts that need access to paths outside the sandbox (e.g. SecondBrain vault).
if [[ "${HERMES_NO_SANDBOX:-}" == "1" ]]; then
  _log "NO_SANDBOX: running on host (HERMES_NO_SANDBOX=1)"
  exec "${INNER[@]}" "$@"
fi

if [[ -z "${OPENSHELL_BIN:-}" || ! -x "$OPENSHELL_BIN" ]]; then
  if [[ "$HERMES_OPENSHELL_FALLBACK" == "1" ]]; then
    _log "FALLBACK: openshell not installed"
    exec "${INNER[@]}" "$@"
  fi
  _log "ERROR: openshell not installed and HERMES_OPENSHELL_FALLBACK!=1"
  exit 1
fi

if [[ ! -f "$POLICY" ]]; then
  _log "ERROR: policy file missing: $POLICY"
  exit 2
fi

ENV_FROM=()
for _k in HERMES_HOME HERMES_PROFILE HERMES_CRON_SESSION HOME PATH TMPDIR PYTHONPATH; do
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
_add_bind "$HOME/.local/lib" true  # user site-packages (anthropic, etc.) needed by interpreter scripts
# W7-H1: always bind the unwrapped canonical scripts dir. When HERMES_HOME
# is a profile root (…/profiles/fork), $HERMES_HOME/hermes-scripts does not
# exist and fork wrappers cannot runpy the canonical scripts.
_add_bind "$HOME/.hermes/hermes-scripts" true
_add_bind "$HOME/.hermes/scripts" true
_add_bind "$PROFILE_ROOT/scripts" true
_add_bind "$PROFILE_ROOT/lib" true       # sandboxed python packages (anthropic, etc.)
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
_add_bind "$HOME/.hermes/cache" false  # cs/math interpreter primers + base cache
_add_bind "$HOME/.hermes/logs" false   # run-header.py writes to ~/.hermes/logs/
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
