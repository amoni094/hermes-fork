# Local Retrieval and Routing

This reference captures the vault-first workflow for local workspace use.

## Intent

Use Obsidian as the durable memory store and retrieval source. Avoid dumping large notes into model context when a small retrieval packet will do.

## Workflow

1. Triage every incoming command with a cheap intermediate model.
2. Classify:
   - intent
   - task class
   - risk level
   - required context
   - best model tier
   - whether verification is needed
   - whether the task should be split
3. Retrieve only the minimum relevant vault context:
   - filename / wikilink / heading lookup
   - lexical search
   - semantic retrieval if needed
   - structured indexes for reused domains
4. Dispatch to the smallest capable worker model.
5. Verify if the task is risky, externally visible, or easy to get wrong.
6. Persist durable conclusions back into Obsidian.

## Retrieval Packet Shape

Keep the packet small and cited:

- note title
- source path or wikilink
- 1–3 short excerpts
- confidence note
- stale/conflict flags if relevant

## Routing Heuristics

- Use local fast models for lookup, extraction, short summaries, and command classification.
- Use mid-tier models for ordinary reasoning, synthesis, and bounded multi-step work.
- Escalate to stronger models for ambiguity, code, architecture, debugging, and high-stakes synthesis.
- Split large tasks before solving them if decomposition reduces risk or token cost.
- Prefer verification for security, irreversible actions, and external side effects.

## Practical Token-Saving Rules

- Keep stable instructions in one canonical note.
- Keep variable task data last.
- Link to notes instead of pasting them when possible.
- Retrieve just enough evidence to answer the current task.
- Prefer structured summaries over replaying raw history.
