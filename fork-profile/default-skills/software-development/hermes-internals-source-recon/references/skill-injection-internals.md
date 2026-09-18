# Worked example: how Hermes injects skills into the system prompt

A fully traced subsystem, produced by reading `~/.hermes/hermes-agent/` source.
Use it as the template for answering "how does subsystem X work" and as the
authoritative reference on the skill-injection path itself.

Line numbers are approximate and drift — grep the symbol names.

## Three files that matter

| Concern | File | Key symbols |
|---|---|---|
| Discovery / parse / filter | `agent/skill_utils.py` | `iter_skill_index_files`, `get_all_skills_dirs`, `parse_frontmatter`, `extract_skill_description`, `skill_matches_platform`, `skill_matches_environment`, `get_disabled_skill_names`, `extract_skill_conditions` |
| Index injection (`<available_skills>`) | `agent/prompt_builder.py` | `build_skills_system_prompt` (~L1417), `_parse_skill_file`, `_skill_should_show`, `_build_snapshot_entry`, `_load_skills_snapshot` |
| Full-content load (on demand) | `tools/skills_tool.py` | `skill_view` → `read_text()` full body (~L784) |
| Footprint measurement | `hermes_cli/prompt_size.py` | `_SKILLS_BLOCK_RE`, `compute_prompt_breakdown` → `hermes prompt-size` |

## (1) Discovery
`iter_skill_index_files(skills_dir, "SKILL.md")` walks each root with `os.walk`,
pruning `EXCLUDED_SKILL_DIRS` (`.git`, `.venv`, `__pycache__`, …) and
`SKILL_SUPPORT_DIRS` (`references/ templates/ assets/ scripts/`) **when the
parent has a SKILL.md** — support files never count as standalone skills. Roots
from `get_all_skills_dirs()`: local `~/.hermes/skills/` first, then
`skills.external_dirs` from config.yaml. Local wins on name collision.

## (2) What is injected per skill: name + ≤60-char description ONLY
`extract_skill_description()` truncates to 60 chars (`desc[:57] + "..."`). The
full body is NEVER in the system prompt. Rendered line per skill:
```
    - <name>: <desc up to 60 chars>
```
Footprint ≈ one line/skill (~20-90 bytes, ~5-25 tokens). Consequence for
authoring: only the first ~57 chars of a description survive into the index —
front-load the trigger. A 1024-char description is legal but mostly unseen there.

## (3) The `<available_skills>` block
Built by `build_skills_system_prompt(available_tools, available_toolsets,
compact_categories)`. Skills grouped into `skills_by_category`; each category may
carry a one-liner from a `DESCRIPTION.md`. Wrapped in `## Skills (mandatory)` +
`<available_skills>…</available_skills>`, placed in the **stable** prompt tier so
per-conversation prompt caching survives.

## (4) Conditional / lazy injection already exists
- **Toolset gating** — `_skill_should_show()` reads
  `metadata.hermes.{requires_tools, requires_toolsets, fallback_for_tools,
  fallback_for_toolsets}` (via `extract_skill_conditions`). `requires_*` hides
  when the tool/toolset is absent; `fallback_for_*` hides when the primary IS
  present.
- **Environment gating** — `skill_matches_environment()` honors
  `environments: [kanban|docker|s6]` at offer time. Unknown tags fail open.
- **Platform gating** — `skill_matches_platform()` honors `platforms: [...]`.
- **Category demotion** — `compact_categories` collapses off-topic categories to
  a `[names only]` line (descriptions dropped, names kept loadable).
- **Disabled** — `get_disabled_skill_names()` reads `skills.disabled` +
  `skills.platform_disabled.<platform>`.
- **Explicit load bypasses all offer filters** — `skill_view` / `--skills` ignore
  environment/compact gating. Explicit load = explicit consent.

## (5) Listed-vs-loaded cutoff (progressive disclosure)
- **Listed:** name + truncated description (`build_skills_system_prompt`).
- **Full content:** entire `SKILL.md` read only on `skill_view(name)`
  (`tools/skills_tool.py`, `read_text()`). The index scan reads only ~4000 chars
  to parse frontmatter.

## Caching (why a new skill isn't visible mid-session)
1. In-process LRU `_SKILLS_PROMPT_CACHE` (max 8), keyed by
   dir/tools/toolsets/platform/disabled/compact_categories.
2. Disk snapshot `~/.hermes/.skills_prompt_snapshot.json`
   (`_SKILLS_SNAPSHOT_VERSION`) validated by an mtime/size manifest of every
   SKILL.md + DESCRIPTION.md.
`clear_skills_system_prompt_cache(clear_snapshot=True)` drops both.

## Token cost model (measured 2026-07-03, 149 skills)

Skills block lives in the **stable** prompt tier → Anthropic prefix caching
means it is paid ONCE at session start, then cached for all subsequent turns.
Disabling skills reduces session-start cost; it does NOT reduce per-turn cost
(the cached prefix already excludes the skill text on subsequent turns).

Actual numbers:
- Static guidance preamble: ~367 tokens
- `<available_skills>` index: ~3,566 tokens (for 149 skills)
- Per-skill average: ~21 tokens (~85 chars)
- Total skills block: ~3,933 tokens

Reproduce: `python3 -c "import sys,os; sys.path.insert(0,'~/.hermes/hermes-agent'); ... from agent.prompt_builder import build_skills_system_prompt; p=build_skills_system_prompt(); print(len(p),'chars',len(p)//4,'tokens')"`
Or run `hermes prompt-size` for the live per-section breakdown.

## Fast recon recipe
```
search_files pattern="def build_skills_system_prompt" path=~/.hermes/hermes-agent/agent/prompt_builder.py
search_files pattern="def extract_skill_description|def iter_skill_index_files" path=~/.hermes/hermes-agent/agent/skill_utils.py
```
Then run `hermes prompt-size` to see the live `<available_skills>` byte/char cost.

## The OTHER skill-listing path: skills_list ≠ system-prompt index

Highest-value disambiguation, and the most common wrong answer here. There are
**two separate skill-listing code paths** — do not confuse them:

| Path | Owner | Cached? |
|---|---|---|
| System-prompt `<available_skills>` block | `agent/prompt_builder.py::build_skills_system_prompt` | YES (LRU + disk snapshot, above) |
| Runtime `skills_list` tool result | `tools/skills_tool.py::skills_list` → `_find_all_skills` (~L604) | NO — fresh filesystem scan every call |

`_find_all_skills(*, skip_disabled=False)` exists **only in
`tools/skills_tool.py`**, and it is NOT the injection path. It scans the FS on
every call, reads ~4000 bytes/SKILL.md, applies platform+environment gates,
dedupes by frontmatter `name` (local wins), truncates description to
`MAX_DESCRIPTION_LENGTH` (1024 — note: not the 60-char index truncation), and
returns `[{name, description, category}]` with **no state field**. When asked
"how does Hermes list skills," first pin down whether the user means the prompt
index or the tool.

## Skill state / telemetry / provenance: tools/skill_usage.py

**Skill lifecycle state is NOT in SKILL.md frontmatter.** It lives in a sidecar
JSON `~/.hermes/skills/.usage.json`, keyed by skill name. States: `active` /
`stale` / `archived` (approx L53-56); `pinned` is an orthogonal boolean.
Read/write: `load_usage`, `get_record`, `set_state`, `set_pinned`; counters:
`bump_view`/`bump_use`/`bump_patch`. Atomic writes, file-locked (`fcntl` Unix /
`msvcrt` Windows); best-effort — a broken sidecar never breaks the tool call.
Provenance: `is_bundled` / `is_hub_installed` / `is_agent_created`;
`PROTECTED_BUILTIN_SKILLS` (e.g. `plan`) may never be archived by the curator.
`_read_skill_name` (~L398) is a cheap manual frontmatter scan for the `name:`
field only (don't mistake it for the canonical `parse_frontmatter`).

## Skill writes + cache invalidation: tools/skill_manager_tool.py

Backs the `skill_manage` tool. Lookup is `_find_skill(name)` (~L569) matching on
**directory name** (`skill_md.parent.name == name`), not frontmatter name. After
any write it calls `clear_skills_system_prompt_cache(clear_snapshot=True)`
(imported from `agent.prompt_builder`) — this is the mechanism by which a skill
edited this session becomes visible in the prompt next turn.

## Four-file mental model for the whole skill subsystem
- `agent/skill_utils.py` — discovery + parse + gate helpers (canonical parser here)
- `agent/prompt_builder.py` — the injected index + its two-layer cache
- `tools/skills_tool.py` — runtime `skills_list` (uncached scan) + `skill_view` (full load)
- `tools/skill_usage.py` — state/telemetry/provenance sidecar
- `tools/skill_manager_tool.py` — writes + cache invalidation
