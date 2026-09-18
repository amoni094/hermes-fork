# Adversarial Audit Findings — 2026-07-03c (Pass 7+)

Session: Recursive adversarial self-improvement on Hermes memory, workflows, token optimization, efficiency.
Surfaces audited: MEMORY.md, USER.md, CTX-now, CTX-systems, CTX-projects, config.yaml, cron (10 jobs), toolsets, MCP servers, skills (.usage.json).

## Key Char Counts at Audit Start
- MEMORY.md: 1435 / 2200
- USER.md: 1383 / 1375 ← OVER BUDGET
- CTX-now: 473
- CTX-systems: 3189
- CTX-projects: 1329

## Findings

### CRITICAL
| ID | Finding | Surface |
|----|---------|---------|
| CRIT-1 | USER.md 8 chars over 1375 limit — any add will fail silently | USER.md |

### HIGH
| ID | Finding | Surface |
|----|---------|---------|
| HIGH-1 | No compression keys in config.yaml — auto-compaction status unknown; sessions accumulate unbounded context | config.yaml |
| HIGH-2 | fallback_model in MEMORY.md as fact only, NOT in config.yaml — no live failover if Anthropic goes down | config.yaml |
| HIGH-3 | skillspector-guard + firecrawl-watchdog both deliver='origin' — silently drops output on CLI (no gateway) | cron |
| HIGH-4 | Dual prune-sessions crons (session-auto-prune every 240m + prune-sessions-daily 2am) — overlap without documented rationale | cron |
| HIGH-5 | Hindsight mode (local_embedded → Ollama) not in MEMORY.md — agent can't diagnose background heat correctly | MEMORY.md |
| HIGH-6 | 60 never-used skills — 20+ are platform-incompatible (macOS/HomeKit/cloud workspace); inflate available_skills block every turn | skills |

### MEDIUM
| ID | Finding | Surface |
|----|---------|---------|
| MED-1 | CTX-projects has no automated expiry enforcement for 30-day Completed policy | CTX-projects |
| MED-2 | MEMORY.md "Memory bridge crons: 3" — stale; live count is 10; misleads every agent turn | MEMORY.md |
| MED-3 | No auxiliary config — compression will use claude-sonnet-4-6 (premium) instead of haiku | config.yaml |
| MED-4 | "Skills: class-level umbrellas, git-tracked" entry in MEMORY.md — vague procedural; belongs in skill not memory | MEMORY.md |
| MED-5 | "Before delegation/cron/bg: check vault+session context; log to..." in MEMORY.md — procedural instruction duplicated from AGENTS.md | MEMORY.md |
| MED-6 | MemPalace MCP enabled in config despite CTX-systems labelling it DORMANT — agents still pay mempalace tool tokens every turn | config.yaml + CTX-systems |
| MED-7 | obsidian-weekly-review shows no Last run — may have never executed | cron |

### LOW
| ID | Finding | Surface |
|----|---------|---------|
| LOW-1 | No resume_display / resume_exchanges config — resume payload uncontrolled | config.yaml |
| LOW-2 | session-auto-prune and prune-sessions-daily show near-identical last-run timestamps — may not complement as designed | cron |
| LOW-3 | GitHub PAT scopes note in MEMORY.md (185 chars) — low daily utility; better in github-operations skill or Hindsight | MEMORY.md |

## Techniques That Worked Well

### Parallel batch reads before analysis
Reading MEMORY.md, USER.md, CTX-now, CTX-systems, CTX-projects, config.yaml, cron list, tools list, MCP list, and skills usage — all in parallel before starting analysis — produced the full cross-surface picture needed for audit Step B. Doing this serially (read one, analyse, read next) produces incomplete findings because you can't see contradictions between surfaces you haven't yet read.

### Finding taxonomy
Using `ID-TYPE-N` codes (CRIT-1, HIGH-3, MED-6) with a severity table made proposals scannable and unambiguous. The user can approve/reject by ID rather than re-reading prose.

### .usage.json analysis
`cat ~/.hermes/skills/.usage.json | python3 -c "..."` to extract never-used skills and skills older than N days. Faster than skills_list + grep. Produces the platform-incompatible shortlist in one pass.

### char count check before any memory operation
`wc -c MEMORY.md USER.md` as the first diagnostic step — catching USER.md over-budget before attempting any write prevented a silent batch failure.

## Config Gaps Confirmed Absent
These keys were expected but absent from config.yaml at audit time:
- `compression` (any keys)
- `auxiliary` (any keys)
- `fallback_model` (any keys)
- `display.resume_display`
- `display.resume_exchanges`
- `skills.disabled`

## Skill Disable Candidates (platform-incompatible on Linux)
apple-notes, apple-reminders, findmy, imessage, macos-computer-use, openhue, airtable, notion, google-workspace, teams-meeting-pipeline, audiocraft, comfyui, manim-video, lm-evaluation-harness, vllm, segment-anything, touchdesigner-mcp, yuanbao, xurl, polymarket, blogwatcher

## Status
Findings surfaced; proposals presented; user initiated skill library update before applying config/memory fixes.
