#!/usr/bin/env python3
"""
l01-efficiency.py — Token-efficiency layer for Hermes L0/L1 conversational queries.

Research basis (wave 1 — English arXiv):
  Chain of Draft (CoD)          arXiv:2502.18600  — ~80% output-token reduction vs CoT
  TALE token budgets            arXiv:2412.18547  — -67% tokens, <3% acc drop
  AdaptThink NoThinking         arXiv:2505.13417  — skip-think wins on easy tasks
  Illusion of Thinking          arXiv:2506.06941  — easy: standard LLM > LRM
  Gricean Quantity maxim        arXiv:2503.14484  — pragmatic minimal informative replies
  Verbosity != Veracity         arXiv:2411.07858  — length is confidence leak, not quality
  Compact Constraint Encoding   arXiv:2604.07192  — -71% constraint tokens, CSR unchanged
  When to Reason router         arXiv:2510.08731  — -48.5% tokens via cheap gate
  Overthinking survey           arXiv:2502.12215  — extra revision hurts on easy items

Research basis (wave 2 — citation sweep + multilingual + practitioner + adjacent):
  Sketch-of-Thought (SoT)       arXiv:2503.05179  — task-typed shorthand, up to 84% fewer tokens
  CAC-CoT connector whitelist   EMNLP 2025 Findings arXiv:2409.xxxx — ~1/3 CoT tokens via "so/therefore/..."
  NoWait filler suppression     arXiv:2506.08343  — ban Wait/Hmm/reconsider → 27-51% shorter
  AdvPrompt / CROP brevity      arXiv:2510.10528, arXiv:2604.14214 — persuasive instruction search
  CodeFast stop+max_tokens      arXiv:2407.20042  — 34-452% less token excess on code
  Reason Wide, not Deep         arXiv:2608.07885  — compact NL skill injects 2.7-6x fewer output tokens
  CoD negative for code         arXiv:2506.10987  — 5-word CoD wrong for code; 55% not 7.6%
  Contrastive CoT (LEAP)        arXiv (accuracy lit) — BAD+GOOD pair in few-shot, unmeasured token savings
  LIFEBench explicit length     arXiv:2505.16234  — "in one sentence / ≤N words" beats "be concise"
  Verbosity Compensation (VC)   arXiv:2411.07858  — re-inject brevity every turn, GPT-4 VC 50.4%
  MCQ/System-1 gate             r/LocalLLaMA 2025 — skip CoD on MCQ/factoid; CoD hurts System-1
  Step budget (3-5)             HN + practitioner — bounded steps beats open CoT or 20-step Reddit
  Qwen3 no-think mode           Qwen3 TR 2505.09388 — /no_think / enable_thinking=False for L0
  Primacy/recency position      lost-in-middle lit — put brevity at END of system prompt
  max_tokens + stop seq         CodeFast 2407.20042 — \n\n stop + max_tokens on L0

Theoretical basis:
  Shannon H(A|Q)  — optimal answer length ≈ conditional entropy of answer given query
  MDL             — stop when extra tokens don't reduce answer entropy (arXiv:2602.14002)
  Grice Quantity  — say exactly as much as required; no more, no less
  K_theta(A|Q)   — LLM-relative Kolmogorov: best proxy is -log p(A|Q) not char length

Commands:
  query-gate      --query "..."                    Classify query type + recommend approach
  prompt          --query "..." [--level L0|L1]    Emit system-prompt prefix for the query
  cod-prefix      [--domain math|factual|code|date|sports|logic|general]
                                                   Emit Chain-of-Draft few-shot prefix
  sot-prefix      [--sketch conceptual|symbolic|lexicon|auto]
                                                   Emit Sketch-of-Thought prefix (wave 2)
  budget-hint     --query "..." [--level L1]       Emit TALE-style token budget instruction
  verbosity-fix   --text "..."                     Score verbosity and emit correction prompt
  grice-block     [--strength weak|medium|strong]  Emit Gricean Quantity prompt block
  unit-cap        --query "..."                    Emit explicit unit-length cap instruction
  noWait-block                                     Emit filler-token suppression block
  step-budget     [--steps N]                      Emit step-count budget (default 4)
  contrastive-cod --domain DOMAIN                  Emit BAD+GOOD contrastive CoD pair
  code-draft      --query "..."                    Emit code-specific draft profile (not 5-word)
  skill-amortize  --domain DOMAIN --summary TEXT   Emit Reason-Wide skill injection block
  multi-turn-reminder                              Emit per-turn brevity re-injection block

Exit codes:
  0  success (JSON output)
  1  bad args or domain error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

HERMES_HOME = Path.home() / ".hermes"
COD_EXAMPLES_PATH = HERMES_HOME / "scripts" / "l01-cod-examples.json"

# ─── Query type taxonomy (cheap deterministic gate, no LLM call) ──────────────

QUERY_TYPES = {
    # Type → (description, recommended_level, reasoning_strategy, max_output_tokens)
    "factual_lookup":   ("Single-fact retrieval, definition, or named entity",  "L0", "direct",      30),
    "yes_no":           ("Binary/boolean answer",                                "L0", "direct",      15),
    "enumeration":      ("List of items with no synthesis",                      "L0", "direct",      80),
    "conversion":       ("Unit/format/type conversion",                          "L0", "direct",      20),
    "greeting":         ("Social/conversational opener",                         "L0", "direct",      30),
    "clarification":    ("User asking about previous answer",                    "L0", "direct",      60),
    "mcq":              ("Multiple-choice question; direct selection",           "L0", "direct",      10),
    "math_arithmetic":  ("Arithmetic without word problem ambiguity",            "L1", "sot_symbolic", 60),
    "math_word":        ("Word problem requiring intermediate steps",            "L1", "cod",        100),
    "date_time":        ("Date/time calculation or scheduling",                  "L1", "cod",         60),
    "code_snippet":     ("Generating a short function/snippet (<50 lines)",      "L1", "code_draft", 300),
    "code_fix":         ("Fixing a clear bug in provided code",                  "L1", "code_draft", 200),
    "sports_logic":     ("Sports knowledge with light inference",                "L1", "cod",         60),
    "summarize_short":  ("Summarizing <500 word input",                          "L1", "cod",        120),
    "instruction_how":  ("How-to question with known procedure",                 "L1", "cod",        180),
    "comparison_simple":("Simple A vs B with few clear dimensions",              "L1", "cod",        120),
    "causal_chain":     ("Cause-and-effect reasoning, multi-hop",                "L1", "sot_chain",  150),
    "unknown":          ("Could not classify; escalate to classifier",           "L2", "reflect",    800),
}

# Map strategy to SoT sketch type (wave 2)
STRATEGY_TO_SKETCH = {
    "sot_symbolic": "symbolic",
    "sot_chain":    "conceptual",
    "cod":          None,        # CoD, not SoT
    "code_draft":   None,        # code profile, not SoT
    "direct":       None,        # L0, no sketch
    "reflect":      None,        # L2+, not this tool
}

# Patterns for cheap gate (evaluated in order; first match wins).
# NOTE: More-specific patterns must come BEFORE broad ones.
QUERY_GATE_PATTERNS = [
    ("greeting",        r"^(hi|hello|hey|good\s*(morning|afternoon|evening)|howdy|sup|yo)\b"),
    # MCQ: lettered options or "which of the following"
    ("mcq",             r"\b(which of the following|choose (the |)(best|correct)|select (the |)(best|correct|all that apply)|(a|b|c|d)\)\s+\w)\b"),
    ("mcq",             r"^(a|b|c|d)\.\s+\w"),
    # Math first to catch "what is 347 divided by 7" before factual_lookup
    ("math_arithmetic", r"\b(\d+[\s\+\-\*\/\^]\s*\d+|\d+\s*(plus|minus|times|divided by|squared|cubed))\b"),
    # Comparison before factual_lookup and enumeration
    ("comparison_simple", r"\b(vs\.?|versus|compared? to|difference between|better than|worse than|pros and cons)\b"),
    # Causal/multi-hop before factual
    ("causal_chain",    r"\b(why (did|does|is|are|would)|how (did|does|would).{0,30}(lead|cause|result|affect)|what (causes?|leads? to|results? in))\b"),
    # Specific factual before yes_no to avoid "what is X" firing yes_no
    ("factual_lookup",  r"^(what|who|where|when|which)\s+(is|are|was|were)\b.{0,60}\??$"),
    ("factual_lookup",  r"^who\s+(invented|discovered|created|founded|designed|wrote|built)\b"),
    ("factual_lookup",  r"\b(define|definition|meaning of|what does .{0,30} mean|capital of|population of)\b"),
    # Yes/No: only short, atomic questions starting with aux verb
    ("yes_no",          r"^(is|are|does|do|can|will|should|would|has|have|did)\b.{0,50}\??$"),
    ("yes_no",          r"\b(true or false|yes or no|is it true)\b"),
    ("conversion",      r"\b(convert|translate|format|transform|encode|decode)\b.{0,40}\b(to|into|from)\b"),
    ("enumeration",     r"\b(list (all|the|every)|give me (all|a list)|what are (all|the) .{0,40})\b"),
    ("math_arithmetic", r"\b(\d+[\s\+\-\*\/\^]\s*\d+|\d+\s*(plus|minus|times|divided by|squared|cubed))\b"),
    ("math_word",       r"\b(how many|how much|calculate|compute|solve|hourly rate|per hour|per day|if .{0,60}(cost|total|per|rate|hour|day|earn))\b"),
    ("date_time",       r"\b(what (time|day|date)|how (long|many days|many hours)|when is|schedule|deadline|timezone|utc|gmt)\b"),
    ("sports_logic",    r"\b(score|win|loss|championship|league|team|player|season|ranking|standings)\b"),
    ("code_snippet",    r"\b(write a? ?(function|method|class|script|snippet|program|code) (to|that|which|for))\b"),
    ("code_snippet",    r"^(write|implement|create|generate).{0,40}(function|method|class|lambda|decorator)\b"),
    ("code_fix",        r"\b(fix|debug|error|bug|fails?|broken|wrong output|exception|traceback)\b"),
    ("summarize_short", r"\b(summar(ize|y)|tl;?dr|in (brief|short|one sentence|a few words)|key points)\b"),
    ("instruction_how", r"^how (do|can|to|should|would) (i|you|we)\b"),
    ("comparison_simple", r"\b(vs\.?|versus|compared? to|difference between|better|worse|pros and cons)\b"),
]


def classify_query(query: str) -> dict:
    """Cheap deterministic query gate — no LLM call."""
    q = query.strip().lower()
    qtype = "unknown"
    for t, pattern in QUERY_GATE_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            qtype = t
            break

    desc, level, strategy, max_tok = QUERY_TYPES[qtype]
    sketch = STRATEGY_TO_SKETCH.get(strategy)
    return {
        "query_type": qtype,
        "description": desc,
        "recommended_level": level,
        "strategy": strategy,
        "sketch_type": sketch,
        "max_output_tokens_hint": max_tok,
        "reasoning": _reasoning_note(level, strategy),
        "api_hints": _api_hints(level, qtype, max_tok),
    }


def _reasoning_note(level: str, strategy: str) -> str:
    notes = {
        "direct":       "No scratchpad. Answer immediately. Thinking tokens: 0.",
        "cod":          "Chain-of-Draft scratchpad: 5 words per step max. Not full CoT.",
        "sot_symbolic": "Sketch-of-Thought Chunked Symbolism: equations, units, variables only.",
        "sot_chain":    "Sketch-of-Thought Conceptual Chaining: A→B→C hop notation.",
        "code_draft":   "Code draft profile: ops + identifiers, NO 5-word cap (would break code).",
        "reflect":      "Full CoT + self-check. Load adaptive-agent-reasoning.",
    }
    return notes.get(strategy, "")


def _api_hints(level: str, qtype: str, max_tok: int) -> dict:
    """Return API-layer hints (max_tokens, stop sequences, thinking budget)."""
    if level == "L0":
        return {
            "max_tokens": max_tok,
            "stop_sequences": ["\n\n", "---"],
            "thinking_budget": 0,
            "note": "Set max_tokens + stop to cap L0 excess. Thinking off. (CodeFast arXiv:2407.20042)"
        }
    elif level == "L1":
        return {
            "max_tokens": max_tok + 50,   # budget + headroom
            "stop_sequences": ["####\n\n"],
            "thinking_budget": None,
            "note": "Use #### as CoD stop; set max_tokens to budget+headroom. No extended thinking."
        }
    else:
        return {"note": "L2+: no API caps from this tool."}


# ─── Gricean blocks ────────────────────────────────────────────────────────────

GRICE_BLOCKS = {
    "weak":   "Answer only what was asked. No preamble.",
    "medium": "Answer only what was asked. No preamble, no padding, no restating the question. "
              "If uncertain, say so in one line rather than hedging at length.",
    "strong": (
        "Gricean maxims (mandatory):\n"
        "  Quantity: say exactly as much as required; no more.\n"
        "  Quality:  only assert what you know; 'I don't know' is shorter than a long hedge.\n"
        "  Relation: every sentence must bear directly on the question.\n"
        "  Manner:   prefer the shortest unambiguous form.\n"
        "Verbosity is a signal of uncertainty, not quality. Do not pad."
    ),
}

# ─── Filler-token suppression (NoWait, wave 2) ────────────────────────────────
# arXiv:2506.08343: banning Wait/Hmm/reconsider → 27-51% shorter CoT, utility preserved

NOWAIT_BLOCK = (
    "Do NOT use filler reflection tokens such as: 'Wait', 'Hmm', 'Let me reconsider', "
    "'Actually', 'On second thought', 'Let me re-examine'. "
    "These inflate token count without improving accuracy. "
    "If a step is wrong, correct it directly; do not narrate the correction."
)

# ─── CAC-CoT connector whitelist (wave 2) ─────────────────────────────────────
# EMNLP 2025 Findings: restrict reasoning to causal connectors → ~1/3 CoT tokens

CAC_COT_BLOCK = (
    "When reasoning, connect steps using ONLY these connectors: "
    "'so', 'therefore', 'thus', 'hence', 'because', 'since', 'which means'. "
    "Do not write full sentences between steps. "
    "Example: 16 eggs, eat 3 so 13 remain, sell at $2 therefore $26."
)

# ─── Explicit unit caps (LIFEBench wave 2) ────────────────────────────────────
# arXiv:2505.16234: "in one sentence" / "≤N words" beats "be concise" empirically
# Position: MUST go at END of system prompt (lost-in-middle; recency effect)

UNIT_CAP_TEMPLATES = {
    "factual_lookup":    "Answer in one sentence or fewer.",
    "yes_no":            "Answer with Yes or No, then one clause of justification if needed.",
    "enumeration":       "Answer as a bare list, one item per line, no explanations.",
    "conversion":        "Answer with the converted value and unit only.",
    "greeting":          "Reply in one short sentence.",
    "mcq":               "State the letter and the answer only.",
    "math_arithmetic":   "Show the calculation on one line, then the answer.",
    "math_word":         "Use ≤3 reasoning steps, then state the answer.",
    "date_time":         "Show date/time arithmetic in one line, then the answer.",
    "code_snippet":      "Write the function; no prose explanation unless asked.",
    "code_fix":          "Show only the corrected line(s) and a one-line explanation.",
    "sports_logic":      "Answer in one sentence with the key fact.",
    "summarize_short":   "Summarize in ≤3 bullet points, each ≤10 words.",
    "instruction_how":   "List steps, each ≤8 words. No intro or conclusion.",
    "comparison_simple": "Compare in ≤3 dimensions; each ≤15 words.",
    "causal_chain":      "Chain cause→effect in ≤3 hops, each ≤10 words.",
    "unknown":           "Be concise. Answer in the fewest words that are accurate.",
}

# ─── Step budget (wave 2, practitioner) ───────────────────────────────────────

STEP_BUDGET_TEMPLATE = (
    "Use at most {steps} reasoning steps. "
    "Stop reasoning as soon as the answer is determined. "
    "Do not add verification, self-critique, or re-examination steps."
)

# ─── NoWait + CAC combined anti-pad block ─────────────────────────────────────

ANTI_VERBOSITY_SUFFIX = (
    "\n\nDo not add: caveats about what you didn't cover, "
    "\"I hope this helps\", \"Let me know if...\", or any filler sentence. "
    "Correct answers are often shorter than wrong ones."
)

# ─── Per-turn re-injection (multi-turn verbosity drift, wave 2) ───────────────
# arXiv:2411.07858 Verbosity Compensation: GPT-4 VC 50.4% — must re-inject per turn

MULTI_TURN_REMINDER = (
    "[Brevity reminder] Keep this reply as short as the previous instruction requires. "
    "Do not expand scope, add caveats, or pad because this is a follow-up."
)

# ─── L0/L1 base prefixes ──────────────────────────────────────────────────────

L0_PREFIX = (
    "Answer directly and concisely. "
    "No preamble, no explanation unless asked, no restating the question."
)

L1_COD_PREFIX = (
    "Think step by step, but keep each reasoning step to 5 words or fewer. "
    "Return the answer after ####.\n"
    "Example: 20 - x = 12; x = 8. #### 8"
)

L1_BUDGET_PREFIX_TEMPLATE = (
    "Think step by step and use fewer than {budget} tokens of reasoning. "
    "Return the final answer after ####."
)

# ─── Sketch-of-Thought prefixes (wave 2, arXiv:2503.05179) ───────────────────
# Up to 84% fewer tokens vs CoT; task-typed, not a word budget

SOT_SKETCHES = {
    "conceptual": {
        "name": "Conceptual Chaining",
        "description": "For causal/multi-hop queries. Compress to A→B→C hops.",
        "system": (
            "Reason using Conceptual Chaining: compress your reasoning to a sequence of "
            "hop-style notations (A → B → C). Each hop is ≤5 words. "
            "No full sentences between hops. Return the answer after ####.\n"
            "Example: Fever → immune response → cytokines → inflammation. #### Cytokines cause fever."
        ),
        "shots": [
            "Q: Why does exercise reduce stress?\nA: Exercise → endorphin release → mood elevation. #### Endorphins.",
            "Q: What causes seasons on Earth?\nA: Tilt 23.5° → hemisphere faces Sun → more direct light → warmer. #### Axial tilt.",
        ],
        "token_reduction": "~84% vs CoT (arXiv:2503.05179)",
    },
    "symbolic": {
        "name": "Chunked Symbolism",
        "description": "For math/arithmetic. Use equations, units, variables only.",
        "system": (
            "Reason using Chunked Symbolism: write only equations, units, and variable names. "
            "No prose narration. Return the answer after ####.\n"
            "Example: v=d/t; d=150mi, t=2.5h; v=60mph. #### 60 mph"
        ),
        "shots": [
            "Q: A 2kg ball falls 5m. What is its kinetic energy at impact?\nA: KE=mgh; 2×9.8×5=98J. #### 98 J",
            "Q: Convert 100°F to Celsius.\nA: (100-32)×5/9=37.8°C. #### 37.8°C",
        ],
        "token_reduction": "~84% vs CoT (arXiv:2503.05179)",
    },
    "lexicon": {
        "name": "Expert Lexicons",
        "description": "For domain-jargon queries. Use technical terms, acronyms, field notation.",
        "system": (
            "Reason using Expert Lexicons: use domain-specific terminology, acronyms, "
            "and field notation instead of plain English prose. "
            "No explanatory sentences. Return the answer after ####.\n"
            "Example: TCP: SYN→SYN-ACK→ACK (3-way HS); reliable, ordered; vs UDP: connectionless, low-lat. #### TCP."
        ),
        "shots": [
            "Q: What is the difference between RAM and ROM?\nA: RAM: volatile DRAM/SRAM; RW; temp storage. ROM: NVM; RO; firmware/boot. #### RAM volatile RW; ROM non-volatile RO.",
            "Q: What does HTTP status 429 mean?\nA: 429=Too Many Requests; rate-limit exceeded; retry-after header. #### Rate limit exceeded.",
        ],
        "token_reduction": "~84% vs CoT (arXiv:2503.05179)",
    },
}

# Auto-detect sketch type from strategy
def _auto_sketch(qtype: str, strategy: str) -> str:
    if strategy == "sot_symbolic":
        return "symbolic"
    if strategy == "sot_chain":
        return "conceptual"
    # Heuristic for unknown/generic
    if qtype in ("code_snippet", "code_fix"):
        return "lexicon"
    return "conceptual"


# ─── Contrastive CoD (BAD+GOOD pair, wave 2) ──────────────────────────────────
# LEAP/Contrastive CoT: one bad-verbose + one good-terse example improves instruction following

CONTRASTIVE_EXAMPLES = {
    "math": {
        "bad": (
            "Q: What is 15% of 80?\n"
            "A (BAD — too verbose): To find 15% of 80, I need to multiply 80 by 15 divided by 100. "
            "So first I'll convert 15% to a decimal by dividing by 100, which gives me 0.15. "
            "Then I'll multiply 0.15 by 80. That's 0.15 × 80 = 12. So 15% of 80 is 12. "
            "I hope that helps! Let me know if you have other questions."
        ),
        "good": (
            "Q: What is 15% of 80?\n"
            "A (GOOD — minimal draft): 0.15 × 80 = 12. #### 12"
        ),
    },
    "factual": {
        "bad": (
            "Q: What is the capital of Australia?\n"
            "A (BAD): That's a great question! Many people think it's Sydney, but actually "
            "the capital of Australia is Canberra. Canberra was selected as a compromise between "
            "Sydney and Melbourne. I hope this clears up any confusion!"
        ),
        "good": (
            "Q: What is the capital of Australia?\n"
            "A (GOOD): Canberra."
        ),
    },
    "code": {
        "bad": (
            "Q: Write a Python function to check if a number is even.\n"
            "A (BAD): Sure! Here's a Python function that checks whether a given number is even. "
            "In Python, we can use the modulo operator (%) which returns the remainder of division. "
            "If a number divided by 2 has no remainder (i.e., the remainder is 0), the number is even:\n\n"
            "```python\ndef is_even(n):\n    # Check if n is divisible by 2\n    if n % 2 == 0:\n"
            "        return True\n    else:\n        return False\n```\n\n"
            "I hope this helps! Let me know if you need any modifications."
        ),
        "good": (
            "Q: Write a Python function to check if a number is even.\n"
            "A (GOOD): def is_even(n): return n % 2 == 0"
        ),
    },
    "general": {
        "bad": (
            "Q: How many days are in a leap year?\n"
            "A (BAD): Great question! A leap year is a year that has an extra day added to it "
            "to keep the calendar year synchronised with the astronomical year. In a regular year "
            "there are 365 days, but in a leap year there are 366 days. The extra day is added to "
            "February, giving it 29 days instead of the usual 28. I hope this answers your question!"
        ),
        "good": (
            "Q: How many days are in a leap year?\n"
            "A (GOOD): 366."
        ),
    },
}


def get_contrastive_cod(domain: str = "general") -> dict:
    """Return a BAD+GOOD contrastive CoD pair for few-shot verbosity training."""
    if domain not in CONTRASTIVE_EXAMPLES:
        domain = "general"
    pair = CONTRASTIVE_EXAMPLES[domain]
    return {
        "domain": domain,
        "bad_example": pair["bad"],
        "good_example": pair["good"],
        "combined": pair["bad"] + "\n\n" + pair["good"],
        "usage": "Prepend combined to system prompt before the regular CoD examples. "
                 "The contrast teaches the model what NOT to do, not just what to do.",
        "source": "Contrastive CoT / LEAP (accuracy literature); wave-2 practitioner sweep.",
        "note": "Token savings vs single good example: unmeasured in 2025 lit. "
                "Adds ~50-100 input tokens; worth it if verbosity score repeatedly high.",
    }


# ─── Code draft profile (wave 2, arXiv:2506.10987) ────────────────────────────
# CoD 5-word cap is WRONG for code: SWE-bench shows 55% not 7.6% savings.
# Code needs ops + identifiers, not natural-language compression.

CODE_DRAFT_PROFILE = (
    "Write code directly. No prose explanation before or after unless explicitly asked. "
    "For reasoning steps, use inline comments (# one short line) not prose paragraphs. "
    "Preserve API names, parameter names, and identifiers exactly — do not abbreviate code. "
    "Do NOT apply a 5-word-per-step limit to code or reasoning about code."
)

CODE_DRAFT_SHOTS = [
    "Q: Write a Python function to find all duplicates in a list.\n"
    "A:\n"
    "```python\nfrom collections import Counter\n\n"
    "def find_duplicates(lst):\n"
    "    # count → keep >1\n"
    "    return [x for x, c in Counter(lst).items() if c > 1]\n```",

    "Q: Fix this Python bug: `print(items[len(items)])`\n"
    "A:\n"
    "```python\nprint(items[len(items) - 1])  # last index is len-1, not len\n```",
]


def get_code_draft_prefix() -> dict:
    """Return code-specific draft profile (not 5-word CoD)."""
    return {
        "code_draft_system": CODE_DRAFT_PROFILE,
        "few_shot_examples": CODE_DRAFT_SHOTS,
        "full_prefix": CODE_DRAFT_PROFILE + "\n\n" + "\n\n".join(CODE_DRAFT_SHOTS),
        "source": "arXiv:2506.10987 CoD-for-SE: 5-word CoD on code gives 55% not 7.6% savings; "
                  "code identifiers must not be truncated.",
        "note": "Use this instead of cod-prefix when query_type is code_snippet or code_fix.",
    }


# ─── Reason Wide / skill amortization (wave 2, arXiv:2608.07885) ──────────────
# Inject compact NL skill summary → 2.7-6x fewer output tokens vs thinking per turn

SKILL_AMORTIZE_TEMPLATE = (
    "Domain knowledge for this task ({domain}):\n"
    "{summary}\n\n"
    "Use the above knowledge directly. Do not re-derive it from scratch. "
    "If the query fits within this knowledge, answer without extended reasoning. "
    "If it does not fit, say so and reason from first principles."
)


def get_skill_amortize_block(domain: str, summary: str) -> dict:
    """Return a Reason-Wide style skill injection block."""
    block = SKILL_AMORTIZE_TEMPLATE.format(domain=domain, summary=summary.strip())
    return {
        "skill_injection_block": block,
        "usage": "Prepend to system prompt for repeated-domain queries. "
                 "Amortizes reasoning cost: model reads skill instead of re-thinking.",
        "source": "arXiv:2608.07885 Reason Wide Not Deep: 2.7-6x fewer output tokens vs thinking each turn.",
        "note": "Effective when the same domain appears repeatedly (e.g. every turn in a math tutoring session). "
                "Not worth it for one-off queries.",
    }


# ─── System-prompt prefix generator ──────────────────────────────────────────

def build_prompt_prefix(query: str, level: Optional[str] = None, grice: str = "medium",
                        budget: Optional[int] = None, use_cod: bool = True,
                        anti_verbosity: bool = True, use_noWait: bool = True,
                        use_unit_cap: bool = True, step_budget: Optional[int] = None) -> dict:
    """Build the optimal system-prompt prefix for a L0/L1 query (wave 1 + wave 2)."""
    gate = classify_query(query)
    if level is None:
        level = gate["recommended_level"]
    strategy = gate["strategy"] if level in ("L0", "L1") else "reflect"
    qtype = gate["query_type"]
    sketch = gate.get("sketch_type")

    prefix_parts = []

    if level == "L0":
        prefix_parts.append(L0_PREFIX)
        prefix_parts.append(GRICE_BLOCKS.get(grice, GRICE_BLOCKS["medium"]))
        if use_noWait:
            # NoWait on L0 is lightweight: just block filler openers
            prefix_parts.append(
                "Do not begin with 'Certainly!', 'Great question!', or similar openers."
            )

    elif level == "L1":
        # Strategy selection: SoT if sketch available, code draft if code, CoD otherwise
        if strategy == "code_draft":
            prefix_parts.append(CODE_DRAFT_PROFILE)
        elif sketch and use_cod:
            sot = SOT_SKETCHES[sketch]
            prefix_parts.append(sot["system"])
        elif use_cod:
            prefix_parts.append(L1_COD_PREFIX)
            prefix_parts.append(CAC_COT_BLOCK)  # wave 2: connector whitelist
        elif budget:
            prefix_parts.append(L1_BUDGET_PREFIX_TEMPLATE.format(budget=budget))
        else:
            prefix_parts.append(L1_BUDGET_PREFIX_TEMPLATE.format(budget=50))

        if use_noWait and strategy != "code_draft":
            prefix_parts.append(NOWAIT_BLOCK)

        if step_budget is not None:
            prefix_parts.append(STEP_BUDGET_TEMPLATE.format(steps=step_budget))
        elif strategy not in ("code_draft",):
            prefix_parts.append(STEP_BUDGET_TEMPLATE.format(steps=4))

        prefix_parts.append(GRICE_BLOCKS.get("weak", ""))

    else:
        # L2/L3 — not this tool's domain
        prefix_parts.append("Answer concisely. Load adaptive-agent-reasoning for full protocol.")

    if anti_verbosity and level in ("L0", "L1"):
        prefix_parts.append(ANTI_VERBOSITY_SUFFIX)

    # Unit cap goes LAST (recency/primacy: end of system prompt for max adherence)
    # arXiv:2505.16234 LIFEBench: "in one sentence" beats "be concise"
    if use_unit_cap and level in ("L0", "L1"):
        cap = UNIT_CAP_TEMPLATES.get(qtype, UNIT_CAP_TEMPLATES["unknown"])
        prefix_parts.append(f"\nLength rule (mandatory, at end): {cap}")

    return {
        "level": level,
        "strategy": strategy,
        "query_type": qtype,
        "sketch_type": sketch,
        "system_prompt_prefix": "\n\n".join(p for p in prefix_parts if p),
        "api_hints": gate.get("api_hints", {}),
        "note": "Prepend this to your system prompt for this query only. "
                "Do not inject heavy skill blocks on L0/L1. "
                "Unit cap is placed last (recency effect for max adherence).",
    }


# ─── Chain-of-Draft few-shot examples ────────────────────────────────────────

def _load_cod_examples() -> dict:
    if COD_EXAMPLES_PATH.exists():
        return json.loads(COD_EXAMPLES_PATH.read_text())
    return COD_EXAMPLES_BUILTIN


def get_cod_prefix(domain: str = "general") -> dict:
    """Return CoD system prompt + few-shot examples for a domain."""
    examples = _load_cod_examples()
    if domain not in examples:
        domain = "general"
    domain_examples = examples[domain]

    system = (
        "Think step by step, but only keep a minimum draft for each thinking step, "
        "with 5 words at most. Return the answer after ####."
    )

    shots = []
    for ex in domain_examples[:3]:  # max 3 shots to limit input tokens
        shots.append(f"Q: {ex['q']}\nA: {ex['reasoning']} #### {ex['answer']}")

    return {
        "domain": domain,
        "cod_system_prompt": system,
        "few_shot_examples": shots,
        "full_prefix": system + "\n\n" + "\n\n".join(shots),
        "token_reduction_vs_cot": "~80% (arXiv:2502.18600, Claude 3.5 Sonnet)",
        "accuracy_note": "Date/sports: accuracy IMPROVES vs CoT. GSM8K: -4.4pp. Factual: neutral.",
        "warning": "Zero-shot CoD degrades on Claude (65.5% vs 90.4% CoT). Use these examples. "
                   "Do NOT use on code queries: use code-draft command instead. "
                   "Do NOT use on MCQ: direct answer is better.",
    }


# ─── Sketch-of-Thought prefix (wave 2) ───────────────────────────────────────

def get_sot_prefix(sketch: str = "auto", qtype: str = "unknown", strategy: str = "cod") -> dict:
    """Return SoT system prompt + shots for a sketch type."""
    if sketch == "auto":
        sketch = _auto_sketch(qtype, strategy)
    if sketch not in SOT_SKETCHES:
        sketch = "conceptual"

    sot = SOT_SKETCHES[sketch]
    return {
        "sketch_type": sketch,
        "sketch_name": sot["name"],
        "description": sot["description"],
        "system_prompt": sot["system"],
        "few_shot_examples": sot["shots"],
        "full_prefix": sot["system"] + "\n\n" + "\n\n".join(sot["shots"]),
        "token_reduction": sot["token_reduction"],
        "source": "arXiv:2503.05179 Sketch-of-Thought: task-typed shorthand beats CoD on math/causal. "
                  "HN thread: https://news.ycombinator.com/item?id=43378822",
        "when_to_use": {
            "conceptual": "Causal chains, why questions, multi-hop reasoning",
            "symbolic": "Arithmetic, unit conversion, equations",
            "lexicon": "Domain-jargon queries (networking, biology, law, etc.)",
        },
    }


# ─── TALE-style token budget hint ────────────────────────────────────────────

# Per-domain calibrated L1 budgets (tokens, P80 estimate from TALE-EP methodology)
# Grounded in arXiv:2412.18547: use P80, not median; minimum ~50 (token elasticity)
DOMAIN_BUDGETS = {
    "factual_lookup":    0,    # L0 — no reasoning
    "yes_no":            0,    # L0 — no reasoning
    "enumeration":       0,    # L0 — no reasoning
    "conversion":        0,    # L0 — no reasoning
    "greeting":          0,    # L0 — no reasoning
    "clarification":     0,    # L0 — no reasoning
    "mcq":               0,    # L0 — no reasoning
    "math_arithmetic":   50,   # L1 SoT-symbolic
    "math_word":         80,   # L1 CoD
    "date_time":         60,   # L1 CoD
    "code_snippet":     200,   # L1 code draft
    "code_fix":         150,   # L1 code draft
    "sports_logic":      50,   # L1 CoD
    "summarize_short":  100,   # L1 CoD
    "instruction_how":  120,   # L1 CoD
    "comparison_simple": 80,   # L1 CoD
    "causal_chain":     100,   # L1 SoT-conceptual
    "unknown":          300,   # fallback; escalate to full classifier
}


def budget_hint(query: str, level: Optional[str] = None) -> dict:
    """Compute TALE-style token budget for a query."""
    gate = classify_query(query)
    qtype = gate["query_type"]
    budget = DOMAIN_BUDGETS.get(qtype, 100)
    eff_level = level or gate["recommended_level"]

    if eff_level == "L0" or budget == 0:
        return {
            "level": "L0",
            "query_type": qtype,
            "budget_tokens": 0,
            "reasoning_prompt": None,
            "note": "L0: no reasoning tokens. Direct answer only.",
        }

    # Token elasticity guard: never below 50 (model ignores <50 budgets, uses more)
    budget = max(budget, 50)

    prompt = L1_BUDGET_PREFIX_TEMPLATE.format(budget=budget)
    return {
        "level": eff_level,
        "query_type": qtype,
        "budget_tokens": budget,
        "reasoning_prompt": prompt,
        "note": (
            f"TALE-style budget (P80 estimate for '{qtype}'). "
            "Do not hard-truncate — guide the model, don't cap it. "
            "arXiv:2412.18547: too-small budgets cause MORE tokens (token elasticity). "
            "Min enforced: 50 tokens."
        ),
    }


# ─── Unit-length cap (wave 2, arXiv:2505.16234 LIFEBench) ────────────────────

def get_unit_cap(query: str) -> dict:
    """Return explicit unit-length cap for a query (goes at END of system prompt)."""
    gate = classify_query(query)
    qtype = gate["query_type"]
    cap = UNIT_CAP_TEMPLATES.get(qtype, UNIT_CAP_TEMPLATES["unknown"])
    return {
        "query_type": qtype,
        "unit_cap": cap,
        "placement": "END of system prompt (recency effect; lost-in-middle if placed early)",
        "source": "arXiv:2505.16234 LIFEBench: 'in one sentence' / '≤N words' beats 'be concise' empirically.",
        "note": "This is the highest-ROI single-instruction improvement from wave-2 adjacent sweep.",
    }


# ─── NoWait filler suppression (wave 2, arXiv:2506.08343) ────────────────────

def get_nowait_block() -> dict:
    """Return filler-token suppression block (NoWait)."""
    return {
        "nowait_block": NOWAIT_BLOCK,
        "source": "arXiv:2506.08343 NoWait: banning Wait/Hmm/reconsider → 27-51% shorter CoT, utility preserved.",
        "note": "Implement at prompt layer by listing banned tokens. "
                "Full method also suppresses at decode; prompt analog is ~60-70% as effective.",
    }


# ─── Step budget (wave 2, practitioner) ───────────────────────────────────────

def get_step_budget(steps: int = 4) -> dict:
    """Return step-count budget instruction."""
    steps = max(2, min(steps, 8))
    return {
        "steps": steps,
        "step_budget_block": STEP_BUDGET_TEMPLATE.format(steps=steps),
        "source": "Practitioner sweep (HN + Reddit r/LocalLLaMA): "
                  "3-5 step budget beats open CoT and 20-step Reddit prompt on L0/L1. "
                  "Reduces reflection loops without a token count.",
        "note": "Use steps=3 for simple arithmetic/factual; steps=4-5 for multi-step word problems.",
    }


# ─── Multi-turn brevity re-injection (wave 2) ─────────────────────────────────

def get_multi_turn_reminder() -> dict:
    """Return per-turn brevity re-injection block."""
    return {
        "reminder_block": MULTI_TURN_REMINDER,
        "source": "arXiv:2411.07858 Verbosity Compensation: GPT-4 VC 50.4% across turns. "
                  "LIFEBench wave-2: brevity instructions drift without re-injection.",
        "usage": "Inject as first line of the HUMAN turn (not system prompt) each turn. "
                 "Do not rely on a one-time system prompt instruction to hold across turns.",
        "note": "Adds ~20 input tokens/turn. Worth it when verbosity drift is observed.",
    }


# ─── Verbosity analyzer ────────────────────────────────────────────────────────

VERBOSITY_MARKERS = [
    # Filler openers
    (r"^(certainly|absolutely|of course|sure|great|excellent|i'd be happy to|I understand that)", 0.3),
    # Restating the question
    (r"you('ve| have) asked (me )?(about|to|for|how)", 0.2),
    (r"you('re| are) (asking|wondering|looking for)", 0.2),
    # Sign-off padding
    (r"(i hope this (helps|answers|clears)|feel free to ask|let me know if|don't hesitate)", 0.3),
    # Hedge pileup
    (r"(however,? it's? (worth|important) (noting|mentioning)|that said,|keep in mind that)", 0.15),
    (r"(it's? (important|worth) (to )?(note|remember|consider))", 0.15),
    # Explanation of what you'll do
    (r"(I('ll| will) (now |)(explain|walk you through|break down|go through))", 0.2),
    # Length-padding transitionals
    (r"(in (summary|conclusion|short|brief),? (I |)(want to |)(say|note|mention))", 0.15),
    # Verbosity compensation (arXiv:2411.07858): hedging when uncertain
    (r"(I('m| am) not (entirely |100% )sure|I might be wrong|I could be mistaken).{0,100}"
     r"(however|but|that said)", 0.2),
    # Filler reflection tokens (NoWait, wave 2)
    (r"\b(wait,|hmm,|let me reconsider|actually,? (let me|I should)|on second thought)\b", 0.25),
]


def verbosity_score(text: str) -> dict:
    """Score a response for verbosity markers. Returns 0.0-1.0 (higher = more verbose)."""
    score = 0.0
    matches = []
    for pattern, weight in VERBOSITY_MARKERS:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            score += weight
            matches.append({"pattern": pattern[:40] + "...", "weight": weight})

    score = min(score, 1.0)
    correction = None
    if score > 0.4:
        correction = (
            "Your response has verbosity markers (score {:.2f}). "
            "Rewrite: remove openers, sign-offs, question restatements, "
            "reflection tokens (Wait/Hmm), and hedge pileups. "
            "Start with the answer. End when done."
        ).format(score)
    elif score > 0.2:
        correction = (
            "Minor verbosity (score {:.2f}). "
            "Consider trimming filler phrases and reflection tokens."
        ).format(score)

    return {
        "verbosity_score": round(score, 3),
        "over_threshold": score > 0.4,
        "matches": matches,
        "correction_prompt": correction,
        "theory": (
            "arXiv:2411.07858: verbosity is a confidence leak, not quality signal. "
            "arXiv:2606.30128: content not length drives CoT gains. "
            "arXiv:2506.08343 NoWait: reflection token filler inflates by 27-51%. "
            "Correct answers are often shorter than wrong ones."
        ),
    }


# ─── Built-in CoD examples (fallback if JSON not present) ─────────────────────

COD_EXAMPLES_BUILTIN = {
    "math": [
        {"q": "If there are 3 cars in the parking lot and 2 more cars arrive, how many cars are in the parking lot?",
         "reasoning": "3 + 2 = 5.", "answer": "5"},
        {"q": "Janet's ducks lay 16 eggs per day. She eats 3 for breakfast and bakes 4 into muffins. She sells the remainder at $2/egg. How much does she make daily?",
         "reasoning": "16 - 3 - 4 = 9. 9 × $2 = $18.", "answer": "$18"},
        {"q": "A train travels 60 mph for 2.5 hours. How far does it go?",
         "reasoning": "60 × 2.5 = 150 miles.", "answer": "150 miles"},
    ],
    "date": [
        {"q": "If today is Tuesday, what day will it be in 17 days?",
         "reasoning": "17 mod 7 = 3. Tue + 3 = Fri.", "answer": "Friday"},
        {"q": "Jane was born on March 3, 1999. How old is she on March 3, 2026?",
         "reasoning": "2026 - 1999 = 27.", "answer": "27"},
    ],
    "sports": [
        {"q": "Is the following plausible? A player scored 70 points in an NBA game.",
         "reasoning": "Record is 100 (Chamberlain). 70 is rare, not impossible.", "answer": "Yes, plausible (unusual but not record)."},
        {"q": "Which team won more Super Bowls: Patriots or Steelers?",
         "reasoning": "Patriots 6, Steelers 6. Tied.", "answer": "Tied at 6 each."},
    ],
    "logic": [
        {"q": "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies?",
         "reasoning": "Bloops ⊆ Razzies ⊆ Lazzies → Bloops ⊆ Lazzies.", "answer": "Yes."},
        {"q": "5 machines make 5 widgets in 5 minutes. How long for 100 machines to make 100 widgets?",
         "reasoning": "Each machine: 1 widget in 5 min. 100 machines: 100 widgets in 5 min.", "answer": "5 minutes"},
    ],
    "factual": [
        {"q": "What is the capital of France?",
         "reasoning": "France capital: Paris.", "answer": "Paris"},
        {"q": "How many sides does a hexagon have?",
         "reasoning": "Hex = 6.", "answer": "6"},
    ],
    "code": [
        {"q": "Write a Python function that returns True if a number is even.",
         "reasoning": "Even: n % 2 == 0. Return bool.", "answer": "def is_even(n): return n % 2 == 0"},
        {"q": "How do you reverse a list in Python?",
         "reasoning": "Built-in: lst[::-1] or lst.reverse().", "answer": "lst[::-1] (new list) or lst.reverse() (in-place)"},
    ],
    "general": [
        {"q": "What is the largest planet in the solar system?",
         "reasoning": "Size order: Jupiter > Saturn > ...", "answer": "Jupiter"},
        {"q": "Convert 100 Fahrenheit to Celsius.",
         "reasoning": "(100-32) × 5/9 = 37.8.", "answer": "37.8°C"},
    ],
}


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="L0/L1 token-efficiency layer for Hermes — wave 1+2 (arXiv:2502.18600, 2412.18547, 2503.05179, ...)"
    )
    sub = parser.add_subparsers(dest="cmd")

    # query-gate
    p_gate = sub.add_parser("query-gate", help="Classify query type + recommend approach")
    p_gate.add_argument("--query", required=True)

    # prompt
    p_prompt = sub.add_parser("prompt", help="Emit system-prompt prefix for a query (wave 1+2)")
    p_prompt.add_argument("--query", required=True)
    p_prompt.add_argument("--level", choices=["L0", "L1", "L2", "L3"], default=None)
    p_prompt.add_argument("--grice", choices=["weak", "medium", "strong"], default="medium")
    p_prompt.add_argument("--no-cod", action="store_true", help="Use TALE budget instead of CoD/SoT")
    p_prompt.add_argument("--no-anti-verbosity", action="store_true")
    p_prompt.add_argument("--no-noWait", action="store_true", help="Disable NoWait filler suppression")
    p_prompt.add_argument("--no-unit-cap", action="store_true", help="Disable explicit unit cap")
    p_prompt.add_argument("--steps", type=int, default=None, help="Step budget (default: 4 for L1)")

    # cod-prefix
    p_cod = sub.add_parser("cod-prefix", help="Emit CoD few-shot prefix for a domain")
    p_cod.add_argument("--domain",
                       choices=["math", "date", "sports", "logic", "factual", "code", "general"],
                       default="general")

    # sot-prefix (wave 2)
    p_sot = sub.add_parser("sot-prefix", help="Emit Sketch-of-Thought prefix (wave 2, arXiv:2503.05179)")
    p_sot.add_argument("--sketch", choices=["conceptual", "symbolic", "lexicon", "auto"], default="auto")
    p_sot.add_argument("--qtype", default="unknown")
    p_sot.add_argument("--strategy", default="cod")

    # budget-hint
    p_budget = sub.add_parser("budget-hint", help="Compute TALE-style token budget")
    p_budget.add_argument("--query", required=True)
    p_budget.add_argument("--level", choices=["L0", "L1", "L2", "L3"], default=None)

    # unit-cap (wave 2)
    p_ucap = sub.add_parser("unit-cap", help="Emit explicit unit-length cap (wave 2, arXiv:2505.16234)")
    p_ucap.add_argument("--query", required=True)

    # noWait-block (wave 2)
    sub.add_parser("noWait-block", help="Emit filler-token suppression block (wave 2, arXiv:2506.08343)")

    # step-budget (wave 2)
    p_step = sub.add_parser("step-budget", help="Emit step-count budget instruction (wave 2)")
    p_step.add_argument("--steps", type=int, default=4)

    # contrastive-cod (wave 2)
    p_ccod = sub.add_parser("contrastive-cod", help="Emit BAD+GOOD contrastive CoD pair (wave 2)")
    p_ccod.add_argument("--domain", choices=["math", "factual", "code", "general"], default="general")

    # code-draft (wave 2)
    sub.add_parser("code-draft", help="Emit code-specific draft profile (wave 2, arXiv:2506.10987)")

    # skill-amortize (wave 2)
    p_amort = sub.add_parser("skill-amortize", help="Emit Reason-Wide skill injection block (wave 2, arXiv:2608.07885)")
    p_amort.add_argument("--domain", required=True)
    p_amort.add_argument("--summary", required=True)

    # multi-turn-reminder (wave 2)
    sub.add_parser("multi-turn-reminder", help="Emit per-turn brevity re-injection block (wave 2)")

    # verbosity-fix
    p_vfix = sub.add_parser("verbosity-fix", help="Score verbosity of a response")
    p_vfix.add_argument("--text", required=True)

    # grice-block
    p_grice = sub.add_parser("grice-block", help="Emit Gricean Quantity prompt block")
    p_grice.add_argument("--strength", choices=["weak", "medium", "strong"], default="medium")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "query-gate":
        print(json.dumps(classify_query(args.query), indent=2))

    elif args.cmd == "prompt":
        print(json.dumps(build_prompt_prefix(
            args.query,
            level=args.level,
            grice=args.grice,
            use_cod=not args.no_cod,
            anti_verbosity=not args.no_anti_verbosity,
            use_noWait=not args.no_noWait,
            use_unit_cap=not args.no_unit_cap,
            step_budget=args.steps,
        ), indent=2))

    elif args.cmd == "cod-prefix":
        print(json.dumps(get_cod_prefix(args.domain), indent=2))

    elif args.cmd == "sot-prefix":
        print(json.dumps(get_sot_prefix(args.sketch, args.qtype, args.strategy), indent=2))

    elif args.cmd == "budget-hint":
        print(json.dumps(budget_hint(args.query, args.level), indent=2))

    elif args.cmd == "unit-cap":
        print(json.dumps(get_unit_cap(args.query), indent=2))

    elif args.cmd == "noWait-block":
        print(json.dumps(get_nowait_block(), indent=2))

    elif args.cmd == "step-budget":
        print(json.dumps(get_step_budget(args.steps), indent=2))

    elif args.cmd == "contrastive-cod":
        print(json.dumps(get_contrastive_cod(args.domain), indent=2))

    elif args.cmd == "code-draft":
        print(json.dumps(get_code_draft_prefix(), indent=2))

    elif args.cmd == "skill-amortize":
        print(json.dumps(get_skill_amortize_block(args.domain, args.summary), indent=2))

    elif args.cmd == "multi-turn-reminder":
        print(json.dumps(get_multi_turn_reminder(), indent=2))

    elif args.cmd == "verbosity-fix":
        print(json.dumps(verbosity_score(args.text), indent=2))

    elif args.cmd == "grice-block":
        print(json.dumps({
            "grice_block": GRICE_BLOCKS[args.strength],
            "strength": args.strength,
            "source": "arXiv:2503.14484 Gricean norms as LLM collaboration policy",
        }, indent=2))


if __name__ == "__main__":
    main()
