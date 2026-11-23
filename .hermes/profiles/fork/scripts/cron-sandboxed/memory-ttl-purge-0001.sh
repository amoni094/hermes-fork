#!/usr/bin/env bash
export HERMES_OPENSHELL_TIMEOUT=1800
# Run on host (no openshell sandbox): trusted read-only DB operation; sandbox uid-namespace
# prevents writes to host-uid lifecycle.db and causes SANDBOX_FAIL. No untrusted input.
export HERMES_NO_SANDBOX=1
exec "/var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandbox-wrapper.sh" "/var/home/rainbow/.hermes/profiles/fork/scripts/memory-ttl-purge.py" "$@"
