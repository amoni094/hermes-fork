---
name: bash-wizard-generator
related_skills: [hermes-cron-and-agents]
description: "Use when generating bash wizards for human-only steps."
---

# Bash Wizard Generator

Use when: a human must do steps the agent cannot — credential setup, third-party dashboard config, CI secrets provisioning, or one-off migrations. Do NOT invoke for steps the agent can do autonomously (gh CLI calls, file writes, API calls).

A **wizard** is a bash script that walks a human, step by step, through a manual procedure. It opens each URL, says exactly what to click and copy, captures values, writes them where they belong (`.env`, GitHub secrets), confirms at every stage, and shows how many stages remain.

Wizards are **ephemeral by default**: save to `/tmp/` or `scripts/`, delete when done. Commit only if the user wants a repeatable setup path in the repo.

The template in `references/template.sh` handles all UX. Your job is to scope the procedure and author the stages — never touch the library section above the `STAGES` marker.

## Process

### 1. Scope the procedure

Read the repo before asking anything:
- Setup wizard: scan `.env`, `.env.example`, `.env.*`, `README`, `docker-compose*`, framework config, `.github/workflows/*` (every `secrets.*`/`vars.*` reference is a value to produce).
- Migration/transition: identify current state, target state, and irreversible actions between them.

Show the user an ordered list of stages and what each captures. Confirm — they may add, drop, or reorder.

Done when: every stage is named in order, and for each captured value you know (a) where the human gets it, (b) where it is written (`.env`, GitHub secret, both, or nowhere), (c) whether it is secret.

### 2. Map each stage's journey

Write the precise path a human follows for each stage: which URL, what to click, where the value appears, which variable it fills. Example: "Dashboard -> Developers -> API keys -> Reveal test key -> copy".

Never invent UI steps you have not verified. If unsure, check the docs or ask the user.

Done when: every stage traces to concrete instructions a stranger could follow.

### 3. Author the wizard

Copy `references/template.sh` to the target path. Replace the example stage with one `stage` per step in dependency order. Set `TOTAL_STAGES` to match.

Library helpers:
- `stage "Name"` — clears screen, announces stage, shows N/TOTAL progress
- `say "..."` / `step "..."` — instruction line / numbered action
- `open_url URL` — cross-platform browser open (Linux xdg-open, macOS open, WSL wslview)
- `ask KEY "Prompt"` / `ask_secret KEY "Prompt"` — visible/hidden input; remembers prior value on re-run
- `write_env KEY VALUE` — idempotent upsert into `.env`
- `set_secret NAME VALUE` / `set_var NAME VALUE` — GitHub Actions secret/variable via gh CLI (graceful fallback if gh absent)
- `pause "msg"` / `confirm "question"` — gates; use `confirm` before any irreversible action

Rules:
- Open the URL before asking for its value
- Use `ask_secret` for anything secret
- Use `confirm` before any irreversible action
- Keep each stage to one focused task (screen clears between stages)
- Never hand-edit the library section above the `STAGES` marker

### 4. Verify and hand off

- `bash -n wizard.sh` to syntax-check
- Tell the user: `bash wizard.sh`
- Ephemeral: remind them to delete after use
- Persistent: confirm they want to commit it

## Pitfalls

- `write_env` is idempotent; raw `>> .env` appends are not — always use the helper.
- `set_secret` gracefully degrades if gh is missing; skipped items appear in the closing summary.
- Never invent UI paths for dashboards you have not verified.
- One focused task per stage — the screen clear is the UX contract.
