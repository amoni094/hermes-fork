# Runtime hooks for Hermes memory capture and vault bridge

Use this pattern when the goal is to turn the memory-capture / bridge playbook into live Hermes runtime behavior instead of manual repetition.

## Hook layout

Place reviewed scripts under `~/.hermes/agent-hooks/` and register them in `~/.hermes/config.yaml` under `hooks:`.

Recommended event mapping:

- `pre_llm_call` → inject a compact routing / delegation note when the current turn mentions agents, delegation, cron, or other long-lived work.
- `post_llm_call` → capture high-signal user+assistant turn summaries into a local JSONL inbox for later curation.
- `post_tool_call` with matcher `write_file|patch` → record Obsidian markdown writes into a local event log and a small dirty-path state file.
- `subagent_stop` → append child-run completion summaries into a task-ledger JSONL file.

## Example local artifacts

- `~/.hermes/logs/hermes-memory-capture.jsonl`
- `~/.hermes/logs/hermes-obsidian-file-events.jsonl`
- `~/.hermes/state/obsidian-dirty-paths.json`
- `~/.hermes/logs/hermes-task-ledger.jsonl`

These are not the final knowledge store. They are compact, machine-readable staging signals that later cron jobs or review passes can inspect.

## Config pattern

```yaml
hooks:
  pre_llm_call:
    - command: "~/.hermes/agent-hooks/inject-hermes-routing-note.py"
      timeout: 5
  post_llm_call:
    - command: "~/.hermes/agent-hooks/capture-turn-memory.py"
      timeout: 5
  post_tool_call:
    - matcher: "write_file|patch"
      command: "~/.hermes/agent-hooks/track-obsidian-write.py"
      timeout: 5
  subagent_stop:
    - command: "~/.hermes/agent-hooks/log-subagent-stop.py"
      timeout: 5
```

## Consent / activation

Hermes shell hooks are gated by the shell-hook allowlist.

Practical activation flow:

1. Write the scripts.
2. Mark them executable.
3. Register them in `config.yaml`.
4. Run one Hermes invocation with hook acceptance enabled so the `(event, command)` pairs are allowlisted.
5. Verify with `hermes hooks list` and `hermes hooks doctor`.

If the environment is non-interactive, the first activation run must still ensure consent is satisfied through Hermes' supported accept-hooks path. Do not assume that merely writing the config makes the hooks live.

## Verification pattern

After wiring the hooks, verify all of the following:

- `hermes hooks list` shows the expected commands.
- `hermes hooks doctor` reports the scripts executable, allowlisted, unchanged since approval, and producing valid JSON.
- A synthetic or real turn causes the expected JSONL/state artifacts to appear.
- The downstream cron or note-sync job is updated to inspect those artifacts when they exist.

## Design rules

- Keep the hook output compact JSON, not prose logs.
- Prefer append-only JSONL for event streams and a tiny JSON map for current dirty state.
- Capture only high-signal turn summaries; do not dump full transcripts.
- Treat the local artifacts as staging inputs for later curation into Obsidian, not as the final memory layer.
- Keep hook scripts fast; expensive work belongs in cron or later summarization passes.
