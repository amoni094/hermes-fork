# Delegation-level escalation for complex work

Use this when the user says some tasks are very complex and wants stronger model help without making normal Hermes turns slower.

## Pattern
- Keep the main session on the normal daily model.
- Put the stronger model on `delegation.*` so only subagents escalate.
- Keep delegation reasoning effort conservative unless depth is explicitly wanted.
- Cap delegation concurrency if token bursts matter more than maximum parallelism.

## Why not fallback?
Fallback is the wrong place for complexity routing in most Hermes setups.
- Fallback is triggered by failure, rate limit, or provider trouble.
- It is not a supported policy for "use this model when the task is especially hard".
- A heavy fallback can worsen latency exactly when the session is already degraded.

## Minimal verification recipe
1. Prove the stronger model is actually available with a one-shot Hermes query.
2. Change:
   - `delegation.provider`
   - `delegation.model`
   - `delegation.reasoning_effort`
   - optionally `delegation.max_concurrent_children`
3. Re-read the parsed config values.
4. Run `hermes config check`.
5. Tell the user a fresh session or service restart may be needed because delegation config can be cached by the current Hermes process.

## Good conservative defaults
- `delegation.reasoning_effort = low`
- `delegation.max_concurrent_children = 2` when the user wants to limit burst token spend

## Tradeoff summary
- Pros: better hard-task handling, faster normal turns, cleaner cost isolation.
- Cons: less parallelism if concurrency is reduced; may require restart before live subagents pick up the new config.
