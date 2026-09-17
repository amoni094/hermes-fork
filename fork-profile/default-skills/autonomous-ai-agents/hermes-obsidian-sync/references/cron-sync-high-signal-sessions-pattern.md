# Cron Sync Pattern: High-Signal Operational Sessions

## When to recognize a rewrite trigger

A single recent session (or related session cluster) warrants a **full live-sync note rewrite** (not just timestamp refresh) when it contains **multiple independent durable clusters**:

1. **Verified operational changes**: config patches applied, commits pushed to canonical repos, settings confirmed live
2. **New capability additions**: new integrations wired, new workflows finalized, new repos created
3. **Threat/security model updates**: veto rules expanded, verification ad-hoc testing passed, fixes verified before merge

### Characteristics of high-signal sessions

- Produce **multiple git commits** across different repos or capability areas
- Include **self-verification** phases (ad-hoc testing, pass 2/3 to catch bugs from pass 1)
- Span **multiple config/infrastructure layers** (veto rules, config.yaml, export repos, deployment decisions)
- Result in **new durable workflows or capabilities** that change how future work happens (not just tweaks)
- Include **hand-offs or decisions** that affect downstream processes (Fable-5 on-request pattern, Cowork port portability matrix)

### Session example: 2026-07-01 config+cowork batch

**Session 1 (config upgrade passes 2 & 3):**
- Opus-4-8 + Fable-5 orchestration (multi-pass pattern)
- Veto rules: 20→24 hard-blocks, 11→13 warn rules
- Config settings: 2 changes applied via `hermes config set`
- Repo exports: 2 commits (4c2fa3e, b974f87) with verification
- Bug discovery and fix: regex bypass caught by Fable, tested 16 cases
- Durable workflow: Fable-5 on-request pattern (Pattern A + Pattern B)

**Session 2 (Hermes → Cowork port):**
- Cowork port repo created (6 files, 185 skills catalogued)
- Pass 1 adversarial review: 7 findings, all fixed
- Pass 2 adversarial review (Opus extended reasoning): structural analysis, 3 additional findings, all fixed
- 3 commits pushed (c662ffb → b3f6059 → 0a364df)
- Durable deliverable: portability matrix, non-portable gaps explicitly called out

**Decision made:** Full rewrite. Two independent durable clusters (infrastructure tightening + new integration port), both with verified state and follow-up implications. Timestamp-only refresh would lose the detail needed for future sessions.

## Decision flow refinement

When the decision tree asks "New durable items found?" check for:

| Session category | Durable signal | Action |
|---|---|---|
| Routine refinement (UX tweaks, small fixes) | 1–2 items | Timestamp-only if already current |
| Single-feature development | 1 cluster | Full rewrite if new capability completed |
| Multi-cluster operational window | 2+ independent clusters | **Always full rewrite** — multiple themes still live |
| Config audit (iterative passes) | 3+ pass findings consolidated | Full rewrite if multiple layers affected |
| Port/porting/migration work | Verify+push cycles complete | Full rewrite (portability matrix is durable) |

## Writing for cron context

When cron sessions contain multi-cluster work:

1. **Group by theme**, not chronology: "Config upgrades (passes 2 & 3)" as one section, "Port creation + review" as another.
2. **Highlight the bridge/connector**: between independent clusters, note what ties them together (e.g., "both part of Hermes resilience hardening initiative").
3. **Call out verification steps**: if multi-pass work included ad-hoc testing, regex verification, or commit-before-fixes, say so — it signals maturity.
4. **Be explicit about hand-offs**: if a session created a durable workflow or new capability, note who/what runs it next (e.g., "Fable-5 on request" triggers, "Cowork port requires user verification").

## Pitfall: high-signal clusters without commits

A session can be durable and high-signal even without git commits (e.g., memory updates, workflow decisions, new skill library patterns). Check for:

- **Config decisions made** (even if applied manually, not via `hermes config set`)
- **Verified architectural choices** (e.g., "decided to use Notion for memory instead of folder structure")
- **New capability finalized** (even if just documented, not yet deployed)
- **Threat model updates confirmed** (veto rules verified, even if not yet merged)

If multiple independent decision/verification clusters exist, rewrite. Timestamp-only refresh loses the decision record.

## Silent suppression caveat

In silent-delivery cron modes, return `[SILENT]` only when:
- Notes already capture all recent durable items AND
- No new sessions added meaningful content AND
- Timestamps are current

If uncertain whether a recent session is "transient refinement" or "independent durable cluster," prefer rewrite. Losing a cluster is worse than rewriting when you might not have needed to.
