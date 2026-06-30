---
name: hermes-memory-surface-selection
description: Choose between Hermes durable memory, session_search, qmd, and MemPalace based on scope, mutability, and retrieval needs.
created_by: agent
---

# Hermes memory surface selection

Use this when deciding where information should live in a Hermes-centered workflow, or which retrieval surface to query first.

## Goal
Keep durable facts small and high-signal in Hermes memory, use transcript search for prior conversations, use qmd for curated local knowledge, and use MemPalace for richer external/project memory retrieval without overloading Hermes core memory.

## Default decision order
1. Hermes durable memory (`memory` tool)
2. `session_search`
3. qmd (`mcp_qmd_*`)
4. MemPalace MCP tools

Choose the smallest surface that can answer the question well.

## Use Hermes durable memory for
- Stable user preferences
- Long-lived environment facts
- Recurring conventions the user should not have to repeat
- Small declarative facts that will still matter in weeks

Do not use Hermes durable memory for:
- task progress
- large notes
- bulk transcripts
- changing research findings
- raw document storage

## Use `session_search` for
- "What did we decide about X?"
- finding prior attempts, errors, or resolutions from old chats
- recovering context before asking the user to repeat themselves
- reconstructing continuity when the user asks "where did we get to", especially after context compaction or interrupted multi-step work

Prefer this before adding new durable memory when the fact may already exist in prior session history.

### Continuity reconstruction pattern
When the user asks where prior work stopped, use `session_search` to recover the stopping point instead of paraphrasing from memory.

Recommended sequence:
1. Run a narrow discovery query for the topic.
2. Open the best matching session by `session_id`.
3. If the session contains compaction summaries, treat them as leads and corroborate with nearby user/assistant turns or additional matching sessions.
4. Summarize three things separately:
   - what was audited or discovered
   - what was actually changed or installed
   - what remained pending
5. Preserve important distinctions from the original work, especially "Hermes-side integration/docs" versus "the upstream product was actually installed and running locally".

This pattern is especially useful for inventory, pruning, migration, and install-tracking conversations where users care about the exact stopping point.

### Install-status inventory pattern
When the user asks for an inventory of requested GitHub/git links that are or are not locally installed, do not answer from session history alone.

Use this separation explicitly:
1. `session_search` to collect the candidate repos/links the user asked to implement.
2. If the user broadens the source set, inspect the direct source too (for example browser history databases such as Firefox `places.sqlite`) and treat those results as a separate bucket from explicit requests.
3. Live local evidence to classify each item:
   - source clone present with matching git remote
   - binary/command installed but no source clone
   - plugin/integration present but not a standalone clone
   - not found locally
4. Report the result in buckets instead of flattening everything into "installed" or "not installed".
5. Keep provenance explicit. Distinguish at least:
   - explicitly requested to implement
   - merely browsed/viewed in history
   - non-repo/profile/settings/login pages that should be excluded
6. Call out ambiguous cases separately, especially when the user may care about the distinction between:
   - requested repo exists as a checkout
   - functionality exists via another integration path
   - tool is installed as a binary only
7. Exclude non-repo/profile links from the install inventory unless the user explicitly asked to treat them as install targets.

Firefox-history specific pattern:
- Prefer the live SQLite history DB over session recollection when the user asks what they viewed.
- Query by a concrete time window first, then normalize URLs down to repo roots (`https://github.com/org/repo`) before deduping.
- Keep account/settings/login/oauth/password-reset pages out of the repo inventory unless the user explicitly wants all GitHub activity, not just repos.
- If a history hit resolves to a repo-like URL but the page title says `Page not found`, keep it only as a browsed-item note, not as evidence the repo is valid.

Important pitfall:
- A prior session saying something was "implemented" is not enough proof that the upstream repo is locally installed. Verify against the live filesystem and installed commands before finalizing.
- Do not merge "explicitly asked me to implement" and "looked at in Firefox" into one flat list unless the user asked for that; provenance matters.

## Use qmd for
- curated local notes and documents
- Obsidian/vault-style knowledge bases
- page/heading/path-oriented retrieval
- workflows where the canonical answer should live in a maintained document

qmd is usually the best first stop for local knowledge that has already been organized.

## Use MemPalace for
- larger memory corpora that should stay outside Hermes core prompt memory
- project or archive retrieval where embeddings/graph/tunnel-style lookup help
- optional exploratory recall over a body of notes or extracted material
- adjunct memory services exposed cleanly over MCP

Treat MemPalace as an extension layer, not a replacement for Hermes memory semantics.

## Decision rules
- If the fact should auto-influence future chats and fits in one compact sentence, save it to Hermes durable memory.
- If the answer probably exists in a past Hermes conversation, use `session_search` first.
- If the answer belongs to a maintained local document or vault note, use qmd.
- If the material is broader, more exploratory, or better kept outside Hermes built-ins, use MemPalace.

## Priority and trust
- Canonical user/profile facts: Hermes durable memory
- Canonical workspace knowledge docs: qmd-backed files
- Historical conversation evidence: `session_search`
- Supplemental/archive/project retrieval: MemPalace

## Prompt-resident memory budget tuning
When the task is to optimize Hermes memory for usefulness vs token spend, treat `MEMORY.md` and `USER.md` as the small always-in-prompt layer, and the configured memory provider (for example Hindsight) as the broader adaptive recall layer.

Recommended workflow:
1. Inspect current config values for `memory.memory_char_limit` and `memory.user_char_limit`.
2. Inspect the actual current sizes of `~/.hermes/memories/MEMORY.md` and `~/.hermes/memories/USER.md`.
3. If either file is saturated or over limit, prefer a modest increase that restores headroom rather than a large budget jump.
4. Keep the always-injected layer compact; rely on the external memory provider for broader recall.
5. Verify the change with `hermes config check` after updating settings.

Important pitfall:
- Do not try to edit `~/.hermes/config.yaml` with generic file patching tools when Hermes blocks security-sensitive config writes. Use `hermes config set memory.memory_char_limit ...` and `hermes config set memory.user_char_limit ...`, then verify on disk.

Heuristic:
- Aim for some breathing room instead of exact saturation. A modest buffer is enough; if files keep filling up, prune/compress entries first and only then raise limits again.

When sources disagree:
1. live files / current system state
2. explicit user instruction
3. Hermes durable memory for user preferences and stable facts
4. curated qmd docs
5. session history
6. MemPalace recall

## Token-pressure / compression handling
When the user explicitly flags context pressure, prompt size, or compression concerns during an investigation:
- switch immediately to the lowest-context path that still completes the task
- prefer direct-source inspection and the minimum number of tool calls needed for verification
- avoid rehashing prior findings unless they are required for the next action
- if slash-command compression is not invokable from the current tool surface, say that briefly and continue with a minimal-context execution path rather than debating it
- summarize only the delta and the current blocker/result

Compression trigger discipline for long sessions:
- treat large `session_search` payloads as a compression boundary
- treat broad repo-wide `search_files` sweeps as a compression boundary
- treat multi-file patch/documentation passes as a compression boundary
- treat task-family switches after heavy tool use as a compression boundary
- if `/compress` is not invokable from the active tool surface, state that briefly and explicitly recommend `/compress` at that point instead of silently continuing

## Hermes memory/compression validation pattern
When the user asks whether Hermes workflows, durable memory, or compression are actually working, do not answer from recollection or config theory alone. Verify the live system with a compact layered check:

1. Hermes-native health/status commands first.
   - Use `hermes config check`, `hermes memory status`, and `hermes status --all`.
2. Read back the persisted config values that govern the claim.
   - Confirm `compression.enabled`, `compression.threshold`, `compression.target_ratio`.
   - Confirm `memory.memory_enabled`, `memory.user_profile_enabled`, provider, and char limits.
3. Inspect the actual prompt-resident memory files.
   - Check that `~/.hermes/memories/MEMORY.md` and `USER.md` exist.
   - Record real character counts against configured limits rather than assuming they are healthy.
4. Look for evidence that compression has fired in practice, not just that it is enabled.
   - Count or otherwise confirm compaction markers in `state.db` or session history.
   - Use `session_search` for recent `compress`, `compression`, or `memory` evidence so you can cite actual handoff/compaction messages.
5. Separate configuration from runtime evidence in the final answer.
   - Example buckets: workflow surfaces enabled, durable memory enabled, compression enabled, compression exercised, session recall working.
6. If a current CLI session may have older startup config, say so explicitly.
   - Distinguish persisted config from behavior already loaded into a long-lived session.
7. If the `memory` tool reports unavailability while Hermes-native status/config checks say memory is enabled and healthy, suspect a session-path mismatch before concluding memory is disabled.
   - Check whether the current runtime may be passing no live memory store (`store is None`) or using a stale tool surface.
   - Prefer precise language like "memory store unavailable in this session path" over blanket claims that memory is disabled.
   - If the code path supports an on-disk fallback store, prefer that over failing closed.

This validation pattern is preferable to broad narrative explanations because it proves both configuration and observed behavior while staying compact.

## Pitfalls
- Do not dump large blobs into Hermes memory.
- Do not save stale task artifacts as durable memory.
- Do not use MemPalace just because it exists; prefer qmd for curated local canonical notes.
- Do not treat compressed session summaries as canonical memory.
- Do not respond to user token-pressure warnings with a long explanation of why compression is difficult; shorten the path instead.

## Quick examples
- "Remember I prefer concise answers" → Hermes durable memory
- "What did we do last week for MCP auth?" → `session_search`
- "Find the note about local retrieval routing" → qmd
- "Search a broad imported archive of project notes" → MemPalace

## Support files
- `references/memory-surface-matrix.md` — compact comparison table and routing examples.
- `references/mempalace-adjunct-pattern.md` — concise decision pattern for treating MemPalace-style MCP systems as adjunct retrieval layers.
