#!/usr/bin/env bash
# desktop-sync.sh — opportunistic backup of Hermes memory stack to F:/Hermes on DESKTOP-PH4F2DK
# Runs nightly at 2:30 AM. Skips silently if desktop unreachable.
# Laptop is always source of truth. Desktop is backup only — never written back.
#
# What gets backed up:
#   ~/.hermes/{skills,memory-facts,cron,scripts,config.yaml,memory/,state/,resources/}
#   ~/.hindsight/  (excl. models/ and logs)
#   FalkorDB RDB snapshot  (Graphiti knowledge graph)
#   Postgres dump  (Hindsight vector store, ~hindsight db)
#
# Uses tar+scp — Windows OpenSSH has no rsync daemon.

set -euo pipefail

DESKTOP_HOST="admin@100.88.247.70"
DESKTOP_BASE="F:/Hermes"
LOG="$HOME/.hermes/logs/desktop-sync.log"
STAMP=$(date '+%Y-%m-%d %H:%M:%S')
DATE=$(date '+%Y%m%d')
MAX_LOG_BYTES=524288  # 512KB rotate threshold
TMPDIR_SYNC=$(mktemp -d /tmp/desktop-sync-XXXXXX)
ERRORS=0

cleanup() { rm -rf "$TMPDIR_SYNC"; }
trap cleanup EXIT

# Log rotation
if [[ -f "$LOG" ]] && (( $(stat -c%s "$LOG" 2>/dev/null || echo 0) > MAX_LOG_BYTES )); then
    mv "$LOG" "${LOG}.1"
fi

log() { echo "[$STAMP] $*" | tee -a "$LOG"; }

SSH_OPTS="-o ConnectTimeout=15 -o BatchMode=yes -o StrictHostKeyChecking=no"

# --- 1. Reachability check ---
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no \
    "$DESKTOP_HOST" "echo ok" &>/dev/null; then
    log "SKIP: desktop not reachable"
    exit 0
fi
log "Desktop reachable — starting sync to $DESKTOP_BASE"

# Helper: rotate old backups on desktop (keep last N by name pattern)
rotate_desktop() {
    local dir="$1" pattern="$2" keep="${3:-3}"
    ssh $SSH_OPTS "$DESKTOP_HOST" \
        "pwsh -NonInteractive -Command \"Get-ChildItem '${dir}\\${pattern}' | Sort-Object LastWriteTime -Descending | Select-Object -Skip ${keep} | Remove-Item -Force\"" \
        2>/dev/null || true
}

# --- 2. Hermes config/memory/skills (targeted — skip venv/cache/backups) ---
log "Syncing Hermes config+skills+memory ..."
HERMES_ARCHIVE="$TMPDIR_SYNC/hermes-${DATE}.tar.gz"

# Only back up what matters — total ~200MB not 15GB
tar -czf "$HERMES_ARCHIVE" \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='*.sock' \
    -C "$HOME" \
    .hermes/config.yaml \
    .hermes/scripts/ \
    .hermes/skills/ \
    .hermes/memory-facts/ \
    .hermes/cron/ \
    .hermes/state/ \
    .hermes/resources/ \
    .hermes/skills-security/ \
    2>/dev/null
# tar exits non-zero on harmless warnings (sockets) — only fail if archive is empty
[[ -s "$HERMES_ARCHIVE" ]] || { log "ERROR: hermes tar produced empty archive"; ERRORS=$((ERRORS+1)); }

if [[ -f "$HERMES_ARCHIVE" ]]; then
    SIZE=$(du -sh "$HERMES_ARCHIVE" | cut -f1)
    scp $SSH_OPTS "$HERMES_ARCHIVE" "${DESKTOP_HOST}:${DESKTOP_BASE}/hermes-home/hermes-${DATE}.tar.gz" 2>&1 | tee -a "$LOG" \
        && rotate_desktop "F:\\Hermes\\hermes-home" "hermes-*.tar.gz" 3 \
        && log "Hermes synced (${SIZE})" \
        || { log "ERROR: hermes scp failed"; ERRORS=$((ERRORS+1)); }
fi

# --- 3. ~/.hindsight (excl. models — they're 500MB HuggingFace weights, reinstallable) ---
log "Syncing ~/.hindsight ..."
HINDSIGHT_ARCHIVE="$TMPDIR_SYNC/hindsight-${DATE}.tar.gz"

tar -czf "$HINDSIGHT_ARCHIVE" \
    --exclude='models' \
    --exclude='*.log' \
    -C "$HOME" \
    .hindsight/ \
    2>/dev/null || { log "ERROR: hindsight tar failed"; ERRORS=$((ERRORS+1)); }

if [[ -f "$HINDSIGHT_ARCHIVE" ]]; then
    SIZE=$(du -sh "$HINDSIGHT_ARCHIVE" | cut -f1)
    scp $SSH_OPTS "$HINDSIGHT_ARCHIVE" "${DESKTOP_HOST}:${DESKTOP_BASE}/hindsight/hindsight-${DATE}.tar.gz" 2>&1 | tee -a "$LOG" \
        && rotate_desktop "F:\\Hermes\\hindsight" "hindsight-*.tar.gz" 3 \
        && log "Hindsight synced (${SIZE})" \
        || { log "ERROR: hindsight scp failed"; ERRORS=$((ERRORS+1)); }
fi

# --- 4. FalkorDB RDB snapshot ---
log "Syncing FalkorDB ..."
FALKORDB_VOL="$HOME/.local/share/containers/storage/volumes/falkordb_data/_data"

if [[ -f "$FALKORDB_VOL/dump.rdb" ]]; then
    # Trigger fresh snapshot
    podman exec falkordb redis-cli BGSAVE 2>/dev/null | grep -q "Background saving started" && sleep 5 || sleep 2
    RDB_COPY="$TMPDIR_SYNC/falkordb-${DATE}.rdb"
    cp "$FALKORDB_VOL/dump.rdb" "$RDB_COPY"
    SIZE=$(du -sh "$RDB_COPY" | cut -f1)
    scp $SSH_OPTS "$RDB_COPY" "${DESKTOP_HOST}:${DESKTOP_BASE}/falkordb/falkordb-${DATE}.rdb" 2>&1 | tee -a "$LOG" \
        && rotate_desktop "F:\\Hermes\\falkordb" "falkordb-*.rdb" 3 \
        && log "FalkorDB synced (${SIZE})" \
        || { log "ERROR: FalkorDB scp failed"; ERRORS=$((ERRORS+1)); }
else
    log "WARN: FalkorDB dump.rdb not found — is falkordb container running?"
fi

# --- 5. Postgres dump (hindsight db, port 5432) ---
log "Syncing Postgres ..."
PG_BIN="$HOME/.pg0/installation/18.1.0/bin"
PG_DUMP="$TMPDIR_SYNC/hindsight-pg-${DATE}.sql.gz"

if "$PG_BIN/pg_isready" -h localhost -p 5432 -U hindsight &>/dev/null 2>&1; then
    PGPASSFILE="$HOME/.pgpass" "$PG_BIN/pg_dump" \
        -h localhost -p 5432 -U hindsight hindsight 2>/dev/null \
        | gzip > "$PG_DUMP" && {
        SIZE=$(du -sh "$PG_DUMP" | cut -f1)
        scp $SSH_OPTS "$PG_DUMP" "${DESKTOP_HOST}:${DESKTOP_BASE}/postgres/hindsight-pg-${DATE}.sql.gz" 2>&1 | tee -a "$LOG" \
            && rotate_desktop "F:\\Hermes\\postgres" "hindsight-pg-*.sql.gz" 3 \
            && log "Postgres synced (${SIZE})" \
            || { log "ERROR: Postgres scp failed"; ERRORS=$((ERRORS+1)); }
    } || { log "ERROR: pg_dump failed"; ERRORS=$((ERRORS+1)); }
else
    log "WARN: Postgres not ready at :5432 — skipping"
fi

# --- 6. Manifest ---
cat > "$TMPDIR_SYNC/last-sync.json" << EOF
{
  "timestamp": "${STAMP}",
  "date": "${DATE}",
  "source_host": "$(hostname)",
  "destination": "${DESKTOP_BASE}",
  "errors": ${ERRORS}
}
EOF
scp $SSH_OPTS "$TMPDIR_SYNC/last-sync.json" \
    "${DESKTOP_HOST}:${DESKTOP_BASE}/logs/last-sync.json" 2>/dev/null || true

# --- Result ---
if (( ERRORS > 0 )); then
    log "DONE with ${ERRORS} error(s) — partial sync"
    exit 1
fi
log "DONE — full sync complete (0 errors)"
