# Adjacent L0/L1 token-efficiency techniques (research sweep, 2026-09-11)

Scope: 10 gaps after CoD/Grice/budget-hint. For each: key finding, measured token effect (or lack), prompt-layer vs API/train.

Verdict legend: **adopt** / **try** / **skip** / **already covered**.

---

## 1. Self-consistency (majority vote) on L0/L1 — SKIP

**Finding.** Classic SC (Wang et al. 2022) samples N CoT paths and majority-votes. Later efficiency papers only make SC cheaper for *hard reasoning*, they do not make it useful for simple queries:

- RASC (Wan et al., arXiv:2408.17017, NAACL 2025): ~70% fewer samples vs naive SC, still multi-sample.
- Adaptive-Consistency (Aggarwal et al., arXiv:2305.14060): ~80% fewer samples than fixed-N SC via stopping when a majority is stable.
- ESC / early-stopping SC (Li et al., arXiv:2401.10480): ~33% sample cut.

**Cost-of-pass on L0/L1.** If single-sample accuracy is already high (typical for L0 factoids / L1 one-hop), extra samples multiply output tokens by N with near-zero accuracy gain. Cost-of-pass ≈ N × (tokens per sample). No 2025 paper shows SC helping *simple* questions.

**Implementable as prompt-layer?** No. Sampling-loop / decode-time. **Do not add SC to L0/L1.**

---

## 2. Prompt format (JSON vs markdown vs plain) — SKIP JSON for L0; prefer plain

**Finding.** Tam et al., “Let Me Speak Freely?” (arXiv:2408.02442, EMNLP 2024 Findings): constrained formats (JSON/XML) *hurt reasoning*; stricter schema → worse task scores. Wrapper tokens (`{}`, keys, quotes) add output length even when payload is short.

No 2025 paper gives a clean “JSON uses X% more tokens than plain on L0.” Direction is unambiguous: structure is overhead unless the *consumer* needs parseable fields.

**Token effect.** Unmeasured % for L0; expected *increase* (schema tokens) not decrease.

**Implementable as prompt-layer?** Yes (ask for plain / one line). **Keep L0/L1 as plain text. Do not route L0 through JSON mode for brevity.**

---

## 3. Few-shot selection for token efficiency (not accuracy) — TRY (shortest-correct, 2–3 shots)

**Finding.** Literature optimizes ICL *accuracy*, not example *token cost*:

- “The Few-Shot Dilemma” (arXiv:2604.06755, 2026): 2–3 shots often peak; more shots can *hurt*.
- Coverage/diversity selectors (e.g. similarity + diversity) exist for accuracy.
- No paper found that selects shots to *minimize output tokens*.

**Implication for CoD.** CoD already needs few-shots. Token-optimal policy is: fewest shots that still elicit draft style; pick *shortest correct* exemplars, not diverse long ones. Extra diversity shots are input-token tax.

**Token effect.** Input: each extra shot costs its full token length every L0/L1 turn. Output: unmeasured; 2–3 short CoD shots is the evidence-backed cap.

**Implementable as prompt-layer?** Yes. **Cap CoD at 2–3 shortest examples.**

---

## 4. System-prompt position (primacy/recency) — ADOPT (brevity at end + near user)

**Finding.**

- Lost-in-the-Middle (Liu et al., arXiv:2307.03172): U-shaped attention — start and end of context followed better than middle.
- Serial-position / instruction-position studies (e.g. arXiv:2412.15254 and follow-ons 2025): recency dominates instruction following; primacy helps if the instruction is not buried.
- “Found in the Middle” (arXiv:2408.00773): some models *can* use middle tokens, but not reliably for constraints.

**Token effect.** Not a reduction % — it is *compliance* of existing brevity rules. Misplaced “be concise” in the middle of a long system prompt is ignored.

**Implementable as prompt-layer?** Yes. **Put L0/L1 brevity block at the *end* of the system prompt (recency). Optionally echo a one-liner immediately before the user turn. Do not bury it in the middle of tool/skill dumps.**

---

## 5. Temperature / sampling vs output length — TRY T≈0 for L0 (API, not prompt)

**Finding.** No 2025 paper with a clean “Δtokens vs T on simple questions” table.

- Atil et al. (arXiv:2408.04667, 2025): even T=0 is not string-deterministic; output *length* still varies; they correlate instability with output length.
- Higher T flattens the distribution → more exploration, typically longer/more rambling text (industry consensus; not a measured L0 %).
- EfficientRollout / RL papers are about training rollouts, not L0 chat.

**Token effect.** Unmeasured %. Direction: lower T → shorter, more peaked answers on L0.

**Implementable as prompt-layer?** No. **API sampling: T=0 (or 0.1) + low top_p for L0/L1.** Prompt “be concise” does not substitute for T.

---

## 6. Stop sequences to cap L0 length — ADOPT (API, cheap)

**Finding.** Decode-time stop is the standard way to cut *excess* generation without budget-hint tricks.

- CodeFast / “When to Stop?” (Guo et al., arXiv:2407.20042): excess-token generation after the useful span; early stop 34–452% faster on code, quality held.
- Provider `stop` / `max_tokens` are first-class; not researched as a 2025 “L0 chat” paper because they are already product features.

**Token effect.** Hard cap: tokens after the stop string are never generated. For L0, `max_tokens` of ~64–128 plus stop on `\n\n` or a sentinel is a hard ceiling.

**Implementable as prompt-layer?** Partial: you can *ask* for a sentinel (`END`), but the real win is API `stop` + `max_tokens`. **Add L0 max_tokens + stop on blank line / sentinel. Not a substitute for CoD, a backstop.**

---

## 7. JSON mode for verbosity reduction — SKIP (same as #2)

**Finding.** Forced JSON does not make answers *less verbose*; it wraps them. Tam et al. 2408.02442: format restriction degrades reasoning and adds schema tokens. Verbosity Compensation (Zhang et al., arXiv:2411.07858) is about *uncertainty padding*, not format.

**Token effect.** Expected *increase* (keys/braces/quotes). No paper shows JSON *reducing* L0 verbosity.

**Implementable as prompt-layer?** Yes, but **do not**. JSON mode is for tools/APIs, not L0 chat.

---

## 8. Negative / contrastive examples (verbose vs terse) — TRY (1 pair, keep short)

**Finding.** Contrastive ICL is validated for *accuracy*, not token count:

- Contrastive CoT (Chia et al., arXiv:2311.09277): valid + invalid reasoning demos reduce reasoning errors.
- LEAP (Zhang et al., arXiv:2402.05403): induce mistakes, distill principles, then answer — extra *input* tokens, accuracy gains (e.g. +7.5% DROP on GPT-4).

No paper measures “verbose BAD / terse GOOD” few-shots cutting output tokens. Mechanism is plausible (contrastive CoD). Risk: negative examples *teach the bad style* if unlabeled, and they cost input tokens every turn.

**Token effect.** Unmeasured output savings. Input cost = one extra (verbose) shot.

**Implementable as prompt-layer?** Yes. **One labeled pair: `BAD (verbose): …` / `GOOD (terse): …`. Do not dump many negatives. A/B vs current CoD shots.**

---

## 9. Implicit vs explicit length control — ADOPT explicit for L0

**Finding.**

- LIFEBench (Zhang et al., arXiv:2505.16234, 2025): 26 LLMs, 10.8k items, 16–8192 word targets. Models follow *short* length instructions reasonably; collapse on long targets. “Be concise” is weaker than a numeric/unit constraint. Reasoning models follow length better than long-text specialists.
- Precise Length Control (Butcher et al., arXiv:2412.11937): LDPE fine-tune, mean error <3 tokens — **training**, not prompt.
- Industry/prompting consensus (aligned with LIFEBench short-range): “in one sentence” / “≤20 words” beats “be concise”.

**Token effect.** LIFEBench: short explicit caps are *followed*; implicit brevity is not quantified as a %. For L0, explicit “one sentence” / “≤N words” is the compliance lever.

**Implementable as prompt-layer?** Yes. **Prefer `Answer in one sentence.` / `≤20 words.` over `Be concise.` Keep Grice as style; add an explicit unit cap on L0.**

---

## 10. Multi-turn verbosity drift — ADOPT re-inject brevity each turn

**Finding.**

- Multi-turn instruction following degrades (e.g. Multi-Turn Puzzles, arXiv:2509.14004; MT-Eval / MT-Bench literature): later turns lose constraints.
- Verbosity Compensation (Zhang et al., arXiv:2411.07858): VC is pervasive (GPT-4 VC frequency 50.40%); verbose vs concise accuracy gap 27.61% on Qasper; verbosity tracks *uncertainty*, not truth. Cascade replacement cut Mistral VC 63.81% → 16.16% on Qasper.
- No paper titled “verbosity drift over chat turns” with a token-growth curve. Combined evidence: constraints fade + uncertainty → padding.

**Token effect.** VC paper: large *frequency* of padding, not a per-turn token slope. Prevention is re-stating the cap, not hoping the system prompt persists.

**Implementable as prompt-layer?** Yes. **Re-attach a 1-line L0/L1 cap on every user turn (or every N turns). Do not rely on a single system-prompt Grice block for long sessions. Optional: if the model hedges/enumerates, treat as VC and tighten the cap.**

---

## Implementation ranking for Hermes L0/L1

| Pri | Change | Layer | Evidence |
|-----|--------|-------|----------|
| 1 | Explicit unit cap (`one sentence` / `≤N words`) | prompt | LIFEBench |
| 2 | Brevity block at **end** of system prompt + echo before user | prompt | lost-in-middle / recency |
| 3 | Re-inject cap every turn | prompt | multi-turn IF + VC |
| 4 | `max_tokens` + stop (`\n\n` / sentinel) on L0 | API | CodeFast + provider stop |
| 5 | T≈0 for L0/L1 | API | sampling physics; Atil 2025 |
| 6 | CoD shots: 2–3 shortest, not diverse | prompt | Few-Shot Dilemma |
| 7 | One BAD/GOOD verbosity pair | prompt | Contrastive CoT / LEAP (proxy) |
| — | Self-consistency / JSON mode / more shots | — | **skip** |

Already in skill (do not duplicate): CoD prefix, Grice block, budget-hint, query-gate.

---

## Sources (primary)

| ID | Paper |
|----|--------|
| 2408.17017 | RASC, NAACL 2025 |
| 2305.14060 | Adaptive-Consistency |
| 2401.10480 | ESC |
| 2408.02442 | Let Me Speak Freely? (format vs reasoning) |
| 2604.06755 | The Few-Shot Dilemma |
| 2307.03172 | Lost in the Middle |
| 2408.00773 | Found in the Middle |
| 2412.15254 | serial position / instruction position |
| 2408.04667 | Non-determinism of “deterministic” settings |
| 2407.20042 | When to Stop? / CodeFast |
| 2311.09277 | Contrastive CoT |
| 2402.05403 | LEAP |
| 2505.16234 | LIFEBench |
| 2412.11937 | Precise Length Control (LDPE; train-time) |
| 2411.07858 | Verbosity ≠ Veracity (VC) |
| 2509.14004 | Multi-Turn Puzzles |

Gaps with **no direct 2025 measurement**: T→token count on L0; few-shot *token* (not accuracy) selection; JSON verbosity reduction; labeled anti-verbosity contrastive shots; per-turn verbosity growth curve.
