#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "usage: $0 <skill-name> [output-dir]" >&2
  exit 2
fi
SKILL="$1"
OUTDIR="${2:-}"
ROOT=/var/home/rainbow/.hermes/integrations/hermes-agent-self-evolution/output/${SKILL}
if [ -z "$OUTDIR" ]; then
  OUTDIR=$(find "$ROOT" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)
fi
/var/home/rainbow/.hermes/scripts/hermes-evolution-review.sh "$SKILL" "$OUTDIR" >/tmp/hermes-evolution-review.out
TARGET=$(find /var/home/rainbow/.hermes/skills -path "*/${SKILL}/SKILL.md" | head -n 1)
[ -n "$TARGET" ]
cp "$OUTDIR/evolved_skill.md" "$TARGET"
echo "PROMOTED $SKILL from $OUTDIR to $TARGET"
