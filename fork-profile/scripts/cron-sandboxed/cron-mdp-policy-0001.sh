#!/usr/bin/env bash
# cron-mdp-policy-0001.sh — run directly; sandbox provider hangs on "Requesting compute"
# HERMES_NO_SANDBOX=1: intentional host execution (no SecondBrain/special host paths;
# justified by sandbox provider hang on this script — pure computation, read-only).
export HERMES_HOME="${HERMES_HOME:-/var/home/rainbow/.hermes}"
export HERMES_PROFILE="${HERMES_PROFILE:-fork}"
exec /usr/bin/timeout 110 /usr/bin/python3 /var/home/rainbow/.hermes/profiles/fork/scripts/cron-mdp-policy.py "$@"
