# Skill Governance, Provenance, and Contamination Detection (Aug 2026)

**Source:** TencentDB Agent Memory — https://github.com/TencentCloud/TencentDB-Agent-Memory (Aug 6 2026)
**Korean analysis:** https://velog.io/@ax_central/agent-memory-from-individual-to-team (Aug 9 2026)
**Session discovered:** multilingual community sweep, Aug 12 2026

---

## Why contamination matters at skill scale

When a shared skill contains an error, that error propagates to *every agent that loads it*
simultaneously. Individual-agent memory errors affect one agent; shared-skill errors affect
the full fleet. The error propagation multiplier is:

    affected_agents = (number of agents loading the skill per day)
    harm_duration   = time until the error is noticed and patched

A skill promoted to "team standard" is load-bearing infrastructure, not a personal note.

**Real-world vector from TencentDB:** Shared Graphiti nodes and shared skills that are
updated by one agent can be read by other agents with different trust levels. Cross-tenant
leakage occurred in production (GitHub issue #864 in TencentDB repo).

---

## Provenance field standard

Add to YAML frontmatter when patching or creating any skill:

```yaml
last_validated: "YYYY-MM-DD"   # ISO date — when the skill was last verified to work
```

**Staleness threshold:** Flag skills with:
- No `last_validated` field, AND
- Reference versioned tooling (CLI flags, API endpoints, model names, package versions)

as staleness candidates if `last_validated` is missing or > 90 days old.

**Quick audit command:**
```bash
python3 -c "
import glob, yaml, datetime
threshold = datetime.date.today() - datetime.timedelta(days=90)
for path in glob.glob('/var/home/rainbow/.hermes/skills/**/*.md', recursive=True):
    if '/.archive' in path or '/.curator' in path: continue
    try:
        parts = open(path, errors='replace').read().split('---')
        if len(parts) < 3: continue
        fm = yaml.safe_load(parts[1]) or {}
        lv = fm.get('last_validated')
        if not lv:
            print(f'NO DATE: {fm.get(\"name\", path)}')
        elif datetime.date.fromisoformat(str(lv)) < threshold:
            print(f'STALE ({lv}): {fm.get(\"name\", path)}')
    except: pass
"
```

---

## Contamination audit step (run after any burst of 5+ skill patches)

1. **Identify recently patched skills** — file mtime or git log for last 7 days
2. **Spot-check each patched skill's primary procedure** — does the stated command/step
   still work? 5 minutes per skill is enough; full re-test only for high-frequency skills.
3. **Identify error propagation vectors** — does this skill:
   - Call or depend_on another skill?
   - Inject content into MEMORY.md, Graphiti, or Hindsight?
   - Define a pattern explicitly referenced by other skills?
   If YES: errors compound across the dependency chain — spot-check dependents too.
4. **Rollback signal** — if a patched skill produces wrong results on first use after
   patching, re-patch immediately. Do not let the bad version accumulate usage history.
   The `last_validated:` field should be bumped on every confirmed-working patch.

---

## Skill authority tier classification (for `trust:` frontmatter field)

Extend the existing `trust:` field beyond supply-chain audit to contamination risk:

| `trust:` value | Meaning | Audit intensity |
|---|---|---|
| `core` | Used by multiple other skills or auto-injected; contamination = fleet-wide | Verify before patching; spot-check after every patch |
| `community` | User-created, shared across sessions | Spot-check on patch; re-test if dependencies change |
| `user` | Personal one-off; single session or rare use | Low priority; monitor only |

High-frequency skills to treat as `core` for contamination purposes (check usage.json):
- `agent-memory-consolidation`
- `hermes-context-hygiene`
- `mnemosyne-atp-safety`
- `trajectory-risk-guardrail`
- `hermes-skill-library-consolidation-audit` (this skill)

---

## Hermes gap analysis

**Mitigations already in place:**
- Graphiti `group_id` namespacing isolates memory by session context
- Curator adoption gate prevents autonomous agents from patching user-owned skills
- skillspector_guard supply-chain scanning flags suspicious new content

**Unaddressed gaps:**
- No mechanism prevents a subagent from writing to a Graphiti namespace that another
  subagent will read in a future session with different trust level
- No automated rollback for skills — only manual re-patch
- `last_validated` field not yet widely adopted across the skill library (as of Aug 2026)

**Recommended next consolidation action:**
1. Add `last_validated` to all skills during next bulk patch session
2. Run the staleness query above and flag skills >90 days stale that reference versioned tools
3. Add contamination audit step to the consolidation audit runbook as Step 4b (between
   "dead cross-references" and "config/cron consistency")

---

## TencentDB Team Memory architecture summary (for context)

TencentDB's key contribution is treating agent memory as *organizational knowledge infrastructure*
with explicit governance:

| Dimension | Individual memory | Team memory (TencentDB) |
|---|---|---|
| Core question | What to remember and when to recall? | Who created it, who approved it, who can use it? |
| Primary risk | Wrong personalization, privacy breach | Error propagation, permission breach, version conflict |
| Required features | Extract, summarize, retrieve, update | Ownership, versioning, review state, ACL, audit log, rollback |

The 4-layer memory types (Chat Memory → Skill → LLM-Wiki → CodeGraph) are well-documented
elsewhere. The governance layer above them is the novel contribution and the gap Hermes
most needs to address at scale.

**Key quote from Korean analysis (translated):**
"The next phase of agent competition is not 'who has the smarter model' but 'who accumulates
more trustworthy organizational memory and reuses it safely.'"
