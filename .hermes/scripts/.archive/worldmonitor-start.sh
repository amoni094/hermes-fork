#!/usr/bin/env bash
set -euo pipefail

containers=(
  worldmonitor-redis
  worldmonitor-redis-rest
  worldmonitor-ais-relay
  worldmonitor
)

health_url="http://127.0.0.1:3000/api/health"

if ! command -v podman >/dev/null 2>&1; then
  echo "podman not found" >&2
  exit 1
fi

python_health='import json,sys,urllib.request; data=json.load(urllib.request.urlopen(sys.argv[1], timeout=10)); print(data.get("status","unknown"))'

if python -c "$python_health" "$health_url" >/dev/null 2>&1; then
  echo "worldmonitor already healthy"
  exit 0
fi

podman start "${containers[@]}" >/dev/null

deadline=$((SECONDS + 45))
while (( SECONDS < deadline )); do
  if status=$(python -c "$python_health" "$health_url" 2>/dev/null); then
    echo "worldmonitor health: $status"
    exit 0
  fi
  sleep 2
done

echo "worldmonitor did not become healthy within 45s" >&2
exit 1
