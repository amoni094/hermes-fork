# Stall prevention taxonomy (S1–S11)

Operational stall classes, signals, recovery, and the escalation decision tree.
Model-choice on stall stays in `claude-routing-hierarchy` SKILL.md (capability class → live ID).
Inventory snapshot 2026-08-30; re-verify procedures against live harness before treating timeouts as current.

## Stall prevention, detection, and escalation (research-grounded, 2026-08-30)

Research basis: arXiv:2607.01641 (IAL taxonomy; IAL-Scan static detector achieves 91.9% precision on test set), arXiv:2608.02464 (real-time detection + repair),
arXiv:2607.06503 (early abort probe cascade), arXiv:2606.29718 (context rot + premature termination),
arXiv:2606.10209 (context pruning = 79%→91.6% task completion). Production patterns: circuit breaker +
retry storm prevention (Portkey/Maxim 2026), async-first escalation design (DigitalApplied 2026).

Stall =/= slow. A session is stalled when it is consuming resources without making progress toward
its goal. A session is slow when it is making progress but taking a long time. The interventions
are different: stalled = stop + diagnose + restart; slow = wait or parallelize.

### Stall taxonomy (7 classes with Hermes-specific signals and recovery)

#### Class S1 — Infinite Agentic Loop (IAL)
Cause: unbounded feedback path. Tool call → observe → same/adjacent tool call → repeat. No
termination condition. arXiv:2607.01641 found 68 IAL failures in 47 of 6,549 real agent projects
(91.9% precision). IALs cause cost exhaustion, context growth, and repeated external side effects.

Signals (observable without tooling):
  - Same tool called 3+ times in one session with near-identical args
  - Semantic loop: different phrasing, same intent (paraphrase IAL; use normalized hash not exact match)
  - Turn count >15 without a concrete intermediate result
  - Tool outputs getting shorter / more error-like while calls continue
  - `same_tool_failure_halt` warning in logs (Hermes partial guard)
  - Note: agents rephrase around prompt-only loop guards (arXiv:2605.05846 LoopTrap tested on
    Grok-4, Claude 4.5, GPT-4o). External termination required, not just a "stop looping" instruction.

Recovery procedure:
  1. Interrupt: if noticing in real time, Ctrl+C or use `delegate_task(action='stop')`
  2. Restate: open a new session or sub-task with an explicit goal + exit condition
  3. Escalate model: if the loop was caused by bad tool-call generation (hallucinated args,
     wrong schema), escalate to Sonnet 5 or Opus 4.8 for the re-attempt
  4. Reduce tool set: disable tools not needed for the specific subtask; IALs often involve
     a model "reaching for" an available tool that doesn't actually apply

Prevention:
  - Every `delegate_task` prompt must include: explicit success criterion + max-turns hint
    ("stop after 10 tool calls if not complete; return what you have")
  - This is a SOFT hint in the prompt; Hermes has no hard max-turn enforcement. External kill
    via `delegate_task(action='stop')` is the only hard stop. Agents rephrase around prompt-only
    loop guards (arXiv:2605.05846 LoopTrap, tested Grok-4/Claude 4.5/GPT-4o).
  - Cron jobs: always set `--max-turns` or equivalent; never open-ended loops
  - IAL-Scan static check (arXiv:2607.01641): review any new agent workflow for feedback
    paths that can reach costly operations without an effective bound
  - NEVER retry with the full failed trajectory in context: arXiv:2605.08563 shows failed trace
    in context raises per-step error rate on the next attempt. Strip or summarize before retry.

#### Class S2 — Context rot / premature termination
Cause: context growth degrades model behavior well before the hard limit. arXiv:2606.29718
(Xia et al.): models exhibit premature termination — giving up or returning uncertain/wrong
answers early — at a rate positively correlated with context length.
  Chroma (2025): 30%+ accuracy drops for information in the middle of long conversations across 18 frontier models ("lost-in-the-middle" phenomenon; see also Liu et al. 2023 arXiv:2307.03172 for the original result; Chroma citation unverified in this session — treat as directional).
Agentic capabilities degrade at ~100k tokens even in models with 1-2M windows (arXiv:2512.02445
"When Refusals Fail", confirmed 2026-08-30). Safety and refusal behavior also become unstable.

Signals:
  - Responses growing shorter and more hedged as session length increases
  - Model starts saying "I'm not sure" about things it was confident about earlier
  - Tool calls shift from specific+targeted to vague+broad
  - Session token count crossing 80k (directional soft threshold; actual degradation onset varies 64k-128k by model)

Recovery procedure:
  1. Context pruning: ask model to summarize the session state to a compact checkpoint, then
     continue in a fresh session. arXiv:2606.10209: last-5-tool-calls + summary achieves
     91.6% task completion vs 71.0% full-history. Do NOT carry full history.
  2. Model escalation: Opus 4.8 is better calibrated at high context (4x less likely to pass
     flawed code; GraphWalks 1M: 68.1% vs GPT-5.5 45.4%). If context rot is suspected, a new
     Opus 4.8 session with the compact checkpoint beats continuing a degraded Sonnet session.
  3. Parallel sampling (arXiv:2606.29718): behavior-aware filtering of parallel samples gave
     2.6-4.9% gain. Approximate: if a result looks wrong, re-run the specific subtask with
     a fresh context rather than retrying in the same long session.

Prevention:
  - Compress tool responses aggressively: MCP/tool outputs should return only the fields
    the task actually needs, not full API payloads. arXiv:2606.10209 quantifies: verbose tool
    responses are the primary driver of context explosion in enterprise workflows.
  - Session hygiene: see hermes-context-hygiene skill. Do not accumulate tool outputs in
    context once they've been acted on.
  - Soft ceiling: treat 80k tokens as a soft warning threshold (directional; from ~100k confirmed
    degradation onset per arXiv:2512.02445; actual inflection varies 64k-128k by model and task type).
    After 80k, compress or checkpoint. Do not wait for 200k hard ceiling to act.
    Config note: compression.threshold_tokens: 120000 in config.yaml is a DEAD setting — the actual
    compression trigger is ratio-based (threshold: 0.35 of context_length: 200000 = ~70k tokens).
    The 80k skill warning is conservative relative to the ~70k actual trigger, which is fine.
    Verified 2026-08-30 against hermes-agent source (conversation_compression.py).
  - CRITICAL: use SCHEDULED compression (every 10-15 tool calls) not emergency compression.
    arXiv:2601.07190: scheduled compact = 22.7% savings; emergency compact = stall amplifier
    (fires under pressure when context is already degraded). Set up compression proactively.

#### Class S3 — Silent provider fallback
Cause: 400/422/402 from provider triggers Hermes fallback chain silently. Session continues
on wrong model; user receives output without knowing model switched.

Signals (from logs):
  - `grep "Fallback activated" ~/.hermes/logs/agent.log | tail -10`
  - Response latency inconsistent with expected model (Grok: 40s first token; Sonnet: 8-15s;
    if Grok-speed but Sonnet session, fallback happened)
  - Response style/verbosity inconsistent with session model
  - Confirmed Hermes-specific causes:
    * 422 `extra_forbidden`: Mistral + `reasoning_effort` set (fixed: compression on Haiku)
    * 400 tool call error: GPT-5.x via `custom:openai` (fixed: use `openai-api`)
    * 402 payment: Cerebras (removed from fallback chain)
    * 429 rate limit: SambaNova gpt-oss-120b (fallback to gemma-4-31B-it)

Recovery procedure:
  1. Check logs immediately: `grep -E "Fallback|Error [0-9]{3}" ~/.hermes/logs/agent.log | tail -20`
  2. Re-pin provider: `hermes chat -m <model> --provider <correct-provider> -q "..."`
  3. Verify model identity: the model itself generally knows what it is and will report correctly.
     The USER doesn't know a fallback happened — asking the model "what model are you?" is a
     quick sanity check. But the definitive check is the logs:
     `grep -E "model=|provider=" ~/.hermes/logs/agent.log | tail -5`
  4. If fallback was to a weaker model: re-run the affected steps explicitly on the correct model.

Prevention:
  - Never use `custom:openai` for GPT-5.x (hard rule, in critical pitfalls)
  - Cron LLM jobs: always pin `--model` and `--provider`; they do not inherit session defaults
  - Review fallback chain order: `hermes fallback list`; ensure only strong-enough fallbacks
    are in the chain
  - Set `reasoning_effort` only for providers that support it; never on Mistral aux models

#### Class S4 — Compression stall
Cause: context compression model fails repeatedly (422/timeout). Context accumulates.
Session grows toward context ceiling. Performance degrades (S2 compounds).

Signals:
  - Context token count climbing despite compression being configured
  - `grep "compression\|summarize\|extra_forbidden" ~/.hermes/logs/agent.log | tail -20`
  - Session feels slow; responses take longer as each turn carries a larger context

Recovery:
  1. Verify compression model: `hermes config get auxiliary.compression`
  2. Should be `claude-haiku-4-5` / `anthropic`. If Mistral: switch immediately.
  3. Do not add `reasoning_effort` to compression config — causes 422 on Mistral;
     Haiku handles it without the flag.
  4. If compression is failing despite correct model: manual compress — ask the session
     to produce a compact state summary, copy to new session.

Prevention:
  - Compression model is locked to Haiku (2026-08-29 fix). Do not change without testing.
  - Aux compression fallback chain: `haiku → gemma-4-31B-it (sambanova)`
    (mistral-large-latest removed 2026-08-30: returns 422 extra_forbidden on reasoning_effort)
    Verify: `hermes config get auxiliary.compression.fallback_chain`

#### Class S5 — Async delegation stall
Cause: `delegate_task` children have a hard wall-clock cap: `delegation.child_timeout_seconds: 900`
(config-verified 2026-08-30). After 900s (~15min) Hermes cuts the child. Parent session stall_timeout
is 1800s (gateway_timeout). Children can be killed mid-research at 900s — not indefinitely running.
Confirmed incident: deleg_95bfa999 completed usefully at 536s (well inside the 900s cap).
Prior skill note "no timeout" was incorrect — child_timeout IS active.

Signals:
  - Child transcript goes silent (no new lines for 3+ min) before the 900s cap
  - `delegate_task(action='list')` shows children still running
  - Child transcript shows same-tool-failure-halt or empty repeated tool calls:
    `tail -50 ~/.hermes/cache/delegation/live/<id>/task-N.log`

Recovery procedure:
  1. Monitor early: `delegate_task(action='list')` after ~5 minutes to check child progress
  2. Steer if drifting: `delegate_task(action='steer', subagent_id='sa-N-...', message='...')`
     Send a concrete redirect: "Stop retrying web_extract. Switch to web_search instead."
  3. Stop if stalled: `delegate_task(action='stop', subagent_id='sa-N-...')`
     Partial results are returned. A stopped child contributes its partial summary.
  4. Re-dispatch with narrower scope: smaller task + explicit tool strategy
  5. Do not dispatch open-ended "find anything useful" tasks. Every subtask needs:
     - Concrete deliverable
     - Fallback tool chain ("if web_extract fails, use web_search")
     - Implicit max scope ("search 3-5 sources, not exhaustive")

Prevention:
  - Include in every delegate_task prompt: fallback instructions + scope limit
  - For research tasks: "use web_search first; if a page fails to extract, skip it"
  - For code tasks: "attempt max 3 approaches; return what works"
  4. Monitor after 8+ min: check if transcript is advancing (making progress) vs stuck. See
     S5 decision tree: do not stop based on time alone; stop only if transcript shows no new
     progress for 3+ min, OR same-tool-failure-halt triggered.

#### Class S6 — Real-time failure detection (telemetry approach)
Research: arXiv:2608.02464 (Dubey, Aug 2026). Deterministic verification catches 60% of
failures at 0 false positives; with coverage check: 96% at 0 FP. Rollback + re-run lifts
task success 52% → 73% (~1 extra model call per run). Full statistical monitor not practical
in Hermes (no step-level ESN infrastructure), but deterministic verification IS practical.

Hermes-applicable patterns from arXiv:2608.02464:
  a) Completion check: after any multi-step task, verify the stated total/count matches
     what the tool calls actually returned. Trigger: when the task reports "done" OR when
     expected steps are complete (don't wait for a model self-report — check at the natural
     task boundary). Template: "You stated N files were updated. I count M confirmed writes. What happened?"
  b) Coverage check: confirm every required tool call was made. Trigger: after the final
     step of any task with a defined checklist. Template: "Task required [A, B, C]. Which of
     these was confirmed in this session?"
  c) Rollback + re-run: if check fails, do NOT append more instructions to the same session.
     Start a new session or sub-task for the failed step. 1 extra call, 45% recovery rate.

#### Class S7 — Doomed episode (early failure signal)
Research: arXiv:2607.06503 (Ruan et al., Jul 2026). Failure is often predictable from
the first 1-3 interaction rounds. Early abort saves 60% of tokens at 90% recall.
Behavior-only monitoring (which is all Hermes can observe) is weaker but still useful.

Hermes-applicable early-abort signals:
  - First tool call returns an error or empty result that the model doesn't recover from
    in 1-2 steps: abort + reframe the task
  - Model's first response shows confusion about the task scope ("I'm not sure what you
    mean by...") despite a clear prompt: abort + clarify + retry
  - After 3 tool calls, no concrete intermediate result exists: high doomed-episode signal;
    stop, restate goal explicitly, retry with a simpler first step
  - Model repeatedly generates tool calls that fail schema validation: escalate model tier
    immediately (not after 10 failures)

Prevention: write initial prompts defensively with explicit success criteria and a
"stop after N steps" instruction (this is a SOFT hint encoded in the prompt; Hermes has
no hard max-turn enforcement — if the model ignores it, the session continues). This matches
the recall-controlled cascade insight: keep successful episodes alive while aborting failing
ones early.

#### Class S8 — Reasoning / no-progress loop
Cause: agent looks busy (plans, searches, writes tests) but goal hasn't advanced. Circuit
breakers miss this — HTTP 200 + fluent text. arXiv:2608.06701 (LivePlan): named patterns include
action oscillation (self-loop edges), ad-hoc test scripts after failures, long unsuccessful
validation. arXiv:2607.00038: named terminal states (success/no-op/blocked/stalled/exhausted)
are needed to distinguish these from genuine progress.

Signals:
  - Workspace/todo/issue hash unchanged for N consecutive turns
  - Output similarity high (last K assistant messages look alike): output cosine/edit-distance
  - "Let me try one more search / let me also check X" after 10+ turns with no artifact delta
  - No new files written, no tests passing, no state change despite active tool calls

Recovery:
  1. Steer before kill: arXiv:2608.06701 shows checkpoint + corrective steer > kill-and-restart.
     Inject: "Stop planning. State the single next concrete action and do it."
  2. If steer fails: shrink tool set (remove the tool being over-used), escalate model
  3. Label terminal state explicitly: "this path is blocked; return what you have"
  4. On escalation: use the stronger model as JUDGE/ARBITRATOR rather than a retry worker.
     If you can produce 2+ candidate continuations cheaply (e.g. rerun the blocked step twice),
     have the larger model compare/arbitrate them (arXiv:2608.21027 COTA). For a single-thread
     stall with no candidates to compare, use the larger model to diagnose why the session
     is stuck and prescribe a specific next action — do NOT have it re-run the full task.

Prevention:
  - Structured progress tracking: before a long agentic task, define a progress criterion
    ("task is done when X test passes" or "when file Y exists with content Z").
    Check it after every 5 turns.
  - arXiv:2606.27009: halt on semantic plateau (progress metric flat), not only on fixed turn cap.
    Fixed max_iterations wastes tokens on easy tasks and truncates hard ones at the wrong moment.

#### Class S9 — Cron / scheduled silent stall
Cause: cron job "succeeds" (exits 0 or produces output) but performs no useful work. Or
never finishes, silently consuming time until next tick fires and overlaps. Production
pattern — no specific arXiv papers; nearest grounding is arXiv:2608.23628 (silent failures
and callability != operability) and arXiv:2607.00038 (named terminal states).

Signals:
  - Job exits without a declared terminal state (success/no-op/blocked)
  - Next cron tick fires while previous job is still running
  - Job duration wildly exceeds expected (check via `cronjob(action='list')`)
  - Output looks coherent but no external state changed

Recovery:
  1. Kill overlapping live run before starting the next tick
  2. Restart from a CLEAN checkpoint (not contaminated context); see arXiv:2603.20625 on
     idempotent resume — DART-SD (2608.18524) covers breakpoint repair more broadly
  3. Add an explicit terminal state declaration at end of every cron prompt:
     "End your response with exactly one of: STATUS:success, STATUS:no-op, STATUS:blocked"
  4. Monitor via `cronjob(action='list')` — check last-run status and duration

Prevention:
  - Overlap guard: cron prompts should begin with a check that the previous run completed
  - Named stop states in every cron prompt
  - Wall-clock SLA per tick; if exceeded, kill + alert

#### Class S10 — Token amplification loop (Clawdrain)
Cause: loop produces tokens that look like progress (new output each turn) but token/min
rate is unbounded and accelerating. arXiv:2603.00902 (Clawdrain): production runaway at
$108/h (specific source unverified; treat as directional order-of-magnitude). Infrastructure
circuit breakers miss this because HTTP calls succeed (200 OK) with non-empty responses.

Signals:
  - Token/min climbing vs session baseline (check session cost estimate if available)
  - Each response is longer than the last, not converging
  - Prompt size growing faster than tool outputs shrinking
  - Cost-per-turn increasing rather than decreasing toward task completion

Recovery:
  1. Kill the session; do not steer (steering produces more tokens)
  2. Diagnose: is each response genuinely new work or elaboration of prior outputs?
  3. Restart with an explicit conciseness constraint: "Return the minimum needed; stop expanding"
  4. Budget breaker: if Hermes exposes a token/cost ceiling, set it; otherwise monitor manually

Prevention:
  - Fingerprint gateway (production pattern; no single arXiv paper; closest: 2607.01641 IAL
    tool fingerprint + 2608.02464 real-time detection): hash(tool+args); 3+ identical → kill
  - Set explicit output length constraints in task prompts
  - Monitor cost/token rate for long-running sessions, not just turn count

#### Class S11 — Control primitive gap (documented-but-not-enforced)
Cause: timeout/cancel/interrupt signals are documented as existing but are not harness-enforced
at runtime. arXiv:2607.14166: control primitives don't actually stop agents mid-flight.
Explicit quit instructions help but are not substitutes for runtime kill (production
observation; specific benchmark paper unverified). AEGIS (arXiv:2603.12621): pause all
tools + LLM, poll HITL at intervals, fail closed after a wall-clock limit.

Signals:
  - You sent a stop/cancel signal but tools are still running
  - `delegate_task(action='stop')` returned but child transcript still growing
  - Cron kill command issued but process still active

Recovery:
  1. SIGTERM / process kill at the harness level (not a prompt)
  2. Drop all pending tool calls; no further LLM calls
  3. Fail closed: if HITL not available, treat as stall, terminate, log

Prevention:
  - Treat stop as harness-enforced, not prompt-enforced. Don't rely on the model to
    honor a "please stop" message in a running session.
  - Add explicit quit token/phrase to task prompts (helps model cooperate with external kill).
  - For cron and delegation: verify termination via log check, not just API return code.



### Escalation decision tree

Use this when a session shows stall signals. Run checks top-to-bottom; stop at first match.
Classify BEFORE acting — arXiv:2608.02464: blind retry amplifies cascade errors.

```
0. Token/min climbing? Output growing each turn with no convergence?
   YES → S10 (amplification loop). Kill immediately. Do not steer (produces more tokens).
          Restart with conciseness constraint. Fingerprint check.
   NO  → continue

1. Provider error in logs (400/422/429/402)?
   YES → S3 (silent fallback). Classify error FIRST:
          - 400/422 (bad request/schema) → fail-fast, NO retry (same args = same fail)
          - 402/403 (billing/auth) → NO retry (permanent until account action)
          - 429/5xx (rate limit/transient) → retry with exponential backoff + jitter
          Start a NEW session with --model and --provider flags pinned. No mid-session re-pin.
          NEVER "try another model blindly" on a 4xx — classify error class first.
   NO  → continue

2. Same tool called 3+ times with near-identical args (exact or semantic/paraphrased)?
   YES → S1 (IAL). Stop. Strip failed trace. Restate goal with exit condition.
          Escalate model if tool-call schema errors present.
          Agents rephrase around prompt-only guards — external kill is the only hard stop.
   NO  → continue

3. Context token count >80k (directional threshold) AND responses getting shorter/vaguer?
   YES → S2 (context rot). Compress to checkpoint (scheduled, not emergency).
          New session: Opus 4.8 if accuracy critical; Grok 4.6 if throughput critical.
          arXiv:2606.11213: do NOT silently evict user turns — surface the condition.
   NO  → continue

4. Context growing but compression enabled?
   YES → S4 (compression stall). Verify auxiliary.compression = claude-haiku-4-5/anthropic.
          If same compressor failed twice: skip compress, prune mechanically, continue.
   NO  → continue

5. Delegate_task batch not returning after 8+ min?
   YES → S5. Check transcript progress: is child making new tool calls / new artifacts?
          - Progress visible: wait (research tasks legitimately take 8-12 min)
          - No new I/O for 3+ min: steer, then stop. Return partial, parent continues.
          Do NOT use a fixed hash to detect progress — arXiv:2608.26225: fixed hash trips
          on 3rd round regardless of actual progress.
   NO  → continue

6. Workspace/todo hash unchanged N turns? Output similarity high?
   YES → S8 (reasoning loop). Steer first: "State the single next concrete action and do it."
          If steer fails: shrink tool set; escalate model as JUDGE (COTA, arXiv:2608.21027),
          not as retry worker. Halt on semantic plateau, not only on fixed turn cap.
   NO  → continue

7. Tool calls failing with invalid args, model retrying same params?
   YES → S7 (hallucinated params). After 2 identical fails: switch tool or escalate model.
          Never silent-retry invalid args.
   NO  → continue

8. Cron job silent / overrun / overlapping?
   YES → S9. Kill live run. Restart from clean checkpoint. Add terminal state to prompt.
   NO  → continue

9. First 3 tool calls (or 2 interaction rounds) failed or empty?
   YES → S7 early-abort signal. Abort. Reframe task. Retry with higher model.
          arXiv:2608.23628: 51% of operability failures occur in first 3 minutes.
   NO  → continue

10. Multi-step task complete but counts/coverage seem off?
    YES → S6 (completion failure). Run completion + coverage check. Rollback + re-run
           failed steps (not full task). 1 extra call, 45% recovery rate.
    NO  → Slow (not stalled). Continue. Add intermediate progress check.
```


### Model escalation on stall (not on task complexity)

Research finding (arXiv:2608.02464): rollback + re-run on correct model recovers 45% of failed
episodes. Escalation is a PROTOCOL with bounds, not "try a bigger model because stuck"
(arXiv:2604.11378): after K classified failures → one bounded escalate → then stop or human.

Critical distinction (arXiv:2608.21027 COTA): on stall, escalate model as JUDGE/ARBITRATOR
(compare/arbitrate competing traces), NOT as a retry worker. Having the big model re-run
the whole task is a retry storm with extra cost.

  Stall class → Escalation target (legal routes only; NEW session + handoff, never mid-session switch):
  S1 (IAL, schema errors)       → stay on sonnet_parent; shrink toolset. If still failing: opus_dedicated JUDGE, not retry worker.
  S2 (context rot, accuracy)    → opus_dedicated (session start / new session with handoff)
  S2 (context rot, throughput)  → sonnet_parent+grok_workers (delegation). NOT Grok-as-parent.
  S3 (provider error)           → re-pin correct provider; no model escalation needed
  S4 (compression)              → claude-haiku-4-5 for compression; no parent escalation
  S5 (async stall)              → re-dispatch with narrower scope on grok-4.6 workers
  S6 (completion failure)       → rollback + re-run on same model (1 extra call pattern)
  S7 (doomed early)             → gpt-5.6-luna for sanity check; sol for adversarial re-check
  S8 (reasoning loop)           → gpt-5.6-sol/luna as JUDGE (COTA), not retry worker
  S9 (cron silent)              → no escalation; fix checkpoint + terminal state
  S10 (amplification)           → kill; restart with constraint; no model upgrade needed
  S11 (control primitive)       → harness-level kill; no model escalation

Failure-mode-specific escalation (arXiv:2608.27455 CritICL, Aug 2026):
Do NOT escalate with a blank model switch. Diagnose the failure class first (using a cheap
small/fast model if needed), then inject a targeted critique into the strong model's context.
Weak-model failure-mode critiques outperform same-budget self-critique on the strong model.

Hermes pattern:
  1. Identify stall class (S1-S11) BEFORE switching model
  2. Construct a short failure-mode summary: "This is an S1 (IAL): tool X was called 4 times
     with identical args. Root cause: missing exit condition on the feedback path."
  3. Open a new session (or re-dispatch delegate_task); include the failure-mode summary in the
     OPENING PROMPT of the new session/task — not as a system note (no mid-session injection
     mechanism exists in Hermes; new session starts fresh)
  4. Have the new model continue from the stall point, not restart from scratch
  Benchmark: this beats generic 'try again with a bigger model' at equivalent cost.

Event-driven escalation (arXiv:2608.07637 Agent-MD): escalate on discrete events (422/400,
N-turn no-progress, compression fail, batch silence), not on task hardness alone.
Bayesian self-escalation (arXiv:2608.24087): agent detects mid-reasoning that it will fail
and transfers control before the episode is lost. Do NOT approximate this with an inline
1-10 self-score. Approximate only via observable events (fact inversion, schema/test
failure, N-turn no-progress, classified S1–S11 stall), then new-session JUDGE.

Circuit breaker (production pattern, Portkey/Maxim 2026):
  - After 3 consecutive provider errors of the same class: stop retrying; switch provider; log
  - Do not retry 402 (billing) or 403 (auth) — permanent until account action
  - Retry with jitter: 429/5xx only; backoff 2s, 4s, 8s + random jitter
  - 400/422 (bad request/schema): do not retry with same args; fix the call first

### Practical stall-prevention stack (research-aligned summary)

The full evidence-ordered stack from arXiv synthesis (arXiv:2608.02464, 2605.06455, 2511.03094,
2608.21027, 2604.11378):

  1. Cheap prefix monitor / fingerprint check (PrefixGuard 2605.06455, tool-call fingerprinting)
     → catches IAL and amplification before they're expensive
  2. Classify failure type before acting (2608.02464, 2608.23628, 2511.03094)
     → 400 != 429 != loop != drift. Wrong classification = retry storm.
  3. Loop guard + wall-clock timeout + idempotent checkpoint (ALAS 2511.03094)
     → versioned restore point; resume the failed region, not the whole graph
  4. ONE bounded MODEL ESCALATION (Bayesian 2608.24087, event-driven 2608.07637, COTA 2608.21027)
     → judge/arbitrate, don't re-run; K-failure budget per arXiv:2604.11378
     → note: one model escalation step is the bound — multiple cheap recovery attempts
       (steer, shrink toolset) before escalation are fine; those are not model switches
  5. Stop or human (AEGIS 2603.12621, fail closed after a wall-clock limit)
     → HITL with hard wall; do not leave stalled session running

  NEVER: silent fallback, same-query retry, bigger model keeps going,
         retry with contaminated context, fixed-hash progress detection.




