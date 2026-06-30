#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/daily-silverblue-update"
STAMP_FILE="$STATE_DIR/last-run-date"
LOCK_FILE="$STATE_DIR/lock"
LOG_FILE="$STATE_DIR/latest.log"
TODAY="$(date +%F)"
UPDATE_SCRIPT="$HOME/.hermes/scripts/daily-silverblue-update.sh"

mkdir -p "$STATE_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  exit 0
fi

if [ -f "$STAMP_FILE" ] && [ "$(cat "$STAMP_FILE")" = "$TODAY" ]; then
  exit 0
fi

{
  printf '[%s] login trigger accepted for %s\n' "$(date --iso-8601=seconds)" "$TODAY"
  if "$UPDATE_SCRIPT"; then
    printf '%s\n' "$TODAY" > "$STAMP_FILE"
    printf '[%s] login trigger marked successful for %s\n' "$(date --iso-8601=seconds)" "$TODAY"
  else
    rc=$?
    rm -f "$STAMP_FILE"
    printf '[%s] login trigger leaving day unstamped after failure (exit %s)\n' "$(date --iso-8601=seconds)" "$rc"
    exit "$rc"
  fi
} >> "$LOG_FILE" 2>&1
