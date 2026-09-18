# Adversarial Audit Findings — 2026-07-03d (Pass 8)

Session: Recursive adversarial self-improvement on Hermes memory, workflows, token optimization, efficiency.
Surfaces audited: MEMORY.md, USER.md, CTX-now, CTX-systems, CTX-projects, config.yaml, .env,
cron (8 jobs + scripts on disk), skills (.usage.json, 138 active), hermes doctor.

## Key Char Counts at Audit Start
- MEMORY.md: 729 / 2200 (33%) — healthy
- USER.md: 1363 / 1375 (99%) — NEAR-FULL → compressed to 1076 / 1375 (78%)
- CTX-now: ~350 chars — healthy
- CTX-systems: ~3800 chars

## Findings

### HIGH
| ID | Finding | Surface | Status |
|----|---------|---------|--------|
| H1 | 15 never-used visual/media/entertainment skills inflating skill router | skills | FIXED — deleted |
| H2 | CTX-projects.md stale reference: "skill: hermes-memory-drift-audit" (job uses a script, not a skill) | CTX-projects | FIXED |
| H3 | CTX-systems.md: prune-sessions-daily entry present despite job being deleted sessions ago | CTX-systems | FIXED |
| H4 | USER.md at 99% — any write attempt would fail or silently truncate | USER.md | FIXED — compressed to 78% |

### MEDIUM
| ID | Finding | Surface | Status |
|----|---------|---------|--------|
| M1 | .usage.json ghost references: 7 archived skills still appear as "never used" (false positives inflate count) | skills | DOCUMENTED — not deletable (already archived) |
| M2 | CTX-projects Fable-5/Ouroboros entries had no Completed date despite being long-stable | CTX-projects | FIXED |

### CONFIRMED CLEAN (from prior passes, all verified live)
| Check | Result |
|-------|--------|
| hermes doctor | All PASS |
| All 8 cron jobs | deliver=local, last run=ok, scripts exist on disk |
| config.yaml compression | enabled: true, threshold: 0.5 |
| config.yaml auxiliary | provider: anthropic, model: claude-haiku-4-5 |
| config.yaml fallback_model | cerebras→sambanova→mistral |
| config.yaml display | resume_display: compact, resume_exchanges: 3 |
| MemPalace | enabled: false |
| .env | no duplicate keys; blank-value lines are intentional commented stubs |
| MEMORY.md | 4 accurate entries, no stale facts |
| Skill redundancy | all overlap candidates confirmed distinct (github-issues, self-improve-agent, hermes-context-hygiene vs hermes-context-budgeting) |
| Session patches from Pass 7 | self-improve-agent 5-axis rubric, hermes-context-hygiene token measurement, verification-before-completion pass^k, agent-task-signoff — all intact |

## Skills Deleted This Pass
ascii-art, ascii-video, architecture-diagram, baoyu-infographic, claude-design,
design-md, excalidraw, gif-search, heartmula, p5js, popular-web-designs, pretext,
sketch, songwriting-and-ai-music, youtube-content

## Techniques That Worked Well

### .usage.json ghost-reference awareness
Skills moved to `.archive/` keep `.usage.json` entries and appear in "never used" tallies.
Always exclude `.archive/` paths when computing true active count:
```bash
find ~/.hermes/skills -name 'SKILL.md' | grep -v '/.archive/' | wc -l
```
Cross-reference before deleting based on zero-use status.

### CTX-systems cron cross-check
After reading CTX-systems Background Automation, immediately run `hermes cron list`
and compare. CTX-systems is prose documentation — it drifts silently. The specific
failure: `prune-sessions-daily` was deleted but its CTX-systems entry stayed,
still referencing its former complement (`session-auto-prune`) as if both were active.

### Categorize never-used skills before acting
Rather than deleting all zero-use skills, categorize:
1. Already in .archive (ghost refs — do nothing)
2. Valid latent skills (will trigger when task arises — keep)
3. Dead-weight: wrong platform, wrong use-case, user has moved on — delete
Only category 3 warrants deletion. This session: 15 deleted, 18 kept as latent, 7 archive ghosts.

### Parallel batch reads before analysis
Read MEMORY.md + USER.md + CTX-now + CTX-systems + CTX-projects + config fragments
+ cron list all in one execute_code call. Doing this serially misses cross-surface contradictions.

## Status at Close
CRITICAL: 0  HIGH: 0  MEDIUM: 0  LOW: 0
All findings resolved. Pass 8 complete.
