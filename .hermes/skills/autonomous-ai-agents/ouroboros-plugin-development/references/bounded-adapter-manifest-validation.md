# Bounded adapter + manifest validation notes

Use this pattern when adapting an external repository into the local `ouroboros-plugins` workspace.

## Durable lessons
- Prefer a bounded adapter plugin over copying upstream implementation wholesale.
- Make the adapter artifact-first:
  - `doctor` for dependency/checkout readiness
  - `inspect` for bounded capability or filesystem evidence
  - `verify` / `prompt` / `benchmark` for prepared invocation or benchmark plans
- Persist provenance and handoff artifacts so the parent workflow can continue without re-inspecting the repo.
- For prompt-style commands, record a digest or metadata instead of the full prompt body unless raw text is contractually required.

## Manifest contract reminders
- In this repo, new plugin manifests must include top-level `capabilities`, `permissions`, and `entrypoint`.
- Validate `upstream.mode` against the schema enum; descriptive ad-hoc strings are not accepted.
- A practical validation command when `jsonschema` is not already installed is:
  - `uv run --with jsonschema python3 scripts/validate_contract.py`

## Verification sequence that worked well
1. `python3 -m py_compile` on plugin modules and new tests.
2. Targeted pytest modules for the new adapters.
3. Schema/contract validation with ephemeral `jsonschema` via `uv run --with ...`.
4. Only after those pass, consider live sample invocations.

## Why this matters
A plugin can pass its direct unit tests while still being uninstallable or invalid at the repo level if the manifest contract is incomplete. Treat schema validation as a separate gate.