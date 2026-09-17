# Anthropic Agent API Sources — August 2026

## Official Docs (retrieved Aug 12 2026)

| Topic | URL |
|-------|-----|
| Dreams API (beta) | https://platform.claude.com/docs/en/managed-agents/dreams |
| Managed Memory Stores (beta) | https://platform.claude.com/docs/en/managed-agents/memory |
| Managed Agents overview | https://platform.claude.com/docs/en/managed-agents/overview |
| Effort parameter | https://platform.claude.com/docs/en/build-with-claude/effort |
| Task budgets (beta) | https://platform.claude.com/docs/en/build-with-claude/task-budgets |
| Memory tool (GA) | https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool |
| Compaction | https://platform.claude.com/docs/en/build-with-claude/compaction |
| Refusals & fallback | https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback |
| Fallback credit | https://platform.claude.com/docs/en/build-with-claude/fallback-credit |
| Mid-conversation system messages | https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages |
| Fable 5 / Mythos 5 intro | https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5 |
| Models overview | https://platform.claude.com/docs/en/about-claude/models/overview |
| Context editing | https://platform.claude.com/docs/en/build-with-claude/context-editing |

## Anthropic Engineering Posts

| Title | URL | Date |
|-------|-----|------|
| Effective Context Engineering for AI Agents | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | Aug 2026 |
| Effective Harnesses for Long-Running Agents | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | Nov 2025 |

## External Sources

| Title | URL | Date |
|-------|-----|------|
| a16z: Can Agents Use a Computer? We've Got the Data | https://a16z.com/can-agents-use-a-computer-yet-weve-got-the-data/ | Aug 12 2026 |
| lance-bundle (portable embeddings) | https://github.com/cloudkj/lance-bundle | Aug 2026 |

## Key Model Facts (Aug 2026)

| Model | API ID | Price (in/out MTok) | Context | Notes |
|-------|--------|---------------------|---------|-------|
| Claude Fable 5 | claude-fable-5 | $10/$50 | 1M | GA Jun 9 2026; safety classifiers; thinking always on; no ZDR |
| Claude Mythos 5 | claude-mythos-5 | $10/$50 | 1M | Limited access (Project Glasswing); no classifiers |
| Claude Opus 5 | claude-opus-5 | $5/$25 | 1M | SOTA coding/agentic; Jul 24 2026 |
| Claude Sonnet 5 | claude-sonnet-5 | $3/$15 | 1M | Jun 30 2026; new tokenizer (1.0–1.35x more tokens vs 4.6) |

## Model Effort Support Matrix

| Model | low | medium | high | xhigh | max |
|-------|-----|--------|------|-------|-----|
| Fable 5 | ✓ | ✓ | ✓ (default) | ✓ | ✓ |
| Mythos 5 | ✓ | ✓ | ✓ (default) | ✓ | ✓ |
| Opus 5 | ✓ | ✓ | ✓ (default) | ✓ | ✓ |
| Opus 4.8 | ✓ | ✓ | ✓ (default) | ✓ | ✓ |
| Opus 4.7 | ✓ | ✓ | ✓ (default) | ✓ | ✓ |
| Sonnet 5 | ✓ | ✓ | ✓ (default) | ✓ | ✓ |
| Sonnet 4.6 | ✓ | ✓ | ✓ (default) | — | ✓ |
| Haiku 4.5 | — | — | — | — | — |

Note: `xhigh` is a newer level; Sonnet 4.6 supports `max` but not `xhigh`.

## Fable 5 Refusal Response Shape

```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "content": [],
  "model": "claude-fable-5",
  "stop_reason": "refusal",
  "stop_sequence": null,
  "usage": { "input_tokens": N, "output_tokens": 0 }
}
```

Key: `stop_reason` is `"refusal"`, `content` is empty, `output_tokens` is 0
(not billed for input tokens when refused before output generation).

## Dreams API (beta, Aug 2026)

Async job that reads a memory store + 1–100 session transcripts and produces a new
reorganized memory store (deduped, contradiction-resolved, insights surfaced).
Input store is never modified. Output is an ordinary memory store you can review before
switching in.

```python
dream = client.beta.dreams.create(
    inputs=[
        {"type": "memory_store", "memory_store_id": store_id},
        {"type": "sessions", "session_ids": [session_a, session_b, ...]},
    ],
    model="claude-sonnet-4-6",
    instructions="Focus on coding-style preferences; ignore one-off debugging notes.",
)
# dream.status: pending → running → completed/failed/canceled
# When completed: dream.outputs[0].memory_store_id = new clean store
```

Limits: 100 sessions per dream, 4096-char instructions.
Supported models: claude-opus-5, claude-fable-5, claude-opus-4-8, claude-opus-4-7,
claude-sonnet-5, claude-sonnet-4-6.
Billing: standard token rates; cost scales ~linearly with number/length of sessions.

**Hermes cron pattern:** nightly job passes last 50–100 session IDs + the current
memory store. Review output in Console before activating. Poll with 10s sleep.

Errors to handle: `timeout`, `input_memory_store_too_large`, `input_session_unavailable`.

## Managed Memory Stores (beta, Aug 2026)

Server-side persistent `memory_store` resources attached to agent sessions.
Multiple stores can be attached simultaneously for layered memory:

```python
session = client.beta.sessions.create(
    agent=agent_id,
    resources=[
        {"type": "memory_store", "memory_store_id": prefs_store_id},    # user prefs
        {"type": "memory_store", "memory_store_id": project_store_id},  # project ctx
        {"type": "memory_store", "memory_store_id": skills_store_id},   # skill catalog
    ],
)
```

Use alongside Dreams API: different stores can have different dream schedules
(e.g. user-prefs store dreamed weekly, project store dreamed per-sprint).
Complements local `memory_20250818` tool — use managed stores for cloud-synced
long-term memory, local tool for session-local working files.

## Anthropic Managed Agents (engineering blog, Aug 2026)

Session as append-only log external to harness — "nothing in the harness needs to
survive a crash." Recovery: `wake(sessionId)` + `getSession(id)` → resume from last event.
Source: https://www.anthropic.com/engineering/managed-agents

Key quote: "Because the session log sits outside the harness, nothing in the harness
needs to survive a crash. When one fails, a new one can be rebooted with wake(sessionId),
use getSession(id) to get back the event log, and resume from the last event."

## lance-bundle Summary

`pip install lance-bundle` — packages embedding vectors + ONNX model into a single
portable .zip. Load anywhere with no server, no re-embedding. Built on LanceDB + ONNX.
Supports Hugging Face dataset registry (e.g. `lance-bundle/paul-graham-essays`).
Hermes use: portable RAG knowledge bases that survive reinstalls; pre-built domain
corpora without embedding infra.
