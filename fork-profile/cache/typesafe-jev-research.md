TypeSafe AI / Jev Research Notes - Sep 18, 2026
Sources: typesafe.ai, docs.typesafe.ai, HN, backnotprop.com critique, mini-jev GitHub

WHAT IT IS
----------
TypeSafe AI (SF, ~25 employees, funded) launched Sep 15 2026.
CEO: Diogo Almeida - co-invented InstructGPT/RLHF at OpenAI
CTO: Erik Gafni - repeat founder
COO: Sasha Sheng - ex-Meta/FAIR
Team from OpenAI, Google Brain, Meta/FAIR, Stripe, Airbnb

Jev = their first "System One Model" - named after William Stanley Jevons
(Jevons paradox: efficiency -> increased demand, not decreased)

CORE THESIS
-----------
RLHF optimizes for human preference -> chatbots.
RLVR optimizes for verifiable rewards -> reasoning models (o1, o3).
RLCD (Reinforcement Learning for Calibrated Decisions) -> structured typed decisions with probabilities.

The claim: 99% of AI automation will be machine-to-machine, not human-chat.
Current LLMs are "horseless carriages" - text models kludged into automation.
System One models are native to software pipelines.

HOW JEV WORKS
-------------
Architecture: NOT a token-generation model. Parallel sampler, not autoregressive.
Outputs: typed decisions, not strings
Training: RLCD - optimizes calibrated probabilities (like proper scoring rules)

Three primitives:
1. Choice: pick one from a list -> {choice, probabilities, confidence}
2. Score: rate on ordered rubric -> {score, probabilities, confidence}
3. Noul: yes/no probability 0-1 -> {noul value}

All questions in one API call evaluated in parallel and independently.
"Context rot" avoided: questions don't share context, evaluated against same state.

Speed: 70-500ms (vs 3-329 seconds for frontier LLMs)
Cost: $0.042/MTok input, output tokens FREE (vs $0.20-$10/MTok for LLMs)
Type-safe: zero hallucinations by construction (constrained output space)

Claims (from launch blog):
- 193.6x faster than LLMs on workflow benchmarks
- 444.6x cheaper
- Zero type errors (mathematically guaranteed - output space is constrained)

Calibration: "A model is calibrated if P(correct | confidence=X) ≈ X"
So a 0.8 confidence answer should be right ~80% of the time, across many queries.

WORKFLOW DESIGN PHILOSOPHY
--------------------------
"Speculative fan-out" pattern: ask ALL questions in one call, ignore irrelevant ones.
No serial chaining. No round trips. Cost of extra questions ~= $0.

"Confidence-gated routing": 
  High confidence -> act autonomously
  Medium -> flag for review
  Low -> route to human or reasoning LLM

"Composite scoring": decompose broad judgments into atomic scores, combine in code.
"Intent routing": classify then route to handler.

Key principle: keep deterministic logic in code; use AI only for semantic judgment.
"Smart if-statements" / neuro-symbolic AI via pragmatic engineering.

BENCHMARKS
----------
Their own "workflow evals" - not public benchmarks (deliberate choice).
Uses average of GPT-6 Astra + Fable 5.1 as reference answers.
4 workflows, all in-house (acknowledged bias risk).
On contested spots: Jev on the Pareto frontier for intelligence vs cost.

INDEPENDENT CRITIQUE (Mike Ramos, backnotprop.com - "Jev is the fish at the poker table")
----------
Ran poker hand evaluation (Texas Hold'em) against a solver (TexasSolver).
Results:
- On easy spots: 63% agreement with solver's top action
- On contested spots: 38% (compared to "check if legal, else call": 24%)
- Jev bets when its own hand is good, checks when not - ignores game theory optimal play
- Showed Jev the opponent's exact flush cards -> still shoved all-in 60% of runs
- Only changed when state named the conclusion ("hero is behind" "hero has 0 outs")
  i.e., it can't infer strategic poker reasoning; it needs you to compute first

Haiku 4.5 (thinking off) handled the same spot correctly (checked the nuts).
Decomposed multi-question approach (6 judgments + code): slightly better but still under solver.

Conclusion: needs thorough domain-specific evaluation before production use.
No public standard benchmarks published by TypeSafe.

COMMUNITY RESPONSE (Sep 15-18 2026)
-------------------------------------
- #1 HN with 1,866 points, 491 comments
- 250,000+ waitlist signups in 48 hours
- 40K Discord members
- 30M views on launch video (X/Twitter)
- X following: 60 -> 50K+ in 24 hours
- CEO of Vercel + Box tweeting about it
- Forbes exclusive
- Open source clones appeared within 48h (mini-jev on Qwen3-4B, open-alternative-jev)

MINI-JEV FINDINGS (r-ms/mini-jev, empirical study on Qwen3-4B)
---------------------------------------------------------------
Key question: how much of this can a frozen model already do?

Method: read next-token logits at answer position instead of generating JSON.
Results:
- Accuracy loss vs JSON grammar: -0.22pp (negligible, CI covers zero) 
- Speed: 4x faster on short texts, 1.4-2.4x faster on long with KV cache
- Reading option letters outperforms writing option names by +10pp
- Weakness: out-of-scope detection and dependent fields

Critical finding about probabilities: with bounded enum, reading logits gives 
better-calibrated probabilities than asking model to write them (the TypeSafe adapter).
Mini-jev reproduces core behavior without specialized RLCD training.

LEGAL NOTE
----------
User used phrase "legal system one" - that was a parsing error. TypeSafe AI
is NOT specifically a legal AI company. "System One" is the model class name
(from Kahneman's Thinking Fast & Slow). They target general enterprise automation,
not legal specifically. Some HN users tried it for contract review, support triage,
spam classification, financial routing.

ACADEMIC GROUNDING
------------------
No public paper for RLCD yet. But connects to:
- Calibration literature: Guo et al. 2017 (temperature scaling), proper scoring rules
- RLHF: Christiano et al. 2017, Stiennon et al. 2020 (Almeida co-authored InstructGPT)
- Structured prediction / constrained decoding: token-level constrained generation
- Kahneman System 1/2 framework as conceptual framing
- Jevons Paradox (economics) for demand growth thesis

HOW IT COMPARES TO EXISTING HERMES PATTERNS
---------------------------------------------
Relevant existing patterns in Hermes:
- confidence-gated routing -> already in hermes-shadow-evaluation (shadow path never raises)
- atomic decomposed questions -> some similarity to multi-agent fan-out
- calibration scoring -> hermes consistency sampling is similar but uncalibrated
- typed decisions -> tool outputs are typed but not probability-annotated

