#!/usr/bin/env python3
# Daily Hermes update (no_agent cron) -- see skill hermes-host-maintenance
import fcntl, json, os, subprocess, sys
from datetime import datetime
from pathlib import Path

# Resolve HERMES_HOME robustly: env var may point to the profile dir in fork sessions,
# so anchor from this script's known location (scripts/ inside the fork profile).
_script_dir = Path(__file__).resolve().parent          # …/profiles/fork/scripts
_profile_dir_from_script = _script_dir.parent          # …/profiles/fork
_hermes_home_from_script = _profile_dir_from_script.parent.parent  # …/.hermes
HERMES_HOME = _hermes_home_from_script
FORK_DIR = HERMES_HOME / "hermes-fork"
PROFILE_DIR = _profile_dir_from_script
LOG_FILE = PROFILE_DIR / "cache" / "scratch" / "hermes-update.log"
LOCK_FILE = PROFILE_DIR / "cache" / "scratch" / "hermes-update.lock"
HERMES_BIN = FORK_DIR / ".hermes" / "bin" / "hermes"
FORK_WRAPPER = Path.home() / ".local" / "bin" / "hermes-fork"
UPSTREAM_REMOTE = "upstream-" + "agent"
UPSTREAM_BRANCH = "main"
UPSTREAM_REF = UPSTREAM_REMOTE + "/" + UPSTREAM_BRANCH

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Concurrency lock: only one instance at a time (H4)
_lock_fh = open(str(LOCK_FILE), "w", encoding="utf-8")
try:
    fcntl.flock(_lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    print("[SKIP] Another hermes-daily-update instance is running; exiting.", file=sys.stderr)
    sys.exit(0)

results = []
start = datetime.now().isoformat()
behind_count = 0  # initialise before use (H9)
merge_ok = False  # track merge outcome for smoke-test gate (H8)


def run(cmd, cwd=None, timeout=300, extra_env=None):
    env = None
    if extra_env:
        env = dict(os.environ)
        env.update(extra_env)
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {timeout}s"
    except Exception as exc:
        return False, str(exc)


def step(name, cmd, cwd=None, timeout=300, extra_env=None):
    ok, out = run(cmd, cwd=cwd, timeout=timeout, extra_env=extra_env)
    results.append({"step": name, "ok": ok, "out": out[:2000]})
    label = "OK  " if ok else "FAIL"
    dest = sys.stdout if ok else sys.stderr
    print(f"[{label}] {name}" + ("" if ok else f": {out[:200]}"), file=dest)
    return ok


def write_log():
    overall_ok = all(r["ok"] for r in results)
    summary = {
        "started": start,
        "finished": datetime.now().isoformat(),
        "behind_upstream": behind_count,
        "steps": results,
        "overall_ok": overall_ok,
    }
    with open(str(LOG_FILE), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return overall_ok


# Explicit git identity env to ensure merge commits work in cron context (H5)
GIT_ID_ENV = {
    "GIT_AUTHOR_NAME": "amoni094",
    "GIT_AUTHOR_EMAIL": "amoni094@gmail.com",
    "GIT_COMMITTER_NAME": "amoni094",
    "GIT_COMMITTER_EMAIL": "amoni094@gmail.com",
}

# Step 0 -- hermes update (runs as subprocess; gateway restart doesn't kill us)
step("hermes-update", [str(HERMES_BIN), "update", "--yes"], timeout=300)

# Step 1a -- fetch upstream; ABORT merge path if fetch fails (H2)
fetch_ok = step("git-fetch-upstream", ["git", "fetch", UPSTREAM_REMOTE, UPSTREAM_BRANCH],
                cwd=FORK_DIR, extra_env=GIT_ID_ENV)

if not fetch_ok:
    results.append({"step": "merge-skipped", "ok": False,
                    "out": "Skipped: fetch failed (network/SSH error)"})
    print("[SKIP] Merge skipped due to fetch failure", file=sys.stderr)
else:
    # Step 1b -- count commits behind
    _, behind_raw = run(["git", "log", f"HEAD..{UPSTREAM_REF}", "--oneline"], cwd=FORK_DIR)
    behind_count = len([ln for ln in behind_raw.splitlines() if ln.strip()])
    results.append({"step": "commits-behind", "ok": True,
                    "out": f"{behind_count} commits behind upstream"})
    print(f"[INFO] {behind_count} commits behind {UPSTREAM_REF}")

    if behind_count > 0:
        tag_name = "backup/pre-merge-" + datetime.now().strftime("%Y%m%d-%H%M")
        step("git-backup-tag", ["git", "tag", tag_name, "HEAD"], cwd=FORK_DIR)

        merge_ok = step(
            "git-merge-upstream",
            ["git", "merge", UPSTREAM_REF, "--no-edit", "-X", "theirs"],
            cwd=FORK_DIR, timeout=180, extra_env=GIT_ID_ENV,
        )

        if merge_ok:
            scripts_src = FORK_DIR / "fork-profile" / "scripts"
            if scripts_src.exists():
                step("rsync-scripts",
                     ["rsync", "-a", "--checksum",
                      str(scripts_src) + "/", str(PROFILE_DIR / "scripts")])
                run(["find", str(PROFILE_DIR / "scripts" / "__pycache__"), "-name", "*.pyc", "-delete"])

            idx_script = PROFILE_DIR / "scripts" / "skill-router-index.py"
            if idx_script.exists():
                idx_env = dict(os.environ)
                idx_env["HERMES_HOME"] = str(HERMES_HOME)
                idx_env["HERMES_PROFILE"] = "fork"
                idx_env["HERMES_CRON_BUILD"] = "1"
                r3 = subprocess.run(
                    [sys.executable, str(idx_script), "--build"],
                    capture_output=True, text=True, timeout=120, env=idx_env,
                )
                results.append({"step": "skill-index-rebuild", "ok": r3.returncode == 0,
                                 "out": (r3.stdout + r3.stderr).strip()[:500]})
                print(f"[{'OK  ' if r3.returncode == 0 else 'FAIL'}] skill-index-rebuild")

            step("git-push-origin", ["git", "push", "origin", "main"],
                 cwd=FORK_DIR, timeout=120, extra_env=GIT_ID_ENV)

            # Step 4 -- reinstall fork in its venv so the running binary picks up changes
            fork_venv_pip = FORK_DIR / "venv" / "bin" / "pip"
            if fork_venv_pip.exists():
                step("fork-pip-install",
                     [str(fork_venv_pip), "install", "-e", ".[all]", "-q"],
                     cwd=FORK_DIR, timeout=300)
            else:
                results.append({"step": "fork-pip-install", "ok": False,
                                 "out": f"venv pip not found at {fork_venv_pip}"})
                print("[FAIL] fork-pip-install: venv pip not found", file=sys.stderr)

            # Step 4b -- restart gateway so the new install is live
            step("gateway-restart",
                 [str(HERMES_BIN), "gateway", "restart"],
                 timeout=60)
        else:
            results.append({"step": "merge-aborted", "ok": False,
                             "out": "Merge failed; skipping rsync/push/smoke-test"})
            write_log()
            sys.exit(1)
    else:
        results.append({"step": "merge-skipped", "ok": True, "out": "Already up to date"})
        print("[INFO] Already up to date")

# Step 5 -- smoke test (merge abort already sys.exit(1) above, so we always run this)
step("smoke-test", [str(FORK_WRAPPER), "-z", "say ok"], timeout=120)

overall_ok = write_log()
print(f"\nLog: {LOG_FILE}")
print(f"Overall: {'OK' if overall_ok else 'FAILED'}")
sys.exit(0 if overall_ok else 1)
