# Durable Item Triage Patterns for Obsidian Sync

## Context
When the timestamp-only decision tree sends you to session inspection (decision tree gate indicates new durable items *may* exist), use these patterns to efficiently separate durable state changes from transient work.

## Three-lens triage for operational sessions

When reviewing recent sessions (typically 3–5 most recent substantive sessions), scan each for these lenses:

### Lens 1: Configuration & Deployment
Look for:
- Config YAML/JSON changes that remain in effect
- Git commits pushed to production or a tracked branch (report the commit SHA and changeset scope)
- Cron job creation/modification that remains active
- API endpoint registration, service restart, or listener start-up
- Package installations or dependency updates that are now in the working environment
- Systemd/init changes that persist across sessions

**Scope**: Only changes that lasted from the session into the current time. Transient config restarts or one-off test servers do not count.

### Lens 2: Verified Fixes & Verified Outcomes
Look for:
- Bugs fixed and confirmed as resolved (with verification command output or reproducible proof)
- Security patches applied and validated (hermes doctor, linters, audits passing)
- Test results that landed
- Operational issues diagnosed and resolved (not just identified)
- Skill patches applied and verified (file size stable, lint/syntax ok, usage not broken)

**Scope**: Only outcomes that were actually confirmed before the session ended. A session that says "I'll fix this next turn" does not count as verified.

### Lens 3: Workflow & Process Changes
Look for:
- New or updated cron jobs, scripts, or automation workflows
- Decision trees or patterns that stabilized during the session
- New skill/reference documentation added or updated
- Integration points that were wired in (not just planned)
- Operational process changes that affect how the system runs going forward (e.g., session auto-pruning now enabled, obsidian sync pattern stabilized)

**Scope**: Changes to HOW the system works, not just what it currently does. If a session established a reusable workflow (e.g., "timestamp-only vs. full-rewrite decision tree works"), that's Lens 3 durable output.

## Session-to-durable-item mapping

When a session contains both routine work and significant durable outcomes:

**Single-lens sessions** (common for config work, bug fixes):
- Report the durable outcome from that lens only.
- Example: "hermes-config git commit 3679661 pushed" (Lens 1), "medical-research-analysis skill 14 patches applied and verified" (Lens 2).

**Multi-lens sessions** (when a single session spans infrastructure + verification + workflow stabilization):
- Keep all three lens clusters separate in the live-sync note.
- Example: "Fable-5 Pass 5 audit" contained Lens 1 (orphan scripts removed, permissions fixed), Lens 2 (all 47 issues verified resolved), and Lens 3 (audit pattern stabilized for future passes).

**Sessions that contain only transient exploration or calibration**:
- If all three lenses show no lasting change (user was testing, researching, or iterating without settling on a durable outcome), do NOT include that session in the sync note unless the settled final state is durable.
- Example: "tried three different recommendations, will decide next time" → not durable, skip it. "Tried three, settled on this config which is now active" → durable, include it.

## Recognition shortcuts

**High-signal durable-item indicators**:
- Git commit SHAs or confirmed pushes to a tracked repo
- `hermes doctor` output showing resolved issues
- File diffs that are small and intentional (not refactors or churn)
- Cron job creation/modification confirmed with `hermes cron list`
- Skill patches confirmed with skill_manage
- Config changes with side-by-side before/after verification
- Deployment to prod or a persistent environment

**Low-signal transient work** (usually skip unless settled):
- Multiple recommendation rounds without a final picked choice
- Test/spike branches without merge
- Back-and-forth debugging with no root cause found
- Exploration or research with open next-steps
- Config testing that was reverted
- Repeated attempts that finally worked but only the final working version matters (capture the working state, skip the failed attempts)

## Filtering strategy

1. **Timestamp-only decision tree gate** → if it says "probably timestamp-only," skim the 3–5 recent sessions for lenses 1, 2, and 3. If you find any concrete hits (config pushed, fix verified, workflow stabilized), move to full-rewrite. Otherwise, stay timestamp-only.

2. **Full-rewrite decision tree gate** → inspect all three lenses for the same recent sessions. Consolidate findings into separate session/theme clusters in the live-sync note (don't combine unrelated lenses into a single vague bullet).

3. **For same-day multiple syncs** → the second sync on the same calendar day should check whether the earlier sync already captured a durable cluster. If so, look only for NEW durable items added after the earlier sync's timestamp. Do not duplicate clusters.

## Writing the sync note

After triaging with the three lenses:

- **Lens 1 findings** → become "config changes," "git commits," "cron modifications," "deployment verified" sections
- **Lens 2 findings** → become "verified fixes," "security hardening," "skill patches applied," "test suite passing" sections
- **Lens 3 findings** → become "workflow stabilized," "new automation added," "process/pattern documented," "decision tree validated" sections

Each lens cluster should have 2–4 bullets with concrete evidence (SHAs, file sizes, error counts, time measurements, etc.). Avoid vague summaries like "improvements made" — be specific.

## Example: 2026-07-03 session triage

**Session A: Fable-5 Pass 5 audit (10:58–11:21)**
- Lens 1: hermes-config git commit 3679661 (config.yaml 751→68 lines, audit docs created, 0 secrets leaked)
- Lens 2: 47 issues fixed, hermes doctor 1 known CVE only, all 8 crons verified ok
- Lens 3: Fable-5 audit pattern (pass 4+5 gates) now reusable for future improvements

**Session B: Medical-research-analysis v1.3.0 adversarial pass 3 (11:20–11:51)**
- Lens 1: Skill file 57,643→61,901 chars, 14 patches applied
- Lens 2: ID gates rewritten (HTTP 200 body check), NICE HST corrected (£100k→£300k), dangling sources fixed
- Lens 3: Recursive adversarial pass strategy (triage findings, batch-patch, verify, prepare next pass) validated as workflow

**Session C: Messaging consent review (11:54–12:10)**
- Lens 1: None
- Lens 2: No issues found (pattern verification-only)
- Lens 3: None

**Result**: Clusters A and B each warrant a section in the live-sync note. Cluster C is verification-only, skip it.
