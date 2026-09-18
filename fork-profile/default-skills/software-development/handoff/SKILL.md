---
name: handoff
triggers:
  - User asks to hand off the current conversation or task to another agent or session
  - Context is getting large and work needs to continue in a fresh session
  - User says "write a handoff", "prepare a handoff doc", "summarise for next session"
  - Multi-session work where the current session has hit its useful limit
description: >
  Use when: Compact the current conversation into a handoff document so another agent or session can continue without loss.
version: 1.0.0
author: Hermes Agent (adapted from mattpocock/skills)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [handoff, context, session, multi-agent, continuity]
    related_skills: [hermes-context-hygiene, subagent-driven-development, plan]
related_skills:
  - verification-before-completion
  - plan
  - hermes-context-hygiene
  - subagent-driven-development
---

# Handoff

Write a handoff document that lets a fresh agent continue the current work with minimal context loss.

## When to use

- Current session is getting large (approaching compression threshold)
- Work spans multiple sessions and you want continuity
- Handing off to a subagent, a different profile, or tomorrow's session
- User asks for a summary to paste into a new chat

## Output location

Prefer a durable location over `/tmp` (which is cleared on reboot on most Linux systems):

```
Preferred: ~/.hermes/cache/handoffs/handoff-<slug>-<YYYYMMDD>.md
Fallback:  /tmp/handoff-<slug>-<YYYYMMDD>.md
```

**Deriving the slug:** use 2–4 words from the task title, lowercased and hyphenated (e.g. `auth-refactor`, `lip-legal-spec`, `dashboard-fix`). If there's no clear title, use the repo name or the main tool/command being worked on.

Create `~/.hermes/cache/handoffs/` if it doesn't exist. Tell the user the absolute path after writing.

If the user passed an argument (e.g. `/handoff "focus on the auth module"`), treat it as a description of what the next session will focus on and tailor the document accordingly.

## Document structure

```markdown
# Handoff: <task title>

**Date:** <fill in today's date, e.g. 2026-07-11>
**Next focus:** <what the next session should do first>
**Receiver model (if known):** <same | escalate HC | downshift LC>

## Goal

One paragraph: what is being built/fixed/investigated and why.

## Current state

What is done, what is working, what is NOT done yet.
Be specific — wrong claims here cause rework.

## Working memory (structured)

Prefer exporting via:
`python3 ~/.hermes/scripts/working-memory.py -s <session> handoff-export`
Paste the JSON (or key fields). Do NOT replace this with a prose chat recap.

## Action-binding constraints (required)

Operational state, not flavor text (arXiv:2608.24569 Constraint Weakening).
Every hard rule MUST keep `binding: must` — never rewrite to should/maybe/consider.

```yaml
constraints:
  - text: <exact rule>
    binding: must          # must | should | info
    authority: user|policy|safety
    fallback: <what to do if blocked>
    consequence_if_ignored: <execution consequence>
```

Lint before finishing: `python3 ~/.hermes/scripts/constraint-binding-lint.py <this-file>`

## Active context

Key files, repos, URLs, commands the next agent needs to know.
Do NOT paste full file contents — use paths or links.

## Open decisions

Unresolved questions or branch points that need a decision before proceeding.

## Blockers

Anything that must be resolved before meaningful work can continue.

## Suggested next steps

Ordered list of what to do next, as specific as possible.

## Suggested skills

Skills the next agent should load at the start:
- skill-name — why
- ...

## Do NOT repeat

Files/plans/commits/ADRs that already capture detail — list them by path or URL so the next agent reads the source, not a stale paraphrase.
```

## Handoff Tax (arXiv:2608.24358) — model / session switches

When escalating LC→HC or downshifting HC→LC (or starting a fresh session):

1. **Prefer structured state over full trajectory.** Full-trajectory transfer recovers
   less than half of native HC quality. Export WM + constraints + repo state first.
2. **Keep repo/filesystem as ground truth.** Receiver re-reads paths; do not trust a
   long chat dump of diffs.
3. **Compaction is not free.** If you must compress history, run constraint-binding-lint
   on the result — compaction is the main place must→maybe weakening appears.
4. **Same-model continuation** can carry a shorter trajectory tail; cross-model handoffs
   should assume the receiver is cold except for the structured packet.

## Topology alert

This skill is a structural articulation point in the skill dependency graph: 21
other skills route through it and it forms a bridge edge to the autonomous-agents
cluster (`handoff <-> run`). It is the canonical session-termination/continuation
primitive. Changes to the document structure or output location affect every skill
that hands off work. Before restructuring, grep dependents:
`grep -r '\bhandoff\b' ~/.hermes/skills --include="SKILL.md" -l`

## Rules

- **Do not duplicate** content already captured in specs, plans, ADRs, issues, commits, or diffs. Reference by path or URL instead.
- **Redact** API keys, passwords, tokens, personally identifiable information.
- **Be concrete about current state** — vague "mostly done" claims are the main failure mode; say exactly what passes and what doesn't.
- **Preserve constraint binding force** — never turn a must into should/info during summarization (arXiv:2608.24569).
- **Structured WM over chat dump** on model switches (arXiv:2608.24358 Handoff Tax).
- **One suggested next step should be immediately actionable** — the next agent should be able to start without asking clarifying questions.
- **Length:** aim for a 5-minute read. No hard word limit, but include only what the next agent needs to get started without questions — no background padding.
