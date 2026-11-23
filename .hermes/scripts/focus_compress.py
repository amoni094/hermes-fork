#!/usr/bin/env python3
"""
focus_compress.py — Focus Agent intra-trajectory compression helper for Hermes.

Implements the Focus Agent sawtooth compression pattern (arXiv:2601.07190):
  - 22.7% average token reduction, up to 57% on exploration-heavy tasks
  - Works with API-only models (no fine-tuning required)
  - Aggressive prompting required (passive prompting yields only 6% savings + accuracy loss)

This script generates the system-prompt snippets to inject into agent loops that
implement the start_focus / complete_focus compression protocol.

Usage:
  python3 ~/.hermes/scripts/focus_compress.py --mode system   # print system prompt snippet
  python3 ~/.hermes/scripts/focus_compress.py --mode reminder # print periodic reminder
  python3 ~/.hermes/scripts/focus_compress.py --mode summary  # print summarization prompt
  python3 ~/.hermes/scripts/focus_compress.py --mode guide    # print full implementation guide

Research: arXiv:2601.07190 (Focus Agent, Nikhil Verma, January 2026)
Hermes skill: hermes-context-hygiene (Focus Agent pattern documented there)
"""

from __future__ import annotations

import argparse
import sys


# ---------------------------------------------------------------------------
# Focus Agent prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_SNIPPET = """
## Intra-task Context Compression (Focus Agent Protocol)

You have two mandatory compression tools available for long tasks:

**start_focus**: Call this BEFORE beginning any exploration phase (reading files,
searching, browsing, running broad queries). It marks a compression checkpoint.

**complete_focus**: Call this AFTER completing an exploration phase (after 10-15
tool calls, or whenever you've gathered information but haven't yet acted on it).
It summarizes what you learned and prunes the raw exploration log from context.

### CRITICAL: These are MANDATORY, not optional.

### Tool Result Compression: Compress Tail, Never Head (ACL 2026 STA)

When compressing tool output, always preserve the FIRST chunk — answers and key data
appear at the top of structured responses. Compress the redundant tail.
WRONG: keep last N chars. RIGHT: keep first N chars + structured summary of tail.

### Breadcrumb Pattern: Compact = Map, Not the Memory (Zenn JP, Aug 2026)

When compressing, never destroy the path back to the original evidence.
Every compressed segment MUST record `source_range` (session:session_id:msgs:N-M).
Format:
  [COMPRESSED: msgs 120-145] Summary: ...
  source_range: session:current:msgs:120-145
  query_hints: keyword1, keyword2

Never regenerate regex, SQL, paths, or exact values from a summary — they must be
recalled from source_range on demand.

### ACM Ingest Rule: Skip Tool Bodies in Observer Context (Habr RU, Aug 2026)

Observer/monitoring models should skip tool result bodies for: Read, Grep, Glob,
WebFetch, terminal (unless the result is explicitly needed for the next decision).
Only tool choice + truncated result (first 200 chars) is needed for trajectory.
Cron/background project tool calls should be excluded entirely from ingest.
Tail window for monitoring: 5 messages (not 20) to avoid quota exhaustion.

- ALWAYS call `start_focus` before ANY exploration
- ALWAYS call `complete_focus` after 10-15 tool calls without compression
- The system will remind you every 15 tool calls if you haven't compressed

### What to put in complete_focus summary:

Structured YAML at the top of context (not free text). Prefer **extractive**
spans (paths, identifiers, error strings, exact commands) over paraphrase
(Paritok arXiv:2608.24188). Condition retention on the current goal intent.

```yaml
knowledge:
  goal: <original task in one sentence>   # intent anchor for what to keep
  found:
    - <key fact 1: specific, concrete, citable; prefer verbatim paths/IDs>
    - <key fact 2>
    - <...>
  tried:
    - <approach 1: outcome>
    - <approach 2: outcome>
  next:
    - <remaining step 1>
    - <remaining step 2>
  # Constraint Weakening (arXiv:2608.24569): NEVER rewrite binding:must → should/info
  constraints:
    - text: <invariant>
      binding: must          # must | should | info
      authority: user|policy|safety
      fallback: <what to do if blocked>
      consequence_if_ignored: <execution consequence>
```

After writing this YAML, instruct the system to drop all messages between
start_focus and the YAML summary. The YAML becomes the persistent Knowledge block.
Sync must-constraints into session WM:
`python3 ~/.hermes/scripts/working-memory.py -s $SESSION add-constraint ...`

### When NOT to compress

Iterative refinement tasks (tight feedback loops between code writes and test runs)
benefit less from compression — the raw diffs ARE the information. In that case,
use /compress at logical phase boundaries instead of mid-loop start/complete_focus.
"""

PERIODIC_REMINDER = """
[COMPRESSION REMINDER: You have made 15+ tool calls without a compression checkpoint.
If you are in an exploration phase (reading, searching, gathering), call complete_focus NOW
with a YAML knowledge summary before continuing. Skipping this will cause context bloat
that degrades output quality on long tasks. If you are in an iterative-refinement phase
(tight code-test loop), use /compress at the next phase boundary instead.]
"""

SUMMARIZATION_PROMPT = """
Generate a structured YAML knowledge block summarizing your exploration so far.
This will replace the raw tool output in context.

Rules (Paritok arXiv:2608.24188 + Constraint Weakening arXiv:2608.24569):
1. Intent-conditioned: keep spans that serve the CURRENT goal; drop exploration detours.
2. Extractive first: prefer verbatim paths, identifiers, error strings, commands, IDs.
   Do not paraphrase identifiers. Do not invent values not present in tool output.
3. Constraints are operational state, not flavor text. Preserve binding force:
   binding:must stays must (never "should"/"consider"/"if convenient").
   Include authority, fallback, and consequence_if_ignored on every must.

Turn retention priority (arXiv:2609.01131, predictive-state compression, 2026-09-07):
Before compressing, mentally classify each turn as one of three types and retain in order:
  CAUSAL:     turns where a decision was made, a command was run, or state was changed.
              These are always retained verbatim — they causally determine what came after.
  STRUCTURAL: turns that established a constraint, file structure, or plan that is still active.
              Retain as a summary line. Prefer extractive (exact path/ID/rule) over paraphrase.
  NOISE:      pure exploration that yielded nothing actionable: reads that returned no findings,
              searches with empty results, failed attempts already noted in tried:.
              These are dropped entirely in the YAML. Do not summarize noise — it adds tokens
              without adding information.
Rule: a turn tagged CAUSAL always outranks a turn tagged STRUCTURAL, which always outranks NOISE,
regardless of recency. Do NOT drop CAUSAL turns to save tokens.

```yaml
knowledge:
  goal: <original task — one sentence>
  found:
    - <key finding 1: specific, grounded, extractive where possible>
    - <key finding 2>
    - <...>  # include all important discoveries, don't omit
  tried:
    - <approach: outcome>  # especially failures — don't omit those
  next:
    - <remaining step 1>
    - <remaining step 2>
  constraints:
    - text: <invariant>
      binding: must|should|info
      authority: user|policy|safety
      fallback: <blocked path>
      consequence_if_ignored: <what breaks if ignored>
  references:
    - <file/URL/ID: reason it matters>
```

After generating this YAML, the system will drop all messages from the last
start_focus checkpoint up to (but not including) this summary. The YAML becomes
your persistent Knowledge block for the rest of the task.

Completeness requirement: if a fact is not in this YAML, it will be lost.
Include everything you'll need — do not assume you can retrieve it again later.
Lint handoffs with: python3 ~/.hermes/scripts/constraint-binding-lint.py <file>
"""

IMPLEMENTATION_GUIDE = """
Focus Agent Implementation Guide
=================================

Research: arXiv:2601.07190 (January 2026, Nikhil Verma)
Benchmark: SWE-bench Lite (Claude Haiku 4.5, N=5 hard instances)
  - 22.7% total token reduction (14.9M → 11.5M tokens)
  - Identical accuracy (3/5 = 60%)
  - Savings up to 57% on exploration-heavy tasks
  - One task showed +110% (iterative refinement — not a good fit)

Key insight from the paper: the difference between 6% savings (passive prompting)
and 22.7% savings (aggressive prompting) is how the instructions are framed.

WRONG (passive):
  "You may optionally compress your context periodically."

RIGHT (aggressive):
  "ALWAYS call start_focus before ANY exploration"
  "ALWAYS call complete_focus after 10-15 tool calls"
  + Periodic reminders injected by the system every 15 tool calls

Implementation steps for Hermes:
1. Add system prompt snippet to the agent's context (see --mode system output)
2. Inject periodic reminder every 15 tool calls (see --mode reminder output)
3. When agent calls complete_focus, inject the summarization prompt (see --mode summary)
4. After agent writes YAML, delete messages from last start_focus to YAML (exclusive)
5. The YAML block persists at the top of context as the Knowledge block

Phases where Focus Agent helps most:
  - Code exploration: reading files, understanding a repo structure
  - Research: searching papers, extracting findings from multiple sources
  - Planning: gathering requirements, surveying existing tools/patterns

Phases where it helps less (use /compress instead):
  - Tight iterative loops: write code → test → fix → test → fix...
  - Short tasks (< 30 tool calls total): overhead not worth it

Token savings formula (from paper):
  avg_savings_per_compression = (tokens_in_exploration / 1.0) - (yaml_tokens)
  typical yaml block: 200-400 tokens
  typical exploration raw: 1500-8000 tokens
  → 1100-7600 tokens saved per compression checkpoint
  → At 6 compressions/task avg, total savings 6000-45000 tokens/task

Hermes-specific notes:
  - The /compress command in Hermes is coarser than Focus Agent (whole-context)
  - Focus Agent is more surgical: only compresses the exploration phase
  - Use both: Focus Agent within a phase, /compress at phase boundaries
  - Keep the Knowledge YAML in a structured format — free-text summaries
    are harder to retrieve and more likely to get truncated on re-read
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Focus Agent compression prompt templates for Hermes agent loops"
    )
    parser.add_argument(
        "--mode",
        choices=["system", "reminder", "summary", "guide"],
        default="guide",
        help="Which template to output (default: guide)",
    )
    args = parser.parse_args()

    templates = {
        "system": SYSTEM_PROMPT_SNIPPET,
        "reminder": PERIODIC_REMINDER,
        "summary": SUMMARIZATION_PROMPT,
        "guide": IMPLEMENTATION_GUIDE,
    }
    print(templates[args.mode].strip())


if __name__ == "__main__":
    main()
