---
name: ouroboros-setup-and-health-check
description: Configure, verify, and troubleshoot a local Ouroboros install by separating install state, runtime backend health, CLI integration, and plugin inventory.
---

# Ouroboros Setup and Health Check

Use this when the user asks to set up, enable, verify, or troubleshoot a local Ouroboros installation.

## When to use
- The user says "setup Ouroboros" or asks whether it is installed and usable.
- You need to determine whether Ouroboros is missing, already configured, or only partially wired.
- You need to verify a runtime backend such as Codex or Hermes.
- You need to inspect installed plugins or basic CLI wiring before a first run.

## Core workflow
1. Start with live discovery, not assumptions.
   - Check whether `ouroboros` exists on PATH.
   - Do not assume the short alias `ooo` exists just because Ouroboros is installed.
2. Verify runtime health before changing config.
   - Run `ouroboros status health`.
   - Read the config and backend with `ouroboros config show` and `ouroboros config backend`.
3. Distinguish healthy warnings from blockers.
   - A warning that the database file will be created on first run is not a setup failure by itself.
   - Missing runtime backend or missing credentials is a real blocker.
4. Verify the active backend's integration path.
   - For Codex-backed installs, run `ouroboros codex doctor`.
   - For backend changes, prefer `ouroboros setup --runtime <backend> --non-interactive` or `ouroboros config backend <backend>` depending on whether full reconfiguration is needed.
5. Inspect plugins with the correct command family.
   - Use `ouroboros plugin list`, not `ouroboros plugins list`.
   - Use `ouroboros plugin inspect <name>` for details.
6. When plugin verification is part of setup, choose a verification target that can actually complete.
   - Prefer a plugin with a unique namespace or command surface so installation does not collide with other installed plugins.
   - Prefer a plugin whose verification path is static inspection or uses tooling already present on the host.
   - Treat `installed and trusted` and `runtime command exercised successfully` as separate checks.
7. Conclude with the shortest truthful next step.
   - If setup is already healthy, say so clearly and recommend a first real command such as `ouroboros init` or `ouroboros auto`.
   - Only prescribe setup steps that the live checks actually justify.
8. For a real workflow smoke test, verify the execution model, not just the handoff.
   - `ouroboros auto` expects to run from a git repository; if you want a disposable smoke test, create a temporary repo first.
   - Do not count `run_handoff_started` or similar handoff output as completion.
   - If the run emits a job ID or execution ID, wait for the terminal state and inspect the recorded result before claiming success.
9. Verify where artifacts actually land.
   - A successful `auto` or `execute_seed` run may complete inside an isolated worktree under `~/.ouroboros/worktrees/<repo>/orch_*` rather than mutating the original project directory directly.
   - When post-run checks in the original repo look empty, inspect the worktree path before concluding the workflow failed.
   - Treat `job completed` and `artifact visible in the expected filesystem location` as separate checks.
10. Treat direct CLI execution and MCP-owned/background execution as separate paths.
   - In this environment, `ouroboros run ... --no-orchestrator` or `ouroboros run workflow ... --no-orchestrator` may print `Would execute workflow from: ...` and exit 0 without creating artifacts.
   - Do not treat exit code 0 from that preview-like path as proof of execution.
   - Prefer MCP-owned execution (`execute_seed`, `start_execute_seed`, or `auto`) when you need a real verified run, then inspect the resulting worktree or recorded job result.

## Preferred implementation patterns

### 1) Setup requests often mean verification, not installation
- When a user asks for setup, first test whether Ouroboros is already installed and configured.
- If the system is already healthy, avoid unnecessary reinstall or reconfiguration advice.
- Present the current state first, then offer the next useful action.

### 2) Use the canonical binary name for verification
- Prefer `ouroboros ...` for health checks and setup guidance.
- Treat `ooo` as optional convenience aliasing, not as a guaranteed command.
- If `ooo` is absent but `ouroboros` works, do not frame that as a broken install unless the user explicitly requires the alias.

### 3) Backend verification before workflow advice
- Confirm the active backend before recommending backend-specific repair steps.
- Useful probes:
  - `ouroboros status health`
  - `ouroboros config show`
  - `ouroboros config backend`
  - `ouroboros codex doctor` when backend is Codex
- Report backend, credential state, and CLI path separately.

### 4) Plugin surface uses singular subcommand naming
- The command family is `ouroboros plugin ...`, singular.
- If a guessed `plugins` subcommand fails, correct the command family immediately and continue with `plugin list`, `plugin inspect`, `plugin add`, or `plugin trust`.

### 5) First-run database warning is benign
- `ouroboros status health` may warn that the database is missing and will be created on first run.
- Treat this as informational unless another command shows an actual database error.

## Verification checklist
- `ouroboros` binary found or confirmed missing.
- Runtime backend identified.
- Config path confirmed.
- Credentials state checked.
- Backend-specific doctor command run when available.
- Plugin inventory checked with the singular `plugin` command family.
- Final guidance reflects live state rather than a generic install script.

## Pitfalls
- Do not assume a setup request implies a fresh install.
- Do not assume `ooo` exists when only `ouroboros` is installed.
- Do not use `ouroboros plugins ...`; the command family is `ouroboros plugin ...`.
- Do not treat a first-run database creation warning as a broken install.
- Do not recommend backend switching before confirming the current backend and credential health.
- Do not count `ouroboros auto` handoff output as a completed workflow; verify the downstream job reached a terminal state.
- Do not run a disposable `ouroboros auto` smoke test outside a git repo; create a temp repo first so `rev-parse HEAD` is satisfied.
- Do not stop at `plugin install` plus `plugin trust` when the goal is runtime verification; exercise one real plugin command or use a static inspection command that returns a completed result.
- Do not conclude a workflow failed solely because the original repo path lacks the expected file; first check whether the run wrote into `~/.ouroboros/worktrees/<repo>/orch_*`.
- Do not trust `ouroboros run ... --no-orchestrator` exit code 0 by itself when the output only says `Would execute workflow from: ...`; verify an artifact or use an MCP-owned execution path instead.

## Support files
- `references/first-pass-cli-checks.md` — minimal probe sequence and interpretation notes for installed-vs-configured-vs-ready states.
- `references/workflow-smoke-and-plugin-selection.md` — concise setup-time rules for choosing a verifiable plugin and for proving a workflow completed rather than merely started.
- `references/worktree-output-and-direct-run-pitfalls.md` — notes on worktree-isolated output verification and the direct `run --no-orchestrator` preview/no-op behavior.
