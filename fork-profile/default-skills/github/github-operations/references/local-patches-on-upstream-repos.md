# Local Patches on Upstream Repos — Update Pattern

When a managed repo has local commits or uncommitted changes on top of upstream, you can't fast-forward it blindly. This pattern was developed while bringing all external repos current (Aug 2026).

## Decision tree

```
Is the working tree dirty (uncommitted changes)?
  YES → commit local changes first (see Case A), then merge/rebase
  NO → is HEAD ahead of origin?
    YES → rebase origin/main onto local branch (see Case B)
    NO → ff-merge is safe
```

## Case A — Uncommitted modifications (dirty working tree)

1. Understand what the local changes are: `git diff --stat HEAD`
2. Commit with a descriptive message that explains WHY the patch exists locally:
   ```
   git add <files>
   git commit -m "fix: <what> — local Hermes patch, not pushed upstream"
   ```
3. Fetch and merge upstream:
   ```
   git fetch origin
   git merge origin/main --no-edit        # or rebase for linear history
   ```
4. Resolve conflicts (see below)
5. Run the repo's test suite to verify

## Case B — Local commits ahead of origin (no uncommitted changes)

1. `git fetch origin`
2. `git rebase origin/main`
   - Preferred over merge for third-party repos: keeps local patches clearly on top
3. If conflicts: resolve (see below), then `GIT_EDITOR=true git rebase --continue`
4. Run the repo's test suite

## Cloning a fresh upstream copy for a private fork

When cloning a large repo from GitHub to create a new private fork:

1. **Use HTTPS for the initial clone, SSH for push.** SSH clones of large repos (Hermes, etc.) reliably time out at 120s in background terminal calls. HTTPS clones complete in the same window:
   ```bash
   git clone https://github.com/ORG/REPO.git my-fork-work   # HTTPS for clone
   cd my-fork-work
   git remote add fork git@github.com:ACCOUNT/fork-name.git  # SSH for push
   git push fork main
   ```

2. **Create the private repo before pushing:**
   ```bash
   gh repo create ACCOUNT/fork-name --private --description "..."
   ```
   Verify privacy after creation: `gh repo view ACCOUNT/fork-name --json name,visibility`

3. **Check upstream API surface before patching.** Feature flags and named attributes in a fork may not exist in the latest upstream — always grep the fresh clone before writing patches:
   ```bash
   grep -rn 'attribute_name' /path/to/fresh-clone/ --include='*.py' | grep -v __pycache__
   ```
   Example: `rr_scorer_lambda` existed only in an old local fork, not in upstream Hermes ≥ v2026.9.7. Patching against the old API wastes effort.

## Case C — Both local and remote have diverged (dual-ahead feature branch)

When `git log HEAD..fork/branch` shows remote commits AND `git log fork/branch..HEAD` shows local commits — both sides are ahead of the merge base — naive `git rebase fork/branch` replays duplicate commits and creates unnecessary conflicts.

Use `--onto` to replay only the unique local commits on top of the remote tip:

```bash
git fetch fork
MERGE_BASE=$(git merge-base HEAD fork/feature/<branch>)
git rebase --onto fork/feature/<branch> $MERGE_BASE
# If clean, push — fast-forward from the remote's perspective:
git push fork feature/<branch>
# If push is rejected because remote moved since fetch, use force-with-lease (safe after --onto):
git push --force-with-lease fork feature/<branch>
```

Never use plain `--force` on a shared feature branch. `--force-with-lease` is safe here because `--onto` already incorporated the remote tip — it only fails if someone pushed between your fetch and push, which is the right signal to stop and re-inspect.

## Conflict resolution heuristics

**Upstream rewrote the whole section you patched:**
- If upstream's version already covers your concern (e.g. added proper guards/validation): keep HEAD (upstream), discard yours entirely.
- Remove any helper methods or imports you added that are now superseded.
- Example: SkillSpector's `_extract_zip` was rewritten with comprehensive zip-slip, size bomb, and symlink guards — our simpler `_validate_zip_member` instance method was completely superseded. Dropped it, kept upstream.

**Upstream made cosmetic/unrelated changes to the same file:**
- Keep both in a clean manual merge. Your substantive change + their formatting.

**Your patch fills a genuine gap upstream doesn't address:**
- Keep yours rebased on top. Leave a comment in the code noting it's a local patch.

**Import conflicts:**
- Upstream often has a richer import set. If their import block is a superset, accept HEAD entirely.

## Test assertion updates after upstream rebase

When upstream changes error message strings that your tests assert:
- Broaden the `match=` regex to cover multiple phrasings:
  ```python
  # Before (brittle):
  with pytest.raises(ValueError, match="Unsafe zip entry path"):
  # After (robust):
  with pytest.raises(ValueError, match="escape|zip.slip|traversal|Unsafe zip"):
  ```
- Same for symlink-related messages: `match="symlink|link.*not supported|Zip links"`
- This keeps tests valid across upstream refactors without hardcoding one library's internal wording.

## Separating your failures from upstream pre-existing failures

Before blaming your patch for a test failure, confirm the failure exists on unmodified upstream:
```bash
git stash   # or checkout a clean branch
python -m pytest tests/path/to/failing_test.py -q --tb=line
git stash pop
```
If the same failure appears without your changes, it is a pre-existing upstream issue — document it and exclude the test with `--deselect` rather than trying to fix it.

Common upstream pre-existing failures to watch for in Hermes:
- `DaemonThreadPoolExecutor._initializer` — Python 3.14 renamed `_initializer` in `ThreadPoolExecutor`. Fails in `tools/daemon_pool.py:53`. Deselect `TestWorkerTeardownOnCeiling` until upstream fixes it.
- `acp` module missing — tests under `tests/acp/` and `tests/acp_adapter/` need the full Hermes install. Use `--ignore=tests/acp --ignore=tests/acp_adapter` when running in a fresh clone without the full install.
- `wcwidth` missing — `test_markdown_tables.py` needs this; use `--ignore=tests/agent/test_markdown_tables.py`.

## Post-rebase verification

Always run the repo's own test suite after rebasing local patches:

| Repo | Test command |
|---|---|
| graphiti | `source .venv/bin/activate && python -m pytest tests/ --ignore=tests/integration -q` |
| SkillSpector | `.venv/bin/pytest tests/unit/ -q` |
| ouroboros-plugins-local | `toolbox run ouroboros test` or `pytest` in venv |
| hermes-fork (fresh clone) | `python -m pytest tests/agent/test_context_compressor.py tests/tools/test_plugin_guard.py -q --ignore=tests/acp --ignore=tests/acp_adapter --deselect tests/agent/test_compression_attempt_lifecycle.py::TestWorkerTeardownOnCeiling` |

For graphiti: integration tests need a live Neo4j instance (localhost:7687). The unit tests run without it; skip integration tests with `--ignore=tests/integration` or `-k "not integration"`.

For graphiti's venv: it uses `uv sync --extra dev` to install test deps (pytest, etc.) into `.venv/`. Do NOT use `uv run pytest` alone — it creates a fresh isolated env that lacks pytest. Use `source .venv/bin/activate && python -m pytest` instead, or ensure dev extras are synced first.

## Repos excluded from automated fast-forward (safely local-ahead)

These repos have local commits that have not been pushed upstream and should remain excluded from the managed auto-update list:

| Repo | Reason |
|---|---|
| `~/ouroboros-plugins-local` | Active local plugin development; we push TO it, not pull FROM it |
| `~/hermes-to-cowork-port` | 1 commit ahead (OpenAI routing sync); port repo, no upstream to merge |

The daily update script handles these correctly: it logs "local branch is ahead" and skips without error.

## Graphiti temperature guard (local patch)

File: `graphiti_core/llm_client/anthropic_client.py`

Upstream graphiti passes `temperature=self.temperature` unconditionally to `client.messages.create()`. This fails when `temperature=None` (which is required for extended-thinking / reasoning models). Our local patch:

```python
# Only pass temperature when it is a valid float; omit when None (reasoning models)
extra_kwargs: dict = {}
if self.temperature is not None:
    extra_kwargs['temperature'] = float(self.temperature)
result = await self.client.messages.create(
    system=system_message.content,
    max_tokens=max_creation_tokens,
    messages=user_messages_cast,
    model=self.model,
    tools=tools,
    tool_choice=tool_choice,
    **extra_kwargs,
)
```

This patch is committed locally as: `fix: skip temperature arg for reasoning models; extend entity/edge types for hermes-default KG`

When merging future upstream changes to this file, check whether upstream has added native reasoning-model support that makes this patch redundant.
