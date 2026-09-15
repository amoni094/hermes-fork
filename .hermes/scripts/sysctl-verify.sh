#!/bin/bash
# sysctl-verify.sh — weekly sanity check that our sysctl tunings survived
# Logs deviations to journal. No remediation (just alerting).
# Run as root via systemd timer.

set -euo pipefail
LOG_TAG="sysctl-verify"
FAIL=0

log()  { echo "$*" | systemd-cat -t "$LOG_TAG" -p info;    echo "$*"; }
warn() { echo "$*" | systemd-cat -t "$LOG_TAG" -p warning; echo "WARN: $*"; FAIL=1; }

check() {
    local key="$1" expected="$2"
    local actual
    actual=$(sysctl -n "$key" 2>/dev/null || echo "MISSING")
    if [[ "$actual" == "$expected" ]]; then
        log "  OK  $key = $actual"
    else
        warn "  DRIFT $key: expected $expected, got $actual"
    fi
}

log "=== sysctl-verify start ==="

check vm.vfs_cache_pressure         35
check vm.compaction_proactiveness   0
check vm.watermark_boost_factor     1
check vm.watermark_scale_factor     125
check fs.inotify.max_user_instances  512
check fs.inotify.max_user_watches    524288
check vm.dirty_writeback_centisecs   1500
check net.ipv4.tcp_fastopen          3

# Check tuned profile
TUNED=$(tuned-adm active 2>/dev/null | grep -oP '(?<=profile: )\S+' || echo "unknown")
if [[ "$TUNED" == "desktop" ]]; then
    log "  OK  tuned profile = desktop"
else
    warn "  DRIFT tuned profile: expected desktop, got $TUNED"
fi

# Check thermald is running
if systemctl is-active --quiet thermald; then
    log "  OK  thermald active"
else
    warn "  DOWN thermald not running"
fi

log "=== sysctl-verify done (FAIL=$FAIL) ==="
exit $FAIL
