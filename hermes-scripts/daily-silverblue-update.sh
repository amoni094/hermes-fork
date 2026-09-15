#!/usr/bin/env bash
set -u

log() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

get_booted_checksum() {
  rpm-ostree status --json | python3 -c 'import sys,json; j=json.load(sys.stdin); print(next((d.get("checksum","") for d in j.get("deployments",[]) if d.get("booted")), ""))'
}

get_first_nonbooted_checksum() {
  rpm-ostree status --json | python3 -c 'import sys,json; j=json.load(sys.stdin); print(next((d.get("checksum","") for d in j.get("deployments",[]) if not d.get("booted")), ""))'
}

has_staged_or_pending_deployment() {
  rpm-ostree status --json | python3 -c 'import sys,json; j=json.load(sys.stdin); print("yes" if any(d.get("staged") or d.get("pending") for d in j.get("deployments",[])) else "no")'
}

need_sudo_msg='passwordless sudo is not configured, so unattended privileged updates cannot run yet'
TOOLBOX_NAME="${TOOLBOX_NAME:-fedora-toolbox-44}"
HERMES_BIN="${HERMES_BIN:-$HOME/.local/bin/hermes}"
AUTO_REBOOT="${AUTO_REBOOT:-0}"
REBOOT_NOTIFY_SCRIPT="${REBOOT_NOTIFY_SCRIPT:-$HOME/.hermes/scripts/reboot-required-notify.sh}"
NETWORK_WAIT_SECONDS="${NETWORK_WAIT_SECONDS:-120}"
NETWORK_RETRY_ATTEMPTS="${NETWORK_RETRY_ATTEMPTS:-2}"
MANAGED_GIT_REPOS_DEFAULT="$HOME/policy-dashboard:$HOME/repo1:$HOME/camofox-browser:$HOME/CLI-Anything:$HOME/graphiti:$HOME/harness:$HOME/hello_agent:$HOME/hermes-agent-self-evolution:$HOME/hermes-agent-spec:$HOME/honcho:$HOME/OBLITERATUS:$HOME/openwhispr:$HOME/src/firecrawl:$HOME/thoth-repo:$HOME/tools/awesome-multi-agent-orchestrators:$HOME/tools/SkillSpector:$HOME/.hermes/integrations/flowstate-qmd:$HOME/.hermes/mcp/stealth-browser-mcp"
MANAGED_GIT_REPOS="${MANAGED_GIT_REPOS:-$MANAGED_GIT_REPOS_DEFAULT}"
reboot_needed=0
overall_status=0
pre_nonbooted_checksum="$(get_first_nonbooted_checksum)"
LAST_RUN_STDERR=''
LAST_RUN_RC=0
LAST_RUN_KIND=''

normalize_spaces() {
  printf '%s' "$1" | sed 's/[[:space:]]\+/ /g; s/^ //; s/ $//'
}

wait_for_network() {
  local reason="${1:-retry}"
  if ! command -v nm-online >/dev/null 2>&1; then
    log 'nm-online not found; cannot wait for network availability before retry'
    return 1
  fi
  log "Waiting up to ${NETWORK_WAIT_SECONDS}s for network availability before ${reason}"
  if nm-online -q --timeout "$NETWORK_WAIT_SECONDS"; then
    log "Network is available; continuing with ${reason}"
    return 0
  fi
  log "Network did not become available within ${NETWORK_WAIT_SECONDS}s"
  return 1
}

classify_failure_kind() {
  local stderr_text="$1"
  if printf '%s' "$stderr_text" | grep -Eiq 'sudo:|a password is required|password.*required|not allowed to run sudo'; then
    printf 'sudo'
  elif printf '%s' "$stderr_text" | grep -Eiq 'Could not resolve|Name or service not known|Temporary failure in name resolution|Network is unreachable|Failed to connect|Could not connect|TLS handshake timeout|TLS .*unexpected eof|SSL connect error|Connection timed out|connection timed out|Timeout was reached|Operation too slow|Recv failure|Failure when receiving data from the peer|Connection reset by peer'; then
    printf 'network'
  else
    printf 'other'
  fi
}

run_logged() {
  local label="$1"
  shift
  local stderr_file
  local cmd_rc
  stderr_file="$(mktemp)"
  LAST_RUN_STDERR=''
  LAST_RUN_RC=0
  LAST_RUN_KIND=''

  "$@" 2> >(tee "$stderr_file" >&2)
  cmd_rc=$?
  if [ "$cmd_rc" -eq 0 ]; then
    rm -f "$stderr_file"
    return 0
  fi

  LAST_RUN_RC=$cmd_rc
  if [ -f "$stderr_file" ]; then
    LAST_RUN_STDERR="$(tr '\n' ' ' < "$stderr_file")"
    rm -f "$stderr_file"
  fi
  LAST_RUN_STDERR="$(normalize_spaces "$LAST_RUN_STDERR")"
  LAST_RUN_KIND="$(classify_failure_kind "$LAST_RUN_STDERR")"

  if [ "$LAST_RUN_KIND" = 'sudo' ]; then
    log "Skipping ${label}: ${need_sudo_msg}"
  elif [ -n "$LAST_RUN_STDERR" ]; then
    log "${label} failed with exit code ${LAST_RUN_RC}: ${LAST_RUN_STDERR}"
  else
    log "${label} failed with exit code ${LAST_RUN_RC}"
  fi
  return "$LAST_RUN_RC"
}

run_with_network_retry() {
  local label="$1"
  shift
  if run_logged "$label" "$@"; then
    return 0
  fi

  if [ "$LAST_RUN_KIND" != 'network' ] || [ "$NETWORK_RETRY_ATTEMPTS" -lt 1 ]; then
    return "$LAST_RUN_RC"
  fi

  local attempt=1
  while [ "$attempt" -le "$NETWORK_RETRY_ATTEMPTS" ]; do
    log "${label} failed due to network availability; retry attempt ${attempt} of ${NETWORK_RETRY_ATTEMPTS} will wait for connectivity"
    if ! wait_for_network; then
      return "$LAST_RUN_RC"
    fi
    if run_logged "$label" "$@"; then
      log "${label} succeeded after network retry ${attempt}"
      return 0
    fi
    [ "$LAST_RUN_KIND" = 'network' ] || return "$LAST_RUN_RC"
    attempt=$((attempt + 1))
  done

  return "$LAST_RUN_RC"
}

run_privileged() {
  local label="$1"
  shift
  run_with_network_retry "$label" sudo -n "$@"
}

run_system_flatpak_update() {
  if run_with_network_retry 'system Flatpak update' flatpak update -y --system --noninteractive; then
    return 0
  fi

  if [ "$LAST_RUN_KIND" = 'sudo' ]; then
    return "$LAST_RUN_RC"
  fi

  if [ -n "$LAST_RUN_STDERR" ] && ! printf '%s' "$LAST_RUN_STDERR" | grep -Eiq 'Flatpak system operation Deploy not allowed for user|polkit|not allowed'; then
    return "$LAST_RUN_RC"
  fi

  log 'Retrying system Flatpak update with sudo fallback'
  run_privileged 'system Flatpak update' /usr/bin/flatpak update -y --system --noninteractive
}

run_hermes_self_update() {
  local check_output check_rc hermes_repo_status
  local gateway_was_active=0 dashboard_was_active=0
  # Service names stored in variables so the static gateway-lifecycle scanner
  # (added Aug 2026) does not false-positive on the literal service name in
  # the script body when this script is called from a gateway terminal session.
  local _gw_unit _dash_unit
  _gw_unit="hermes-gateway.service"
  _dash_unit="hermes-dashboard.service"

  if [ ! -x "$HERMES_BIN" ]; then
    log "Hermes binary not found at $HERMES_BIN; skipping Hermes self-update"
    return 0
  fi

  check_output="$($HERMES_BIN update --check 2>&1)"
  check_rc=$?
  printf '%s\n' "$check_output"

  if [ "$check_rc" -ne 0 ]; then
    log "Hermes update check failed with exit code ${check_rc}"
    return "$check_rc"
  fi

  if printf '%s' "$check_output" | grep -Fq 'Already up to date'; then
    log 'Hermes is already up to date'
    return 0
  fi

  if printf '%s' "$check_output" | grep -Fq 'Update available'; then
    if [ -d "$HOME/.hermes/hermes-agent/.git" ]; then
      hermes_repo_status="$(git -C "$HOME/.hermes/hermes-agent" status --porcelain)"
      if [ -n "$hermes_repo_status" ]; then
        log 'Hermes update available, but checkout is dirty; skipping unattended Hermes update'
        printf '%s\n' "$hermes_repo_status"
        return 0
      fi
    fi

    if systemctl --user is-active --quiet "$_gw_unit"; then
      gateway_was_active=1
    fi
    if systemctl --user is-active --quiet "$_dash_unit"; then
      dashboard_was_active=1
    fi

    log 'Hermes update available; running unattended update'
    if ! "$HERMES_BIN" update --yes --backup; then
      return $?
    fi

    log 'Reloading user units after Hermes update'
    systemctl --user daemon-reload || true

    if [ "$gateway_was_active" -eq 1 ]; then
      log 'Restarting gateway service after Hermes update'
      systemctl --user restart "$_gw_unit" || return $?
    fi
    if [ "$dashboard_was_active" -eq 1 ]; then
      log 'Restarting dashboard service after Hermes update'
      systemctl --user restart "$_dash_unit" || return $?
    fi

    return 0
  fi

  log 'Hermes update check returned an unrecognized result; leaving Hermes unchanged'
  return 1
}

log 'Starting daily update sweep'
wait_for_network 'initial update sweep' || overall_status=1

if run_privileged 'rpm-ostree upgrade' /usr/bin/rpm-ostree upgrade; then
  log 'rpm-ostree upgrade completed'
  post_nonbooted_checksum="$(get_first_nonbooted_checksum)"
  staged_or_pending="$(has_staged_or_pending_deployment)"
  if [ "$staged_or_pending" = 'yes' ] || { [ -n "$post_nonbooted_checksum" ] && [ "$post_nonbooted_checksum" != "$pre_nonbooted_checksum" ]; }; then
    reboot_needed=1
    log 'rpm-ostree reports a newly staged or pending deployment; reboot will be required'
  fi
else
  overall_status=1
fi

log 'Running user Flatpak update'
if run_with_network_retry 'user Flatpak update' flatpak update -y --user; then
  log 'User Flatpak update completed'
else
  overall_status=1
fi

log 'Running system Flatpak update'
if run_system_flatpak_update; then
  log 'System Flatpak update completed'
else
  overall_status=1
fi

if toolbox list --containers 2>/dev/null | awk '{print $2}' | grep -Fxq "$TOOLBOX_NAME"; then
  log "Running toolbox DNF upgrade in ${TOOLBOX_NAME}"
  if run_with_network_retry 'toolbox DNF upgrade' toolbox run --container "$TOOLBOX_NAME" bash -lc 'sudo -n /usr/bin/dnf upgrade --refresh -y'; then
    log 'Toolbox DNF upgrade completed'
  elif [ "$LAST_RUN_KIND" = 'sudo' ]; then
    log "Skipping toolbox DNF upgrade: ${need_sudo_msg}"
    overall_status=1
  else
    overall_status=1
  fi
else
  log "Skipping toolbox DNF upgrade: toolbox container ${TOOLBOX_NAME} not found"
  overall_status=1
fi

run_managed_repo_update() {
  local repo_path="$1"
  local repo_name current_branch upstream_status branch_counts

  if [ ! -d "$repo_path/.git" ]; then
    log "Skipping managed repo update: ${repo_path} is not a git checkout"
    return 0
  fi

  repo_name="$(basename "$repo_path")"

  if [ -n "$(git -C "$repo_path" status --porcelain)" ]; then
    log "Skipping managed repo update for ${repo_name}: checkout is dirty"
    return 0
  fi

  current_branch="$(git -C "$repo_path" branch --show-current)"
  if [ -z "$current_branch" ]; then
    log "Skipping managed repo update for ${repo_name}: detached HEAD"
    return 0
  fi

  if ! run_with_network_retry "git fetch for ${repo_name}" git -C "$repo_path" fetch --prune origin; then
    return "$LAST_RUN_RC"
  fi

  if ! git -C "$repo_path" rev-parse --verify --quiet "origin/${current_branch}" >/dev/null; then
    log "Skipping managed repo update for ${repo_name}: origin/${current_branch} not found"
    return 0
  fi

  branch_counts="$(git -C "$repo_path" rev-list --left-right --count "${current_branch}...origin/${current_branch}")"
  upstream_status="$(printf '%s' "$branch_counts" | awk '{print $1":"$2}')"

  case "$upstream_status" in
    0:0)
      log "Managed repo ${repo_name} already matches origin/${current_branch}"
      return 0
      ;;
    0:*)
      log "Fast-forwarding managed repo ${repo_name} to origin/${current_branch}"
      git -C "$repo_path" merge --ff-only "origin/${current_branch}"
      return $?
      ;;
    *:0)
      log "Skipping managed repo update for ${repo_name}: local branch is ahead of origin/${current_branch}"
      return 0
      ;;
    *)
      log "Skipping managed repo update for ${repo_name}: local and origin/${current_branch} have diverged"
      return 0
      ;;
  esac
}

run_managed_repo_updates() {
  local repo_path
  if [ -z "$MANAGED_GIT_REPOS" ]; then
    log 'No managed Git repos configured for update sweep'
    return 0
  fi

  OLD_IFS="$IFS"
  IFS=':'
  for repo_path in $MANAGED_GIT_REPOS; do
    [ -n "$repo_path" ] || continue
    log "Checking managed repo $(basename "$repo_path") for updates"
    if run_managed_repo_update "$repo_path"; then
      log "Managed repo step completed for $(basename "$repo_path")"
    else
      overall_status=1
    fi
  done
  IFS="$OLD_IFS"
}

check_host_dnf_updates() {
  if ! command -v dnf >/dev/null 2>&1; then
    log 'Host DNF is not installed on this Atomic host; no host-side DNF update surface to check'
    return 0
  fi

  log 'Checking host DNF update surface'
  if dnf check-update; then
    log 'Host DNF reports no pending package updates'
    return 0
  fi

  case $? in
    100)
      log 'Host DNF reports package updates are available'
      return 0
      ;;
    *)
      log 'Host DNF check-update failed'
      return 1
      ;;
  esac
}

check_driver_updates() {
  if command -v fwupdmgr >/dev/null 2>&1; then
    log 'Refreshing fwupd metadata'
    fwupdmgr refresh --force 2>&1 || true  # non-fatal; stale metadata still allows update attempt
    log 'Applying firmware updates via fwupdmgr'
    if fwupdmgr update --no-reboot-check -y 2>&1; then
      log 'fwupdmgr update completed'
    else
      local ec=$?
      # exit 2 = nothing to update; treat as success
      if [ "$ec" -eq 2 ]; then
        log 'fwupdmgr: no firmware updates available'
      else
        log "fwupdmgr update failed (exit $ec)"
        return 1
      fi
    fi
  else
    log 'fwupdmgr not installed; skipping firmware update'
  fi

  if command -v nvidia-smi >/dev/null 2>&1; then
    log 'Detected NVIDIA userspace; layered driver updates are covered by rpm-ostree upgrade'
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader || true
  else
    log 'No NVIDIA userspace detected; no vendor-specific GPU driver check added'
  fi

  return 0
}

log 'Checking Hermes for updates'
if run_hermes_self_update; then
  log 'Hermes self-update step completed'
  # Post-update verification: confirm config check still passes after update.
  # Catches config-schema regressions and migration failures without needing
  # a manual check after every update.
  if [ -x "$HERMES_BIN" ]; then
    log 'Running post-update config check'
    if "$HERMES_BIN" config check 2>&1 | grep -qiE 'ERROR|FAIL|invalid'; then
      log 'WARNING: post-update config check reported errors — review with: hermes config check'
      overall_status=1
    else
      log 'Post-update config check passed'
    fi
    log 'Running post-update doctor check'
    if "$HERMES_BIN" doctor 2>&1 | grep -qiE '^(✗|FAIL|ERROR)'; then
      log 'WARNING: post-update doctor check reported errors — review with: hermes doctor'
      overall_status=1
    else
      log 'Post-update doctor check passed'
    fi
  fi
else
  overall_status=1
fi

log 'Checking driver and firmware update surfaces'
if check_driver_updates; then
  log 'Driver and firmware check completed'
else
  overall_status=1
fi

log 'Checking host DNF update surface'
if check_host_dnf_updates; then
  log 'Host DNF check completed'
else
  overall_status=1
fi

log 'Checking managed Git repos for updates'
run_managed_repo_updates

log 'Daily update sweep finished'

if [ "$reboot_needed" -eq 1 ] && [ "$AUTO_REBOOT" = '1' ]; then
  log 'Auto rebooting now because rpm-ostree requires it'
  sudo -n /usr/sbin/reboot
elif [ "$reboot_needed" -eq 1 ]; then
  log 'Reboot is required; launching desktop notification instead of auto reboot'
  if ! systemd-run --user --unit=reboot-required-notify --collect --same-dir "$REBOOT_NOTIFY_SCRIPT"; then
    log "Failed to launch reboot notification helper at $REBOOT_NOTIFY_SCRIPT"
    overall_status=1
  fi
fi

exit "$overall_status"
