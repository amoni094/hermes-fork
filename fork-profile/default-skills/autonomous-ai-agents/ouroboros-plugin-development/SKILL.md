---
name: ouroboros-plugin-development
triggers:
  - A plugin command needs to be added, renamed, patched, or inspected in Ouroboros
  - A plugin works when run directly but behaves differently through ooo dispatch
  - Building, installing, or verifying a local Ouroboros plugin with collision checks
  - Plugin workspace paths, artifact paths, or dispatcher trust need adjustment
description: >
  Use when: Build, patch, install, and verify local Ouroboros plugins with collision checks, workspace-safe artifact paths, and dispatcher-vs-direct execution comparison.
related_skills:
  - autonomous-agent-loop-design
  - verification-before-completion
---

# Ouroboros Plugin Development

Use this when creating, patching, or debugging an Ouroboros plugin or a local plugin fork.

Reference: `references/skill-assimilator-similarity-hygiene.md` — ranking/tokenization hygiene for consolidation-candidate generators, including path-noise avoidance, structured-signal weighting, and regression-test guidance.
Reference: `references/display-overlap-token-hygiene.md` — keep normalized similarity scoring internal while rendering human-readable overlap evidence from unnormalized display tokens.
Reference: `references/display-evidence-prioritization.md` — prefer structured display evidence, keep prose buckets as fallback-only, and make reason strings cite the same surfaced evidence.
Reference: `references/bounded-adapter-manifest-validation.md` — bounded external-repo adapter pattern plus manifest-schema validation and `uv run --with jsonschema` verification flow.

## When to use
- A plugin command needs to be added, renamed, or inspected.
- A plugin works when run directly but behaves differently through `ooo` dispatch.
- A local fork must be installed safely for verification.
- You suspect command-name collisions with other plugins or core commands.
- A plugin writes artifacts and you need to verify they land in the caller workspace rather than mutating the installed plugin tree.

## Core workflow
1. Inspect the plugin manifest first.
   - Read `ouroboros.plugin.json` before changing code.
   - Identify command namespace, command names, entrypoint, permissions, and expected artifact paths.
2. Check for command collisions before patching behavior.
   - Look for generic subcommand names like `inspect`, `catalog`, `convert`, `list`, or `run`.
   - Prefer plugin-qualified names when the command family is broad or likely to overlap, e.g. `hermes-inspect` instead of `inspect`.
3. Verify the plugin entrypoint directly before blaming the dispatcher.
   - Run the Python module directly with `PYTHONPATH=<plugin-dir> python3 -m <module> ...`.
   - Confirm whether the plugin itself succeeds and what files it writes.
4. Reinstall the local fork and grant trust deliberately.
   - Remove the installed plugin if needed, install from the local path, then grant only the scopes declared by the manifest.
5. Compare direct execution with `ooo` dispatcher execution.
   - Run the same operation both ways.
   - If direct execution succeeds but `ooo ...` exits nonzero, treat that as a dispatcher/firewall issue until proven otherwise.
6. Verify artifact placement.
   - Confirm that run artifacts land under the caller workspace, typically `$PWD/.omx/...`.
   - Confirm the installed plugin home under `~/.ouroboros/plugins/<name>` is not being mutated by routine runs.
7. Capture the split clearly.
   - Distinguish `plugin logic works`, `artifacts written correctly`, and `dispatcher exit behavior broken` as separate findings.
8. Verify the active Ouroboros runtime backend before attributing failures to one provider.
   - Check whether Ouroboros is actually using `claude`, `codex`, `hermes`, `copilot`, or another backend.
   - If a failure log mentions a provider adapter (for example `claude_code_adapter`), confirm whether that is the current backend or stale evidence from an earlier run.
   - Use backend setup/switch commands to reproduce under the intended runtime before concluding a plugin requires a specific vendor.
9. Validate the handoff/seed contract end-to-end.
   - If a plugin emits a recommended next command, run it once and verify the referenced artifact format matches what the target Ouroboros command expects.
   - Treat `prepared artifact exists` and `recommended command actually accepts that artifact` as separate checks.
10. After any local plugin source edit, expect the installed-plugin digest/trust subject to change.
   - Reinstall the plugin from the local path before re-testing dispatched invocation.
   - Re-grant only the required scopes after reinstall.
   - If the dispatcher says plugin bytes changed since installation, treat that as an install/trust refresh step, not as evidence the code patch failed.

## Preferred implementation patterns

### 0) Runtime backend attribution before provider conclusions
- Before concluding that a plugin or workflow "requires Claude" or any other vendor, verify the active backend first.
- Useful checks in Ouroboros include:
  - `ouroboros config backend`
  - `ouroboros config show`
  - `ouroboros status health`
  - `ouroboros setup --runtime <backend> --non-interactive` for a clean reproduction under the intended backend
- Read the resulting config and confirm both high-level and orchestrator settings align, for example:
  - `llm.backend: codex`
  - `orchestrator.runtime_backend: codex`
- Treat old logs that mention `claude_code_adapter` or similar as historical evidence until you re-run under the current backend.
- Important distinction: a plugin can be backend-agnostic even when one previously-tested execution path was wired to a specific provider.

### 1) Collision-resistant command naming
- In plugin manifests and argparse subcommands, avoid bare utility verbs when they could plausibly collide with other plugin ecosystems.
- Before installing a local candidate, scan nearby plugin manifests and compare namespace + command names so you can predict collisions up front instead of learning only from install failure.
- Prefer namespaced verbs such as:
  - `hermes-inspect`
  - `hermes-catalog`
  - `hermes-convert`
- Update both the manifest and the Python CLI parser together.
- Update README examples in the same patch so the install path and direct-module path stay consistent.
- When you need only one safe setup-time verification plugin, prefer the candidate with the narrowest unique command surface.

### 2) Workspace-safe artifact roots
- Do not assume `Path.cwd()` reflects the caller workspace when invoked through the Ouroboros dispatcher.
- For plugins that write runtime artifacts, prefer this precedence:
  - explicit `--output-dir` when available
  - `OUROBOROS_PLUGIN_OUTPUT_DIR` when the dispatcher/runtime provides it
  - `OUROBOROS_PLUGIN_WORKDIR` as the caller-workspace hint
  - only then fall back to `$PWD` or `Path.cwd()`
- Safe default pattern:
  - if explicit output dir is provided, use it
  - else if `OUROBOROS_PLUGIN_OUTPUT_DIR` is set, use it directly
  - else derive the workspace root from `OUROBOROS_PLUGIN_WORKDIR`, then `$PWD`, then `Path.cwd()`
- Prefer a stable workspace-local tree such as `.ouroboros/plugin-artifacts/<plugin-name>/...` for prepared runs and handoff artifacts.
- This avoids writing transient state into the installed plugin directory, which can cause trust/digest drift or dirty local plugin homes.

### 3) Direct-vs-dispatch diagnosis
When `ooo <plugin> ...` fails but the plugin appears to have run:
- Re-run the same operation directly through the module entrypoint.
- Compare:
  - exit code
  - stdout/stderr
  - artifact paths
  - whether the dispatcher prints a trailing framework error after plugin output
- If direct succeeds and dispatch fails, preserve the plugin fix you verified and report the remaining problem as dispatcher/core behavior, not as an unresolved plugin failure.
- If the dispatcher surfaces plugin output successfully but still ends with a Typer/Click traceback, inspect the fallback command's exit path. In the top-level `ooo` fallback dispatcher, prefer `typer.Exit(...)` over `click.exceptions.Exit(...)` so successful prepared runs return cleanly instead of printing a framework traceback.

### 4) Seed artifact alignment for workflow runners
- When a plugin prepares a follow-on Ouroboros workflow input, prefer emitting a real Seed YAML artifact such as `seed.yaml`, not prose markdown like `seed.md`.
- If the next step is a workflow runner, prefer an explicit recommendation such as:
  - `ooo run workflow <seed.yaml>`
- Minimum verification:
  - the generated file parses as structured YAML
  - the file contains the fields expected by the installed Ouroboros Seed contract
  - the parse/load step succeeds before any provider-runtime work begins
- Treat "YAML parse error before model execution" as a strong sign the plugin emitted the wrong artifact shape, even if the handoff prose itself looks reasonable.

### 5) Frontmatter-driven workflow classification and parser verification
- If a plugin classifies Hermes skills or emits workflow Seeds from `SKILL.md`, inspect how it parses frontmatter before blaming the scoring heuristics.
- Treat nested metadata such as `metadata.hermes.tags` and `metadata.hermes.related_skills` as first-class signals; a flat parser can silently drop them or promote them into the wrong level.
- After changing a lightweight YAML/frontmatter parser, run a tiny direct module probe that prints the parsed structure and any flattened keys before relying on the full test suite.
- Prefer a probe that verifies three stages separately:
  - parsed nested structure is preserved
  - flattened lookup keys match what the classifier expects
  - the classifier reason/candidate list changes in the intended direction
- When adding regression tests for mixed workflow signals, assert the real contract you care about (for example "nested metadata contributes to scoring" or "candidate list includes fanout_fanin") instead of forcing a brittle exact winner when the skill intentionally mixes planning, verification, and subagent cues.
- If a test fails after a scoring tweak, inspect the parser output directly before retrying the same full-suite command; repeated identical test reruns are usually a signal that the bug is below the heuristic layer.
- When overlap evidence is shown to humans, separate display tokens from scoring tokens: keep normalized/stemmed tokens for weighted similarity math, but render overlap from a parallel unnormalized token view so review output stays readable.
- Add a focused regression that proves a readable token appears in overlap output (for example `planning`) and that its stem artifact does not (for example `plann`), then rerun the broader consolidation-ranking test to prove presentation cleanup did not move the winner.
- After the display-token fix, do one live candidate-output readback as a second verification layer; tests may still miss path fragments or generic frontmatter keys leaking into displayed overlap.
- For human-facing overlap evidence, suppress whole path-derived display buckets and filter generic frontmatter keys such as `metadata`, `name`, `description`, `tags`, and `related_skills` from the rendered overlap list; keep those signals available to internal scoring if they still help ranking.
- Add a focused regression that proves temporary-directory/path fragments (for example `tmpabc`) do not leak into displayed overlap, because fixture-based tests often pass while live output still surfaces path noise.
- After overlap-display cleanup, prefer structured evidence buckets in the rendered overlap list (`related_skill_names`, name tokens, tag tokens, related-skill tokens, workflow tokens) and keep description/generic prose buckets as fallback-only when no stronger display evidence exists.
- Expand display-only stopwords for weak prose leftovers discovered in live readback (for example `direct`, `checks`, `for`) rather than weakening internal ranking weights.
- Make similarity reason strings cite the same surfaced evidence the human can actually see (for example `shared skill terms: planning; shared tags: planning`) instead of generic labels like `shares skill identity`.
- Before claiming shared workflow shape in the reason string, verify the actual profile fields or display tokens support it; fixture pairs can share normalized overlap while still having different `workflow_family` values.

### 6) Install/trust refresh after local edits
- Local plugin patches can invalidate the dispatcher's recorded plugin digest.
- After editing plugin source in a local fork:
  - reinstall the plugin from the local path
  - re-grant the declared trust scopes
  - only then compare direct execution versus dispatched execution again
- Typical dispatcher symptom:
  - `plugin '<name>' bytes have changed since installation; refusing to invoke`
- Interpret that as a required reinstall/trust refresh, not as a logic regression in the code you just changed.
- If the byte-mismatch returns immediately after a successful reinstall, check whether routine plugin execution is mutating the installed plugin tree itself.
  - Common culprits: `.omx/...` artifacts written under `~/.ouroboros/plugins/<name>/`, or Python-generated `__pycache__` under the installed plugin directory.
  - Fix the artifact root first so routine runs write outside the installed plugin tree, then reinstall once more and retest dispatched invocation.

### 6) Clean-repo verification for prepared workflow handoffs
- Treat "prepared handoff" and "workflow execution in a clean project" as separate verification stages.
- If the plugin writes `.omx/...` inside the target repo, a later `ooo run workflow ...` can fail before runtime startup with:
  - `Task workspace error: Cannot start task worktree from a dirty checkout`
- For end-to-end verification of a prepared seed/handoff:
  - prepare artifacts outside the repo under test (for example `/tmp/.../.omx/<plugin>`), or use an explicit external `--output-dir`
  - create or choose a clean git repo as the execution target
  - run the workflow with `--project-dir <clean-repo>` so worktree creation is tested against a clean checkout rather than the artifact directory
- This clean split lets you verify three distinct stages truthfully:
  - seed/handoff preparation succeeded
  - worktree creation succeeded
  - runtime backend initialization/execution succeeded or failed downstream

### 7) Assimilating an external repo into a bounded adapter plugin
- When a user asks to "implement a repo if it helps the Ouroboros workflow", prefer an adapter plugin over copying upstream logic wholesale.
- Keep the adapter artifact-first and bounded:
  - inspect local checkout signals
  - prepare invocation plans or benchmark plans
  - emit handoff artifacts and provenance
  - avoid executing unbounded upstream workflows inside the plugin itself
- Good bounded command families are:
  - `doctor` for readiness/dependency checks
  - `inspect` for filesystem or capability evidence
  - `verify` / `prompt` / `benchmark` for prepared plans that tell Ouroboros what to run next
- If the upstream tool is optional or not installed locally, still make the adapter useful by emitting blocked/completed artifacts with concrete next actions instead of failing noisily.
- For prompt-bearing adapters, persist prompt digest/metadata rather than raw prompt text unless the contract explicitly requires the body.
- When a bounded benchmark or verify command does not execute upstream code, say so explicitly in the report and provenance so later sessions do not mistake preparation for execution.

### 8) Manifest-schema compliance is part of plugin development, not a final afterthought
- New plugin manifests in this repo must include the full top-level contract expected by `schemas/0.1/plugin.schema.json`, including:
  - `capabilities`
  - `permissions`
  - `entrypoint`
- Validate `upstream.mode` values against the schema enum before assuming a descriptive string is allowed.
  - Use only supported values such as `installed_tool`, `pinned_checkout`, `managed_install_deferred`, or `none`.
- If local dev dependencies are missing, prefer schema validation through an ephemeral tool environment instead of leaving the manifest unchecked.
  - Useful pattern: `uv run --with jsonschema python3 scripts/validate_contract.py`
- Treat contract validation as a first-class verification gate alongside unit tests; a passing CLI test does not prove the plugin is installable by the repo's manifest contract.

### 9) When extending a plugin's output contract, update tests and docs in the same pass
- If a plugin starts emitting new artifact files or metadata fields, treat code, regression tests, and README contract as one change set.
- Add at least one focused stdlib/unit test that asserts the new fields or artifact names directly.
- Prefer a verification sequence of:
  - `python3 -m py_compile ...` for syntax safety
  - a targeted unit-test module for the new contract
  - `uv run --with jsonschema python3 scripts/validate_contract.py` for manifest/schema compliance
  - one live direct-module generation against a real installed skill or fixture, followed by readback of the emitted files
- For workflow-generating plugins, verify both machine-readable and operator-readable surfaces:
  - JSON/YAML artifacts contain the new contract fields
  - markdown handoff/review files surface the same semantics clearly
- If the feature is about complexity-gated behavior or consolidation guidance, assert the actual mode/recommendation strings instead of only checking that files exist.

## Verification checklist
- Manifest read and understood before edits.
- Local fork patched in code + manifest + README when command names change.
- Plugin reinstalled from local path.
- Required trust scopes granted after reinstall.
- Direct module execution succeeds.
- `ooo` dispatcher path exercised separately.
- Artifact files verified on disk.
- Installed plugin home checked for accidental `.omx` mutation.
- Final report separates plugin success from dispatcher failure.
- If verifying a follow-on workflow, preparation artifacts are stored outside the clean execution repo or the repo is confirmed clean before workflow launch.
- If dispatcher byte-drift persists after reinstall, installed plugin tree checked for `.omx` or `__pycache__` mutations.
- If the workflow runtime uses Codex CLI, verify Codex authentication with a minimal `codex exec 'OK'` smoke test before attributing downstream AC failures to the plugin or seed artifact.

## Pitfalls
- Do not conclude a plugin is broken solely because `ooo` returns exit code 1; inspect whether the plugin still emitted valid JSON or wrote expected artifacts.
- Do not conclude a plugin or workflow is Claude-only from one historical `claude_code_adapter` failure; verify the current configured backend and rerun under it.
- Do not stop at "artifacts were prepared" when a plugin prints a recommended next command; execute that handoff path once to verify the generated artifact format matches the consumer command.
- Do not leave a markdown `seed.md` handoff in place when the installed Ouroboros workflow runner expects Seed YAML; generate a structured `seed.yaml` and recommend `ooo run workflow <seed.yaml>` explicitly.
- After editing a local plugin fork, do not interpret a plugin-byte mismatch refusal as a fresh logic bug; reinstall the plugin and re-grant trust before retesting dispatch.
- Do not leave generic verbs in a plugin CLI when the plugin is meant to coexist with other command families.
- Do not document artifact output as “current working directory” unless you have verified how the dispatcher sets working directory for subprocesses.
- Do not patch only the manifest or only the parser when renaming commands; they must move together.
- Do not stop after reinstall; verify both direct execution and dispatched execution.
- Do not treat a dirty-checkout worktree failure as evidence the prepared seed/handoff is bad; first separate artifact storage from the clean repo used for workflow execution.
- Do not keep validating a dispatched plugin from an installed tree that is being mutated by its own runtime artifacts; move artifacts out of the installed tree and reinstall before drawing conclusions about trust drift.

## Superpowers Seed YAML Contract (from superpowers-seed-yaml-contract.md)

**Problem pattern:** A plugin prepares artifacts and recommends a workflow run, but the runner fails immediately with a YAML parse error because the seed artifact is markdown prose (`seed.md`) rather than structured YAML.

**Fix pattern for workflow-runner handoff:**
- Emit `seed.yaml`, not markdown `seed.md`.
- Generate a structured Seed document with contract fields expected by the installed Ouroboros version.
- Recommend: `ooo run workflow <seed.yaml>` explicitly.

**Minimum seed checks before claiming handoff is correct:**
1. Open the generated seed artifact and confirm it is actual YAML (not prose).
2. Verify the seed contains required contract fields for the installed Ouroboros version.
3. Run the workflow command once and confirm it gets past the seed-load phase.
4. Only then investigate runtime/backend/provider failures.

**Dispatch/trust follow-up after local plugin edits:**
- Symptom: `plugin 'superpowers' bytes have changed since installation; refusing to invoke`.
- Fix: reinstall from the edited local path, re-grant declared trust scopes, then retest dispatched invocation.

## Support files
- `references/dispatcher-and-collision-pitfalls.md` — concrete reproduction notes for command collisions, workspace artifact routing, and dispatch-vs-direct verification.
- `references/runtime-backend-and-seed-contract.md` — notes on backend switching, provider-attribution checks, and handoff/seed contract verification.
- `references/superpowers-seed-yaml-contract.md` — concrete fix pattern for plugins whose prepared workflow seed must be YAML plus the reinstall/trust-refresh step after local edits.
- `references/clean-repo-and-dispatch-drift.md` — verification pattern for keeping prepared artifacts outside the clean execution repo and diagnosing post-reinstall byte-drift in dispatched invocations.
- `references/dispatcher-exit-and-codex-auth.md` — dispatcher exit-path pitfall (`typer.Exit` vs `click.exceptions.Exit`) and the Codex-auth smoke-test gate before blaming plugin/runtime logic.
