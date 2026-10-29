#!/usr/bin/env bash
export HERMES_OPENSHELL_TIMEOUT=180
# Run on host (no openshell sandbox): trusted memory analysis; expanduser("~") gives wrong
# path inside container (different uid). MEMORY.md is host-only. No untrusted input.
export HERMES_NO_SANDBOX=1
exec "/var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandbox-wrapper.sh" "/var/home/rainbow/.hermes/profiles/fork/scripts/memory-staleness-cron.py" "$@"
