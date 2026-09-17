---
name: l01-token-efficiency
description: Use for L0/L1 short queries. CoD+Grice+budget fix.
version: 1.0.0
author: Hermes
tags: [token-efficiency, l0, l1, chain-of-draft, verbosity, grice, budget]
triggers:
  - Short conversational query needs to be answered cheaply
  - Simple factual, yes/no, arithmetic, or code-snippet query
  - Noticing verbosity or padding in a generated response
  - Wanting to reduce output tokens without losing accuracy
  - Correcting RLHF verbosity bias on a simple answer
  - Applying Gricean Quantity maxim to a response
  - Generating a CoD (Chain of Draft) prompt for light reasoning
related_skills:
  - adaptive-agent-reasoning
  - hermes-context-budgeting
  - metacognition
---

# L0/L1 Token Efficiency

Research-grounded protocol for making short discrete conversational queries
cheaper and more accurate. Prevents two failure modes specific to simple queries:

  - Verbosity bias: RLHF padding, hedge pileups, unnecessary CoT (arXiv:2411.07858)
  - Over-reasoning: thinking tokens on L0/L1 add cost and can *reduce* accuracy
    (arXiv:2506.06941 Illusion of Thinking; arXiv:2502.12215 Overthinking)

NOT a substitute for adaptive-agent-reasoning at L2/L3. Handles the 95%+ of
live traffic that should not CoT (arXiv:2505.11896 AdaCoT: CoT on 3.18% traffic).

Key research sources:
  Chain of Draft (CoD)    arXiv:2502.18600  -- ~80% output-token cut vs CoT on Claude
  TALE token budgets      arXiv:2412.18547  -- -67% tokens, <3% acc drop
  Illusion of Thinking    arXiv:2506.06941  -- easy: standard > LRM; extra think hurts
  Gricean norms           arXiv:2503.14484  -- pragmatic minimal informative replies
  Verbosity != Veracity   arXiv:2411.07858  -- length is confidence leak not quality
  Compact constraints     arXiv:2604.07192  -- -71% constraint tokens, CSR unchanged
  When to Reason router   arXiv:2510.08731  -- -48.5% tokens via cheap deterministic gate
  AdaCoT production       arXiv:2505.11896  -- CoT on 3.18% traffic, -69% response tokens
  Shannon H(A|Q)          theory            -- optimal answer ~= conditional entropy bits

Wave-2 (citation sweep + multilingual + practitioner + adjacent, Sep 2026):
  Sketch-of-Thought (SoT) arXiv:2503.05179  -- task-typed shorthand; up to 84% fewer tokens
    Conceptual Chaining -- A->B->C for causal/multi-hop; Chunked Symbolism -- equations for math
    Expert Lexicons -- domain jargon for technical queries
  CAC-CoT connector list  EMNLP 2025        -- so/therefore/hence whitelist, ~1/3 CoT tokens
  NoWait filler suppress  arXiv:2506.08343  -- ban Wait/Hmm/reconsider; 27-51% shorter
  LIFEBench unit cap      arXiv:2505.16234  -- 'in one sentence' > 'be concise'; goes LAST
  Contrastive CoD (LEAP)  accuracy lit      -- BAD+GOOD pair improves instruction following
  Code draft profile      arXiv:2506.10987  -- 5-word CoD wrong for code; ops+identifiers
  Reason Wide skill       arXiv:2608.07885  -- NL skill injection; 2.7-6x fewer out-tokens
  Multi-turn re-inject    arXiv:2411.07858  -- VC 50.4%: brevity drifts without per-turn
  Step budget (3-5)       practitioner      -- bounded steps beats open or 20-step CoT
  MCQ/System-1 gate       r/LocalLLaMA      -- CoD degrades on MCQ; use direct L0

---

## Core Decision Rule

Before answering ANY short query, run the query gate (1ms, no LLM):

  python3 ~/.hermes/scripts/l01-efficiency.py query-gate --query "QUERY"

Output: query_type, recommended_level, strategy, sketch_type, api_hints.

  L0 direct       -> No CoT; Gricean Quantity; unit cap at end; max_tokens+stop_seq
  L1 cod          -> CoD + CAC connector + NoWait + step budget + unit cap
  L1 sot_symbolic -> Chunked Symbolism (math) -- beats 5-word CoD on arithmetic
  L1 sot_chain    -> Conceptual Chaining (causal/why/multi-hop)
  L1 code_draft   -> Code draft profile -- NO 5-word cap; ops+identifiers preserved
  L2/L3           -> NOT this skill. Load adaptive-agent-reasoning.

  MCQ queries -> always L0 direct; CoD degrades on System-1/MCQ (r/LocalLLaMA)

---

## L0 Protocol (factual_lookup, yes_no, enumeration, conversion, greeting, mcq)

Get the system-prompt prefix:

  python3 ~/.hermes/scripts/l01-efficiency.py prompt --query "QUERY"

What this does (wave-1+2):
  - Disables CoT (Answer directly and concisely)
  - Applies Gricean Quantity (no preamble/padding)
  - Applies anti-verbosity suffix (blocks filler sign-offs)
  - Adds NoWait (no filler opener "Certainly!")
  - Unit cap placed at END of system prompt (recency effect; arXiv:2505.16234)
  - api_hints: max_tokens + stop_sequences=["\n\n", "---"] (CodeFast arXiv:2407.20042)
  - Targets Shannon H(A|Q): shortest string that uniquely identifies the answer

Expected effect:
  - Output: 1-30 tokens vs 500-4k with thinking on (arXiv:2507.02076 Table 2)
  - Accuracy: neutral or better (direct > CoT on simple items per arXiv:2506.06941)
  - No skill blocks on L0 (stable cached prefix only; don't dump skill content)

---

## L1 Protocol (math, code, date, instruction_how, comparison_simple, causal_chain)

Use the all-in-one builder (recommended -- all wave-2 techniques composed automatically):

  python3 ~/.hermes/scripts/l01-efficiency.py prompt --query "QUERY" [--steps N]

  Returns: system_prompt_prefix + api_hints (max_tokens, stop_sequences).
  Composition order: reasoning style -> CAC connector -> NoWait -> step budget ->
    Gricean weak -> anti-verbosity -> unit cap (LAST).

Or compose manually:

  Reasoning style (auto-selected by strategy from query-gate):
    sot_symbolic  -> sot-prefix --sketch symbolic     (math_arithmetic)
    sot_chain     -> sot-prefix --sketch conceptual   (causal_chain)
    code_draft    -> code-draft                       (code_snippet, code_fix)
    cod (default) -> cod-prefix --domain DOMAIN       (all other L1)

  Then add in order:
    noWait-block          (27-51% shorter; arXiv:2506.08343)
    step-budget --steps N (3 for arithmetic, 4-5 for word problems)
    unit-cap --query Q    (LAST; arXiv:2505.16234)

  Optional (high-verbosity contexts):
    contrastive-cod --domain D   (~80 input tokens; pre-pend before few-shot)
    skill-amortize --domain D --summary TEXT   (repeated-domain batches)

  API params from api_hints field:
    max_tokens: budget + headroom
    stop_sequences: ["####\n\n"]

Expected effect:
  - CoD: ~80% output-token cut vs CoT (arXiv:2502.18600, Claude 3.5 Sonnet)
  - SoT: up to 84% cut vs CoT (arXiv:2503.05179)
  - NoWait: additional 27-51% on CoD/SoT traces (arXiv:2506.08343)
  - Token elasticity: budget < 50 -> more tokens. Min enforced at 50.
  - GSM8K accuracy: CoD -4.4pp vs CoT (acceptable for L1). Sports/date: improves.

---

## Verbosity Correction (any level)

If a generated response looks padded or over-hedged:

  python3 ~/.hermes/scripts/l01-efficiency.py verbosity-fix --text "RESPONSE"

  Score > 0.4 -> over-threshold. Use correction_prompt to instruct a rewrite.
  Score > 0.2 -> minor; trim manually.

Markers detected: filler openers (Certainly!), question restating,
sign-off phrases (I hope this helps), hedge pileups, verbosity compensation.

Theory: length is a confidence leak (arXiv:2411.07858). Correct answers are
often shorter than wrong ones (arXiv:2606.30128). Never use length as quality.

---

## Gricean Quantity Block (any level)

  python3 ~/.hermes/scripts/l01-efficiency.py grice-block --strength [weak|medium|strong]

  weak:   single line for L0 appending
  medium: 2-line block (default)
  strong: 5-line maxims block for repeated verbosity violators

Source: arXiv:2503.14484, arXiv:2608.13484 (Gricean retreat: uncertain speaker
should despecify, not hedge at length. "I don't know" < long hedge.)

---

## Anti-Patterns (Do NOT do these for L0/L1)

  NEVER use a second LLM call to classify think vs no-think.
  NEVER inject skill blocks on L0 queries.
  NEVER use LLMLingua on short queries (<200 tokens input).
  NEVER set reasoning budget below 50 tokens (elasticity backfire).
  NEVER add self-critique loops on simple answers.
  NEVER use extended thinking for L0/L1.
  NEVER use 5-word CoD on code_snippet/code_fix -- use code-draft.
  NEVER use CoD on MCQ -- use direct L0 answer.
  NEVER rely on one-time system prompt for multi-turn brevity -- re-inject per turn.
  NEVER place unit cap at start of system prompt -- goes LAST (recency effect).
  NEVER use self-consistency on L0/L1 (N x cost; only helps hard reasoning).

---

## Stable Prefix Rule (KV-cache efficiency)

  Keep a byte-stable system prefix. Never shuffle injected skills per turn.
  Put volatile routing (L0/L1 flags, query-specific prompts) AFTER the cached prefix.
  Anthropic prompt caching fires when the prefix is identical across turns.

---

## Information-Theoretic Grounding

Target for L0 answers: H(A|Q) -- the conditional entropy of the answer given
the query. For entity/yes-no/time answers: typically 1-20 bits (1-8 tokens).
Everything beyond is RLHF padding or style.

  - Simple fact: optimal response = shortest string uniquely identifying answer.
  - Uncertain: Grice Quality -> shorter claim, not longer hedge (arXiv:2608.13484).
  - Length != effort: deep-thinking token *ratio* correlates with accuracy;
    raw length does not (arXiv:2602.13517).

---

## Quick Command Reference

Wave-1:
  query-gate    --query Q          -> L0/L1/L2, strategy, sketch_type, api_hints
  prompt        --query Q [--steps N] -> full system_prompt_prefix (wave-2 composed)
  cod-prefix    --domain D         -> CoD few-shot prefix (non-code L1)
  budget-hint   --query Q          -> TALE P80 budget
  verbosity-fix --text T           -> score + correction prompt
  grice-block   --strength S       -> Gricean Quantity block

Wave-2 (new):
  sot-prefix    --sketch S         -> Sketch-of-Thought (conceptual|symbolic|lexicon)
  unit-cap      --query Q          -> explicit unit cap (place at END of system prompt)
  noWait-block                     -> filler token suppression (Wait/Hmm/reconsider)
  step-budget   --steps N          -> step-count budget (3 for arithmetic, 4-5 for L1)
  contrastive-cod --domain D       -> BAD+GOOD pair (pre-pend before few-shot)
  code-draft                       -> code draft profile (not 5-word CoD)
  skill-amortize --domain D --summary TEXT -> Reason-Wide NL skill injection
  multi-turn-reminder              -> per-turn brevity re-injection (inject in HUMAN turn)

All commands emit JSON stdout. Exit 0 on success.

---

## Pitfalls

  Zero-shot CoD collapses on Claude: always include few-shot examples.
  Micro-budgets backfire: P80 per domain (min 50); never hard-cap.
  Verbosity score is pattern-based: false-negatives on novel padding. Trust directionally.
  query-gate misclassifies ambiguous queries (returns unknown): escalate to classifier.
  Shannon floor is ~1-8 tokens for facts; prompt tricks plateau at ~15-50 tokens.
    Closing further requires RL training.
  SoT input overhead (longer shots) vs CoD: SoT wins on batches, CoD fine for one-offs.
  CAC connector whitelist adds ~20 input tokens but saves ~65% output tokens. Net positive.
  Step budget and TALE budget conflict: use one or the other. Step budget simpler for non-math.
  Contrastive CoD adds ~80 input tokens: only when verbosity score repeatedly high.
  multi-turn-reminder: inject in HUMAN turn, not system prompt (system is cached/stable).
  code-draft: still applies Gricean Quantity and unit cap; only removes 5-word step constraint.
