#!/usr/bin/env bash
# system-update-cron.sh — wrapper for daily-silverblue-update.sh, runs on HOST.
# Sandbox skipped intentionally: needs rpm-ostree, toolbox, fwupdmgr, sudo, dbus.
export PATH="/var/home/rainbow/.local/bin:/usr/local/bin:/usr/bin:/usr/sbin:$PATH"
export HERMES_HOME="${HERMES_HOME:-/var/home/rainbow/.hermes}"
export HOME="/var/home/rainbow"

exec /usr/bin/bash "$HOME/.hermes/scripts/daily-silverblue-update.sh"
