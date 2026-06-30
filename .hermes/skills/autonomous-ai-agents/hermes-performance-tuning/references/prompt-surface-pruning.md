# Prompt-surface pruning for Hermes

Use this when the user's goal is token optimization by reducing Hermes support surface rather than changing the main model.

## Principle
The biggest wins usually come from shrinking default prompt surface in this order:
1. enabled toolsets
2. enabled MCP servers
3. enabled skills
4. only then deeper content surgery inside large umbrella skills

Do not start by deleting lots of skill files. First reduce what is eligible to appear in the session.

## Recommended audit order
1. Run `hermes tools list` and separate daily-core toolsets from occasional ones.
2. Run `hermes mcp list` and identify MCP servers that are not part of the user's current operating loop.
3. Run `hermes skills list` plus inspect `~/.hermes/skills/.usage.json`.
4. Read `~/.hermes/config.yaml` and compare `skills.disabled` against actual usage.
5. Measure the broad shape:
   - total enabled vs disabled skills
   - enabled local skills with `use_count` 0-2
   - largest enabled local `SKILL.md` files
   - number and health of cron jobs that may be keeping stale skills alive

## Conservative pruning rules

### Toolsets first
Disable by default any toolset that is not part of the user's normal daily loop.
Common high-surface candidates:
- `image_gen`
- `tts`
- `computer_use`
- `browser` when stealth or interactive browsing is only occasional

Keep the core small when possible:
- `terminal`
- `file`
- `web`
- `code_execution`
- `skills`
- `memory`
- `session_search`
- `todo`
- `clarify`

Treat `delegation`, `cronjob`, `browser`, `vision`, and media-generation toolsets as opt-in unless they are genuinely frequent.

### MCP second
Each enabled MCP server expands tool surface. Disable servers that are not currently central to the workflow.
Typical review order:
- keep local retrieval systems aligned with the user's daily loop
- review browser-specialized MCP separately from the built-in browser toolset
- disable large specialist stacks such as workflow engines when not actively in use

### Skills third
Prefer disabling or archiving low-use enabled local skills before rewriting large umbrella skills.
Good candidates:
- enabled local skills with `use_count == 0`
- enabled local skills with `use_count <= 2` and no recent `last_used_at`
- narrow convenience skills that duplicate an umbrella workflow

Do not overreact to installed count alone. Disabled skills are less important than enabled skills that remain eligible for loading.

## Size-aware heuristics
When pruning skills, inspect both usage and byte size.

Important pattern:
- a huge, frequently used umbrella skill is usually worth keeping but may deserve internal summarization or support-file extraction;
- a medium or large skill with very low use is a better archive/disable candidate than many tiny unused files.

Useful buckets:
- `use_count >= 10`: usually keep
- `use_count 3-9`: review by size and recency
- `use_count 0-2`: default review bucket

## Cron hygiene interaction
Check `hermes cron list --all` before finalizing pruning.
A noisy or timing-out watchdog can keep a maintenance skill operationally relevant even if direct human loads are rare.
If a cron job is timing out or obsolete, fix/pause the job separately instead of encoding the skill as broadly important forever.

## Reporting format
For a clean recommendation, produce:
- current enabled toolsets
- current MCP servers
- current enabled/disabled skill counts
- immediate disable candidates
- reversible next commands
- optional later consolidation targets

## Pitfalls
- Do not capture secrets or raw config credentials in the audit notes.
- Do not treat a disabled builtin catalog as the main optimization win if the real issue is enabled local surface.
- Do not delete class-level umbrellas just because they are large; first ask whether they are frequently used.
- Do not confuse filesystem size with prompt cost. Eligibility to load matters more than disk usage.
- Do not ignore MCP servers; a single large MCP can outweigh many tiny skill files in live prompt surface.
