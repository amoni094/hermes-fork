#!/usr/bin/env bash
export HERMES_OPENSHELL_TIMEOUT=1800
# Run on host (no openshell sandbox): trusted skill analysis; sandbox uid-namespace causes
# Permission denied on omni/score-history.json even with correct bind mounts. No untrusted input.
export HERMES_NO_SANDBOX=1
exec "/var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandbox-wrapper.sh" "/var/home/rainbow/.hermes/profiles/fork/scripts/omni_skill_scan.py" "$@"
