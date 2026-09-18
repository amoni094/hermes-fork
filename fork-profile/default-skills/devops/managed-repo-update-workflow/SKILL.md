---
name: managed-repo-update-workflow
description: Use when updating managed external git repos safely.
triggers:
  - updating external git repos beyond the system update script
  - a managed repo is dirty (local changes) and also behind upstream
  - merging upstream into a repo that has local commits
  - post-merge service restart and test verification
  - "is any external repo out of date?"
related_skills:
  - silverblue-system-update-trigger
  - hermes-agent-independent-update-protocol
---

# Managed Repo Update Workflow

The daily update script (`~/.hermes/scripts/daily-silverblue-update.sh`) fast-forwards
repos that are behind origin and have no local changes. Repos that are dirty or
ahead of origin require manual handling. This skill covers that manual path.

## Step 1 — Classify all repos

```bash
for repo in $(echo "$MANAGED_GIT_REPOS" | tr ':' '\n'); do
  name=$(basename $repo)
  branch=$(git -C $repo branch --show-current 2>/dev/null || echo main)
  behind=$(git -C $repo rev-list --count HEAD..origin/$branch 2>/dev/null || echo ?)
  ahead=$(git -C $repo rev-list --count origin/$branch..HEAD 2>/dev/null || echo ?)
  dirty=$(git -C $repo status --porcelain 2>/dev/null | grep -v '^??' | wc -l)
  echo "$name behind=$behind ahead=$ahead dirty=$dirty"
done
```

Three categories:

| State | behind>0, dirty=0 | behind>0, dirty>0 | ahead>0, behind=0 |
|-------|-------------------|--------------------|-------------------|
| Action | Fast-forward (script handles) | Manual: commit then merge | Skip (nothing to pull) |
| Risk | Low | Possible conflicts | None |

## Step 2a — Dirty + behind: commit then merge

Do NOT stash. Stash hides the patch and makes it easy to lose.

```bash
cd ~/affected-repo
git add <modified files>
git commit -m "fix: <describe your local change>"
git merge origin/main --no-edit
```

If the merge conflicts: check whether upstream rewrote the same area with a stronger
version. Accept theirs for the core logic; keep yours only if it adds something
they don't have (a method, a type, extra fields). After resolution:

```bash
git add <conflicted files>
GIT_EDITOR=true git rebase --continue  # if rebasing; or git commit after resolving
```

## Step 2b — Dirty + ahead+behind: rebase

When you have local commits on top of old upstream:

```bash
cd ~/affected-repo
git rebase origin/main 2>&1 | tail -20
# On conflict: inspect, resolve, then:
git add <conflicted file>
GIT_EDITOR=true git rebase --continue
```

After rebase: if test assertions reference error message strings that upstream changed,
update the match patterns to accept both old and new wording:

```python
# Instead of:  match="Unsafe zip entry path"
# Use:         match="escape|zip.slip|traversal|Unsafe zip"
```

### Recurring conflict sites on long-lived fork branches

When a fork branch lives for many upstream rebase cycles, certain files
become permanent conflict sites. For each, establish a resolution recipe:
1. Read what upstream changed (their side) and what the fork adds (our side).
2. If the changes are orthogonal (different locations, independent purposes),
   keep BOTH — apply upstream's change AND the fork addition.
3. Document the resolution in the fork's skill so the next rebase operator
   doesn't re-derive it.

Common case: upstream adds filtering/safety logic to a dict comprehension
while the fork adds a new key to the same dict. Resolution: add the key
AND apply the filter. Neither supersedes the other.

## Step 3 — Post-update: uv sync and test

For any Python repo managed with uv:

```bash
cd ~/affected-repo
uv sync --extra dev   # sync base + dev deps
.venv/bin/pytest tests/unit/ -q --tb=short 2>&1 | tail -10
# Exclude integration tests that need a live DB:
.venv/bin/pytest tests/ -q --ignore=tests/integration --tb=short 2>&1 | tail -10
```

Do NOT use `pip install` in uv-managed venvs — those venvs have no pip binary.

## Step 4 — Restart any running services

If the repo backs a running systemd user service, restart it after merging:

```bash
systemctl --user restart <service>.service
sleep 4
systemctl --user is-active <service>.service   # must be: active
# Verify new PID (confirms new code is loaded):
ps -p $(systemctl --user show <service>.service -p MainPID --value) -o lstart=
```

For graphiti specifically:

```bash
systemctl --user restart graphiti-mcp.service && sleep 5
curl -s -X POST http://127.0.0.1:8765/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print("MCP OK:", d.get("result",{}).get("serverInfo"))'
```

## Pitfalls

### firecrawl: podman-compose up triggers a source build, not an image pull

`~/src/firecrawl/docker-compose.yaml` has `build: apps/api` active by default (the
`image:` line is commented out). Running `podman-compose up -d` starts a Rust+Node
compile that will time out.

To restart the api container after a git pull without building from source:

```bash
sed -i 's|build: apps/api|image: ghcr.io/firecrawl/firecrawl|' ~/src/firecrawl/docker-compose.yaml
cd ~/src/firecrawl && podman-compose up -d --no-recreate api
git -C ~/src/firecrawl checkout -- docker-compose.yaml   # restore
sleep 3 && curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3002/v1/scrape
# 404 on a bare GET = healthy (API is up, just needs a POST body)
```

### graphiti MCP server uses stale code after merge

The graphiti-mcp.service process loads Python at start time. A `git merge origin/main`
does not hot-reload it. Always restart after merging upstream into ~/graphiti.

### graphiti temperature fix: committed to source, propagates via uv sync

Our temperature guard (`if self.temperature is not None: extra_kwargs['temperature']`)
is committed as a local commit in `~/graphiti/`. `uv sync` rebuilds the venv from source,
so the fix propagates automatically. Do NOT patch the venv copy directly — it will be
overwritten. If the fix is ever dropped, reapply to source first, then `uv sync`.

### SkillSpector uses uv, not pip

`~/tools/SkillSpector/.venv` is uv-managed and has no pip binary.
After rebasing: `uv sync --extra dev` then `.venv/bin/pytest tests/unit/ -q`.

### Git ref locking errors on fetch (`cannot lock ref`)

Symptom: a managed repo fetch fails with lines like:

```
error: cannot lock ref 'refs/remotes/origin/some-branch': is at <sha-A> but expected <sha-B>
```

Cause: remote branches were force-pushed or rebased. The local ref cache holds the old
SHA and git can't atomically swap it during fetch.

Effect: benign — the main branch and working tree are unaffected. The script logs the
fetch as a failure (exit 1) and continues, but the repo's actual code is fine.

Fix: prune the stale refs manually, then the next update sweep fetches cleanly:

```bash
git -C ~/path/to/repo remote prune origin
```

Observed 2026-08-30: `hello_agent` had 7 branches with stale remote refs after a
series of agent-created PR branches were force-updated.

### Stash conflict after upstream splits a file into submodules

When a large upstream update refactors a single file into several submodules
(e.g. `browser_tool.py` → `browser_tool_cdp.py`, `browser_tool_cloud.py`, etc.),
any local stash that touched the original file will always conflict on pop: the
patched lines no longer exist in the refactored file.

Resolution:

1. `git diff HEAD <file>` to inspect what the local change actually added.
2. `grep -r '<function_name>' <dir>/` to confirm whether the functionality
   now lives in one of the new submodules.
3. If fully absorbed: `git checkout HEAD -- <file> && git stash drop stash@{N}`.
4. If the local change adds something genuinely new NOT in the submodules,
   surface it to the user with a diff — do not force-resolve.

Observed 2026-09-05: `tools/browser_tool.py` → `browser_tool_cdp`,
`browser_tool_cloud`, `browser_tool_lightpanda_fallback`; local session-function
additions were fully subsumed by the refactor.

### hermes config migrate warns about gateway restart even after updater restarted it

After `hermes update`, `hermes config migrate` may print:
"A previous `hermes update` pulled new code but did not restart running gateways."

This is a false positive when the CLI session running `config migrate` IS the
gateway process (it can't detect its own restart). Confirm with:

```bash
systemctl --user is-active hermes-gateway.service
```

If active, the warning is safe to ignore. If not active, restart it:

```bash
systemctl --user restart hermes-gateway.service
```

### Lock file deletions in working tree

If git shows `D bun.lock` / `D uv.lock` / `D flake.lock` (generated lock files deleted
in the working tree but not committed), restore from HEAD:

```bash
git -C <repo> checkout -- bun.lock uv.lock flake.lock
```

### hermes update switches branches when checkout is on a fork branch

When the active checkout is on a branch that has commits not merged into
`origin/main` (e.g. a feature/fork-dev branch), `hermes update` detects this,
prints a warning, and switches to main before pulling. The feature branch is
not touched — its commits stay. Your pre-update stash is still accessible from
main because git stash is repo-global, not branch-scoped. Pop it normally after
the update.

Do NOT assume the autostash occupies `stash@{0}` after the update. The updater
may or may not push its own autostash depending on whether it needed one. Always
run `git stash list` and find your named entry (`pre-update-<timestamp>`) before
popping.

### delegate_task: curly-brace placeholders rejected in goal/context strings

Any `{word}` pattern in a task goal or context string triggers a validation error:
"Task N goal contains an unexpanded template marker ({http_code})."
This includes valid curl options like `-w '{http_code}'` and Python f-string remnants.
Write delegate_task goals in plain prose — never use format-string placeholders.

## Adding a repo to the managed list

Append `:\$HOME/new-repo` to `MANAGED_GIT_REPOS_DEFAULT` in the update script.
Repos with local commits ahead of origin are safe to include — the script skips
repos where `ahead > 0` automatically.

```bash
bash -n ~/.hermes/scripts/daily-silverblue-update.sh && echo "syntax OK"
```

See `references/system-update-script-partial-failures.md` for known partial failure
patterns from the shared daily update script (Flatpak CDN errors, reboot notify,
rpm-ostree transaction conflicts) — captured here because the same script owns
both the Flatpak and git-repo update steps.
