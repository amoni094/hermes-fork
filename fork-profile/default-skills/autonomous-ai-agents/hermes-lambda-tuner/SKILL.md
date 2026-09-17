---
name: hermes-lambda-tuner
description: "Use when debugging lambda-tuner adaptive compression."
tags: [hermes, compression, lambda]
related_skills:
  - hermes-fork
  - hermes-context-budgeting
  - rr-compaction-scorer
---

# lambda-tuner

## Files

- Plugin (vanilla): `~/.hermes/plugins/lambda-tuner/__init__.py`
- Plugin (fork): `/tmp/hermes-fork-work/plugins/user/lambda-tuner/` (or the clone's `plugins/user/lambda-tuner/`)
- Wrapper: `~/.local/bin/hermes-session`
- Hint: `${HERMES_HOME:-~/.hermes}/cache/last-session-type.json`
- Canonical fork docs: `FORK_README.md` § lambda-tuner (explain once, reference many)
- Working on the fork itself: skill `hermes-fork`

## How it works

Plugin accumulates ALL user turns, classifies research/code/mixed, writes JSON hint for the NEXT session. Wrapper reads hint at startup, checks 6h TTL, patches config.yaml rr_scorer_lambda, exec hermes.

**Vanilla Hermes:** that hint path is the only lever. `rr_scorer_lambda` is bound at compressor init, so classification on session N takes effect at session N+1.

**hermes-fork:** live `set_compression_profile`, hook table, predicates, complexity scoring, reasoning mode — canonical in skill `hermes-fork` and `FORK_README.md`. Do not duplicate those tables here.

## Lambda table

  research          -> 0.55  (evict stale web/skill dumps; exec-state protection shields read_file/terminal)
  mixed             -> 0.40  (conservative default; expired/missing hint)
  code              -> 0.20  (keep all episodic exec/read state)
  entropy-adaptive  -> 0.40  (wrapper warm-up same as mixed; live threshold is R(D), not this lambda)

Do NOT raise research to 0.7. Phase-1 exec-state already holds web_extract. 0.55 is sufficient and avoids demoting misclassified coding sessions.

## Classifier design

- Weighted lexicons. No unigram traps (dropped: error, code, class, test, review, extract, summarize, what is, who is, monitor).
- Greeting filter: _GREETING_RE; greeting-only turns return mixed, conf=0.0.
- Accumulation: all user turns concatenated; updated until lock.
- Lock: once confident (non-mixed) type committed, further turns do not overwrite.
- Margin: winning >= loser * 1.5 AND winning >= 1.
- Close scores: emit mixed.
- Article: use (?:an?\s+)? not (?:a\s+)? for 'add an endpoint'.

## Hint JSON schema

  {"type": "research", "lambda": "0.55", "confidence": 0.82,
   "scores": {"research": 2.5, "code": 0.0},
   "ts": 1726000000.0, "expires_at": 1726021600.0, "source": "classifier"}

Atomic write via tempfile + os.replace. HERMES_HOME env (profile-aware). TTL 6h. Missing/expired -> mixed.

## Wrapper

  hermes-session [research|code|mixed|auto] [args...]
  HERMES_SESSION_TYPE=code hermes-session [args...]

Explicit mode or env var beats hint. auto: read hint; cwd heuristic fallback.
Fallback: word-boundary grep arxiv|papers?|sweep; git = +1 only; code files = +1.
OSError/YAML error: print WARNING, exec hermes unchanged. NEVER abort.

On the fork, use the wrapper when you need **session-0** `rr_scorer_lambda` (and optional `entropy-adaptive`) before turn 1. Rely on the plugin alone when live `set_compression_profile` is enough and N+1 lambda lag is acceptable. See skill `hermes-fork`.

## Critical pitfalls

These still apply on **vanilla Hermes**. On the fork, live mutation of threshold/prune/protect_last_n is available; `rr_scorer_lambda` still needs the wrapper/hint.

- rr_scorer_lambda is bound at compressor init. On vanilla Hermes, plugins CANNOT mutate it live. N->N+1 lag is fundamental. On the fork, `set_compression_profile()` mutates compressor attributes live; it does **not** rebind `rr_scorer_lambda`.
- Live mutation of `rr_scorer_lambda` remains skipped (I-26/27/28). Do not claim the fork closed that gap.
- No global agent singleton exposed to plugins. Fork passes `agent=` on `pre_llm_call` so plugins use the per-session object.
- Never use bare $VAR inside python3 -c strings. Use os.environ injection.
- (?:a\s+)? does not match 'an'; use (?:an?\s+)?.
- _MIN_SIGNAL=2 too strict for short messages. Keep MIN_SIGNAL=1.
- _fired set is per-process; not safe for multi-tenant gateway.
- Hint path MUST use HERMES_HOME not hardcoded ~/.hermes.
- Stale hint (>6h) falls to git-biased cwd heuristic. Use explicit mode for important sessions.

## Verification

  hermes plugins doctor ~/.hermes/plugins/lambda-tuner
  bash -n ~/.local/bin/hermes-session
  python3 -m py_compile ~/.hermes/plugins/lambda-tuner/__init__.py
  python3 -m py_compile plugins/user/lambda-tuner/__init__.py   # from fork clone

## Research sources

I-02/I-21/G-01: Confidence-gated mixed; weighted multi-label (AWS Lex, IntentGrasp)
I-03/G-02: Tight lexicons, no unigram traps
I-06/I-13/G-03/G-07: JSON + TTL + atomic write + HERMES_HOME
I-10/G-08: Accumulate turns; greeting filter (arXiv:2411.12307)
I-14: CLI override / HERMES_SESSION_TYPE
I-15: Atomic writes. G-04: OSError warn+continue. G-05: word-boundary fallback.
I-19/I-20: code 0.2; research 0.55 (arXiv:2508.21433, arXiv:2604.15877)

SKIPPED (vanilla): per-cwd hints (I-07), LLM cascade (I-08), depth classes (I-09), EMA (I-11), live mutation of rr_scorer_lambda (I-26/27/28).
FORK ADDS: live `set_compression_profile` (not rr_scorer_lambda), `pre_compress` hook, `entropy-adaptive` profile.

## Denuto Middleware → Fork Plugin Hook Mapping

Source: Denuto `src/harness/middleware.py`. See `hermes-llm-middleware-stack`.

The fork's plugin hooks map directly to Denuto middleware patterns:

| Denuto Middleware | Fork Hook | Implementation notes |
|---|---|---|
| `CostGuardMiddleware` | `pre_llm_call` | Read cumulative cost from contextvar; downgrade model if > threshold |
| `LoopDetectionMiddleware` | `pre_llm_call` | MD5-hash per (session, stage); short-circuit on duplicate |
| `FewShotInjectionMiddleware` | `pre_llm_call` | Prepend examples to prompt for known stage patterns |
| Cost accumulator init | `on_session_start` | Initialize cost contextvar to 0.0 |
| Loop detection reset | `on_session_start` | Clear hash registry for new session |
| State flush | `on_session_finalize` | Emit shadow telemetry events for cost/loop stats |
| `GroundingMiddleware` | (no direct hook) | Would need a post_llm_call hook — GATE GAP |

**Cost guard thresholds** (from config.yaml `cost_guard:`):
- extractor_usd: 0.10 → downgrade to haiku if exceeded
- compiler_usd: 0.20 → downgrade to haiku
- session_total_usd: 1.00 → hard cap, downgrade all stages

**Loop detection**: MD5 of LLM response text per `(session_id, agent_stage)`.
Limitation: catches exact duplicates only. Semantically identical but rephrased
responses NOT caught (needs embedding similarity — GATE GAP).
