#!/usr/bin/env bash
set -euo pipefail

SERVICE="firecrawl.service"
URL="http://127.0.0.1:3002/"
STAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"

if ! systemctl --user is-active --quiet "$SERVICE"; then
  systemctl --user restart "$SERVICE"
  sleep 8
  if systemctl --user is-active --quiet "$SERVICE" && curl -fsS --max-time 8 "$URL" >/dev/null; then
    echo "[$STAMP] Firecrawl watchdog: service was down; restarted successfully."
    exit 0
  fi
  echo "[$STAMP] Firecrawl watchdog: service was down; restart attempted but health check still failed."
  exit 1
fi

if ! curl -fsS --max-time 8 "$URL" >/dev/null; then
  systemctl --user restart "$SERVICE"
  sleep 8
  if curl -fsS --max-time 8 "$URL" >/dev/null; then
    echo "[$STAMP] Firecrawl watchdog: API health check failed; restarted successfully."
    exit 0
  fi
  echo "[$STAMP] Firecrawl watchdog: API health check failed; restart attempted but endpoint is still unhealthy."
  exit 1
fi

exit 0
