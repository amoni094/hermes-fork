#!/usr/bin/env bash
# stage-improvement.sh — write a pending improvement proposal to the staging area.
# Usage: stage-improvement.sh <skill-name> <description-one-liner>
# Then pipe or append the proposal body on stdin.
#
# The curator (slow pass, 168h) reviews staged proposals and applies them via skill_manage.
# Never apply staged proposals directly from autonomous loops — route through this script first.
#
# Output: path to the staged file (printed to stdout)

set -euo pipefail

SKILL="${1:-unknown}"
DESC="${2:-no description}"
STAGE_DIR="${HOME}/.hermes/cache/pending-improvements"
mkdir -p "${STAGE_DIR}"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SAFE_SKILL="${SKILL//\//_}"
FILENAME="${STAGE_DIR}/${TIMESTAMP}_${SAFE_SKILL}.md"

cat > "${FILENAME}" <<HEADER
---
staged_at: ${TIMESTAMP}
skill: ${SKILL}
description: ${DESC}
status: pending
source: autonomous-loop
---

HEADER

# Append stdin body (proposal content)
if [ ! -t 0 ]; then
    cat >> "${FILENAME}"
fi

echo "${FILENAME}"
