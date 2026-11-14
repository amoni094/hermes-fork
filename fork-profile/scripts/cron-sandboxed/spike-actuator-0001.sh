#!/usr/bin/env bash
export HERMES_OPENSHELL_TIMEOUT=1800
exec "/var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandbox-wrapper.sh" "/var/home/rainbow/.hermes/profiles/fork/scripts/spike-actuator.py" "$@"
