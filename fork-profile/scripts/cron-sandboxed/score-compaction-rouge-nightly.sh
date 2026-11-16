#!/usr/bin/env bash
export HERMES_OPENSHELL_TIMEOUT=300
exec "/var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandbox-wrapper.sh" "/var/home/rainbow/.hermes/profiles/fork/scripts/score-compaction-rouge.py" "$@"
