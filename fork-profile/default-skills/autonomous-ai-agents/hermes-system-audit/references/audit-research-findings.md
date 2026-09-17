# Hermes System Audit — External Research Findings (Sep 2026)

Synthesis from 37 sources (arXiv 2025-2026, GitHub, HN, Reddit r/LocalLLaMA,
practitioner blogs). Full report at /tmp/audit-external.md (session artifact).

## Memory pipeline

### Poisoning defenses (arXiv:2608.21230)
- Content-filter write-gates catch 0 out of 360 poisoned memories in controlled study
- 1.2% poison rate degrades retrieval accuracy from 0.85 to 0.30
- Effective defenses: typed source provenance (not content filters), occupancy caps,
  temporal decay, no-revive rule for retracted facts
- Conversation-only memory (no structured store): facts vanish at compaction

### Write-gate recommendations
- Tag source type on every write: user_message, tool_result, agent_reasoning, external_web
- Never write raw agent reasoning traces as memory facts
- Implement no-revive: once a fact is marked retracted, no future write can revive it
- Apply occupancy cap: max N facts per source type per session to prevent flooding

## Multi-agent handoff

### Orchestration patterns (Anthropic 2026 agent patterns)
- One orchestrator + full execution traces + input_filter is most reliable
- Subagents return summaries, not full traces, to the parent
- Multi-agent ROI is modest: +4.6 pp accuracy at 2-4x token cost vs single agent
- Re-anchor policy at each hop (MasDrift paper): models drift from instructions over hops

### Context packets
- Pass minimal context — only what the child genuinely needs
- Include: task goal, success criteria, output schema, tool scope
- Exclude: full session history, parent reasoning traces, unrelated prior tasks

## Cron and scheduling

### Token efficiency patterns (Hermes no_agent / wakeAgent)
- `wakeAgent: false` / `no_agent: true` pattern: run shell pre-check, fire LLM only if needed
- no nested cron (cron job spawning cron jobs) — creates runaway fan-out risk
- `cron_mode: deny` in subagent context prevents accidental nested scheduling
- Toolset scoping (`enabled_toolsets`) cuts ~2000 tokens per unneeded toolset loaded

### Race conditions
- Memory pipeline jobs with overlapping schedules produce double-writes and stale deletions
- TTL/purge jobs must always run after retention-scoring jobs
- Stagger dependent pipeline jobs by 20-30 min minimum
- Machine suspension causes catch-up runs to overlap with next scheduled slot

## Security

### Tool surface minimization (practitioner consensus)
- Smaller tool surface = better accuracy AND lower token cost (measured -48% tokens, +8% accuracy)
- Rule of Two: no single agent should have both read and write access to the same sensitive store
- 26.1% of community-shared skills contain at least one security vulnerability (GitHub analysis)

### Secret management
- .env files in home directory root have higher exposure than ~/.hermes/.env
- Approval mode (hermes config approval_mode) should be set to supervised for tools with
  destructive capability; auto-approve only for read-only tool classes

## Skill library maintenance

### Deduplication and routing
- ~3.8M SKILL.md files in community; ~1.88M unique content (50% duplication rate)
- 26.4% of skills missing adequate trigger descriptions (routing failures)
- Prune/merge/rerank as deterministic rules, not LLM-driven librarian
- Skills with no usage in 90+ days and no unique content are safe to archive

## Model routing for subagents

### Key findings from this session
- grok-4.6 with extended reasoning hits the 120s Codex stream idle threshold on long
  arXiv+web research tasks (observed: 2/3 research subagents failed with stream timeout)
- claude-sonnet-4-6 completed the same research workload successfully in the same session
- Use claude-sonnet for external research subagents, not grok-4.6 with extended reasoning
- For short bounded tasks (< 5 min expected), grok-4.6 is fine

## Harness effect (arXiv:2607.06906)

- Orchestration layer dominates model choice for cost/quality: 41% cost cut, 44% latency
  cut, 38% token reduction, +82% quality-per-dollar via harness optimization alone
- Cache-shape discipline: stable system prompt prefix, no dynamic insertions before
  cache boundary, volatile fields pushed to user-message tail
- Context eviction on subtask completion: don't carry completed-subtask output forward
- Failure-spend governance: cap retries at 2 attempts max before switching strategy
