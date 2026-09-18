#!/usr/bin/env bash
# tool-sandbox.sh — SkillEffect-inspired memory-bounded execution sandbox
# arXiv:2608.17007 (SkillEffect: Checked Lowering for Memory-Bounded Agent Tools)
#
# Usage:
#   ~/.hermes/scripts/tool-sandbox.sh [--mem MB] [--cpu PCT] [--timeout SEC] \
#       [--image IMAGE] [--mount-rw PATH] -- COMMAND [ARGS...]
#
# Wraps a shell command in a rootless podman container with hard memory + CPU limits.
# Falls back to systemd-run (host-native, no container isolation) if podman unavailable.
#
# SCOPE: designed for untrusted/LLM-generated shell snippets, bulk data transforms,
# and memory-risk one-shot scripts. NOT suitable as a drop-in wrapper for Hermes
# interpreter cron jobs (those need network, Python, and home dir access).
#
# Image selection:
#   Default: alpine:3.20  (no Python, no network — maximum isolation)
#   For Python scripts: use --image python:3.11-slim
#   For Hermes interpreters: use --image python:3.11-slim --mount-rw "$HOME/.hermes"
#
# Exit codes (from container / timeout):
#   0   — success
#   1   — command non-zero exit (propagated)
#   137 — OOM killed by cgroup (memory limit hit)
#   124 — timeout (killed by outer timeout)
#   2   — sandbox setup failure (usage error)
#   N   — any other exit from the wrapped command (passed through unchanged)
#
# Security notes:
#   --volume with :z relabels the mounted path as container_file_t on SELinux systems.
#   Avoid mounting $HOME directly; mount only the specific subdirectory you need.
#   --network=none blocks all outbound calls; remove if the command needs internet.

set -euo pipefail

MEM_MB=512
CPU_QUOTA=50      # percent of one core (50 = 0.5 CPU)
TIMEOUT_SEC=120
IMAGE="alpine:3.20"
EXTRA_MOUNTS=()   # accumulates --mount-rw args as volume flags
WORKDIR="$(pwd)"

usage() {
    cat >&2 <<'USAGE'
Usage: tool-sandbox.sh [OPTIONS] -- COMMAND [ARGS...]

Options:
  --mem MB          Memory limit in MB (default: 512)
  --cpu PCT         CPU quota, % of one core (default: 50)
  --timeout SEC     Wall-clock timeout in seconds (default: 120)
  --image IMAGE     Container image (default: alpine:3.20)
  --mount-rw PATH   Mount host PATH into container at same path, read-write.
                    Repeat for multiple mounts. Avoid mounting $HOME.
  -h, --help        Show this help

Example (Python script with hermes cache access):
  tool-sandbox.sh --mem 256 --image python:3.11-slim \
      --mount-rw "$HOME/.hermes/cache" \
      -- python3 my-transform.py
USAGE
    exit 2
}

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mem)       MEM_MB="$2";       shift 2 ;;
        --cpu)       CPU_QUOTA="$2";    shift 2 ;;
        --timeout)   TIMEOUT_SEC="$2";  shift 2 ;;
        --image)     IMAGE="$2";        shift 2 ;;
        --mount-rw)
            # Mount the given host path at the same container path, rw.
            # Do NOT use :z — on Fedora Silverblue (SELinux enforcing), relabeling
            # user home dirs and project dirs is blocked and would corrupt labels.
            _MNTPATH="$2"
            EXTRA_MOUNTS+=("--volume" "${_MNTPATH}:${_MNTPATH}:rw")
            shift 2 ;;
        --)          shift; break ;;
        -h|--help)   usage ;;
        *)           echo "Unknown flag: $1" >&2; usage ;;
    esac
done

if [[ $# -eq 0 ]]; then
    echo "Error: no command specified after --" >&2
    usage
fi

CMD=("$@")
MEM_BYTES=$((MEM_MB * 1024 * 1024))

# ── Podman path (preferred: rootless, cgroup v2) ─────────────────────────────
if command -v podman &>/dev/null; then

    SANDBOX_OUT="${HOME}/.hermes/cache/sandbox"
    mkdir -p "${SANDBOX_OUT}"

    # Mount workdir at /work; extra mounts added by --mount-rw flags.
    # :z only on enforcing SELinux, only on the workdir (not user-supplied paths,
    # which were already handled above).
    # Never use :z on the workdir — it would relabel $HOME or project dirs
    # on SELinux-enforcing systems (Fedora Silverblue), which is both blocked
    # and destructive. Use :z only on explicitly user-supplied --mount-rw paths.
    WORKDIR_FLAG=("--volume" "${WORKDIR}:/work:rw")

    # Run with timeout. If podman run itself fails (missing image, permission),
    # do not silently fall through — let the error surface.
    exec timeout "${TIMEOUT_SEC}" podman run \
        --rm \
        --network=none \
        --memory="${MEM_BYTES}" \
        --memory-swap="${MEM_BYTES}" \
        --cpu-quota=$((CPU_QUOTA * 1000)) \
        --cpu-period=100000 \
        --pids-limit=64 \
        --security-opt=no-new-privileges \
        --read-only \
        --tmpfs /tmp:rw,size=64m \
        "${WORKDIR_FLAG[@]}" \
        --volume "${SANDBOX_OUT}:/output:rw" \
        "${EXTRA_MOUNTS[@]+"${EXTRA_MOUNTS[@]}"}" \
        --workdir /work \
        "${IMAGE}" \
        "${CMD[@]}"
fi

# ── systemd-run fallback (host-native, cgroup memory + CPU only) ─────────────
# No container isolation. Memory and CPU limits are real via cgroup.
# Uses RuntimeMaxSec (not TimeoutStopSec) for wall-clock enforcement.
if command -v systemd-run &>/dev/null; then
    echo "[tool-sandbox] podman not found; using systemd-run (no container isolation)" >&2
    exec systemd-run \
        --user \
        --scope \
        --property="MemoryMax=${MEM_BYTES}" \
        --property="CPUQuota=${CPU_QUOTA}%" \
        --property="RuntimeMaxSec=${TIMEOUT_SEC}" \
        -- "${CMD[@]}"
fi

# ── Last resort: bare timeout (no memory/CPU limits) ─────────────────────────
echo "[tool-sandbox] Neither podman nor systemd-run available; running unsandboxed" >&2
exec timeout "${TIMEOUT_SEC}" "${CMD[@]}"
