#!/usr/bin/env bash
# hindsight-ensure.sh — idempotent daemon health check and auto-start
# Called by AGENTS.md startup rule and optionally by gateway hook.
# Exit 0 = healthy, Exit 1 = failed to recover

set -euo pipefail

HINDSIGHT_PORT="${HINDSIGHT_PORT:-9177}"
HEALTH_URL="http://127.0.0.1:${HINDSIGHT_PORT}/health"
LOCK_FILE="${HOME}/.hindsight/profiles/hermes.lock"
LOG="${HOME}/.hindsight/daemon.log"
HERMES_VENV="${HOME}/.hermes/hermes-agent/venv"
HINDSIGHT_API="${HERMES_VENV}/bin/hindsight-api"

log() { echo "[hindsight-ensure] $*" >&2; }

# 1. Quick health check
if curl -sf --max-time 3 "${HEALTH_URL}" >/dev/null 2>&1; then
    log "daemon healthy on :${HINDSIGHT_PORT}"
    exit 0
fi

log "daemon not responding — attempting recovery"

# 2. Clear stale lock file
if [[ -f "${LOCK_FILE}" ]]; then
    log "removing stale lock: ${LOCK_FILE}"
    rm -f "${LOCK_FILE}"
fi

# Kill any zombie hindsight-api processes
pkill -f 'hindsight-api' 2>/dev/null || true
sleep 1

# 3. Do NOT manually start hindsight-api — Hermes plugin manages the daemon.
#    Triggering any hindsight tool call from within the agent session will
#    cause the plugin to start the daemon. This script is diagnostic only
#    for non-agent callers; from inside a Hermes session, use hindsight_recall.
#
#    For non-Hermes callers (e.g. cron), attempt a direct start:
if [[ "${HERMES_SESSION:-}" == "" ]]; then
    if [[ -x "${HINDSIGHT_API}" ]]; then
        log "starting hindsight-api directly (non-agent context)"
        PROFILE_ENV="${HOME}/.hindsight/profiles/hermes.env"
        if [[ -f "${PROFILE_ENV}" ]]; then
            set -a; source "${PROFILE_ENV}"; set +a
        fi
        "${HINDSIGHT_API}" --port "${HINDSIGHT_PORT}" >> "${LOG}" 2>&1 &
        sleep 5
        if curl -sf --max-time 5 "${HEALTH_URL}" >/dev/null 2>&1; then
            log "daemon started successfully"
            exit 0
        else
            log "ERROR: daemon failed to start — check ${LOG}"
            exit 1
        fi
    else
        log "ERROR: hindsight-api not found at ${HINDSIGHT_API}"
        exit 1
    fi
fi

# Inside a Hermes session: report status for agent to act on
log "inside Hermes session — agent should call hindsight_recall to trigger daemon start"
exit 0
