#!/usr/bin/env python3
"""
feature_watch_run.py — Feature watch runner for hermes-research-ops.
Referenced by: hermes-research-ops SKILL.md L244

Watches for new features/PRs in tracked repos and notifies.
Currently a stub — implement with GitHub API polling.

Usage:
  python3 feature_watch_run.py --watch REPO [--interval 3600]
  python3 feature_watch_run.py --status
"""
import argparse, json, os, pathlib, sys, time

HERMES_HOME = pathlib.Path(os.environ.get("HERMES_HOME", str(pathlib.Path.home() / ".hermes")))
WATCH_STATE = HERMES_HOME / "cache" / "feature-watch-state.json"


def load_state() -> dict:
    if WATCH_STATE.exists():
        try:
            return json.loads(WATCH_STATE.read_text())
        except Exception:
            pass
    return {"repos": [], "last_checked": {}}


def cmd_watch(repo: str, interval: int = 3600) -> None:
    state = load_state()
    if repo not in state["repos"]:
        state["repos"].append(repo)
        WATCH_STATE.parent.mkdir(parents=True, exist_ok=True)
        WATCH_STATE.write_text(json.dumps(state, indent=2))
        print(f"Added {repo} to watch list. Interval: {interval}s")
    else:
        print(f"{repo} already watched.")
    # TODO: implement actual polling loop


def cmd_status() -> None:
    state = load_state()
    repos = state.get("repos", [])
    if not repos:
        print("No repos being watched.")
        return
    print(f"Watching {len(repos)} repos:")
    for r in repos:
        last = state.get("last_checked", {}).get(r, "never")
        print(f"  {r}: last checked {last}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Feature watch runner")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--watch", metavar="REPO", help="Add repo to watch list (owner/name)")
    group.add_argument("--status", action="store_true", help="Show watch status")
    parser.add_argument("--interval", type=int, default=3600, help="Poll interval in seconds")
    args = parser.parse_args()
    if args.watch:
        cmd_watch(args.watch, args.interval)
    elif args.status:
        cmd_status()


if __name__ == "__main__":
    main()
