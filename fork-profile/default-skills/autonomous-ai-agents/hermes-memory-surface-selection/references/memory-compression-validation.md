# Hermes memory and compression validation pattern

When the user asks whether Hermes workflows, durable memory, or compression are actually working,
verify the live system — do not answer from recollection or config theory.

## Layered check

1. Hermes-native health first: `hermes config check`, `hermes memory status`, `hermes status --all`
2. Read back persisted config values:
   - `compression.enabled`, `compression.threshold`, `compression.target_ratio`
   - `memory.memory_enabled`, `memory.user_profile_enabled`, provider, char limits
3. Inspect actual prompt-resident memory files:
   - `~/.hermes/memories/MEMORY.md` and `USER.md` — real char counts vs configured limits
4. Look for evidence compression has fired, not just that it's enabled:
   - Count compaction markers in state.db or session history
   - Use `session_search` for recent "compress"/"compression"/"memory" events
5. Separate config from runtime evidence in the final answer:
   - buckets: workflow surfaces enabled / durable memory enabled / compression enabled / compression exercised / session recall working
6. If the current CLI session may have older startup config, say so.
7. If the `memory` tool reports unavailability while status checks say memory is healthy, suspect a session-path mismatch:
   - Check whether the runtime is passing no live memory store (`store is None`)
   - Prefer "memory store unavailable in this session path" over blanket "memory is disabled"
   - If the code path supports an on-disk fallback store, prefer that over failing closed.
