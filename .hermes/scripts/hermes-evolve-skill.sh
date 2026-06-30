#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "usage: $0 <skill-name> [--eval-source synthetic|sessiondb] [extra args...]" >&2
  exit 2
fi
SKILL="$1"
shift
cd /var/home/rainbow/.hermes/integrations/hermes-agent-self-evolution
. .venv/bin/activate
python -m evolution.skills.evolve_skill --skill "$SKILL" --hermes-repo /var/home/rainbow/.hermes "$@"
echo "Inspect results under /var/home/rainbow/.hermes/integrations/hermes-agent-self-evolution/output/${SKILL}/"
