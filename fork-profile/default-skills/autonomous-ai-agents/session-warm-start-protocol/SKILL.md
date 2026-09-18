---
name: session-warm-start-protocol
description: >-
  Use when a new session starts in the same domain as a recent session. Warm-start
  from last-session-type.json, pre-classified compression profile, and inherited
  working-memory summary (ChronoMem / hermes-session wrapper).
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
tags: [session, warm-start, chronomem, lambda-tuner, compression, context]
triggers:
  - New Hermes session in the same domain as a session that just ended
  - Need to apply last-session-type.json / hermes-session research|code|mixed profile
  - User continues a research or coding thread after /new or a gateway restart
  - Wrapper vs plugin decision for session-0 compression warm-up
related_skills:
  - hermes-lambda-tuner
  - hermes-fork
  - hermes-context-hygiene
  - hermes-memory-surface-selection
  - agent-memory-consolidation
---

# Session Warm-Start Protocol

When a new session starts in the **same domain** as a recent one, reuse type, complexity, and compressed working memory — do not cold-start mixed defaults. Based on ChronoMem (arXiv:2607.27773), lambda-tuner `last-session-type.json`, and the `hermes-session` wrapper.

Same domain means: same project/repo, same research corpus, or the user is clearly continuing the last thread. If the new prompt is unrelated, skip warm-start.

## 1. Read last-session-type.json

Path: `/var/home/rainbow/.hermes/cache/last-session-type.json`  
(or `${HERMES_HOME}/cache/last-session-type.json`)

Writers: hermes-session wrapper at launch; plugin `_write_hint` on classify (mid-session); plugin `_write_warm_start_cache` on finalize. Readers: wrapper (respects `expires_at`); plugin currently does NOT check `expires_at` or domain — do not claim otherwise until patched. Example:

```json
{
  "type": "code",
  "lambda": "0.2",
  "confidence": 1.0,
  "scores": {"research": 0.0, "code": 7.0},
  "ts": 1789106774.014698,
  "expires_at": 1789128374.0146983,
  "source": "lambda-tuner-plugin"
}
```

Rules:
- If file missing or `expires_at` is in the past → cold start (`mixed`)
- If `confidence` is low (<0.5) → treat as hint only, do not force profile
- `type` is `research` | `code` | `mixed` (entropy-adaptive is a live compressor profile, not always in this file)

Do not copy `turn_clock` or entropy checkpoints across `/new`. ChronoMem: `ContextCompressor.bind_session_state` resets `_turn_clock` so session 2 cannot inherit session 1's skip-gate. Warm-start is **profile + summary**, not clock.

## 2. Apply the pre-classified profile

| last `type` | Compression profile | `rr_scorer_lambda` (wrapper) | Intent |
|---|---|---|---|
| research | `research` (threshold 0.45, protect_last_n 15) | 0.55 | Compress sooner; bulky tool dumps |
| code | `code` (threshold 0.55, protect_last_n 25) | 0.2 | Keep causal exec/read chains |
| mixed | `mixed` (0.50 / 20) | 0.4 | Conservative default |

**Wrapper (`hermes-session`)** when you need session-0 warm-up before compressor init:

```
hermes-session research|code|mixed|auto|entropy-adaptive
# or HERMES_SESSION_TYPE=...
```

**Plugin alone** when this fork's `set_compression_profile` exists and N+1 lag on lambda is acceptable.

Vanilla Hermes has no live mutation path: always wrapper + hint file.

Complexity: if the prior session was high complexity (`TaskComplexityScorer` >0.7), keep a larger `protect_last_n` (cap 40). Low complexity (<0.3) may lower `proactive_prune_tokens` (floor 8000). Do not invent scores — only reuse what the plugin stored or what hermes-fork documents.

## 3. Inherit working-memory summary — not the transcript

Warm-start payload (short):
- Task class / domain of the last session
- Open artifacts (paths, branch, arXiv IDs) — not full file bodies
- Pending decisions and unresolved disagreements
- Compression profile + lambda from the hint file

Do **not** inherit:
- Raw tool_result dumps
- `_turn_clock` / entropy skip-gate
- Unverified child CONTINUITY grants
- Secrets

ChronoMem discipline: user correction of a fact is **rollback of a version**, not a forward-only overwrite. If the new session starts because the user corrected the last one, load the prior version trail (`hermes-memory-surface-selection` ChronoMem section) instead of the last write.

Prefer a compact Hindsight / working-memory summary tagged for the task class over `session_search` of the full prior transcript. If you must search, apply Cross-Session Context Locality: scan last 5 tool results in *this* session before recalling the old one.

## Procedure (first turns of a same-domain session)

1. Read `last-session-type.json` if present and unexpired
2. If same domain: apply profile via wrapper or `set_compression_profile`
3. Pull one working-memory / Hindsight summary for that task class
4. State the inherited profile in one line so the user can override
5. Proceed. If the user changes domain, switch to `mixed` and drop the inherited summary

The plugin applies the hint profile regardless of domain. Until cwd-keyed files are implemented, a different-domain session may inherit a prior session type.

## Pitfalls

- Warm-start on a new domain pollutes compression (research thresholds on a code session)
- Expired hint files: ignore, do not extend `expires_at` (wrapper respects this; plugin currently does not)
- Inheriting the full prior transcript defeats `/new`
- Plugin hint without wrapper does not set lambda on turn 0
- Plugin applies the hint profile regardless of domain until cwd-keyed files exist

## Pre-Study Artifacts for Complex Tasks (arXiv:2609.10824) ★ MED

**Task-Agnostic Environment Preprocessing** (Sep 2026): agents that can "pre-study" an environment before task assignment — building indices, scaffolding, or lightweight scripts — outperform cold-start approaches on 5/6 benchmarks. A meta-agent variant dynamically decides what to pre-build based on environment signals.

**Hermes adaptation:**
- For recurring cron tasks or known-domain sessions: cache a pre-built environment summary (available tools, relevant file paths, known constraints) in `~/.hermes/cache/prestudy/<domain>.json`
- At session warm-start: if a prestudy artifact exists and is <24h old, inject it as the first context block rather than rediscovering the environment from scratch each run
- The prestudy artifact should contain: key file paths, frequently-used commands, known failure modes from prior runs, and available tool inventory — NOT a full prior transcript
- For the hermes-research cron itself: the prestudy artifact is the last apply report + seen_papers cache + skill index — already produced; load it at apply-job start

<!-- why: pre-building environment indices before task assignment reduces task-time sampling overhead and is empirically faster on 5/6 benchmarks; Hermes research cron already does this implicitly — make it explicit for other domains -->
---
