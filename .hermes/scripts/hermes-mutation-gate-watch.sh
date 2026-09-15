#!/usr/bin/env bash
set -euo pipefail
ROOT=/var/home/rainbow/.hermes/integrations/hermes-agent-self-evolution/output
GATE=/var/home/rainbow/.hermes/scripts/hermes-mutation-gate.sh
if [ ! -d "$ROOT" ]; then
  echo "SKIP: evolution output dir absent ($ROOT) — mutation gate inactive"
  exit 0
fi
found=0
while IFS= read -r -d '' dir; do
  found=1
  if ! "$GATE" "$dir"; then
    echo "FAILED candidate: $dir"
  fi
done < <(find "$ROOT" -mindepth 2 -maxdepth 2 -type d -print0 | sort -z)
if [ "$found" -eq 0 ]; then
  exit 0
fi
