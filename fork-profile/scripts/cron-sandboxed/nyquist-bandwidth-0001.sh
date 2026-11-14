#!/usr/bin/env bash
# nyquist-bandwidth-0001.sh — run directly; sandbox provider hangs on "Requesting compute"
# HERMES_NO_SANDBOX=1: intentional host execution (pure computation, no privileged paths;
# justified by sandbox provider hang on this script).
export HERMES_HOME="${HERMES_HOME:-/var/home/rainbow/.hermes}"
export HERMES_PROFILE="${HERMES_PROFILE:-fork}"
exec /usr/bin/timeout 110 /usr/bin/python3 /var/home/rainbow/.hermes/profiles/fork/scripts/nyquist-bandwidth-estimator.py "$@"
