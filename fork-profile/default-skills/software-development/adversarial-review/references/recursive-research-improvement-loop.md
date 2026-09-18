# Recursive Research-to-Implementation Loop

Pattern for deep research improvement cycles where the goal is saturation,
not a single pass.

## Saturation sweep procedure

Run multiple parallel research waves until diminishing returns:

1. Wave 1: dispatch 5-6 parallel subagents, one per topic cluster, each given
   the full list of already-covered arXiv IDs to skip.
2. Collect results. Count net-new HIGH-priority findings.
3. If >= ~5 new HIGHs exist: spawn Wave N+1 with expanded exclusion lists
   and narrower focus on still-active clusters only.
4. Declare saturation per-cluster when it returns 0-1 new HIGHs. Cap at 5 waves.
5. Only after saturation: implement all accumulated HIGHs, then run adversarial.

Do NOT interleave research and implementation waves. Research to saturation first.

## Implementation triage order

After saturation, apply findings in this order:

1. Safety/correctness bugs in existing scripts (fix before adding new features)
2. Script logic fixes (loop thresholds, key names, exit codes)
3. Config fixes (YAML structure, threshold corrections, label clarity)
4. Skill patches (new protocols, metric qualifications, precedence tables)
5. New scripts (new capabilities)

## Adversarial review loop

After implementation, dispatch a cold adversarial reviewer (different model/provider).
Receive report. Triage all issues (ACCEPT/REJECT/PARTIAL) before touching any code.
Apply all accepted fixes in one batch, then re-verify. Re-dispatch adversarial
if critical/major issues remain. Declare done when only MINOR issues remain or zero issues.

'Wait for it' rule: do not begin fixing until the full adversarial report arrives.
Applying partial fixes before the report hides issues the reviewer would have caught.

## Research wave execution: inline vs delegation

For arXiv sweeps where each wave builds on the previous exclusion list:
- **Prefer execute_code (inline)** for waves 1-N: faster (no delegation overhead, no
  subagent startup), exclusion list is already in kernel state from prior wave, and
  abstract fetching is efficient with web_extract batches of 5 URLs.
- **Prefer delegate_task** only for the cold adversarial review pass: the adversarial
  reviewer MUST be isolated (different model, no session state, reads all files from disk).
  Inline adversarial review with the same model anchors to its own prior output.

Inline wave loop pattern:
  1. Run web_search across 5-6 queries in parallel (single execute_code call)
  2. Parse all arXiv IDs from results; filter against COVERED set
  3. Fetch abstracts for new IDs in batches of 5 (web_extract, char_limit=3000-4000)
  4. Classify each as HIGH/MED/W-only based on: prompt-level implementable? novel vs covered?
  5. Add new HIGHs to next exclusion list; continue to wave N+1
  6. Convergence criterion: wave returns <5 new IDs (not just <5 HIGHs) AND the new IDs
     are all W-only or benchmark-evaluation-only. Typically converges at wave 7-9.

## Parallel implementation batch dispatch

After triage produces 5–10 HIGH findings, group them into 3–4 batches by target surface
(skill-A + script, skill-B + config, etc.) and dispatch one subagent per batch concurrently.
This is faster than serial implementation and prevents a single slow subagent from blocking
the whole session.

Batch grouping heuristics:
- Group findings that share a target file or skill — they can be applied in sequence within
  one subagent without interleave risk.
- Split findings that write to the same SKILL.md across batches only when the sections are
  independent (no heading collision risk). Always grep the skill for existing heading names
  before dispatching, and include the list in the subagent's context.
- Math/CS sweep (interpreter run + triage + implement) always goes in its own batch since it
  is longer and script-heavy; do not co-dispatch with pure-skill-patch batches.

Sweep log update procedure (do this in the parent, not a subagent):
1. Write sweep-NN.md to the appropriate skill's references/ directory with:
   Boundary (cutoff arXiv ID), sweep date, source file path, paper counts per category,
   HIGH/MED/SKIP tallies per finding with arXiv ID + target.
   Math/CS results section (fill in after math subagent returns).
2. Add a boundary row to the SKILL.md table (| sweep | date | from_id | to_id | notes | HIGH | MED | ref |).
3. Do not create the sweep log as a subagent — it requires the parent's triage results.

Post-dispatch parent-side checks (run while subagents are in flight):
- Grep each target skill for the section header the subagent will add — if it already exists,
  steer the subagent before it patches (duplicate heading = corruption).
- Check that `source_text_raw` (or equivalent raw-source field) is defined before use in any
  script patch that references it — undefined variable patches compile but fail at runtime.
- Verify py_compile on any Python file touched by a subagent before calling its batch done.
- **Skill-documents-ahead-of-code gap:** when a skill section says "embed X in metadata" or
  "the script writes field Y", verify the actual script contains the code that does it. Skill
  documentation written before or alongside implementation frequently describes the intent without
  completing the wiring. Grep the script for the field name before calling the implementation done.
  Concrete case: Memory Portability section said "embed model_version tag in Graphiti episode
  metadata" but `l1-graphiti-write.py` had no `model_version` field — the skill was ahead of
  the code by one missed line.

## Convergence criterion

Declare saturation when a full wave of 4-5 distinct search queries returns:
  - No new implementable (P-level) techniques, AND
  - Remaining new IDs are all: W-only (weight/latent access required), benchmark papers
    (evaluation focus only), or already covered by concept (different paper, same rule).
This is stricter than "0 new IDs" (which rarely happens) and avoids false convergence
from running only one query per wave.


Every new or modified script must have an ad-hoc verification battery:
- Write test cases to /tmp/, run them, clean up the temp file in the same command.
- Tests must be written from actual CLI help output (`python3 script.py subcmd --help`),
  not from assumed argument shapes.
- Include both positive (correct behavior) and negative (safety floor, no-trigger) cases.
## Pitfalls for multi-subcommand script patches

- When fixing a bug that affects multiple subcommands in the same script, fix ALL of them
  in the same patch. Patching cmd_check and cmd_prompt but not cmd_reconcile leaves one
  subcommand with the original bug; the cold reviewer will catch it next cycle.
  Pattern: grep the script for all occurrences of the buggy pattern before patching any.

- Write smoke tests from `python3 script.py subcmd --help` output, not from assumed argument
  shapes. Assumed-shape tests can PASS against a wrong interface and hide real failures.

- Run smoke tests with the full production HERMES_HOME env var set, not the kernel's default
  home. Scripts resolving paths via Path.home() write to /root/.hermes in root-owned kernels.

## Verification discipline for scripts (when writing skills from research)

Every numeric claim from a paper must be qualified:
- What model was tested (e.g. Gemini-Flash, Qwen-8B, N=10 debate agents)
- What dataset/benchmark (LOCA-Bench, AIME, WebArena)
- Whether the result requires fine-tuning, logprobs, or latent access
- That the result is NOT reproduced by a prompt-only proxy implementation

Format: `(paper: [model] on [dataset]; not reproduced here; prompt-only proxy)`

Thresholds labeled 'from paper' must be traceable to a specific experiment
using the same method. Lexical heuristics approximating learned classifiers
must be labeled 'uncalibrated lexical proxy; not from paper'.
