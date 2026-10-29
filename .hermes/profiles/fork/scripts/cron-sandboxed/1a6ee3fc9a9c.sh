#!/usr/bin/env bash
# Raise openshell timeout to match the job's 6h window. stale_bound = max(3*INACTIVITY, SCRIPT_TIMEOUT, 7200)
# With 10800 the claim was declared wedged after 2h idle; 21600 matches the allowed 6h run.
export HERMES_OPENSHELL_TIMEOUT=21600
exec "/var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandbox-wrapper.sh" "/var/home/rainbow/.hermes/profiles/fork/scripts/research-pipeline-weekly.py" "$@"
