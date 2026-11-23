# AGENTS.md - Workspace Rules

This folder is home. Treat it that way.

## Session startup (mandatory, runs first)

At the start of every new session, before any other work:

1. **Check Hindsight daemon health** by calling `hindsight_recall(query="startup check")`.
   - If it returns results or an empty list: daemon is healthy, proceed.
   - If it returns an error (failed to search / connection refused): daemon is down.

2. **If daemon is down**, fix it immediately before doing anything else:
   a. Run `pkill -f 'hindsight-api' 2>/dev/null; rm -f ~/.hindsight/profiles/hermes.lock` to clear stale state.
   b. Call `hindsight_recall(query="startup check")` again — the Hermes plugin will start the daemon on the call.
   c. Verify with `curl -sf http://127.0.0.1:9177/health` — must return `{"status":"healthy"}`.
   d. If still failing, load `hindsight-stack-operations` skill and follow the full recovery steps.
   e. Do not proceed with the user's task until Hindsight is confirmed healthy.

3. **Root cause for intermittent failures** (known, patched Aug 2026):
   The plugin's `_build_embedded_profile_env()` was not forwarding `HINDSIGHT_API_EMBEDDINGS_*`
   keys from config.json into `~/.hindsight/profiles/hermes.env`. This caused a spurious
   `config_changed=True` on every session start, which overwrote hermes.env with a stripped
   version and restarted the daemon without embedding credentials.
   Fix: plugin patched to forward all `HINDSIGHT_API_EMBEDDINGS_*` keys. hermes.env now has
   9 keys and `config_changed` resolves False on session start.
   If intermittent failures recur, verify hermes.env still has embedding keys:
     `cat ~/.hindsight/profiles/hermes.env | grep EMBEDDINGS`
   If missing, manually run: `~/.hermes/scripts/hindsight-reembed-env.sh` (or re-trigger by
   stopping the daemon and calling `hindsight_recall` once).

Note: daemon port is 9177 (local_embedded mode). Config lives at ~/.hermes/hindsight/config.json.
Diagnostic script: ~/.hermes/scripts/hindsight-ensure.sh (useful for non-session callers).

## Operating rules

- Use runtime-provided context first.
- Read existing files before writing memory or notes.
- Keep durable facts in files, not in chat.
- Prefer small, verifiable changes.
- Avoid destructive commands unless explicitly asked.
- If something is uncertain and retrievable, check the files or tools first.
- For Hermes self-work, prefer Hermes-native commands (`hermes config`, `hermes doctor`, `hermes cron`, `hermes skills`, `hermes tools`) over hand-edited guesswork when possible.

## Verification defaults

- For Hermes/config changes: run `hermes config check` and `hermes doctor`.
- For cron changes: run `hermes cron list --all` and read back the affected job fields.
- For model/provider assumptions: verify live state with the provider endpoint or runtime CLI, not just saved YAML.
- For repo changes: inspect `git status --short --branch` and the changed files directly.

## Export hygiene

- Never initialize git inside `~/.hermes`.
- Keep exports in a dedicated repo/workdir such as `~/hermes-config`.
- Never export `.env`, `auth.json`, `state.db*`, `sessions/`, `logs/`, `gateway_state.json`, `channel_directory.json`, or `processes.json` unless explicitly requested.
- Sanitize config snapshots and redact gateway/chat identifiers before writing them to a repo.
- Treat private repos as sensitive, not as safe-by-default.

## Memory

- Daily notes live under `memory/YYYY-MM-DD.md`.
- Long-term memory lives in `MEMORY.md`.
- `SOUL.md` is personality, `TOOLS.md` is local setup notes.
- Keep memory compact and current.
- Before claiming a missing memory, use `session_search` or local search first.

## Orchestration

- Spawn sub-agents when a task can be split cleanly or would flood context.
- Prefer parallel subtasks for independent work.
- Keep worker prompts self-contained.
- Delegation packets should include goal, scope, paths, constraints, done criteria, and proof commands.
- Use cron or tracked background processes for durable work; use delegation for bounded work.

## Mid-task steering and queuing (deliberate habits)

- Use `/steer <instruction>` mid-flight to redirect a long-running task without killing it (e.g. "use staging not prod", "switch provider", "skip file X").
- Use `/queue <task>` to stack the next task while the current one is still running — reduces babysitting on multi-step chains.
- Use `/branch` before risky experiments (dangerous refactors, alternate strategies) — like git for cognition, keep/discard after.
- These replace the impulse to kill-and-restart; prefer steering over interruption.

## Cron and watchdogs

- Keep a compact human-readable note of each job's purpose, schedule, delivery mode, and expected output.
- On this CLI, local cron jobs do not message this terminal session; do not assume `deliver: origin` semantics from messaging platforms apply here.
- If a bridge or watchdog is optional and unhealthy, either fix it fully or document it as intentionally dormant.
- Keep WhatsApp disconnected unless the user explicitly asks to reconnect or remediate it.

## Red lines

- Do not exfiltrate private data.
- Do not send external messages or posts without asking.
- Prefer recoverable actions over irreversible ones.

## Tool use

- Use tools for real actions and verification.
- Keep responses concise and grounded in actual outputs.

## Context compression discipline

- The 35% floor applies to **uniform** summarization of arbitrary text. Never compress
  any single coherent section below 35% of its original length using uniform methods —
  catastrophic reliability loss results (arXiv:2608.01056).
- **Structured compression can safely go below 35%** when content type is known:
  - Tool output (raw JSON/HTML): compress 70%+ — minimal semantic loss
  - User messages: compress ≤20% max — preserve intent
  - Assistant reasoning: compress ≤40%
  - Skill bodies: use progressive disclosure (Core always, Detail on-demand)
  When applying structured compression, validate that Decision and Artifact context is preserved.
- Prefer dropping an entire old/stale section over compressing all sections uniformly.
  Full-section-drop is safer than snippet-everything.
- Section-based compression: preserve logical units (a complete tool result, a complete
  reasoning block, a complete skill excerpt) rather than sampling tokens uniformly.
- When manually reviewing context pressure (/context), prioritise evicting completed-
  subtask outputs first — their task-relevance has expired (TokenPilot, arXiv:2606.17016).
- Block-wise eviction: when proactive pruning triggers, evict whole coherent blocks
  (tool-call + result + reasoning = one block) in order of age × relevance, not by
  individual token attention scores. Preserves local coherence (EACL 2026 PagedEviction).
- Compression summary schema (for auxiliary model): use four fields —
  exchange_core (key decision/finding per turn), specific_context (non-obvious facts
  discovered), thematic_room (active work domain), artifacts_touched (files/URLs/tools
  created or modified). Target 10x compression. Preserve all four fields even if empty.
- Context drift is a more common failure mode than context exhaustion (65% of enterprise
  agent failures). If task alignment degrades across turns, trigger early compaction rather
  than waiting for the token threshold (Zylos Research, 2026).

## Skill routing discipline

- Skill library is at 180+ skills and growing. Routing accuracy degrades logarithmically at scale
  (arXiv:2605.16508). At >150 skills, flat description matching hits an accuracy ceiling.
- Prefer loading skills by explicit name when the task closely matches a known skill.
- Broad/vague tasks should route to a category first, then a specific skill within it.
- Watch for black-hole skills (capturing >5% of queries that shouldn't universally apply).
- When authoring or updating skills: descriptions must start with "Use when" and stay
  under 57 chars. Add `scope:` (category list) and `trust: core` to bundled skills.

## Agent loop guardrail safety

- Self-improving harnesses can hallucinate failures and install phantom guardrails (25%
  rate, arXiv:2607.13083). Any new guardrail added programmatically must have at least
  one verified true-positive trigger — not just a reduced observed failure count.
- Tool failure retry is stateless by default (api_max_retries=1). For recurring tool
  failures, log the failure type (auth/schema/timeout/rate-limit) + what resolved it —
  this enables cross-session recovery patterns (MERIT, arXiv:2608.05906).
- Prospective plan critique (checking for problems before execution) outperforms
  post-hoc correction. When a task plan seems uncertain, critique it first.

## When to stop without acting further

- If the same tool call returns the same result twice: summarize current state and halt.
- If no tool call in the last 3 turns has changed task state: declare inability and stop.
- If the task was ambiguous at start and remains unresolvable after 5 turns: report
  findings and abstain. Do not loop hoping for a different result.
- Never retry a tool call more than once with identical arguments expecting a different
  outcome — record the failure and escalate or stop.

