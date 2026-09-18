# Runtime backend attribution and seed-contract verification

Use this note when an Ouroboros plugin or workflow appears provider-specific, or when a plugin-generated "next command" may not match the current Ouroboros CLI contract.

## Verify backend before blaming a provider

Useful commands:
- `ouroboros config backend`
- `ouroboros config show`
- `ouroboros status health`
- `ouroboros setup --runtime <backend> --non-interactive`

What to confirm after switching:
- `llm.backend` matches the intended backend
- `orchestrator.runtime_backend` matches the intended backend
- health check reports the runtime backend and credentials as OK

Example durable lesson:
- A prior failure path used `claude_code_adapter` and failed with `Not logged in · Please run /login`.
- Re-running setup under Codex changed the active config to:
  - `llm.backend: codex`
  - `orchestrator.runtime_backend: codex`
- After that, the same install no longer supported the claim "this requires Claude". The real question became whether the plugin/handoff worked under the selected backend.

## Separate these findings
1. Plugin command prepares artifacts successfully.
2. Recommended next command is syntactically accepted by the current Ouroboros CLI.
3. The referenced artifact format matches what that consumer command expects.
4. The backend/provider can authenticate and execute the run.

Do not collapse these into one verdict.

## Seed/handoff contract check

If a plugin prints a recommended next step such as `ooo run <seed>`, run it once against the generated file.

What to inspect:
- file extension and actual content format
- whether the consumer expects YAML, Markdown, JSON, or another schema
- whether the command name in the recommendation still exists in the installed Ouroboros version

Example lesson captured here:
- `ouroboros superpowers brainstorming --goal ...` successfully prepared run artifacts under `.omx/superpowers/...`.
- The generated `seed.md` contained plain Markdown prose beginning with a heading like `# Seed preparation: ...`.
- Running `ouroboros run workflow <seed.md>` failed before provider execution with a YAML parse error.
- Therefore the bug class was a handoff/seed contract mismatch, not a Claude-vs-Codex authentication problem.

## Reporting pattern

Prefer conclusions like:
- "Backend switched successfully to Codex; credentials OK."
- "Plugin artifact preparation works locally."
- "Generated seed is Markdown but workflow runner expected YAML; recommended command appears mismatched for this Ouroboros version."

Avoid conclusions like:
- "Plugin requires Claude."
- "Plugin is broken."