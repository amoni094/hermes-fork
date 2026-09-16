# Compression trigger checklist

Use `/compress` or explicitly recommend it at these boundaries:
- after large `session_search` results
- after broad repo-wide `search_files` sweeps
- after multi-file patch or docs maintenance passes
- before switching task families after heavy tool use
- whenever the user explicitly flags context pressure

**Pre-condition for all of the above:** before acting on any compression trigger, flush the current subtask checklist + key decisions to `hindsight_retain` or a `/tmp` scratch file first. Do not rely on the compactor to preserve working state.

If `/compress` is not invokable from the active tool surface:
- say so briefly
- recommend `/compress`
- continue on the lowest-context path available

## Think-in-code pre-check (run before bulk tool calls)

Before reading files in bulk, grepping across large repos, or fetching data-rich pages:
  Q: "Can a script extract only what I need and print it?"
  If YES → use execute_code; only the printed output enters context
  If NO (targeted read of known small section) → proceed with direct tool call

## Guidance drift checkpoint (every ~15 tool calls in long sessions)

Ask: "Am I still following the routing rules / skill constraints from session start?"
  If drift detected → re-state the specific constraint in the next reasoning block (one paragraph, not a full skill reload)
  At each major phase boundary (research → implement → verify) → include a compact constraint header
