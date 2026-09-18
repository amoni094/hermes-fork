# Research → Implement → Adversarial Pipeline (Aug 2026)

Validated pattern from the Aug 2026 Hermes architecture improvement session.
Use when the request is "research X and implement improvements" across multiple
topic clusters simultaneously.

## Pipeline shape

```
Phase 1: Parallel research subagents (3–4, one per topic cluster)
  └── Each writes /tmp/research_<topic>.md
  └── Covers: arXiv (EN + CN), GitHub, HN, Reddit, ≥1 non-EN source
  └── Duration: ~7 minutes parallel

Phase 2: Local audit (run while subagents are in flight)
  └── skillspector --enforce (clear pending quarantine queue)
  └── xref audit (broken related_skills refs)
  └── hermes doctor + config check baseline
  └── Duration: ~5 minutes

Phase 3: Synthesise research → implement
  └── Read all /tmp/research_*.md files
  └── Classify each finding: REAL runtime change vs DOC-ONLY
  └── Implement REAL changes first (scripts, config, AGENTS.md)
  └── Patch skills second (reference files for new findings)

Phase 4: Adversarial subagent
  └── delegate_task with: list of all changed files, change descriptions, scope
  └── Subagent finds HIGH/MEDIUM issues → fixes them itself → final verify
  └── Duration: ~15 minutes

Phase 5: Final verification
  └── 21-check ad-hoc script (l1 pipeline + YAML + Use-when coverage)
  └── hermes doctor + hermes config check
  └── Skill library counts (YAML errors, missing Use when, 57-char window)
```

## What counts as a REAL runtime change (not doc-only)

| Change type | Effect | Example from Aug 2026 |
|---|---|---|
| `~/.hermes/scripts/*.py` edit | Immediate on next cron run | l1-extract memory_type, l1-promote dedup gate |
| `hermes config set ...` | Immediate on next session | web.extract_backend=firecrawl |
| AGENTS.md addition | Every session, immediately | 35% floor clarification, skill routing |
| New cron job | Runs independently | N/A this session |
| Skill SKILL.md patch | Only when skill is loaded | Research findings documented |

Doc-only changes (skill patches, reference files) are still valuable — they encode
institutional knowledge — but don't claim runtime effect until a session loads that skill.

## Adversarial subagent context packet

The adversarial subagent needs:
1. Complete list of changed files with absolute paths
2. Description of each change (what was added/removed)
3. The research findings that motivated each change
4. The verification checks that should pass after fixes

It CANNOT edit AGENTS.md — that file is write-protected in subagent context.
Any AGENTS.md changes must be made by the parent session before dispatching the subagent.

## Findings from Aug 2026 run

**Research topics covered:**
- Agent runtime behaviour (arXiv: MERIT 2608.05906, MemTool 2507.21428, PreFlect 2602.07187)
- Memory topology (G-Memory 2506.07398, GAM 2604.12285, HKUST survey 2604.01707)
- Skill library at scale (SkillRouter 2605.16508, SkillDAG 2606.03056, SkillRAE 2605.10114)
- Context compression (structured vs uniform 2608.01056, SkillReducer 2603.29919)

**Implemented (REAL):**
- l1-extract.py: 5-type memory_type tagging (`fact|correction|outcome|preference|reasoning`)
- l1-promote.py: `parse_fact_type()`, `VALID_TYPES` allowlist, `write_to_staging()` with `[type=X] [valid_from=Y]`, recurrence gate bypass for corrections/outcomes
- cron_l1_retain.py: strip `[type=X]` and `[valid_from=Y]` fields before Hindsight ingest
- AGENTS.md: structured compression rules, 2-level skill routing guidance, updated guardrails section

**Implemented (DOC):**
- hermes-semantic-skill-routing: 2-level hierarchical routing, SkillDAG typed edges
- hindsight-stack-operations: dedup gate, memory_type, temporal validity, temporal reranking
- hermes-skill-library-consolidation-audit: frontmatter schema extensions, 57-char pitfall, pipeline pitfall

**Adversarial pass findings (all resolved):**
- F1: cron_l1_retain.py not stripping new metadata fields → RESOLVED (already fixed by parent)
- F2: hindsight-stack-operations doc inaccuracy about type metadata → RESOLVED (skill patch)
- F4: 15 skills with "Use when" past 57-char window → RESOLVED (bulk rewrite)
- F5: parse_fact_type() no type allowlist → RESOLVED (VALID_TYPES + coercion)
- F6: false comment in l1-promote.py (valid_to/superseded_by set downstream) → RESOLVED (comment corrected)

## Verification script (21 checks)

```python
# Core checks from the final verification pass
# See /tmp/hermes-verify-l1-final.py (deleted after use — regenerate from this)

checks = [
    "normalise backward compat",           # old string facts + new typed dicts both handled
    "normalise types preserved",
    "VALID_TYPES + parse_fact_type found in source",
    "pft '[preference] text' -> preference",
    "pft '[correction] c' -> correction",
    "pft 'plain string' -> fact",
    "pft '[outcome] done' -> outcome",
    "pft '[unknown_type] x' -> fact",      # unknown coerced, not crashed
    "write_to_staging found in source",
    "staging field '[type=preference]'",
    "staging field '[valid_from='",
    "staging field 'Test fact'",
    "retain strip: new format",            # [type=X] [valid_from=Y] stripped
    "retain strip: old format",            # old format still works
    "cron_retain has type= regex",
    "cron_retain has valid_from regex",
    "recurrence bypass in l1-promote",
    "l1-extract outputs type field",
    "all 164 SKILL.md valid YAML",
    "no skills missing 'Use when'",
    "'Use when' within 57-char window",
]
# Expected: 21 pass, 0 fail
```
