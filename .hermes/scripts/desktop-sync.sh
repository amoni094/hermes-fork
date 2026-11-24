#!/usr/bin/env bash
# desktop-sync.sh — full Hermes backup to F:/Hermes on DESKTOP-PH4F2DK
# Runs nightly at 2:30 AM. Skips silently if desktop unreachable.
# Laptop is always source of truth. Desktop is backup only — never written back.
#
# What gets backed up (everything that matters, nothing reinstallable):
#
#   BUNDLE 1 — hermes-home (~/.hermes default profile):
#     config.yaml, memories/, plugins/, scripts/, hermes-scripts/, skills/,
#     skills-security/, skills-quarantine/, memory-facts/, cron/, state/,
#     state-snapshots/, resources/, omni/, kanban/, veto/, reports/,
#     session-exports/, agent-hooks/, hook_outputs/, telemetry/, mcp/,
#     pastes/, checkpoints/, pending/, research/
#
#   BUNDLE 2 — hermes-fork profile (~/.hermes/profiles/fork/):
#     All subdirs EXCEPT cache/, logs/, terminal-sessions/, audio_cache/,
#     image_cache/, images/, browser_screenshots/ (ephemeral/large)
#
#   BUNDLE 3 — ~/.hindsight/ (excl. models/ — HuggingFace weights, reinstallable)
#
#   BUNDLE 4 — FalkorDB RDB snapshot (Graphiti knowledge graph)
#
#   BUNDLE 5 — Postgres dump (Hindsight vector store)
#
# NOT backed up (reinstallable or already in git):
#   .hermes/tools/          — Python runtimes (3.1G, uv-managed, reinstallable)
#   .hermes/hermes-agent/   — upstream source repo (8.2G, in git)
#   .hermes/hermes-fork/    — fork source repo (2.5G, in git + pushed)
#   .hermes/installs/       — package cache (4.6G, reinstallable)
#   .hermes/backups/        — existing local backups (redundant here)
#   .hermes/integrations.disabled/ — disabled, recoverable
#   .hermes/cache/          — ephemeral cache
#   .hermes/bin/            — hermes executable (reinstallable via uv)
#   .hermes/lsp/            — language server binaries (reinstallable)
#   fork/cache/, fork/logs/, fork/lsp/, fork/bin/, fork/lib/  — ephemeral/reinstallable
#   fork/state-snapshots/   — 263M compaction snapshots (recoverable, not critical)
#
# Uses tar+scp — Windows OpenSSH has no rsync daemon.

set -euo pipefail

DESKTOP_HOST_TS="admin@100.88.247.70"
DESKTOP_HOST_LAN="admin@192.168.0.181"
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

# --- 1. Reachability check (Tailscale first, LAN fallback) ---
DESKTOP_HOST=""
for _host in "$DESKTOP_HOST_TS" "$DESKTOP_HOST_LAN"; do
    if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no \
        "$_host" "echo ok" &>/dev/null; then
        DESKTOP_HOST="$_host"
        break
    fi
done

if [[ -z "$DESKTOP_HOST" ]]; then
    log "SKIP: desktop not reachable (tried Tailscale $DESKTOP_HOST_TS and LAN $DESKTOP_HOST_LAN)"
    exit 0
fi
log "Desktop reachable at $DESKTOP_HOST — starting full sync to $DESKTOP_BASE"

# Helper: rotate old backups on desktop (keep last N by name pattern)
rotate_desktop() {
    local dir="$1" pattern="$2" keep="${3:-3}"
    ssh $SSH_OPTS "$DESKTOP_HOST" \
        "pwsh -NonInteractive -Command \"Get-ChildItem '${dir}\\${pattern}' | Sort-Object LastWriteTime -Descending | Select-Object -Skip ${keep} | Remove-Item -Force\"" \
        2>/dev/null || true
}

# Helper: scp + rotate, sets ERRORS on failure
ship() {
    local archive="$1" dest_dir="$2" pattern="$3" label="$4" keep="${5:-3}"
    if [[ ! -s "$archive" ]]; then
        log "ERROR: $label archive empty or missing"
        ERRORS=$((ERRORS+1))
        return
    fi
    local size
    size=$(du -sh "$archive" | cut -f1)
    local fname
    fname=$(basename "$archive")
    scp $SSH_OPTS "$archive" "${DESKTOP_HOST}:${dest_dir}/${fname}" 2>&1 | tee -a "$LOG" \
        && rotate_desktop "${dest_dir//\//\\}" "$pattern" "$keep" \
        && log "$label synced (${size})" \
        || { log "ERROR: $label scp failed"; ERRORS=$((ERRORS+1)); }
}

# --- 2. BUNDLE 1: Hermes default profile (everything that matters) ---
log "Bundle 1: Hermes default profile ..."
HERMES_ARCHIVE="$TMPDIR_SYNC/hermes-${DATE}.tar.gz"

tar -czf "$HERMES_ARCHIVE" \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='*.sock' \
    --exclude='.hermes/sessions' \
    --exclude='.hermes/sessions.bak.*' \
    --exclude='.hermes/backup-broken' \
    --exclude='.hermes/integrations' \
    --exclude='.hermes/integrations.disabled' \
    --exclude='.hermes/backups' \
    --exclude='.hermes/cache' \
    --exclude='.hermes/tools' \
    --exclude='.hermes/hermes-agent' \
    --exclude='.hermes/hermes-fork' \
    --exclude='.hermes/installs' \
    --exclude='.hermes/bin' \
    --exclude='.hermes/lsp' \
    --exclude='.hermes/profiles' \
    --exclude='.hermes/logs' \
    -C "$HOME" \
    .hermes/config.yaml \
    .hermes/memories/ \
    .hermes/plugins/ \
    .hermes/scripts/ \
    .hermes/hermes-scripts/ \
    .hermes/skills/ \
    .hermes/skills-security/ \
    .hermes/skills-quarantine/ \
    .hermes/memory-facts/ \
    .hermes/cron/ \
    .hermes/state/ \
    .hermes/state-snapshots/ \
    .hermes/resources/ \
    .hermes/omni/ \
    .hermes/kanban/ \
    .hermes/veto/ \
    .hermes/reports/ \
    .hermes/session-exports/ \
    .hermes/agent-hooks/ \
    .hermes/hook_outputs/ \
    .hermes/telemetry/ \
    .hermes/mcp/ \
    .hermes/pastes/ \
    .hermes/checkpoints/ \
    .hermes/pending/ \
    .hermes/research/ \
    2>/dev/null || true

ship "$HERMES_ARCHIVE" "${DESKTOP_BASE}/hermes-home" "hermes-*.tar.gz" "Bundle 1 (hermes default)" 3

# --- 3. BUNDLE 2: Hermes fork profile ---
log "Bundle 2: Hermes fork profile ..."
FORK_ARCHIVE="$TMPDIR_SYNC/hermes-fork-${DATE}.tar.gz"

tar -czf "$FORK_ARCHIVE" \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='*.sock' \
    --exclude='.hermes/profiles/fork/cache' \
    --exclude='.hermes/profiles/fork/logs' \
    --exclude='.hermes/profiles/fork/terminal-sessions' \
    --exclude='.hermes/profiles/fork/audio_cache' \
    --exclude='.hermes/profiles/fork/image_cache' \
    --exclude='.hermes/profiles/fork/images' \
    --exclude='.hermes/profiles/fork/browser_screenshots' \
    --exclude='.hermes/profiles/fork/lsp' \
    --exclude='.hermes/profiles/fork/bin' \
    --exclude='.hermes/profiles/fork/lib' \
    --exclude='.hermes/profiles/fork/state-snapshots' \
    -C "$HOME" \
    .hermes/profiles/fork/ \
    2>/dev/null || true

ship "$FORK_ARCHIVE" "${DESKTOP_BASE}/hermes-fork" "hermes-fork-*.tar.gz" "Bundle 2 (fork profile)" 3

# --- 4. BUNDLE 3: ~/.hindsight (excl. models — HuggingFace weights, reinstallable) ---
log "Bundle 3: ~/.hindsight ..."
HINDSIGHT_ARCHIVE="$TMPDIR_SYNC/hindsight-${DATE}.tar.gz"

tar -czf "$HINDSIGHT_ARCHIVE" \
    --exclude='models' \
    --exclude='*.log' \
    -C "$HOME" \
    .hindsight/ \
    2>/dev/null || true

ship "$HINDSIGHT_ARCHIVE" "${DESKTOP_BASE}/hindsight" "hindsight-*.tar.gz" "Bundle 3 (hindsight)" 3

# --- 5. BUNDLE 4: FalkorDB RDB snapshot ---
log "Bundle 4: FalkorDB ..."
FALKORDB_VOL="$HOME/.local/share/containers/storage/volumes/falkordb_data/_data"

if [[ -f "$FALKORDB_VOL/dump.rdb" ]]; then
    podman exec falkordb redis-cli BGSAVE 2>/dev/null | grep -q "Background saving started" && sleep 5 || sleep 2
    RDB_COPY="$TMPDIR_SYNC/falkordb-${DATE}.rdb"
    cp "$FALKORDB_VOL/dump.rdb" "$RDB_COPY"
    ship "$RDB_COPY" "${DESKTOP_BASE}/falkordb" "falkordb-*.rdb" "Bundle 4 (FalkorDB)" 3
else
    log "WARN: FalkorDB dump.rdb not found — is falkordb container running?"
fi

# --- 6. BUNDLE 5: Postgres dump (hindsight db) ---
log "Bundle 5: Postgres ..."
PG_BIN="$HOME/.pg0/installation/18.1.0/bin"
PG_DUMP="$TMPDIR_SYNC/hindsight-pg-${DATE}.sql.gz"

if "$PG_BIN/pg_isready" -h localhost -p 5432 -U hindsight &>/dev/null 2>&1; then
    PGPASSFILE="$HOME/.pgpass" "$PG_BIN/pg_dump" \
        -h localhost -p 5432 -U hindsight hindsight 2>/dev/null \
        | gzip > "$PG_DUMP" \
        && ship "$PG_DUMP" "${DESKTOP_BASE}/postgres" "hindsight-pg-*.sql.gz" "Bundle 5 (Postgres)" 3 \
        || { log "ERROR: pg_dump failed"; ERRORS=$((ERRORS+1)); }
else
    log "WARN: Postgres not ready at :5432 — skipping"
fi

# --- 7. Manifest ---
cat > "$TMPDIR_SYNC/last-sync.json" << EOF
{
  "timestamp": "${STAMP}",
  "date": "${DATE}",
  "source_host": "$(hostname)",
  "destination": "${DESKTOP_BASE}",
  "bundles": ["hermes-home", "hermes-fork", "hindsight", "falkordb", "postgres"],
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
