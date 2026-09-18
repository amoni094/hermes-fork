#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/daily-silverblue-update"
PENDING_FILE="$STATE_DIR/reboot-required"
mkdir -p "$STATE_DIR"

printf '[%s] reboot required by rpm-ostree update\n' "$(date --iso-8601=seconds)" > "$PENDING_FILE"

if ! command -v notify-send >/dev/null 2>&1; then
  exit 0
fi

action="$(notify-send \
  --app-name='Silverblue Updates' \
  --icon=system-software-update \
  --urgency=normal \
  --action='ok=Reboot now' \
  --action='later=Later' \
  'Reboot required' \
  'Silverblue updates were staged. Select Reboot now when you are ready.' || true)"

case "$action" in
  ok)
    rm -f "$PENDING_FILE"
    exec sudo -n /usr/sbin/reboot
    ;;
  later|'')
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
