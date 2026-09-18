# Skill Visibility Control

## Making a skill dormant (disabled but callable on-demand)

Hermes supports globally disabling skills so they don't appear in the
available_skills list injected into every session's system prompt. The
skill files stay on disk and can be explicitly loaded any time — but only
from the CLI directly, not via the `skill_view` MCP tool (see correction
below).

### Config mechanism

Add to `~/.hermes/config.yaml`:

```yaml
skills:
  disabled:
    - skill-name-a
    - skill-name-b
```

This is the same backing store that `hermes skills config` (interactive
curses UI) writes to. Both methods are equivalent.

### Verification

```bash
hermes skills list | grep skill-name-a
# should show: disabled
```

Bottom line of `hermes skills list` shows the count: e.g. "149 enabled, 2 disabled".

### Per-platform disable

To disable a skill only on one platform (e.g. cli but not telegram):

```yaml
skills:
  platform_disabled:
    cli:
      - skill-name-a
```

Global `disabled` takes precedence over per-platform lists — a globally
disabled skill stays disabled everywhere.

### On-demand invocation of a disabled skill

- In-session (interactive CLI): `/skill skill-name-a`
- At startup: `hermes -s skill-name-a`
- **Agent call via MCP `skill_view(name='skill-name-a')`: DOES NOT WORK.**
  Observed 2026-07: this returns
  `{"success": false, "error": "Skill 'skill-name-a' is disabled. Enable it
  with \`hermes skills\` or inspect the files directly on disk."}` for both
  the main SKILL.md and any `file_path=` lookup. There is no MCP-level
  bypass — the CLI slash-command path (`/skill`) and the MCP `skill_view`
  tool are not equivalent despite both being "on-demand invocation."
  `skill_manage(action='patch'|'edit')` also refuses on a disabled skill
  with "the current SKILL.md content has not been loaded in this review
  turn," because it requires a prior successful `skill_view` in the same
  turn.

### Working with a disabled skill from an agent session

When you're in an MCP-driven agent session (not the interactive CLI) and
need to read or edit a disabled skill:

1. Read it with the generic `read_file` tool at
   `~/.hermes/skills/<category>/<name>/SKILL.md` — find the category via
   `search_files(pattern='<keyword>', target='content')` if you don't know it.
2. Edit it with the generic `patch`/`write_file` tools against that same
   disk path — not `skill_manage`, which stays gated on the live
   `skill_view` load precondition.
3. Tell the user the skill is disabled and suggest
   `hermes skills enable <name>` if the task recurs, instead of silently
   dropping the skill's guidance because the entry point is gated off.

### When to disable vs delete

- **Disable**: skill content is verified and useful, but rarely needed
  (e.g. brand formatting guides you only want when explicitly doing
  NAB or UCB documents). Keeps the system prompt lean.
- **Delete**: skill is stale, superseded, or was a one-off. Use
  `skill_manage(action='delete')`.

### Pitfall: hermes skills config is interactive-only

`hermes skills config --help` shows no CLI flags — it's a curses UI only.
For scripted or agent-driven changes, edit `~/.hermes/config.yaml` directly
or append via `hermes config set`.

The direct append that works:

```bash
cat >> ~/.hermes/config.yaml << 'EOF'
skills:
  disabled:
    - my-skill
EOF
```

Verify immediately with `hermes skills list | grep my-skill`.
