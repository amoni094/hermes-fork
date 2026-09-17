---
name: hermes-observability-and-task-ledger
triggers:
  - Tracing Hermes agent runs for cost attribution
  - Logging token usage per turn
  - Task ledger for multi-step agent work
  - Observability for delegate_task children
description: >
  Use when you need tracing, cost attribution, task-ledger entries, or per-turn token logging
  for Hermes agent runs and delegate_task children.
version: 1.0.0
author: Hermes
related_skills:
  - hermes-cron-and-agents
  - dispatching-parallel-agents
  - hermes-acp-routing
---

# Hermes Observability and Task Ledger

Use this skill to instrument Hermes agent runs with structured logging, token tracking, and task ledger entries so cost and behavior are auditable after the fact.

## Run headers (content-addressed IDs)

At the start of any significant agent run, write a run header with `run-header.py`:

```python
# ~/.hermes/scripts/run-header.py
import json, hashlib, time, pathlib, os

def write_run_header(session_id, goal, toolsets):
    h = hashlib.sha256(f"{session_id}:{goal}".encode()).hexdigest()[:12]
    entry = {
        "run_id": h,
        "session_id": session_id,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "goal": goal,
        "toolsets": toolsets,
    }
    path = pathlib.Path.home() / ".hermes/logs/run-headers.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return h
```

The content-addressed `run_id` ties all per-turn token logs back to the originating run.

## Task ledger

For multi-step agent work, maintain a ledger entry per step:

```json
{"run_id": "abc123", "step": 1, "tool": "terminal", "status": "ok", "ts": "2026-09-15T00:00:00Z"}
{"run_id": "abc123", "step": 2, "tool": "file", "status": "ok", "ts": "2026-09-15T00:00:01Z"}
{"run_id": "abc123", "step": 3, "tool": "verification-before-completion", "status": "ok", "ts": "2026-09-15T00:00:02Z"}
```

Ledger path: `~/.hermes/logs/task-ledger.jsonl`. Append-only.

## Async Per-Turn Token Usage Logging

Log per-turn token usage to `~/.hermes/logs/token-usage.jsonl` using a **daemon thread** to avoid blocking the turn loop.

**Schema:**

```json
{
  "ts": "2026-09-15T00:00:00Z",
  "session_id": "<session identifier>",
  "turn_id": "<turn number or UUID>",
  "model": "claude-sonnet-4-6",
  "prompt_tokens": 12345,
  "completion_tokens": 678,
  "tool_calls_count": 3
}
```

**Fields:**
- `ts` — ISO-8601 UTC timestamp of the turn completion
- `session_id` — Hermes session identifier (matches run-header.py session_id)
- `turn_id` — turn number (integer) or UUID; monotonically increasing within a session
- `model` — model name string as returned by the API
- `prompt_tokens` — prompt/input token count for this turn
- `completion_tokens` — completion/output token count for this turn
- `tool_calls_count` — number of tool calls made in this turn

**Implementation (daemon thread, non-blocking):**

```python
import json, threading, time, pathlib

LOG_PATH = pathlib.Path.home() / ".hermes/logs/token-usage.jsonl"
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

def _rotate_if_needed(path: pathlib.Path):
    if path.exists() and path.stat().st_size >= MAX_SIZE_BYTES:
        rotated = path.with_suffix(f".{int(time.time())}.jsonl")
        path.rename(rotated)

def log_token_usage(session_id, turn_id, model, prompt_tokens, completion_tokens, tool_calls_count):
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session_id": session_id,
        "turn_id": turn_id,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tool_calls_count": tool_calls_count,
    }
    def _write():
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _rotate_if_needed(LOG_PATH)
        with LOG_PATH.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    t = threading.Thread(target=_write, daemon=True)
    t.start()
```

**Rules:**
- Use a daemon thread so the process does not hang on exit waiting for the write
- Append-only; never rewrite or truncate mid-file
- Rotate at **10 MB**: rename the current file to `token-usage.<unix_ts>.jsonl` and start a fresh `token-usage.jsonl`
- Complements `run-header.py` content-addressed IDs with per-turn granularity — join on `session_id` to correlate

## Cost attribution query

```bash
# Total tokens for a session
jq -r 'select(.session_id == "MY_SESSION") | [.prompt_tokens, .completion_tokens] | add' \
  ~/.hermes/logs/token-usage.jsonl | paste -sd+ | bc
```

## Guardrails

- Never log sensitive content (secrets, PII) — log only counts and IDs
- Rotate all log files at 10 MB to prevent unbounded disk growth
- Daemon threads must not perform retries — if the write fails, drop the entry silently rather than blocking the turn

## Context Pressure Monitoring (VISTA, arXiv:2606.30005)

The per-turn token logger (S9, `turn-usage.jsonl`) is the data source for context pressure signals.

**Flag:** If a single turn exceeds 60% of the model context window (default 200,000 tokens), flag it as `HIGH_CONTEXT_PRESSURE` in the JSONL log.

**Pattern:** Add a `pressure_flag` field to the `_log_turn_usage_async()` record in `turn_usage.py` when `prompt_tokens > 0.6 * context_window`. The actual code uses `os.environ.get("HERMES_CONTEXT_WINDOW", "200000")` — not a module-level constant:

```python
context_window = int(os.environ.get("HERMES_CONTEXT_WINDOW", "200000"))

def _log_turn_usage_async(session_id, turn_id, model, prompt_tokens, completion_tokens, tool_calls_count):
    pressure_flag = "HIGH_CONTEXT_PRESSURE" if prompt_tokens > 0.6 * context_window else None
    entry = {
        "ts": ...,
        "session_id": session_id,
        "turn_id": turn_id,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tool_calls_count": tool_calls_count,
    }
    if pressure_flag:
        entry["pressure_flag"] = pressure_flag
    # append to turn-usage.jsonl ...
```

**Query pressure turns:**
```bash
jq 'select(.pressure_flag == "HIGH_CONTEXT_PRESSURE")' ~/.hermes/logs/turn-usage.jsonl
```

Reference: arXiv:2606.30005, "VISTA: LLM Agents Are Latent Context Managers (State Proprioception)", 2026.

## Bi-Temporal Memory Debug (SuperLocalMemory 4.0, arXiv:2608.08253)

## Crash-Boundary Patterns for Durable Task State (Denuto ADR-0010)

Source: Denuto `src/run_ledger/` and ADR-0010.  
Runtime: `~/.hermes/scripts/run_ledger.py`

### Core Constraints

**CoordinationStore — Conditional Writes Only**
ZERO unconditional writes to shared state. Every write is either:
- `put_if_absent(key, value)` — creates only if key doesn't exist
- `update_if(key, expected, new_value)` — updates only if current value matches expected

This is Optimistic Concurrency Control (OCC, Kung & Robinson 1981). Prevents silent overwrites in concurrent/retry scenarios.

**ContentStore — Content-Addressed, Write-Once**
Store task outputs by SHA-256(content). Same content → same key → idempotent.
This is the Merkle DAG pattern (same as git object storage).
```python
key = content_store.put("analysis output here")  # SHA-256 hex
data = content_store.get(key)  # always same bytes
```

**Clock — Injected Time Source**
Never call `time.time()` or `datetime.now()` directly. Always use an injected Clock.
Replace with `FakeClock` in tests for deterministic timing.
```python
class FakeClock(Clock):
    def __init__(self, start=0.0): self._t = start
    def now(self) -> float: self._t += 0.001; return self._t
```

**State Transitions — Always Raise on Illegal**
All state changes go through `is_legal_transition(from, to)`. Illegal transition RAISES.
Never silently apply an out-of-order transition.
```python
LEGAL = {"pending": {"running"}, "running": {"completed", "failed"}}
if to_state not in LEGAL.get(from_state, set()):
    raise ValueError(f"Illegal: {from_state!r} → {to_state!r}")
```

**RetryPolicy — Explicit Random Instance (Karn's Algorithm)**
Never use module-global `random.random()` in retry logic. Always pass `random.Random` explicitly.
Full-jitter: `sleep = rng.uniform(0, min(cap, base * 2**attempt))`

**DecisionAuditChain — Append-Only Hash Chain**
SHA-256 hash chain: `event_hash = SHA256(prev_hash + ":" + SHA256(payload))`.
Same structure as blockchain / certificate transparency logs.
Tamper-evident: modifying any event invalidates all subsequent hashes.
Use for skill version auditing and agent run audit trails.
```python
audit = DecisionAuditChain(chain_path)
audit.append("state_transition", {"from": "pending", "to": "running"})
assert audit.verify()  # False if any event was modified
```

**Usage**:
```python
from run_ledger import RunLedger, Clock

clock = Clock()
ledger = RunLedger(run_id="run_abc123", clock=clock)
ledger.transition("running")
output_key = ledger.store_content("analysis results here")
ledger.add_event("task_done", {"findings": 5})
ledger.transition("completed")
assert ledger.verify_audit()
```

See also: `hermes-improvement-governance` (proposal lifecycle), `hermes-shadow-evaluation` (feature flags).

**Pattern:**
```sql
-- What did the memory surface look like at a specific past time?
SELECT * FROM fact_lifecycle
WHERE valid_from <= '<failure_timestamp>'
  AND (valid_to IS NULL OR valid_to > '<failure_timestamp>')
ORDER BY inserted_at DESC;
```

**Use when:** post-task investigation of memory retrieval failures, TTL bug diagnosis, audit of what was visible to the agent at a specific turn.

**Implementation note:** `lifecycle.db` at `~/.hermes/memory-facts/lifecycle.db` uses columns `valid_from`, `valid_to`, `inserted_at`, `updated_at`. Schema confirmed: no `created_at`/`expired_at` columns.

Reference: arXiv:2608.08253, "SuperLocalMemory 4.0: The Governed Memory Operating System for AI Agents", Aug 2026. Bi-temporal recall: 1.687ms median governed write overhead, <3ms at p99.

### VikingRAG Experience-Edge Cache (arXiv:2609.11390)
Cache file: ~/.hermes/cache/recall-experience-cache.json
Hit condition: cosine(new_query, cached_query) > 0.85 AND age < 3600s
Inspect hits: `python3 -c "import json,pathlib; d=json.loads(pathlib.Path('~/.hermes/cache/recall-experience-cache.json').expanduser().read_text()); print(len(d), 'entries')"`
