# Memory Pipeline Audit — Aug 2026 Bug Register

Audit performed 2026-08-13. Read-only; no code was changed.
See parent SKILL.md "CRITICAL Pipeline Bugs" section for summary.

## BUG C1: PATCH /memories/{memory_id} → 405 (all metadata writes are no-ops)

**Affected:** `l1-promote.py` `hindsight_patch_metadata()` — called for:
- Dedup access-count increment after cosine+LLM dual-gate hit (P1.1, line ~280)
- Contradiction supersede: `valid_to=now`, `superseded_by=pending/fact_id` (P1.4, line ~552)
- Interference penalty: `interference_count=increment`, `last_interfered` (P2.6, line ~559)

**Verification:**
```bash
curl -s -w '\n%{http_code}' -X PATCH \
  -H 'Content-Type: application/json' \
  -d '{"metadata": {"test_key": "test_val"}}' \
  http://127.0.0.1:9177/v1/default/banks/hermes-default/memories/test-nonexistent-id
# → {"detail":"Method Not Allowed"}\n405
```

Hindsight REST API (confirmed via /openapi.json):
- `/v1/default/banks/{bank_id}/memories/{memory_id}` → only GET
- PATCH only on: mental-models/{id}, directives/{id}, documents/{id}, banks/{id}

**Consequence:** The following research-derived features are silently broken:
- Temporal reranking (access_count never incremented → recency signal dead)
- Bi-temporal lifecycle (`valid_to` never written → no contradiction tracking in Hindsight)
- Interference-based forgetting (interference_count string "increment" neither lands nor aggregates)

**Fix options:**
1. Re-retain via `hindsight_retain` with a note field indicating supersession (new node created)
2. Write lifecycle fields to local SQLite sidecar (`~/.hermes/memory-facts/lifecycle.db`)
3. Track in staging.md itself (before truncation) and replay on next promote pass

## BUG C2: 2,796 failed retain operations, no alerting

Observed via:
```bash
curl -s "http://127.0.0.1:9177/v1/default/banks/hermes-default/operations?status=failed&limit=5"
```

Sample failure:
```json
{
  "task_type": "retain",
  "error_message": "Fact extraction failed: 1/1 chunks failed. First failures: chunk 0: BadRequestError",
  "retry_count": 3,
  "next_retry_at": null
}
```
Date range: 2026-07-23 to 2026-07-31. All retries exhausted; next_retry_at=null means abandoned.

Root cause hypothesis: Hindsight's internal LLM fact-extraction hit a BadRequestError
(likely anthropic-version header mismatch or model quota during that period). The l1-promote
cron and l1-hindsight-promote cron both exit 0 after queuing — they never poll this endpoint.

**Operations endpoint for health monitoring:**
```bash
# Count active failures
curl -s "http://127.0.0.1:9177/v1/default/banks/hermes-default/operations?status=failed" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'failed: {d[\"total\"]}')"

# Retry a specific operation
curl -X POST "http://127.0.0.1:9177/v1/default/banks/hermes-default/operations/{operation_id}/retry"
```

## BUG C3: failed_consolidation=92 in bank stats

```bash
curl -s http://127.0.0.1:9177/v1/default/banks/hermes-default/stats | python3 -m json.tool
# "pending_consolidation": 92, "failed_consolidation": 92
```
These 92 facts exist as nodes but may not be reachable via graph-traversal recall paths.
No cron retries consolidation failures. The `background` endpoint may help:
```bash
curl -X POST http://127.0.0.1:9177/v1/default/banks/hermes-default/background
```

## GAP G1: Staging metadata never forwarded to Hindsight

The `l1-hindsight-promote` cron prompt (job `e034d017`) instructs the LLM agent to:
1. Strip timestamp and score prefix
2. Parse `[type=...]` field only
3. Call `hindsight_retain(content=..., context="l1-extract", tags=[...])`

Fields present in staging.md that are **never passed to hindsight_retain**:
- `[valid_from=2026-08-13T11:54Z]` — temporal start
- `[retention=1.00]` — computed retention score
- `[status=active]` — lifecycle status
- `[access_count=1]` — initial recurrence count
- `[entities: Organisation:Obsidian, Location:...]` — POLE+O annotations
- `[supersedes=<id>]` — contradiction back-link

The cron prompt needs update to parse and forward these as Hindsight `tags` or metadata.

## GAP G2: l1-graphiti-write.py metadata loss

`parse_staging()` regex (`TIMESTAMP_RE`) captures only `mem_type` (group 1) and
`inline_source` (group 2). The `write_fact()` function builds episode_body as:
```
[source_type=internal] <bare fact text>
```

Lost at Graphiti write:
- POLE+O entity annotations → Graphiti must re-extract from raw text
- `valid_from` timestamp → no temporal anchoring in graph
- `retention`, `status`, `access_count` → no lifecycle metadata in graph
- `supersedes` → no explicit supersession edge in graph

Minimal fix: append entities as structured text so Graphiti's extractor can use them:
```python
# In write_fact(), before building episode_body:
entity_hint = ""
if entities:
    entity_hint = " Entities: " + ", ".join(f"{e['type']}:{e['name']}" for e in entities) + "."
episode_body = f"{source_tag} {fact['text']}{entity_hint}"
```

## TYPE MISMATCH: `"observation"` in cron prompt vs VALID_TYPES in l1-promote.py

`l1-hindsight-promote` cron prompt step 2 lists `[type=observation]` as a valid type.
`l1-promote.py` line ~347: `VALID_TYPES = {"fact", "correction", "outcome", "preference", "reasoning"}`

`"observation"` and `"ephemeral"` are absent from VALID_TYPES. If either appears in a
staging.md line (written by older l1-extract or manually), l1-promote.py silently maps
it to `"fact"` — but the cron prompt would parse `[type=observation]` correctly.
In practice the mismatch is latent (l1-extract.py doesn't emit these types) but the
vocabularies are out of sync and will diverge on any extension.

## Retention Score Formula Mismatch (skill doc vs code)

`llm-agent-memory-pipeline-research` SKILL.md Priority 2 item 5 claims:
> "compute_retention_score() uses Ebbinghaus formula (confidence × e^(-days/30) × log(1+access_count))"

**Actual code** (`l1-promote.py` lines ~420–432):
```python
base = score_3 / 3.0                                          # RUQ sum, not confidence
type_boost = 0.15 if fact_type in ("correction", "outcome") else 0.0
recur_boost = min(0.20, (max(0, recurrences - 2)) * 0.05)
return min(1.0, base + type_boost + recur_boost)
```
No `days`, no `e^(-x)`, no `access_count` read from Hindsight. The formula is a static
linear RUQ sum with type and recurrence boosts. The Ebbinghaus formula is the research
*target* (arXiv:2604.04514), not the current implementation.

## PSE Source_type Retrieval Gap

`l1-graphiti-write.py` tags all episodes with `[source_type=internal|cron|external]`.
Trust weights (internal=1.0, cron=0.7, external=0.4) are documented.

**No retrieval consumer implements the weighting.** No `search_memory_facts` wrapper in
any skill applies a trust-weight filter or score adjustment. The PSE mitigation (arXiv:2608.07952)
is write-side only.

## L1 Pipeline Timing (verified)

| Job | Cron ID | Schedule | Completed runs |
|-----|---------|----------|----------------|
| l1-extract-periodic | ebe4fd06 | every 180m | 96 |
| l1-promote-periodic | a0898914 | every 180m | 95 |
| l1-hindsight-promote | e034d017 | every 240m | 75 |

Both extract and promote fire every 180m, created 4 seconds apart (last_run_at differs by 4s).
Risk: they fire near-simultaneously; promote may score facts from the same extraction pass
before the file handle is fully flushed on slow I/O.

l1-hindsight-promote fires every 240m vs extract/promote's 180m — staging.md can accumulate
up to one full 180m promote cycle before the ingest job runs. Max latency: 7h (180m + 240m gap
at worst phase alignment), not the 4h documented in some skills.
