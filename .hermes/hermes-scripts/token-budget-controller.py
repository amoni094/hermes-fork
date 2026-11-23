#!/usr/bin/env python3
"""
Token Budget Controller for Hermes Agent
=========================================
Research basis:
  arXiv:2604.02155  FR-CoT: cap tool-calling CoT to 8-32 tokens; non-monotonic budget effect
  arXiv:2605.07686  Split thinking/answer budgets; coupling tax causes accuracy collapse
  arXiv:2512.19585  Best-of-N short traces beats one long trace at matched compute
  arXiv:2604.10739  Overthinking reverses correct answers; snapshot first committed answer
  arXiv:2509.07820  Certainty-guided stop: periodic probe during thinking, abstain if low
  arXiv:2502.02542  OverThink attack: strip injected puzzles/decoys from retrieved context
  arXiv:2511.22176  F-CoT: extract structured facts first, then reason only over that list

CLI:
  python3 token-budget-controller.py fr-cot  --text TEXT
      Extract FR-CoT prefix: function + key args within 8-32 tokens
  python3 token-budget-controller.py difficulty --text TEXT
      Classify task difficulty and suggest CoT budget
  python3 token-budget-controller.py overthink-check --trace TEXT
      Check if a reasoning trace shows overthinking reversal
  python3 token-budget-controller.py overthink-attack --context TEXT
      Detect OverThink attack patterns (injected puzzles/games) in retrieved context
  python3 token-budget-controller.py fcot-extract --text TEXT
      Extract structured fact list (F-CoT first stage)
  python3 token-budget-controller.py certainty-probe --trace TEXT --cap INT
      Assess certainty from trace and recommend stop/continue/abstain

All commands output JSON.
"""
from __future__ import annotations
import argparse, json, math, re, sys
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────────────────

FR_COT_OPTIMAL_TOKENS = 16        # midpoint of 8-16 optimum range
FR_COT_MAX_TOKENS     = 32        # hard cap before first tool call
FR_COT_WORDS_PER_TOK  = 0.75      # rough words-to-tokens estimate

CERTAINTY_STOP_THRESHOLD   = 0.80  # abstain if below this after cap (UNCALIBRATED; calibrate per domain)
# NOTE: The paper (arXiv:2509.07820) uses logprob min-aggregation with theta=0.99, not verbalized hedging.
# CERTAINTY_STOP_THRESHOLD here is an uncalibrated lexical proxy. Do not treat as equivalent to paper theta.

# L0-L3 budget mapping: aligns with reasoning-complexity-classifier.py (authoritative)
# Use classify() from that script; do not call cmd_difficulty() when the classifier is available.
DIFFICULTY_BUDGETS_L = {
    "L0": 0,     # trivial — no CoT
    "L1": 300,   # routine — light chain
    "L2": 1200,  # complex — reflect
    "L3": 3000,  # critical — deliberate
}

# OverThink attack patterns: blocks that look like puzzle/game injections
PUZZLE_PATTERNS = [
    re.compile(r'\b(?:solve the following|find the path|minimum steps|maximum score)\b', re.I),
    re.compile(r'\b(?:sudoku|crossword|maze|grid puzzle|wordle|chess puzzle|kakuro)\b', re.I),
    re.compile(r'\bMDP\b|\bMarkov decision process\b', re.I),
    re.compile(r'\b(?:state space|transition function|reward function|policy optimization)\b', re.I),
    re.compile(r'^\s*\d+\s*[\|:]\s*\d+\s*[\|:]\s*\d+', re.M),   # grid rows
    re.compile(r'\b(?:from state|to state|action cost|heuristic value)\b', re.I),
    re.compile(r'\bgoal state\b.*\binitial state\b|\binitial state\b.*\bgoal state\b', re.I),
    re.compile(r'\b(?:BFS|DFS|A\*|Dijkstra|dynamic programming)\b.*\bpath\b', re.I),
    re.compile(r'\btowers of hanoi\b|\bnqueens\b|\bn-queens\b|\btraveling salesman\b', re.I),
    re.compile(r'(?:step \d+:|move \d+:|action \d+:)\s*(?:left|right|up|down|swap|rotate)', re.I),
]

# Commitment signals in a reasoning trace (first committed answer)
COMMITMENT_SIGNALS = [
    re.compile(r'\bthe answer is\b', re.I),
    re.compile(r'\btherefore[,:]?\s+(?:the\s+)?(?:answer|result|solution|value)\b', re.I),
    re.compile(r'\bso[,:]?\s+(?:the\s+)?(?:answer|result)\b', re.I),
    re.compile(r'\bconclusion[:]?\s', re.I),
    re.compile(r'\bfinal answer[:]?\s', re.I),
    re.compile(r'\bin summary[,:]?\s', re.I),
    re.compile(r'\bto conclude[,:]?\s', re.I),
]

# Reversal signals (agent reversing a committed answer without new evidence)
REVERSAL_SIGNALS = [
    re.compile(r'\bactually[,\s]', re.I),
    re.compile(r'\bwait[,\s]', re.I),
    re.compile(r'\bno[,\s]+(?:wait|actually|let me reconsider)\b', re.I),
    re.compile(r'\blet me reconsider\b', re.I),
    re.compile(r'\bi was wrong\b|\bI made an error\b', re.I),
    re.compile(r'\bon second thought\b', re.I),
    re.compile(r'\brecalculating\b|\brethinking\b', re.I),
]

# Evidence markers (valid reason to change a committed answer)
NEW_EVIDENCE_MARKERS = [
    re.compile(r'\baccording to\b', re.I),
    re.compile(r'\bthe tool (?:returned|shows|says)\b', re.I),
    re.compile(r'\bweb search\b|\bsearch result\b', re.I),
    re.compile(r'\bthe file (?:says|shows|contains)\b', re.I),
    re.compile(r'\bI checked\b|\bI looked up\b', re.I),
    re.compile(r'\bthe database\b|\bthe API\b|\bthe output\b', re.I),
]

# Hedge patterns for certainty probing
HIGH_CERTAINTY_PATTERNS = [
    re.compile(r'\bI(?:\'m| am) (?:certain|confident|sure)\b', re.I),
    re.compile(r'\bthe answer is (?:definitely|clearly|certainly)\b', re.I),
    re.compile(r'\bwithout (?:doubt|question)\b', re.I),
    re.compile(r'\bI(?:\'ve| have) verified\b', re.I),
]

LOW_CERTAINTY_PATTERNS = [
    re.compile(r'\b(?:I think|I believe|perhaps|maybe|possibly|might be|could be)\b', re.I),
    re.compile(r'\bnot (?:sure|certain|confident)\b', re.I),
    re.compile(r'\b(?:roughly|approximately|around|about)\b', re.I),
    re.compile(r'\bI(?:\'m| am) (?:not sure|unsure|uncertain)\b', re.I),
    re.compile(r'\bI(?:\'m| am) (?:guessing|estimating)\b', re.I),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _word_count(text: str) -> int:
    return len(text.split())

def _approx_tokens(text: str) -> int:
    """Rough token estimate: words / 0.75."""
    return max(1, int(_word_count(text) / FR_COT_WORDS_PER_TOK))

def _find_first_commitment(trace: str) -> Optional[tuple[int, str]]:
    """Find the character position and signal of the first answer commitment."""
    best_pos = len(trace) + 1
    best_sig = None
    for pattern in COMMITMENT_SIGNALS:
        m = pattern.search(trace)
        if m and m.start() < best_pos:
            best_pos = m.start()
            best_sig = pattern.pattern
    if best_sig is None:
        return None
    return best_pos, best_sig

def _has_new_evidence_after(trace: str, pos: int) -> bool:
    """Check if any new-evidence marker appears after position pos."""
    after = trace[pos:]
    return any(p.search(after) for p in NEW_EVIDENCE_MARKERS)

def _count_reversals_after(trace: str, pos: int) -> int:
    """Count reversal signals after commitment position."""
    after = trace[pos:]
    return sum(1 for p in REVERSAL_SIGNALS if p.search(after))

def _certainty_score(trace: str) -> float:
    """
    Score certainty from 0 (very uncertain) to 1 (very certain).
    Based on balance of high-certainty vs low-certainty signals.
    """
    high = sum(1 for p in HIGH_CERTAINTY_PATTERNS if p.search(trace))
    low  = sum(1 for p in LOW_CERTAINTY_PATTERNS  if p.search(trace))
    total = high + low
    if total == 0:
        return 0.5  # neutral
    return min(1.0, max(0.0, high / total))


# Shannon context utilization tracker (Shannon 1948 section 1)
# Tracks consecutive low-utilization calls; list of ratios
_SHANNON_UTIL_HISTORY: list[float] = []
_SHANNON_UTIL_UNDERUSE_THRESHOLD = 0.10
_SHANNON_UTIL_CONSECUTIVE_TRIGGER = 3


def shannon_context_utilization(completion_tokens: list[str]) -> float:
    """Compute bigram entropy H2 / log2(vocab_estimate) as context utilization ratio.

    Shannon 1948 section 1: entropy H = -sum(p * log2(p)).
    Utilization = H2 / log2(max(vocab_estimate, 1000)).
    Returns ratio in [0, 1]; close to 1 means diverse/rich context use.
    """
    if not completion_tokens or len(completion_tokens) < 2:
        return 0.0

    # Build bigram counts
    bigram_counts: dict[tuple[str, str], int] = {}
    for i in range(len(completion_tokens) - 1):
        bg = (completion_tokens[i], completion_tokens[i + 1])
        bigram_counts[bg] = bigram_counts.get(bg, 0) + 1

    total_bigrams = sum(bigram_counts.values())
    if total_bigrams == 0:
        return 0.0

    # Bigram entropy H2
    h2 = -sum(
        (c / total_bigrams) * math.log2(c / total_bigrams)
        for c in bigram_counts.values()
        if c > 0
    )

    # Vocab estimate: unique unigrams, floored at 1000 (Shannon 1948 §1 English ~8000 types)
    vocab_estimate = max(len(set(completion_tokens)), 1000)
    max_h2 = math.log2(vocab_estimate)
    if max_h2 <= 0:
        return 0.0
    return min(1.0, h2 / max_h2)


def _log_shannon_util(completion_tokens: list[str]) -> None:
    """Compute and print SHANNON_UTIL; warn on 3+ consecutive underutilization calls."""
    ratio = shannon_context_utilization(completion_tokens)
    _SHANNON_UTIL_HISTORY.append(ratio)
    print(f"SHANNON_UTIL: {ratio:.4f}  # Shannon 1948 §1: H2/log2(vocab)")
    # Warn if last N calls are all below threshold
    if len(_SHANNON_UTIL_HISTORY) >= _SHANNON_UTIL_CONSECUTIVE_TRIGGER:
        recent = _SHANNON_UTIL_HISTORY[-_SHANNON_UTIL_CONSECUTIVE_TRIGGER:]
        if all(r < _SHANNON_UTIL_UNDERUSE_THRESHOLD for r in recent):
            print(
                "WARNING: Context underutilization - consider compressing prompt "
                "or switching to cheaper model"
            )




def cmd_fr_cot(text: str) -> dict:
    """
    FR-CoT analysis: estimate if text fits within the 8-32 token cap,
    extract the function name and key args if present.
    Research: 2604.02155 — cap pre-tool thinking to 8-32 tokens.
    """
    tokens = _approx_tokens(text)
    words  = _word_count(text)

    # Emit Shannon context utilization for this token sequence (Shannon 1948 §1)
    _log_shannon_util(text.split())

    # Try to extract function name and key args pattern
    func_match = re.search(r'(?:Function|Tool|Call):\s*([^\n/,]+)', text, re.I)
    args_match  = re.search(r'(?:Key\s+args?|Args?|Parameters?):\s*([^\n]+)', text, re.I)

    function_name = func_match.group(1).strip() if func_match else None
    key_args      = args_match.group(1).strip()  if args_match else None

    within_cap = tokens <= FR_COT_MAX_TOKENS
    within_opt = tokens <= FR_COT_OPTIMAL_TOKENS

    recommendation = "OK" if within_cap else "TRIM"
    if not within_cap:
        target_words = int(FR_COT_MAX_TOKENS * FR_COT_WORDS_PER_TOK)
        recommendation = f"TRIM to ~{target_words} words"
    elif not within_opt:
        recommendation = "ACCEPTABLE (above optimal 8-16 tokens but within 32-cap)"

    return {
        "tokens_estimated": tokens,
        "words": words,
        "within_optimal": within_opt,
        "within_cap": within_cap,
        "function_name": function_name,
        "key_args": key_args,
        "recommendation": recommendation,
        "note": (
            "arXiv:2604.02155: optimal 8-16 tokens, cap at 32. "
            "Template: 'Function: [name] / Key args: [k=v ...]'"
        ),
    }


def cmd_difficulty(text: str) -> dict:
    """
    Classify task difficulty and suggest CoT token budget.
    Maps to L0-L3 levels from reasoning-complexity-classifier.py (authoritative).
    When that classifier is available, prefer it over this heuristic.
    Research: 2604.10739, 2509.07820 — difficulty-gate thinking length.
    """
    text_lower = text.lower()
    words = _word_count(text)

    # Simple heuristics — not a trained classifier; defers to reasoning-complexity-classifier.py
    level = "L1"  # default (routine, light chain)

    l0_patterns = [
        r'\bwhat is \d+\s*[\+\-\*\/]\s*\d+\b',
        r'\bwhat(?:\'s| is) (?:the )?(?:capital|author|year|date)\b',
        r'\bdefine\s+\w+\b',
        r'\bspell\b',
        r'\btranslate\s+\w+\b',
    ]
    l2_patterns = [
        r'\b(?:implement|develop|design|architect|build)\b',
        r'\b(?:debug|diagnose|troubleshoot|investigate)\b',
        r'\b(?:compare|analyze|evaluate|assess)\b.{0,50}\b(?:tradeoffs?|pros and cons)\b',
        r'\b(?:multi-step|multi-hop|long-horizon)\b',
        r'\bprove\b|\bderive\b|\bdeduce\b',
    ]
    l3_patterns = [
        r'\b(?:full implementation|entire codebase|complete system)\b',
        r'\birreversible\b|\bproduction deploy\b|\bpublish\b|\bsend email\b',
        r'\bend-to-end\b.{0,30}\b(?:pipeline|workflow|system)\b',
        r'\b(?:drop|delete|rm -rf|truncate)\b',
    ]

    for p in l0_patterns:
        if re.search(p, text_lower):
            level = "L0"
            break
    else:
        for p in l3_patterns:
            if re.search(p, text_lower):
                level = "L3"
                break
        else:
            for p in l2_patterns:
                if re.search(p, text_lower):
                    level = "L2"
                    break

    # Bump up on length
    if words > 200 and level == "L0":
        level = "L1"
    if words > 500 and level == "L1":
        level = "L2"

    budget = DIFFICULTY_BUDGETS_L[level]
    split_recommended = level in ("L2", "L3")

    return {
        "level": level,
        "thinking_budget_tokens": budget,
        "split_budget_recommended": split_recommended,
        "meta_loop_recommended": level == "L3",
        "recommendation": (
            f"L{level[-1]}: use at most {budget} thinking tokens. "
            + ("Prefer split thinking/answer or <=half-budget fallback. " if split_recommended else "")
            + ("Use two-role object/meta loop for very hard tasks. " if level == "L3" else "")
            + "Prefer reasoning-complexity-classifier.py classify for authoritative L0-L3."
        ),
        "note": (
            "arXiv:2604.10739: optimal length depends on difficulty; uniform max budgets wasteful. "
            "Budgets aligned with L0-L3 from reasoning-complexity-classifier.py (0/300/1200/3000)."
        ),
    }


def cmd_overthink_check(trace: str) -> dict:
    """
    Check if a reasoning trace shows overthinking reversal.
    Research: 2604.10739 — overthinking abandons previously correct answers.
    """
    commitment = _find_first_commitment(trace)
    if commitment is None:
        return {
            "overthinking_detected": False,
            "has_commitment": False,
            "reversals_after_commitment": 0,
            "has_new_evidence": False,
            "recommendation": "No committed answer found in trace.",
            "note": "arXiv:2604.10739: snapshot first committed answer.",
        }

    commit_pos, commit_signal = commitment
    reversals = _count_reversals_after(trace, commit_pos)
    new_ev    = _has_new_evidence_after(trace, commit_pos)

    # Overthinking: reversal without new evidence
    overthinking = reversals > 0 and not new_ev

    recommendation = "OK"
    if overthinking:
        recommendation = (
            "OVERTHINKING WARNING: Answer was reversed without tool-grounded evidence. "
            "Trigger one targeted verification before accepting the reversal. "
            "Do NOT automatically revert to the earlier answer; first commitments can be wrong."
        )
    elif reversals > 0 and new_ev:
        recommendation = "Reversal appears tool-evidence-grounded; likely a legitimate correction."

    return {
        "overthinking_detected": overthinking,
        "has_commitment": True,
        "commitment_position": commit_pos,
        "commitment_signal": commit_signal,
        "reversals_after_commitment": reversals,
        "has_new_evidence_after_commitment": new_ev,
        "recommendation": recommendation,
        "note": (
            "arXiv:2604.10739: if later tokens reverse the first committed answer "
            "without new tool evidence, keep the earlier answer."
        ),
    }


def cmd_overthink_detect(context: str) -> dict:
    """
    Detect OverThink attack patterns in retrieved context.
    Research: arXiv:2502.02542 — injected puzzles force huge token spend.
    Strips puzzle-like blocks and returns cleaned context.
    """
    hits = []
    for i, pattern in enumerate(PUZZLE_PATTERNS):
        m = pattern.search(context)
        if m:
            hits.append({
                "pattern_index": i,
                "pattern": pattern.pattern,
                "match": m.group(0)[:80],
                "position": m.start(),
            })

    attack_detected = len(hits) >= 2  # require at least 2 signals to reduce FP

    # Attempt to strip suspicious paragraphs
    cleaned = context
    if attack_detected:
        # Split into paragraphs and drop those with multiple puzzle hits
        paragraphs = re.split(r'\n{2,}', context)
        clean_paragraphs = []
        for para in paragraphs:
            para_hits = sum(1 for p in PUZZLE_PATTERNS if p.search(para))
            if para_hits < 2:
                clean_paragraphs.append(para)
        cleaned = "\n\n".join(clean_paragraphs)

    return {
        "attack_detected": attack_detected,
        "puzzle_signals_found": len(hits),
        "signals": hits[:5],
        "cleaned_context": cleaned if attack_detected else context,
        "cleaned_context_length": len(cleaned),
        "original_context_length": len(context),
        "chars_stripped": len(context) - len(cleaned),
        "recommendation": (
            "STRIP PUZZLE BLOCKS: Context cleaned_context field has puzzle paragraphs removed. "
            "SCOPE: Only apply to retrieved/untrusted context, NOT to the user task itself. "
            "HIGH FALSE POSITIVE RISK on CS/planning/RL content — verify irrelevance before stripping."
            if attack_detected
            else "Context appears clean."
        ),
        "note": (
            "arXiv:2502.02542: injected decoys force huge CoT spend. "
            "Requires >=2 pattern signals. High FP on legitimate algorithm/planning content."
        ),
    }


def cmd_fcot_extract(text: str) -> dict:
    """
    F-CoT first stage: identify whether structured extraction is warranted
    and provide extraction prompt.
    Research: arXiv:2511.22176 — 2-3x fewer tokens at matched accuracy.
    """
    words = _word_count(text)
    sentences = len(re.split(r'[.!?]+', text))

    # Heuristics: long, noisy, document-like content benefits most
    noisy_signals = [
        bool(re.search(r'\b(?:however|although|despite|while|whereas)\b', text, re.I)),
        bool(re.search(r'\b(?:for example|for instance|such as|e\.g\.)\b', text, re.I)),
        bool(re.search(r'\b(?:according to|as stated in|the article says)\b', text, re.I)),
        words > 150,
        sentences > 8,
    ]
    noisy_score = sum(noisy_signals)
    apply_fcot  = noisy_score >= 3

    extraction_prompt = (
        "From the text above, extract ONLY the relevant quantities, constraints, "
        "and facts needed to answer the question. Format as a bullet list:\n"
        "- [fact or quantity]: [value or description]\n"
        "Omit background, examples, and narrative. Keep under 10 bullets."
    )
    reasoning_prompt = (
        "Using ONLY the structured facts listed above, answer the question. "
        "Do not refer back to the original text."
    )

    return {
        "apply_fcot": apply_fcot,
        "noisy_score": noisy_score,
        "word_count": words,
        "sentence_count": sentences,
        "extraction_prompt": extraction_prompt if apply_fcot else None,
        "reasoning_prompt": reasoning_prompt if apply_fcot else None,
        "recommendation": (
            "Apply F-CoT two-stage: extract structured facts, then reason over them only."
            if apply_fcot
            else "Input is short/clean; F-CoT overhead not warranted."
        ),
        "note": (
            "arXiv:2511.22176: F-CoT yields 2-3x fewer tokens at matched accuracy "
            "for arithmetic word problems and document-heavy inputs."
        ),
    }


def cmd_certainty_probe(trace: str, cap: int = 512) -> dict:
    """
    Assess certainty from a reasoning trace and recommend stop/continue/abstain.
    Research: arXiv:2509.07820 — certainty-guided stop during thinking.
    """
    tokens = _approx_tokens(trace)
    certainty = _certainty_score(trace)

    # Find whether there's a committed answer
    commitment = _find_first_commitment(trace)
    has_answer = commitment is not None

    # Decision logic — aligned with skill: abstain if below tau after cap
    if certainty >= CERTAINTY_STOP_THRESHOLD and has_answer:
        decision = "STOP"
        action = f"Certainty score {certainty:.2f} >= {CERTAINTY_STOP_THRESHOLD} with committed answer. Emit final answer; apply Hard Confidence Gate check first."
    elif tokens >= cap:
        if certainty < CERTAINTY_STOP_THRESHOLD:
            decision = "ABSTAIN"
            action = f"Budget cap ({cap} tokens) reached and certainty {certainty:.2f} < {CERTAINTY_STOP_THRESHOLD}. Abstain or escalate; do not guess."
        else:
            decision = "STOP"
            action = f"Budget cap ({cap} tokens) reached. Certainty {certainty:.2f} >= threshold — emit best answer."
    else:
        decision = "CONTINUE"
        action = f"Certainty {certainty:.2f} < {CERTAINTY_STOP_THRESHOLD}. Continue reasoning (tokens used: {tokens}/{cap})."

    return {
        "decision": decision,
        "action": action,
        "certainty_score": round(certainty, 3),
        "tokens_used": tokens,
        "token_cap": cap,
        "has_committed_answer": has_answer,
        "high_certainty_signals": sum(1 for p in HIGH_CERTAINTY_PATTERNS if p.search(trace)),
        "low_certainty_signals": sum(1 for p in LOW_CERTAINTY_PATTERNS  if p.search(trace)),
        "note": (
            "arXiv:2509.07820: probe certainty every 64 tokens during thinking; "
            "stop when p > tau; abstain if certainty stays low after cap. "
            "Calibrate tau on a held-out set (default 0.80 is illustrative)."
        ),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Token Budget Controller for Hermes Agent"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # fr-cot
    fc = sub.add_parser("fr-cot", help="Analyze text for FR-CoT pre-tool cap compliance")
    fc.add_argument("--text", required=True, help="Pre-tool reasoning text to analyze")

    # difficulty
    df = sub.add_parser("difficulty", help="Classify task difficulty and suggest CoT budget")
    df.add_argument("--text", required=True, help="Task description to classify")

    # overthink-check
    oc = sub.add_parser("overthink-check", help="Detect overthinking reversal in reasoning trace")
    oc.add_argument("--trace", required=True, help="Full reasoning trace text")

    # overthink-attack (was: overThink-detect — renamed to lowercase)
    od = sub.add_parser("overthink-attack", help="Detect OverThink attack in retrieved context (puzzle injection)")
    od.add_argument("--context", required=True, help="Retrieved context text to check (NOT the user task)")

    # fcot-extract
    fe = sub.add_parser("fcot-extract", help="F-CoT: assess if structured extraction is warranted")
    fe.add_argument("--text", required=True, help="Input text to analyze")

    # certainty-probe
    cp = sub.add_parser("certainty-probe", help="Assess certainty from trace; recommend stop/continue/abstain")
    cp.add_argument("--trace", required=True, help="Current reasoning trace")
    cp.add_argument("--cap",   type=int, default=512, help="Token budget cap (default 512)")

    args = parser.parse_args()

    if args.command == "fr-cot":
        result = cmd_fr_cot(args.text)
    elif args.command == "difficulty":
        result = cmd_difficulty(args.text)
    elif args.command == "overthink-check":
        result = cmd_overthink_check(args.trace)
    elif args.command == "overthink-attack":
        result = cmd_overthink_detect(args.context)
    elif args.command == "fcot-extract":
        result = cmd_fcot_extract(args.text)
    elif args.command == "certainty-probe":
        result = cmd_certainty_probe(args.trace, args.cap)
    else:
        parser.error(f"Unknown command: {args.command}")
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
