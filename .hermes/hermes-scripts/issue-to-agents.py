#!/usr/bin/env python3
"""
issue-to-agents.py — Route open GitHub issues to Hermes subagents with worktree isolation
~/.hermes/scripts/issue-to-agents.py

Usage:
  python3 ~/.hermes/scripts/issue-to-agents.py --repo OWNER/REPO [--label LABEL] [--limit N] [--dry-run]

Fetches open issues (filtered by label if given), creates a git worktree for each,
then prints the hermes delegate_task invocations that would execute them.
Actually dispatches using hermes CLI if --execute flag is given.

Requires: gh CLI authenticated.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

WORKTREE_BASE = Path.home() / "hermes-worktrees"


def gh(cmd: list[str]) -> list:
    result = subprocess.run(
        ["gh"] + cmd,
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"gh error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def get_issues(repo: str, label: str | None, limit: int) -> list[dict]:
    args = ["issue", "list", "--repo", repo, "--state", "open",
            "--json", "number,title,body,labels,assignees",
            "--limit", str(limit)]
    if label:
        args += ["--label", label]
    return gh(args)


def ensure_worktree(repo_path: Path, issue_num: int, repo: str) -> Path | None:
    wt_path = WORKTREE_BASE / repo.replace("/", "_") / f"issue-{issue_num}"
    if wt_path.exists():
        return wt_path
    if not repo_path.exists():
        print(f"  [skip] repo not cloned locally: {repo_path}", file=sys.stderr)
        return None
    WORKTREE_BASE.mkdir(parents=True, exist_ok=True)
    branch = f"issue-{issue_num}-agent"
    result = subprocess.run(
        ["git", "-C", str(repo_path), "worktree", "add", "-b", branch, str(wt_path), "HEAD"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  [warn] worktree create failed: {result.stderr.strip()}", file=sys.stderr)
        return None
    return wt_path


def build_task_prompt(issue: dict, repo: str, wt_path: Path | None) -> str:
    title = issue["title"]
    body = (issue.get("body") or "")[:1000]
    num = issue["number"]
    wt_note = f"Work in worktree: {wt_path}" if wt_path else "No local worktree available."
    return (
        f"You are fixing GitHub issue #{num} in repo {repo}.\n"
        f"Title: {title}\n"
        f"Description:\n{body}\n\n"
        f"{wt_note}\n"
        f"When done: commit your changes, push the branch, open a PR referencing issue #{num}, "
        f"and post a comment on the issue with the PR link."
    )


def main():
    parser = argparse.ArgumentParser(description="Route GitHub issues to Hermes subagents")
    parser.add_argument("--repo", required=True, help="OWNER/REPO")
    parser.add_argument("--label", help="Filter by label")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--local-repo", help="Path to local clone (for worktrees)")
    parser.add_argument("--dry-run", action="store_true", help="Print tasks, don't dispatch")
    parser.add_argument("--execute", action="store_true", help="Actually dispatch via hermes CLI")
    args = parser.parse_args()

    issues = get_issues(args.repo, args.label, args.limit)
    if not issues:
        print("No open issues found.")
        return

    repo_path = Path(args.local_repo) if args.local_repo else None

    print(f"Found {len(issues)} open issues in {args.repo}")
    print("=" * 60)

    tasks = []
    for issue in issues:
        num = issue["number"]
        title = issue["title"]
        labels = [l["name"] for l in issue.get("labels", [])]
        print(f"\nIssue #{num}: {title}")
        if labels:
            print(f"  Labels: {', '.join(labels)}")

        wt_path = None
        if repo_path:
            wt_path = ensure_worktree(repo_path, num, args.repo)
            if wt_path:
                print(f"  Worktree: {wt_path}")

        prompt = build_task_prompt(issue, args.repo, wt_path)
        tasks.append({
            "issue_number": num,
            "title": title,
            "prompt": prompt,
            "worktree": str(wt_path) if wt_path else None,
        })

    if args.dry_run or not args.execute:
        print("\n" + "=" * 60)
        print("DRY RUN — would dispatch these tasks as Hermes subagents:")
        for t in tasks:
            print(f"\n  Issue #{t['issue_number']}: {t['title'][:50]}")
            print(f"  Worktree: {t['worktree'] or 'none'}")
        print("\nRe-run with --execute to dispatch (or use the github-issue-agent skill).")
        return

    # Write task manifest for the skill to consume
    manifest_path = Path.home() / ".hermes" / "state" / f"issue-tasks-{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    _tmp_manifest_path = manifest_path.with_suffix('.tmp')
    _tmp_manifest_path.write_text(json.dumps(tasks, indent=2))
    _tmp_manifest_path.replace(manifest_path)
    print(f"\nTask manifest written to: {manifest_path}")
    print("Load the github-issue-agent skill and call dispatch_issue_tasks() to execute.")


if __name__ == "__main__":
    main()
