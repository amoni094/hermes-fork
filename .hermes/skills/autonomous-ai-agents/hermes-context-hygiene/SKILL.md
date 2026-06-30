---
name: hermes-context-hygiene
description: "Use when a Hermes session is getting tool-heavy or context-bloated and you need explicit compression-trigger discipline plus minimal-context execution habits."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, context, compression, hygiene, token-budget]
    related_skills: [hermes-agent, hermes-memory-surface-selection, hermes-performance-tuning, writing-skills]
---

# Hermes Context Hygiene

Use this when:
- a session has become tool-heavy
- the user complains about prompt bloat, slowdowns, or missed compression
- you are about to run broad searches, session-history recovery, or large documentation/patch passes
- you need explicit rules for when to compress and when to switch to a minimal-context path

## Goal

Keep long Hermes sessions usable by applying compression-trigger discipline and minimizing unnecessary context growth.

## Core rule

Do not rely on intuition alone. Treat certain events as mandatory context-hygiene checkpoints.

## Compression triggers

Trigger compression or an explicit compression recommendation at these boundaries:
1. after a large `session_search` result or transcript recovery pass
2. after a broad repo-wide `search_files` sweep
3. after multi-file patching or large docs/skill maintenance work
4. before switching from one task family to another after heavy tool use
5. whenever the user explicitly flags context pressure, compression, or prompt bloat

## If `/compress` is available
- use `/compress` at those trigger points instead of waiting for the session to degrade further

## If `/compress` is not invokable from the current tool surface
- say that briefly and plainly
- recommend `/compress` explicitly at the trigger point
- then continue with the lowest-context execution path available
- do not produce a long explanation about why compression cannot be invoked
- if the user explicitly says some version of "compress context", treat that as a request for immediate action: give the direct `/compress` instruction first, keep the explanation to one or two lines, and do not bury the answer under caveats

## User-facing preference for this task class
For this user, context-hygiene interventions should be terse and operational.
- Prefer: `Use /compress now.` plus one short note if a limitation matters.
- Avoid long meta-explanations about why compression was missed or hard to invoke.
- If the user is frustrated about consistency, acknowledge it directly and move to the fix path.

## English-only maintenance rule
When auditing or maintaining Hermes itself for this user:
- keep backend/frontend/runtime surfaces in English only unless the user explicitly asks for multilingual support
- if repo searches hit localized docs or i18n assets, do not paste non-English content into the response unless it is required evidence
- prefer reporting the existence of localized surfaces in English, then change the configuration or docs as needed
- when making English-only repo/runtime changes, verify all three layers separately: runtime config, backend i18n codepaths, and frontend/docs locale configuration
- after changing repo-side runtime or locale code, restart long-lived sibling Hermes processes such as dashboard and gateway, then verify the new PIDs and listeners instead of assuming the restarted process is the one you launched
- explicitly note when the current live CLI/chat process is still the old session and therefore needs its own manual restart to pick up in-memory code changes
- see `references/english-only-surface-audit.md`
- do not silently continue past a clear compression boundary; call out the boundary and the recommended `/compress` action

User preference learned from live correction:
- the user expects proactive context hygiene rather than retrospective explanation
- when a session is already tool-heavy, prefer a short operational note like `good point — this is a compression boundary; please run /compress` over a longer justification

## Lowest-context execution path

After a trigger fires, prefer:
- direct-source inspection over broad historical reconstruction
- narrow file reads over repeated large searches
- small delta summaries over full recaps
- one verification command over multiple overlapping proof passes
- routing to the right specific skill quickly instead of loading many loosely relevant ones

## Reporting rule

When the session is under pressure:
- summarize only the delta
- name the blocker or current result
- avoid repeating already-established background unless needed for the next action

## Pressure scenario

Baseline failure pattern:
- the agent keeps doing useful tool work
- large tool outputs accumulate
- the agent does not pause at natural boundaries
- the session becomes harder to steer, slower, and more repetitive

The fix is not only enabling compression in config; it is applying consistent trigger discipline during long turns.

## Verification

Check both configuration and behavior when relevant:
- `compression.enabled`
- `compression.threshold`
- whether recent sessions/logs show real compression activity
- whether the agent explicitly recommended or used compression at high-volume boundaries

## Pitfalls

- continuing silently through huge tool output without a compression checkpoint
- explaining compression limitations at length instead of shortening the path
- rehashing prior findings after the user already signaled context pressure
- assuming enabled compression alone solves operator-discipline failures

## Completion rule

This skill is applied successfully only if the session behavior changes: compression/recommendation happens at the trigger points, and the remaining execution path stays compact.
