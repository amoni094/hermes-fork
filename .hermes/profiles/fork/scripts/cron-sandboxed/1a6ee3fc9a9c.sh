#!/usr/bin/env bash
# Raise openshell timeout to match the job's 6h window. stale_bound = max(3*INACTIVITY, SCRIPT_TIMEOUT, 7200)
# With 10800 the claim was declared wedged after 2h idle; 21600 matches the allowed 6h run.
export HERMES_OPENSHELL_TIMEOUT=21600
# This job requires outbound HTTP (arxiv API) — run on host, not in network-isolated sandbox
export HERMES_OPENSHELL_FALLBACK=1
exec "/var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandbox-wrapper.sh" "/var/home/rainbow/.hermes/profiles/fork/scripts/research-pipeline-weekly.py" "$@"
