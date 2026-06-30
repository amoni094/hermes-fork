# Clean repo workflow verification and dispatch-byte drift

Use this reference when an Ouroboros plugin prepares a follow-on workflow seed/handoff and dispatched invocations still behave inconsistently after reinstall.

## Durable lessons

1. Separate preparation artifacts from the clean execution repo.
- A prepared handoff can be valid while `ooo run workflow ...` still fails early because the target repo is dirty.
- If `.omx/...` artifacts are written inside the target repo, worktree provisioning can fail with:
  - `Task workspace error: Cannot start task worktree from a dirty checkout`
- Reliable verification pattern:
  - prepare artifacts under an external directory such as `/tmp/.../.omx/<plugin>`
  - create or select a clean git repo
  - run `ooo run workflow <seed.yaml> --runtime codex --project-dir <clean-repo>`

2. Reinstall/trust refresh is necessary but may not be sufficient.
- After local plugin edits, reinstall the plugin and re-grant scopes.
- If dispatch still says plugin bytes changed since installation immediately afterward, inspect whether runtime files are mutating the installed plugin directory.
- Watch especially for:
  - `.omx/...` created under `~/.ouroboros/plugins/<name>/`
  - `__pycache__/` under the installed plugin tree

3. Interpret the stages separately.
- `prepared` output with a valid `seed.yaml` proves the handoff contract is aligned.
- Successful task worktree creation in a clean repo proves the dirty-checkout problem is separate from seed validity.
- Codex runtime initialization and later AC failure mean execution has progressed beyond plugin prep, YAML parsing, and worktree setup.

## Example symptoms from this class of issue
- `plugin 'superpowers' bytes have changed since installation; refusing to invoke`
- `Task workspace error: Cannot start task worktree from a dirty checkout`
- Workflow reaches codex runtime, creates a task worktree, then fails downstream on AC execution rather than on seed parsing.

## Recommended report split
- plugin prep result
- dispatcher/trust-subject result
- clean-repo worktree result
- runtime execution result
