---
name: adversarial-review
version: 1.5.0
author: Hermes Agent
depends_on: [requesting-code-review, verification-before-completion]
provides: [adversarial-review, cross-platform-consistency, contradiction-detection]
description: 'Use when: adversarial review is needed before merging multi-part refactors or cross-platform specs. Systematic
  review for self-contradictions, broken references, portability gaps, and inconsistencies.'
keywords:
- qa
- cross-platform
- porting
- contradiction-checking
- self-consistency
- verifiability
license: MIT
metadata:
  hermes:
    related_skills:
    - requesting-code-review
    - risk-based-review
    - verification-before-completion
    - hermes-skill-library-consolidation-audit
    - claude-routing-hierarchy
    tags:
    - review
    - qa
    - adversarial
    - consistency
    - portability
    - pre-merge
platforms:
- linux
- macos
- windows
skills-to-load-first:
- verification-before-completion
title: Adversarial Review
triggers:
- Porting code, config, or agent specifications across platforms (e.g., Hermes → Cowork, macOS ↔ Windows, Docker → Podman)
- Reviewing multi-file refactors or large config ports for internal consistency
- Pre-merge QA when feature descriptions might contradict implementation
- Checking task prompts or docs for unfollowable references, literal placeholders, or platform-incompatible instructions
- Scientific paper synthesis — recursively reviewing molecular/clinical claims for false equivalence, proxy limitations, in
  vitro-to-clinical translation gaps, and funding bias before presenting findings
- Research/knowledge corpus synthesis — reviewing cross-tradition or cross-domain synthesis findings for semantic equivalence
  over-claim, factual errors in specific text strata, analytical framework scope over-application, source quality asymmetry,
  and hermeneutic loop bias. Run the five intellectual attack vectors below.
- Reviewing an AI/agent system design spec (evaluation methodology, autonomy/governance framework, agent rollout plan) against
  domain standards (NIST AI RMF, professional-supervision guidance, OWASP LLM Top 10) before build
- Running a full system adversarial pass across Hermes runtime, config, code, memory topology, and workflows — beyond skills alone: audit config.yaml for silent cost leaks (e.g. MoA enabled after experimentation), script dedup logic vs research findings, MEMORY.md content-type discipline, orphan script archaeology, cron/script consistency, schema design-vs-implementation coherence, and documentation drift vs live system state
- Reviewing a Python utility library after a consolidation refactor — checking for API/docstring contract mismatches, mixed-type
  serialization crashes, sandbox escape vectors, and single-hop vs. transitive logic bugs
- Reviewing a research/analysis deliverable for citation accuracy, fabricated product names, count consistency, dangling gap
  references, and severity-label cohesion — use the recursive loop until no HIGH or MEDIUM findings remain
- Reviewing a research-to-runtime implementation patch (e.g. paper → compressor rule, arXiv → skill preamble, IT concept →
  agent config) — apply the inference-time feasibility gate, proxy overclaim scan, over-eviction risk check, and internal
  consistency check from references/research-citation-checklist.md § Inference-Time Constraint + Proxy Implementation Review
- Reviewing a financial model document (revenue acceleration, NII pull-forward, ROI scenario tables) for formula basis ≠ table
  basis mismatches, hidden multiplier assumptions, and per-loan vs portfolio-level calculation inconsistencies
- Reviewing ML training/evaluation code for holdout discipline, data leakage, temporal leakage, pipeline order correctness,
  and shadow/A/B gate completeness — use the ML holdout checklist in the operating rules below
- Reviewing test suite changes for regression test quality: snapshot auto-accept anti-pattern, mutation testing scope, property
    test invariant adequacy, flaky test introduction, and fuzz corpus discipline
- Reviewing a batch of concurrent skill patches from parallel synthesis agents — checking
  for incoherent same-skill merges (two agents patched the same SKILL.md), write-owner
  circular loops (multiple skills can independently call skill_manage on the same failure),
  human-gate bypasses (interactive session treated as human approval), and over-hardening
  (gates that would block normal non-hazard work)
- Improving or auditing any recursive self-critique / self-review loop design (RCI, Reflexion, Self-RAG pattern variants)
- Reviewing a multi-agent implementation of new reasoning framework subcommands (causal-check,
  boundary-check, lookahead, subplan-verify, hypothesize) — apply projected-state, post-revision
  action, exit-code contract, argparse consistency, docstring currency, and config-script parity
  checks (see references/reasoning-type-taxonomy.md § Adversarial Attack Vectors)
related_skills:
- requesting-code-review
- risk-based-review
- verification-before-completion
- hermes-skill-library-consolidation-audit
- claude-routing-hierarchy
- adaptive-agent-reasoning
---


# Adversarial Review

## Deep Module Design Vocabulary

When reviewing or designing code structure, use this precise vocabulary (from Ousterhout / mattpocock/skills):

- **Module**: anything with an interface and implementation — a function, class, package, or tier-spanning slice.
- **Interface**: everything a caller must know to use it correctly — type signature AND invariants, ordering constraints, error modes, required config, perf characteristics. NOT just the TypeScript `interface` keyword.
- **Depth**: leverage at the interface — amount of behaviour a caller can exercise per unit of interface they must learn. Deep = lots of behaviour behind a small interface. Shallow = interface nearly as complex as implementation (avoid).
- **Seam** (Feathers): place where you can alter behaviour without editing at that place — the location at which an interface lives. Say "seam", not "boundary" (overloaded with DDD).
- **Adapter**: a concrete thing satisfying an interface at a seam. Describes role, not substance.
- **Leverage**: what callers get from depth. One implementation pays back across N call sites.
- **Locality**: what maintainers get from depth. Fix once, fixed everywhere.

Key tests:
- **Deletion test**: imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- **One adapter means hypothetical seam; two adapters means real one.** Don't introduce a seam unless something actually varies across it.
- **Interface is the test surface.** If you want to test past the interface, the module is the wrong shape.

When reviewing code: flag shallow modules (large interface, thin implementation), tight coupling to internal structure, and seams placed at the wrong level.

## When to use

Use this skill when you've built or ported something large (5+ files, multi-layer config, cross-platform spec, agent rules, or docs) and need to catch self-contradictions, portability claims that don't hold, and broken references before shipping.

Also use the **recursive review loop** (below) when the user asks for issues to be fixed and re-reviewed until clean — a single review pass is never sufficient for complex artifacts.

**Not a full test suite.** This is systematic QA for consistency and breakage, not functional verification. Pair with domain-specific test suites if they exist.

**Model (live, `claude-routing-hierarchy`):** this skill is a *procedure*, not a router.
Run it in the current parent session. For a cross-family adversarial pass on our own
routing/config, start a dedicated session `gpt-5.6-sol` via `openai-api` (NOT `custom:openai` — that causes HTTP 400 and silently falls back to Grok; see claude-routing-hierarchy critical fix). Do not set `delegation.model` to Sol (multiplies cost). Do not use Grok to grade Grok.

## Recursive Fix-and-Re-Review Loop

When the user says "fix all issues and re-review until clean," run this loop rather than a single pass:

```
PASS N:
  1. CRITIQUE phase (adversarial stance — do not fix yet):
     a. Review the artifact across all attack vectors (see Operating rules below)
     b. Produce a findings table: severity (HIGH / MEDIUM / LOW), category,
        description, EXACT LOCATION (section heading / line number / token span)
     c. For each finding, state which error class it belongs to
        (contradiction / false_claim / gap / label_drift / structural / count_drift / etc.)
     d. Cross-check: did any of these error classes appear in a prior pass?
        If yes, mark it OSCILLATING — a fix in pass N-1 re-introduced it.
  2. FIX phase (switch to fixer role — not the critic):
     a. Fix ALL findings — high, medium, and low — in the same pass
     b. Re-read the sections you changed to verify the fix didn't introduce new issues.
        EXCEPTION — label/count/heading normalisation fixes propagate silently. If the fix
        changes a token that appears in more than one place (a severity label, a count, a
        renamed heading, a cross-reference), grep the WHOLE artifact for both old and new
        token BEFORE moving on — do not defer this to the next pass.
     c. Update the error-class carry-forward log (see below)
  3. Run PASS N+1 on the full artifact
  4. STOP when: no HIGH or MEDIUM findings remain in a full pass
     (LOW findings in the final pass are acceptable if they don't affect correctness)
  5. ALSO STOP and escalate to human review if:
     - The same finding (same error class + same location) appears in 3+ passes (oscillation)
     - Still finding MEDIUM issues after 6 passes (structural problem, not a patch problem)
```

**Role-split discipline (RCI + Reflexion, 2023):** The critique phase and the fix phase
are distinct mental stances. During critique, take an adversarial position — assume the
artifact is wrong and look for evidence. During fix, switch to a constructive position.
Blending the two in a single cognitive act collapses the adversarial stance and produces
weaker findings. Run them as sequential sub-steps even when the same agent does both.

**Error-class carry-forward log:** After each pass, append to a running log:
```
Pass N findings: [error_class_1 at location_A, error_class_2 at location_B, ...]
Pass N fixes:    [what was changed to address each]
```
Example after a first pass:
```
Pass 1 findings: [label_drift at "findings table header row", gap at "Verification section — no command"]
Pass 1 fixes:    [normalised all severity labels to HIGH/MEDIUM/LOW; added python verify script]
```
Before starting pass N+1, read the log. If an error class reappears at the same location,
it was not fully fixed — mark it OSCILLATING and escalate, do not just patch again.
Concrete pattern (Reflexion, arXiv:2303.11366): verbal trace memory prevents the agent
from repeating the same class of mistake by making prior failures visible at inference time.

**Critique specificity mandate:** Every finding must cite an exact location — section
heading, line range, or quoted token span. Vague findings ("this section is unclear")
are not actionable and should be rejected from the findings table and rewritten before
the fix phase begins. Exact-location citations also enable automated oscillation detection
(same location + same class across passes = oscillation signal).

Also see **Research basis for recursive adversarial loop design** (bottom of this skill) for
the RCI, Reflexion, Self-RAG, and CoT-step-length papers that underpin the loop design.

### Recursive implementation improvement cycle (parallel sweep + cold review)

For large implementation tasks spanning many files and domains, use this cycle pattern instead of a single pass:

```
CYCLE N:
  1. SWEEP phase — dispatch parallel subagents, one per domain cluster.
     Each gets a concrete task spec (what to read, what to implement, compile+test commands,
     where to write the commit). Run cold — no shared state between sweep agents.
  2. REVIEW phase — dispatch a COLD adversarial reviewer concurrently with the sweep,
     or immediately after commit. Reviewer reads the diff from scratch (no summary coaching).
     Require: read every changed file, cite line numbers, give confirmed/false_positive verdict.
  3. FIX phase — triage all confirmed HIGH+ findings from the reviewer. Apply fixes directly
     in the parent session (not another subagent) for precision. Compile + test after each fix.
  4. Commit and push. Begin CYCLE N+1.
  5. SATURATION: stop when the cold reviewer says SATURATING (< 2 confirmed HIGH+ findings
     in a full pass). Final state: only MEDIUM/LOW findings remain or none at all.
```

Key discipline:
- Run sweep and reviewer CONCURRENTLY when the sweep commits first — give the reviewer the
  post-commit SHA explicitly. If they run against the same base, the reviewer finds bugs the
  sweep is already fixing, inflating the confirmed-bug count (stale-snapshot bug).
- Apply HIGH fixes in the PARENT session, not a new subagent — a fixer subagent introduces
  another round-trip and may re-introduce bugs the parent can see directly.
- **'Wait for it' on skill/config patches**: when reviewing a batch of skill patches (not code), dispatch the cold reviewer as a background `delegate_task` and run deterministic parent-side cohesion checks in parallel — do not start fixing yet. Wait for the full reviewer report, then apply ALL confirmed findings in one shot. Splitting into partial-fixes-before-report hides bugs the reviewer would have caught.
- **Deterministic parent checks run while reviewer is waiting**: grep the changed files immediately after patching for mechanically-detectable corruption — literal `\n\n` escape sequences, headings embedded in comment lines, section-placement errors (a section in the wrong skill), duplicate heading names. These are structurally obvious and catch artifact-level defects the LLM reviewer may miss or rate LOW when they are actually HIGH. Run these checks while the cold reviewer is in flight so no time is lost; a literal `\n\n` in a SKILL.md body is a corruption (HIGH), not a style issue (LOW).
- Each cycle's domain list should grow: domains E/F/G/H in cycle 1, I/J/K/L in cycle 2, etc.
  Stop adding domains when you run out of high-value theory-to-practice mappings, not just
  when the adversarial reviewer saturates.
- 'Wait for it' still applies: do not start fixing HIGH findings until the full reviewer report
  arrives. Partial fixes before the report hides bugs the reviewer would have caught.
- Saturation signal is adversarial-reviewer-driven, not sweep-driven. A sweep can always find
  more to implement; the reviewer's <2 HIGH signal is the exit criterion.

Key discipline for the loop:

- Fix ALL severities each pass, not just high first then medium — low issues introduced in a fix cycle compound across passes.
- **RCI + CoT step-out**: before writing the fix, explicitly state "the flaw is X at location Y, the correct form is Z" — this one-sentence critique-then-fix articulation reliably improves fix quality (RCI, arXiv:2303.17491; CoT step-length, arXiv:2401.04925). Do not skip directly from "finding" to "edit."
- After each fix, re-read the changed sections for immediate regressions before moving to the next pass. For label/count/heading normalisation fixes that touch tokens appearing in multiple places, also grep the whole artifact (see step 2b in the loop above).
- Categorise each finding consistently (correctness, false claim, gap, contradiction) so you can tell if the same category keeps producing issues — that's a structural problem, not a one-off.
- A pass that finds only LOW issues is a near-clean pass. One more pass to confirm is sufficient.
- Typical convergence: complex artifacts (skills, specs, multi-section docs) converge in 4–6 passes. If you're still finding MEDIUM issues after 6 passes, the artifact has a structural problem — pause and flag it rather than continuing to patch.

Common new-issue sources when fixing code in docs/skills:
- Pasting two patterns as sequential assignments to the same variable (second silently overwrites first) — use distinct variable names
- Adding a new code example that references an import not present in the block — every code block must be self-contained or explicitly note its dependencies
- Introducing a new method call that doesn't exist in the target library (e.g. `.clear()` on a python-docx paragraph)
- **Projected-state vs actual-state mismatch** — a function computes a projected/speculative state (e.g. `projected = apply(current, action)`) but then passes the ORIGINAL state to the constraint check (e.g. `check(action, self._state)` instead of `check(action, projected)`). The projection becomes dead code, defeating the purpose of lookahead logic. When reviewing any function that: (a) computes a projected or hypothetical state, (b) then checks constraints or guards — verify the check uses the PROJECTED state, not the original. Pattern: grep for `new_state = f(old_state, ...)` and confirm every downstream check in that scope uses `new_state`, not `old_state`. Concrete case (Jul 2026): `ATPGate.propose()` projected state correctly then checked `check_fn(action, self._state)` — constraints ran against committed state, not committed+proposed. This is especially subtle in admission-control, speculative-execution, and pre-flight-check patterns where the whole value proposition depends on checking projected state.

- **Post-revision execution uses the pre-revision action** — a gate that calls `revise(proposed)` to fix a rejected action, then wraps with `execute(proposed_action)` or `commit(proposed_action)` rather than `execute(result["action"])`, silently runs the original rejected draft. The revised action is computed but never used. Pattern: whenever a function calls a `revise()`/`fix()`/`retry()` helper and gets back a result, verify that all downstream `execute`/`commit`/`apply` calls consume the result's output, not the original input variable. Concrete case (Sep 2026): `ATPGate.wrap()` called `revise()` on Step 3 failure but then executed `proposed_action` — the revision became dead code, committing the originally-rejected action. Complementary to the projected-state check: that one is about constraint evaluation; this one is about which action actually gets executed.

## LLM Observer Unreliability — Use Deterministic Scoring (arXiv:2609.04198, Sep 2026) ★ HIGH

Preregistered study: same-window LLM judge repeat rankings agree at Spearman 0.40 against a
required 0.90. Black-box LLM observers on shared endpoints are unreliable quality gates.

**Concrete finding:** Using an LLM-as-judge on a shared API endpoint to score output quality
produces rankings that are reproducible at only r=0.40 Spearman correlation on repeat runs.
This is catastrophically below the r=0.90 threshold required for a credible quality gate.

**Hermes rule:** For any quality gate, eval scoring, or adversarial review step that requires
consistent verdicts across runs:
- Use deterministic scoring (fixed seed, local model, rule-based metrics) NOT black-box LLM judges
- If an LLM judge is unavoidable: pin model + seed + system prompt + temperature=0; log hash of
  all three before each scoring run so drift is detectable
- Never use a shared/production endpoint for eval gates — endpoint-level variation dominates
- Treat any LLM-scored quality metric as directional, not precise. The ±25% and >0.3 margin
  figures are not derived from this paper — they are conservative heuristics. Do not quote them
  as established thresholds. The paper's finding is that repeat rankings agree at r=0.40, not
  that any specific numerical margin is safe.

**Applies to:**
- `adversarial-review` subagent verdict aggregation
- `hermes-swarm-consensus` voting where an LLM grades peer outputs
- Any cron job that uses Claude/GPT to assess its own output quality
- Math/CS paper interpreter confidence scores (note: these are LLM-generated and carry this variance)

## Coalition Reviewer Selection (arXiv:2608.28754)

Greedy coverage-based reviewer selection (k=3) beat random k=5 on catch rate in that paper
(0.968 vs 0.930 — **paper-specific, not a timeless threshold**). Apply only when reviewers
cover distinct decision types; homogeneous same-model reviewers degenerate to random.

**BoN certification is not a practical quality gate** when N_high > 2 (spike 003, invalidated
2026-09-08). Report P_cert with the verdict; do not claim "sufficient coverage."

## Reviewer Pool Quality

DP threshold policy (math-008, paper-only): in a calibrated reviewer pool, threshold at p>0.70 per voter has cost ratio 0.944. Hermes has no per-reviewer accuracy ledger today. Practical application: use heterogeneous-model majority vote (e.g. grok-4.6 + claude-sonnet-4-6 + gpt-5.6) until a reviewer accuracy log exists. Revisit trigger: cobra-outcome logs grow a reviewer-accuracy field.

## Operating rules

1. **Identify contradiction vectors** — categories where the code or config could contradict itself:
   - Stated compatibility vs. actual platform checks
   - API/endpoint references vs. documented unreachability
   - Count claims ("5 jobs") vs. actual enumeration
   - Placeholder syntax (YYYY-MM-DD) in code that should be concrete
   - Task prompts referencing endpoints that connectors explicitly forbid

2. **Build a portability matrix** — for cross-platform ports, list each component and mark portable/non-portable:
   - Hermes-specific cron jobs → non-portable to Cowork/Claude Cowork
   - Linux-CLI tools (rootless-podman, silverblue-*) → non-portable to macOS/Windows
   - macOS-only skills (`apple-notes`, `apple-reminders`, `findmy`, `imessage`, `macos-computer-use`) → macOS only; present on Linux hosts = dead weight
   - Hermes cron `no_agent: true` + `prompt` field → prompt is dead code (see pitfall below)
   - localhost services → blocked in isolated VMs
   - Browser-based Computer Use → works everywhere once port syntax is right

3. **Validate placeholder patterns** — if docs use placeholders (YYYY-MM-DD, <TODAY>, [TOPIC]), ensure:
   - No placeholder appears bare in code blocks without a nearby substitution instruction
   - All references to the placeholder are consistent (not sometimes `YYYY-MM-DD`, sometimes `[DATE]`)
   - Task prompts don't ask the user to substitute while the example shows a literal

4. **Enumerate and verify counts** — if docs claim "N items", spot-check:
   - Count actual items in the source
   - Check all stated items are mentioned in all documents that reference them
   - Flag discrepancies before merge

5. **Check for unfollowable references** — scan task prompts and instructions for:
   - API references that don't exist in the target platform (e.g., "list session artifacts" → no such API in Cowork)
   - Endpoints documented as unreachable in the same repo
   - Steps that assume a feature that was explicitly ruled out elsewhere

6. **ML holdout and regression-test attack vectors** — when reviewing ML training/eval
   code or test-quality claims, load
   `skill_view(name='requesting-code-review', file_path='references/regression-testing-and-model-runs.md')`.
   Headline checks (do not treat paper % as timeless): no preprocess-before-split; no
   `train_test_split(shuffle=True)` on time-ordered data; mutation score over raw coverage;
   do not auto-accept snapshots to green CI. Quantified leakage/flaky-test figures live in
   that reference and must be re-verified against the cited papers before quoting.

8. **Skill/agent integrity: CDH (Convergent Detour Hijacking) check** — when reviewing a skill, agent prompt, or multi-agent workflow spec (arXiv:2608.12273, Sweep 12):

   **What CDH is:** A skill or agent whose *description* correctly matches the trigger intent, but whose *body* routes through unrelated tool calls before completing the task. The task succeeds and the output is correct — but token cost and latency spike because the body detours through unnecessary work. Evidence: CDH attack causes +66.91% token overhead, +92.45% latency, 80.02% coordinator selection rate even when output is correct. <!-- why: prevents treating correct output as proof of uncompromised trajectory in skill-review sessions -->

   **Key principle:** Correct task output does NOT equal trajectory integrity. A skill that produces the right answer via an unnecessary detour through 3 extra benign skills has still been compromised.

   **3-point CDH checklist (HIGH severity when any point fires):**
   1. Does the skill body's first 2–3 tool calls semantically match the declared trigger semantics? If not, flag as detour candidate.
      - A skill that triggers on "search arXiv" should open with `web_search`/`arxiv` calls — not a file read, memory write, or code execution
      - A skill that triggers on "review a PR" should open with `gh pr view` or similar — not a Hindsight recall of unrelated sessions
   2. Does token cost or tool call count spike anomalously vs session baseline? Spikes > 2x baseline signal an active CDH detour.
   3. Does wall-clock latency spike unexpectedly (>2x baseline for the task type)? Also a detour signal.

   **Hermes-specific patterns to check:**
   - Skill body references `hindsight_recall` or `session_search` as its FIRST action when the trigger is about external data retrieval — memory lookup before fetching is often a detour
   - Skill body calls `skill_view` on a skill that isn't a declared dependency of the current task — implicit detour loading
   - Multi-agent workflow: coordinator dispatches to an agent whose subprompt triggers a chain of unrelated agents before returning — check that coordinator → agent hops are direct, not convergent

   **Resolution:** If a CDH pattern is found, either (a) remove the detour steps and verify the task still completes correctly, or (b) if the steps are genuinely needed, move them to a declared `depends_on` skill and load explicitly.

## Verification checklist (ad-hoc, not unit tests)

```bash
# 1. No breaking platform assumptions in task prompts
grep -r 'localhost:' scheduled-tasks/ workflows/ connectors/
# should find NONE in code blocks, OK in explanatory notes

# 2. No bare placeholder literals
python3 -c "
import re, pathlib
for f in pathlib.Path('.').rglob('*.md'):
  src = f.read_text()
  blocks = re.findall(r'\`\`\`.*?\`\`\`', src, re.DOTALL)
  for b in blocks:
    if re.search(r'YYYY-MM-DD\.md|<TODAY>\.md', b):
      print(f'FAIL: {f}')
"

# 3. Stated counts match actual counts
grep "Total.*:" README.md  # e.g., "Total skills: 185"
ls -1 skills-catalog/*.md | wc -l  # should match

# 4. All enumerated items listed
for item in $(grep "^##" scheduled-tasks/README.md | cut -d' ' -f2-); do
  grep -q "$item" CLAUDE.md || echo "MISSING in CLAUDE.md: $item"
done

# 5. Portability claims not contradicted elsewhere
grep "Not portable" scheduled-tasks/README.md
grep -r "localhost" connectors/  # should document explicitly if it blocks the item
```

## OBLIVION — Workflow-Level Skill Unlearning (arXiv:2608.08264, Aug 2026)

After a skill is removed from the registry, residual carriers (archives, transcripts,
schemas, memory) can reconstruct it. Attack-success numbers in the paper are **not**
timeless. Review check: grep Hindsight, Graphiti, cron `context_from`, and session
history for the revoked name and tombstone all carriers together. Evaluate revocation
at workflow level, not just the skill file.

## Recursive Global Coherence Audit Pattern

When auditing a system with many interacting surfaces (scripts, skills, config, feature lists,
memory), a single narrative audit pass misses cross-surface drift. Use a **named-check catalogue**:

1. Build a catalogue of named checks: `(id, severity, label, fn)`. Each `fn` returns `(bool, detail)`.
   Group by surface dimension (CLI correctness, AST validity, config keys, skill flag correctness,
   cascade order consistency, feature index completeness, behavior scenarios).
2. Run the catalogue. For FAIL items: fix the underlying code/skill/config AND fix the check
   logic if the check regex/path was wrong — a false-PASS is as dangerous as a false-FAIL.
3. Rebuild the catalogue (do not reuse a stale kernel that references old local variables) and
   re-run. Repeat until 0 CRIT, 0 HIGH, 0 MED.
4. Name each check with a stable ID (D1-04, D5-02) so oscillating failures are detectable
   across waves without keeping a manual log.

Pitfalls specific to this pattern:
- Check logic that tests the wrong YAML path (e.g. top-level vs nested canonical path) will
  report PASS while the real system is broken. After writing any config patch, confirm the
  check reads from the same path the system actually consumes (see attack vector 9 above).
- Single-line regex checks on multi-line CLI invocations produce false PASSes — a command
  split across continuation lines (`\`) will not match a single-line `re.search`. Use
  multi-line block scanning (join a N-line window around each `python3` invocation) instead.
- After fixing check logic, the kernel must be reset — stale `checks` list from a prior
  `execute_code` run still references old functions and will re-PASS the old broken check.
  Reset explicitly: pass `reset=True` to `execute_code` or rebuild the catalogue in a fresh block.
- Variable name casing mismatch between check regex and real code: if a constant is defined as
  `CASCADE_ORDER = [...]` (uppercase) but the check searches for `cascade_order\s*=\s*\[` (lowercase),
  the check always passes as a false-PASS regardless of the actual value. Match the exact casing
  and bracket syntax (`[...]` vs `(...)`) used in the real code.
- **Argparse `required=False` with a plausible-sounding `default=` is the silent-default failure class:**
  a flag like `--framework-a` with `default='framework-a'` silently produces misleading output
  instead of rejecting the call. When reviewing argparse for required semantic args, verify
  `required=True` on every arg whose absence makes the output meaningless — not just args whose
  absence causes a crash.
- **Heuristic scope narrower than the data it should scan:** a `false-attribution` check that
  only inspects `context` for supporting evidence misses evidence embedded in the `claim` itself
  (e.g. "as confirmed by three RCTs with p<0.001"). Heuristic signal-search must span all inputs
  that could carry the relevant signal. When reviewing heuristics that classify risk or quality,
  verify the search scope covers ALL string inputs, not just the ancillary ones.

- **Shell-var-in-python false-positive from scanning the wrong scope:** a regex like
  `re.findall(r'\$[A-Z_]+', block)` applied to the full wrapper source will match the
  `CONFIG="$CONFIG" python3 -c` env-var prefix assignment and report a false positive even when
  the python string itself is clean. The correct check: extract only the text BETWEEN the outer
  quotes of the python -c argument, then scan that interior for bare `$VAR` patterns. Env-var
  assignment prefixes live outside the quotes and are safe.

- **Multi-line python3 -c block not matched by single-line regex:** a single-line
  `re.findall(r'python3 -c [\'"].*?[\'"]\n', src)` does not match multi-line heredoc-style
  `-c` arguments (where the closing `"` is on its own line). Use `re.findall(r'python3 -c "(.*?)"(?=\n)', src, re.DOTALL)` to capture multi-line blocks correctly, then scan the captured group.
  A check that silently returns 0 matches because the regex did not span newlines will report
  a false-PASS, not a false-FAIL — making it a worse class of error.

## Common Pitfalls

Load `references/common-pitfalls.md` for the full list. Do not skip these five:

- **Self-review independence gap** — recursive loop by the same agent that made the changes
  cannot close its own blind spots. After the self-loop, dispatch one cold subagent (different
  model, file paths only, no problem-statement coaching).
- **Oscillating findings** — same error class + location across passes → escalate, do not
  patch again. Keep an error-class carry-forward log.
- **Blended critique/fix stance** — critique then fix as sequential roles (RCI / Reflexion).
- **`no_agent: true` + non-empty `prompt`** — prompt is silently dead in Hermes cron.
- **Re-litigating changelog-resolved concerns** — read the artifact’s own revision history
  first; only re-open as “regression on previously-resolved concern.”
- **Two-condition gate: test all four quadrants, not just the obvious two** — when a guard fires on `A AND B` (e.g. `new_floor < old_floor AND new_floor < current_rearm`), tests must cover: (1) both true (tightening), (2) A false/B true (loosening-but-below-rearm — the bug quadrant), (3) A true/B false (tightening-but-above-rearm), (4) both false (clearly looser). The "loosening-below-rearm" quadrant is systematically missed because testers write a "clearly tighter" case and a "clearly looser" case — both of which fail to trigger the broken single-condition guard. Mutation-test by removing each sub-condition separately; if removing one leaves all tests green, a quadrant is missing. <!-- why: the old single-condition `new_floor < current_rearm` guard fires on loosening (quadrant 2), which collapses hysteresis and forces immediate cache-break; the only test that catches it exercises precisely that quadrant -->

- **Subagent live transcript log lines are truncated at ~600 chars** — the delegation log daemon truncates long assistant-message lines with `…(+N chars)` in the `.log` file. `terminal` grep and `read_file` both see the truncated form. To recover the full text: use `execute_code` to open the `.log` file as Python and read the raw line bytes directly (`open(path).readlines()[N]`). The full text is in the file; only the display layer truncates. If a subagent's findings are in a long final message, always read them this way rather than through `terminal`. <!-- why: terminal output is itself capped, so truncated log line + terminal cap = double truncation; execute_code reads directly from the file object and prints the full string -->

- **Test collection import errors mask real failures** — running a broad test directory (e.g. `tests/agent/ tests/plugins/ tests/tools/`) against a fork or fresh-clone environment can hit `ImportError` on optional dependencies (`snowballstemmer`, `wcwidth`, etc.) that are not installed, causing pytest to report ERRORS during collection and exit without running any tests. Always run the narrow targeted suite over the files you changed, then separately confirm any broad-suite collection errors are pre-existing upstream (check on the base commit with `git stash`). Never treat a broad-suite collection error as confirming the fork is broken.

  plus fix-and-retest instructions will regularly hit a 900s timeout. Scope to one category
  per agent, or dispatch parallel per-category agents, or instruct the agent to write a
  partial result file at the first stopping point so the parent can recover partial work.
  A timed-out agent with no result file delivers nothing. Always have the agent write its
  result to a `/tmp/` file incrementally, not only at the end.
- **Parallel optimizer + adversarial reviewer stale-snapshot bug** — when an optimizer agent
  and a cold adversarial reviewer run concurrently, the reviewer reads the pre-optimization
  commit and produces confirmed findings for bugs the optimizer has already fixed. This
  inflates the confirmed-bug count and wastes the reconciliation pass. Correct sequencing:
  optimizer commits first, adversarial reviewer dispatches AFTER the commit lands. If you
  need a parallel run for speed, give the adversarial agent the post-optimization commit SHA
  explicitly and have it `git checkout <sha>` before reviewing — never let it default to HEAD
  from an earlier snapshot. <!-- why: stale snapshot produces confirmed=true findings that
  are already resolved, requiring a full re-triage pass to filter them out -->
- **Same-model conflict of interest in adversarial review** — dispatching a model to adversarially
  review claims about itself produces a structurally compromised pass. Grok-4.6 reviewing claims
  that "Grok workers deliver 4x token efficiency" cannot be independent — it is the model being
  evaluated. The adversarial subagent identified the claim as `need_more_context` but could not
  call it FLAWED, which is the correct verdict for an unvalidated overclaim. Cross-family is
  mandatory for routing/model claims: use Sol (`openai-api`) to grade Grok, and vice versa.
  The "Do not use Grok to grade Grok" line in the Model section is the rule; this pitfall explains
  the mechanism: same-family reviewers systematically under-flag positive claims about themselves.
  <!-- why: adversarial integrity requires the reviewer to have no stake in the verdict; a model
  reviewing its own performance class has an implicit stake even without intent -->

- **Adversarial reviewer timeout recovery** — a cold adversarial reviewer (especially on gpt-5.6-sol
  via openai-api) may timeout at 900s if it tries to spawn a nested subprocess or `hermes chat`
  to invoke a different model. This approach is always wrong: adversarial reviewers must be
  dispatched from the PARENT via `delegate_task`, not self-spawn via shell. When a reviewer
  times out, read its partial `.log` transcript to recover what citations and findings it had
  gathered before the timeout, then re-run the pass in-session (for simple artifacts) or as a
  fresh `delegate_task`. Do not re-run with the same approach that caused the timeout.
  <!-- why: nested hermes subprocess inside a subagent creates a process deadlock waiting
  for stdin; the subagent's 900s wall clock expires without result -->
- **Hermes wiring sprint: `sys.exit()` in shadow/lock handler is a shadow violation** — calling `sys.exit()` inside a `BlockingIOError` handler or any except block terminates the process before `finally` blocks run and before atexit handlers fire, leaking lock FDs and preventing clean teardown. It is re-raise-equivalent. Correct pattern: a module-level `_LOCK_HELD = False` bool set on successful acquisition; an `atexit` handler that releases the lock when held; and `if not _LOCK_HELD: return` at the top of `main()`. When reviewing any lock or resource-acquisition pattern, check that the failure branch uses `return` or `print(stderr)`, never `sys.exit()` or `raise SystemExit`.
  <!-- why: sys.exit() inside an except block is not caught by any enclosing try/finally; the lock fd is never closed; atexit never fires; on the next invocation the lockfile is stale and the script may silently not run -->\n\n- **Hermes wiring sprint: non-atomic writes to shared state files cause data loss on crash** — bare `path.write_text(json.dumps(data))` on a shared cache file is not atomic. A crash between truncation and final write leaves a zero-byte file that resets all learned state (routing weights, trust posteriors, calibration thresholds, adaptive TTL). Required pattern for every cron script writing JSON state: `_tmp = path.with_suffix('.tmp'); _tmp.write_text(json.dumps(data)); _tmp.rename(path)`. POSIX `rename()` is atomic within the same filesystem. When reviewing any cron script, grep for bare `.write_text(json.dumps(` and verify each uses the tmp+rename pattern.
  <!-- why: os.rename() is atomic on POSIX within the same filesystem; write_text is not; a crash between open-for-write and fsync produces a zero-byte file that json.loads() cannot parse, silently resetting all learned state -->\n\n- **Hermes wiring sprint: `schedule: {}` empty object means the cron job never fires** — when adding new entries to `jobs.json`, an empty `schedule: {}` object is not a valid schedule; the Hermes cron daemon requires at minimum `{"kind": "cron", "expr": "..."}` or `{"kind": "interval", "minutes": N}`. Always verify the schedule key is non-empty after patching. Pattern: grep for `"schedule": {}` in jobs.json after any programmatic write. A job that appears successfully added but has `schedule: {}` will silently never fire, and ARCHITECTURE.md closure claims for that cron entry are false closures until fixed.
  <!-- why: execute_code wrote the schedule key but the cron-expr fields defaulted to an empty dict; the daemon reads the kind field, finds it absent, and the job is registered but never enqueued -->

- **Hermes wiring sprint: Python forward-reference NameError — function defined after its call site** — when patching a script that adds a new function, always verify that the definition lineno is less than the call site lineno. `ast.parse` validates syntax only and never catches forward references in function bodies — the NameError is a runtime error. Fix: locate both linenos explicitly before patching; if def_lineno > call_lineno, move the definition block above the enclosing function that contains the call.
  <!-- why: ast.parse passes; NameError only surfaces when the code actually runs, which for a cron script may be days later -->

- **Hermes wiring sprint: EMA anchored to hardcoded constant produces a stateless filter** — an EMA `updated = CONST * alpha + observed * (1-alpha)` that never reads back the prior value from disk always anchors to CONST regardless of run count. Always verify the three-step pattern: load prior → compute EMA using prior → save. When reviewing any IIR filter in a cron script, check that it reads its own prior output before computing the next value.
  <!-- why: a script that writes a threshold file but does not read it before computing the next threshold is a stateless transform disguised as a stateful filter; it converges to CONST + a fixed fraction of observed, not toward observed -->

- **Hermes wiring sprint: undefined name in `except` block breaks the intended safe fallback** — when an `except` clause references an undefined name (e.g. `logger_mh.debug(...)` with no logger defined), the except block itself raises NameError, which propagates out of the try/except and crashes the caller. The "safe fallback" becomes the crash path. After writing any except clause, grep the file for every name it references; if any lack an assignment or import, replace with `print(..., file=sys.stderr)`.
  <!-- why: NameError inside an except block is not caught by the same try/except; it propagates as an uncaught exception, defeating the shadow-pattern intent -->

- **Hermes wiring sprint: function defined but never called = dead code, not wired** — defining a function in a script and adding it to ARCHITECTURE.md as "closed" is a false closure. A wiring check requires confirming a live call site: grep the entire scripts directory for the function name and verify at least one call site exists outside the definition. New functions added by subagents are especially prone to this because subagents can only write to the file they own; the caller is in a different file they do not own.
  <!-- why: subagent owns one file; the caller lives in another; without a cross-file call site the function is dead code and the advertised integration never fires -->

- **Book-to-skill parallel ingestion: description field capped at 60 chars by skill_manage** —
  `skill_manage` create rejects frontmatter `description` strings longer than ~60 chars with a
  routing-budget error. When dispatching parallel book-ingestion subagents, instruct them to use
  a short trigger in the frontmatter (`description: "Use when <trigger phrase>."`) and put the
  full user-facing description in the skill body. Do not retry with the same long string.
  <!-- why: the 60-char budget is a routing index limit enforced at create time; the body
  has no such constraint and is the right place for extended trigger text -->
- **Importance-biased eviction must match session-type intent** — a pruner that evicts
  messages with the lowest importance score (e.g. user/assistant turns at 0.7) is a harmful
  operation in research sessions, where mid-conversation history IS the payload. The same
  pruner is beneficial for code sessions where repetitive boilerplate dominates. Enable
  aggressive eviction strategies only for the session type where redundancy outweighs history.
  When reviewing a prune/eviction strategy, verify the enabling condition checks session type:
  code=enable, research=disable, mixed=default conservative. Inverting this causes silent
  unique-history deletion that is exactly the opposite of the stated research goal.
  <!-- why: importance scorer roles (tool=1.0, user/asst=0.7) appear to protect tools
  while deleting history; for research sessions history is the high-value content, not tools -->
- **Telegraphic/compressor threshold must be consistent end-to-end** — a gate function (e.g. `should_compress`) that fires at threshold X and a compressor function (e.g. `compress()`) that passthrough-returns for content up to Y where Y > X creates a silent dead zone: the gate says "compress this" but the compressor does nothing. Pattern: whenever reviewing a two-function gate/execute pair, verify both functions use the same threshold constant, not independently hard-coded values. Concrete case: `should_compact` fired at 2000 chars, `compact()` passthrough-returned at <=4000 — payloads 2001–4000 chars triggered the gate but received zero compression.
<!-- why: the gate and compressor look correct in isolation; the mismatch is only visible by comparing their thresholds side-by-side -->

- **A PluginContext method with no call site in the live path is dead code, not wired.** When auditing plugin systems, grep for actual call sites of every public method — defining a method on a context object (e.g. `compact_tool_result`) and defining a hook dispatch point (e.g. `transform_tool_result`) are separate steps. The method only becomes active when a plugin registers a callback that invokes it. Existence of both does not imply wiring.
<!-- why: auditors read both the method definition and the hook registration and assume wiring; the grep proves otherwise -->

- **Pre-recorded transcript batch pre-pass degrades recall vs live hook** — when a compressor is applied as a batch transform over a pre-existing transcript (rather than live on each new tool result), it strips literals that the compressor's own summary pass would need later, collapsing recall. Confirm placement: compressors belong as live hooks on each new message entering context, not as retroactive batch transforms. Verify this by running eval with both arms; recall drop >15pp is the signal.
<!-- why: the compressor was designed for live context management; retroactive application removes the ground-truth literals it needs to reconstruct signal during summary generation -->

- **Plugin context attribute that needs session-scoping must be cleared at finalize, not just set at start** — if a PluginContext attribute (e.g. `_session_id`) is written in `on_session_start` but never cleared in `on_session_finalize`, a long-lived gateway context carries the previous session's value into the next session. This causes session-2 code to operate on session-1 data (wrong predicates, wrong type lookups). Fix: always pair attribute writes at `on_session_start` with an explicit `None` or reset at `on_session_finalize`. The liveness of a PluginContext across `/new` boundaries is the failure mechanism.
  <!-- why: gateway reuses PluginContext objects; session_id written in session 1 survives until on_session_finalize clears it; any method reading _session_id in session 2 before finalize gets the wrong value -->
- **Plugin API docstring example as live contract** — a plugin system's docstring hook
  example (e.g. `def on_pre_llm_call(ctx, agent=None, **kw)`) is the primary template
  developers copy. If `ctx` is not in the actual payload, every plugin copying this example
  fails with TypeError at dispatch time — not at load time. Review plugin API docstrings
  with the same adversarial posture as code: trace what kwargs the dispatcher actually
  passes, then verify the docstring example signature matches. A plausible-looking example
  that silently mismatch the real payload is a HIGH-severity documentation bug.
  <!-- why: hook failures at dispatch time are hard to diagnose without knowing the
  dispatcher's actual kwargs; docstring examples are the only spec most plugin authors read -->
- **Hook name resolves per-turn not per-session** — in Hermes plugin systems, hooks named
  `on_session_end` or similar may fire at the end of EVERY TURN (via turn_finalizer), not
  at actual session end (process exit or `/new`). Always grep the hook dispatcher source
  (e.g. `turn_finalizer.py`) to confirm the actual firing cadence. Use the true session-end
  hook (e.g. `on_session_finalize`) for cleanup/state-eviction that must survive across
  turns. Misusing a per-turn hook for per-session cleanup causes state to be wiped on every
  message — 3-turn lock patterns and session-scoped caches both break silently.
  <!-- why: the hook name implies once-per-session semantics but the dispatcher fires it per-turn; cleanup code clears state it should be accumulating -->
- **Profile knobs leak across session resets** — `bind_session_state()` (or equivalent
  session-rebind path) typically resets cooldowns and counters but NOT plugin-mutated
  knobs like `threshold_percent`, `protect_last_n`, `proactive_prune_tokens`, and boolean
  flags like `importance_biased_prune_enabled`. After a `/new` command the compressor is
  reused with stale profile settings from the prior session. Fix: snapshot config-default
  values at `__init__` and restore them in the session-rebind call. Grep `bind_session_state`
  and verify it resets ALL plugin-mutable fields, including boolean enablement flags.
  <!-- why: compressor is long-lived; /new rebinds session context but does not reinstantiate the compressor object, so plugin profile mutations persist -->
- **AEP floor budget formula must be context-length relative, not self-referential** — a
  formula like `budget_bits = H * tokens * 0.5` yields `floor = ceil(tokens/2)`, which is
  always less than `tokens` and never blocks compression. The floor is meaningless. The
  correct formula anchors to available context: `budget_bits = H * context_length * target_fill`
  so the floor reflects how many tokens are needed to reach the information density of a
  full context window — not a fraction of what is already there.
  <!-- why: self-referential budget scales with current tokens, so floor < tokens always holds; context-length anchor produces a floor that can actually exceed current tokens when context is sparse -->
- **Subagent config.yaml write blocked** — Hermes security guard refuses skill_manage
  and patch tool writes to `~/.hermes/config.yaml` in subagent context. Parent session
  can write config via `terminal()` with a heredoc Python script. Steer blocked subagents
  to write config changes to a staging file and surface them as OPEN_ISSUES for the parent
  to apply.

When findings are produced by subagents or reviewers, require a **three-way verdict** per finding rather than a confidence score:

- `confirmed` — finding is real, supported by code evidence, action required
- `false_positive` — finding does not hold up under full context; discard
- `need_more_context` — ambiguous; surface for human inspection rather than auto-pass or auto-fail

Three-way verdicts beat confidence percentages: a calibrated-sounding score (e.g. "85% confident") is unreliable as a hard filter and forces a binary decision on inherently ambiguous findings. `need_more_context` creates an explicit third lane that prevents both silent pass and unnecessary blocking.

This applies to the Recursive Fix-and-Re-Review Loop, the Meta-review pattern, and any use of subagents for adversarial verification.

## Critic KILL Scope-Narrowing Recovery

A KILL verdict from an adversarial critic is binding on the failure domain the critic
analyzed — not on all possible scopes of the spike. When a critic's stated failure mode
is domain-specific (e.g. "fails on tool-heterogeneous embeddings"), the spike can be
reinforced with a narrowed scope that excludes the failed domain.

Procedure:
1. Read the critic's failure mode: is it universal or domain-specific?
2. If domain-specific: rewrite the spike's scope to exclude that domain explicitly.
3. Mark as "UN-KILLED, scoped" with the critic's failure domain listed as out-of-scope.
4. Do NOT apply the narrowed spike to the excluded domain without a new full chain evaluation.
5. If a second independent source (e.g. a later empirical paper) confirms the spike works
   in a domain the critic did NOT analyze, that is positive evidence for the narrowed scope
   — not a contradiction of the critic's verdict.

Pitfall: treating a KILL on domain A as a KILL on all domains. The critic evaluates the
scope they were given. If the spike was specified too broadly, narrow it and resubmit;
do not abandon the entire idea.

Concrete case (Sep 2026): Spike K (geometric loop detection via cosine distance) was
killed because cosine-distance early-stopping fails on tool-heterogeneous trajectories
(file path vs code vs error text embed in incompatible spaces). Wave 2 empirical paper
(arXiv:2606.27009) confirmed the same heuristic works reliably for homogeneous text
refinement loops (writer-critic, summarization). Spike un-killed and scoped to text
refinement sub-loops only; tool-heterogeneous exclusion preserved as permanent out-of-scope.

## Adversarial Consensus Roster (pre-planning, contested proposals)

For contested proposals or architectural decisions BEFORE a plan is written, run an adversarial consensus rather than a single planner's confidence. This is distinct from the post-fan-out verdict reduction in `hermes-swarm-consensus` — use this when the question is "should we do X" not "which agent is right."

Seat 3–5 perspectives; no two seats argue the same angle:

| Seat | Attacks from |
|---|---|
| skeptic | The assumption being treated as fact. Asks what breaks if the load-bearing assumption is false. |
| validator | Verifiability. Asks how anyone would know this worked, and what the failing case looks like. |
| researcher | Prior art and current behavior. Asks what the sources, upstream docs, or existing code already say. |
| architect | Structure and blast radius. Asks what else this couples to and what it makes impossible later. |
| creative | The unexamined framing. Asks what a different shape of the solution would cost, including doing nothing. |

Substitute a domain seat (security, cost, operations, accessibility) when the problem warrants it. A duplicated angle buys nothing while making the run look broader than it is.

Three rounds in order — the order is the contract, do not reorder:

1. Independent findings: each perspective produces findings without seeing any other's output. Every finding names its evidence or labels itself an assumption. Record ALL findings before opening round two. If a single-context window prevents true blindness, mark the round's independence as caveated — a caveated round is still useful; a run that silently claims independence it did not have is not.
2. Cross-attack: every perspective attacks OTHER perspectives' findings and never defends or restates its own. Self-defense in this round is the most common way the exercise produces agreement disguised as review.
3. Defend, refine, or concede: each perspective responds to attacks. "Defend" means defend with new evidence — not restatement; "concede" means the objection stands.

The bundle from round 3 is INPUT to planning, not the plan itself. Emitting a plan from this step skips the reviewed-plan gate. Hand the distilled objections to the planning step.

<!-- why: agreement reached by perspectives that read each other is convergence not review; independent findings plus an attack round nobody can defend in produce objections a single planner never surfaces -->

## Code Review Completion Checklist (both axes required)

When producing a code review, both axes must appear in the report:

1. Correctness/risk axis: ranked findings by severity, each citing file, diff, command output, artifact, or expected behavior evidence. Findings come FIRST before summary or praise.
2. Spec-axis verdict: explicitly name the Claim source being reviewed against, or state not_assessed with the reason.

No-issue reviews still require:
- Named residual risk (what could still go wrong)
- Missing tests and their gaps
- Independent review evidence if unavailable — say so directly instead of implying a second reviewer passed it

"Attempted" is not "addressed." A fix is done when the specific defect no longer reproduces, shown by the same command that showed it. A commit message saying it was fixed is not that command.

Fix implementation, architecture follow-up, and CI/merge claims stay separate from the review result — the review names the issue; the executor closes it with observed evidence.

<!-- why: merging correctness and spec axes in one prose blob lets one pass cover neither; separating them makes gaps explicit -->

For critique/review documents delivered to a reader (design reviews, PR reviews, paper
syntheses), include an explicit "Adversarial Self-Review Notes" section in the final
output itself — not only as an internal step you perform before finalizing. Document,
in the reader-facing text:
- what self-contradiction or unwarranted-certainty check you ran across your own draft
  findings (e.g. "does praising X as a strength contradict rating Y as high-severity
  elsewhere? confirmed these are distinct axes, not a contradiction")
- any severity or claim you walked back after reconsideration, and why (e.g. downgrading
  "unprecedented risk" to "significantly sharpens an existing risk" after checking
  whether the risk category was actually novel or just newly automated)
- confirmation that every citation appearing in your own review text was itself checked
  before inclusion, with unverifiable ones explicitly marked rather than asserted
This costs one extra section but converts "trust my QA process" into an inspectable,
falsifiable trail the reader can check — and it forces you to actually do the adversarial
pass rather than assert it happened. Treat a review deliverable with no visible self-review
trail as incomplete, the same way an untested code change is incomplete.


### Meta-review: nuance axis + over-correction risk
The nuance axis assesses whether the artifact is balanced vs one-sided. Flag when a synthesis:
- Makes no acknowledgment of valid counter-evidence or competing frameworks
- Uses hedging language (might, could, arguably) so consistently it becomes meaningless
Over-correction failure mode: reviewers trained to find flaws will manufacture them when none exist. The meta-review must ask: Is the review itself balanced? Does the adversarial review apply the same critical standard to its own objections as it does to the artifact?

*Meta-review pattern (auditing a critique/review document itself) — see references/meta-review-pattern.md.*

*Pitfall: critiquing docs that already have changelog/revision sections — see references/pitfall-changelog-docs.md.*
## Rendering Floor + Completion Contracts

Findings need a surface-agnostic **rendering floor** (decision-first, HIGH/MEDIUM/LOW only,
per-surface layouts) and skills with a handoff are not done until the user-chosen action
is executed (pipeline mode excepted). Full contract text:
see `references/rendering-floor-and-completion-contracts.md`.

## See also

- **references/math-research-pipeline-adversarial-checks.md** — Adversarial checks for patches derived from a math primers → paper classification → spike pipeline: authority laundering detection, CP edge-case numeric verification, LTL schema separation, Beta cold-start bypass, hash-chain-in-fact-text failure, skip-gate path coverage, and system surface mapping (scripts/config/cron, not skills alone).

- **references/legal-tech-product-name-verification.md** — verified legal-tech product names (Lexis+ AI, Westlaw Advantage, iManage Knowledge Unlocked, CoCounsel Legal, Harvey, Luminance, EvenUp) and verified legal NLP arXiv IDs (CUAD 2103.06268, ContractNLI 2110.01799) with fabrication-counterexamples and verification patterns. Use before writing any competitive landscape or build-or-buy section touching legal tech.
- **references/nii-pull-forward-model.md** — worked example of the formula basis ≠ table basis failure mode in an AU bank NII pull-forward model (trust deed AI, Aug 2026): arithmetic derivation, how to detect the hidden loan-life multiplier, and a Python verification snippet for financial scenario tables.
- **references/hermes-to-cowork-adversarial-checks.md** — worked example: actual findings and fixes from a real Hermes agent port (contradictions, count drift, placeholder literals, missing specs, platform blindspots).
- **references/scientific-paper-adversarial-synthesis.md** — recursive pass methodology for scientific paper review: attack vectors (false equivalence, proxy limitation, in vitro-to-clinical gap, overexpression bias, mechanism-to-outcome causality, funding bias), severity table, Sirina et al. 2026 worked example, **plus clinical literature brief vectors** (abstract≠protocol, routine-as-synthesis, NMA vs CPG, citation bleed, triple restatement, protocol restated twice, end-only citation mode, single-version rewrite; Aug 2026 migraine brief).
- **references/skill-library-audit.md** — bulk skill audit methodology: skill classification taxonomy (routing vs slash-cmd vs repo-specific vs tool-wrapper vs builtin), frontmatter extraction script, five adversarial checks, trigger-insertion patch pattern, severity classification, and baseline coverage outcomes.

Python bulk frontmatter extraction + trigger insertion: see `references/skill-library-audit.md`.
Strip fenced code from descriptions before "Use when" checks. `user-invocable: false` skills never need Use when.

- **references/ai-agent-spec-adversarial-review.md** — reviewing an AI/agent system design spec (evaluation methodology, autonomy framework): domain-specific attack-vector checklist (undefined risk taxonomy, no named accountable human, missing confidentiality/data-governance, no prompt-injection defense, no model-version change control, unpopulated thresholds, no dataset representativeness requirement), the discipline of flagging judgment-call values instead of fabricating them, and a multi-sheet workbook deliverable shape when the reviewed artifact is a spreadsheet.
- **skill_view(name='requesting-code-review', file_path='references/regression-testing-and-model-runs.md')** — full reference for regression testing and ML holdout review: multilingual tool landscape (Python/JS/Go/Rust/Java), mutation testing CI gate commands, snapshot discipline, holdout checklist, temporal leakage code patterns, shadow/A/B deployment checklist, and academic anchors (arXiv IDs with quantified findings).
- **skill_view(name='hermes-agent-skill-authoring')** — for capturing platform constraints and non-portability in skill SKILL.md.


*Research basis — see references/research-basis.md. Historical citations and design rationale for the recursive adversarial loop.*

## Regex Call-site vs Function Definition False Positive (2026-08-19) <!-- why: prevents false-positive code review findings that block valid implementations -->

When using regex to detect call-site patterns in Python code review (e.g. checking for prohibited function calls), do NOT match on function definitions — a regex like `re.search(r'redact_pii\(', source)` will match both call sites AND the `def redact_pii(` definition, producing false positives that flag the function's own definition as a violation.

**Correct pattern:** Use `ast.walk(ast.Call)` nodes to find actual call sites:
```python
import ast
tree = ast.parse(source)
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and hasattr(node, 'col_offset'):
        # node.func.id or node.func.attr gives the function name
        if getattr(node.func, 'id', None) == 'redact_pii':
            # this is a genuine call site, not a definition
            ...
```

**False positive class:** `DEFINITION_AS_CALLSITE` — regex matches `def func_name(` and `func_name(args)` identically. The `ast.Call` approach is structurally correct and cannot match definitions. Always use AST-level inspection when checking for call presence in a code review pass.

Concrete case (Aug 2026, pii-redaction pass 3): regex check `re.search(r'redact_pii\(', code)` flagged the function's own definition as a prohibited call.

## Skill Document Adversarial Review — Attack Vector Class (Sep 2026)

A SKILL.md is a procedural spec (terminology, formula gates, worked examples, cross-refs).
Full attack vectors (dangling terms, dual-variable collapse, worked-example drift, unverified
arXiv calibration IDs, disanalogy propagation, step-order mismatch):
see `references/skill-document-attack-vectors.md`.

## Skill Library: Multi-Agent Concurrent Patch Defect Classes (Aug 2026)

When reviewing a batch of skill patches written by parallel synthesis agents, apply these
named defect classes in the critique phase:

**Class G: Same-skill concurrent patch (CRITICAL)**
Two agents patched the same SKILL.md. Content is incoherently interleaved: duplicate section
headers, contradictory adjacent instructions, conflicting version numbers. Detection: compare
which topic clusters each agent covered against which skills they patched. If any skill
appears in two agents' patch lists, it is a Class G candidate. Verify by reading the skill
for duplicate headings and adjacent contradictions.

**Class H: Write-owner circular loop (CRITICAL)**
Multiple skills can independently initiate `skill_manage` on the same failure event —
no single owner. Detection: list all skills that contain a `skill_manage` create/patch call
and verify no two can fire on the same failure type without a designated owner.
Fix: one write owner per action type (crystallize / human proposal / score / memory);
all others route to it. Concrete owner map: runtime-skill-synthesis=crystallize/merge/promote;
self-improve-agent=human-gated proposals; skillopt=score/diagnose only (no writes);
agent-memory-consolidation=hindsight/memory only; umbrella router skills=route only.

**Class I: Interactive-session-as-human-approval (CRITICAL)**
Skill states "if interactive session: apply now" or "a human (interactive) approves" —
treating agent presence in an interactive session as explicit user consent.
Agent in an interactive session is NOT a human.
Fix: require explicit "yes" from user before any skill_manage create/patch/promote.
Autonomous/cron: stage only. Interactive: propose and wait.

**Class J: Over-hardening (MAJOR)**
A protective gate fires on normal non-hazard work. E.g., requiring a planner+critic subagent
before any multi-step task, or critique-before-commit on every local edit.
Detection: if the gate trigger would fire on >30% of routine tasks, it is over-hardened.
Fix: narrow to explicit hazard signals (HAZARD flag, merge/push/promote/publish only,
2+ divergent approaches exist).

## Skill Library Adversarial Audit — Structural Defect Classes

Classes A–F (self-related_skills, spurious template related_skills, disabled-skill refs,
fallback-chain order, missing disabled marker): see `references/skill-library-audit.md`.
Canonical fallback chain: `web_extract → firecrawl-research → defuddle → blocked-page-recovery`.

## Pitfall: Re-litigating already-resolved concerns

When reviewing an artifact that carries its own revision-history/changelog section (design specs, governance frameworks with traceability tables):
1. Read the existing changelog/traceability section in full BEFORE drafting findings
2. Treat every concern already listed as resolved there as OUT OF SCOPE — do not re-raise it, even if your research independently surfaces supporting citations
3. State the scope boundary explicitly in the critique's opening ("this critique excludes concerns already resolved in §N; see net-new findings below")
4. Exception: if evidence surfaces that a "resolved" item was resolved incorrectly, flag it as **"regression on previously-resolved concern"** — NOT as an original gap

Re-litigating already-fixed concerns is the most common way a critique ends up hollow or redundant.

See `references/pitfall-changelog-docs.md` for the full pattern note.

## Reference files

- **references/named-check-catalogue-pattern.md** — full catalogue builder template: 4-tuple check structure, run loop, recursive fix loop, dimension naming (D1–D8), severity levels, and pitfalls (wrong YAML path, single-line regex, stale kernel, casing mismatch). Use this when auditing a system with many interacting surfaces.

- `references/common-pitfalls.md` — full pitfall catalogue (load; do not re-expand in body)
- `references/system-infra-adversarial-pass.md` — sys/infra pass (dated metrics are not timeless)
- `references/skill-document-attack-vectors.md` — skill-document attack-vector class
- `references/rendering-floor-and-completion-contracts.md` — rendering floor + completion contracts
- `references/math-research-pipeline-adversarial-checks.md` — math-to-code pipeline checks
- `references/example-hermes-cowork-port-2026.md` — Worked Hermes→Cowork port findings (localhost vs VM, placeholders, count drift)
- `references/research-citation-checklist.md` — Metric-identity, config-wiring, script-existence, aspirational-vs-active
- `references/sweep33-security-patterns.md` — Sweep 33 security cluster: 11-item tool-authorization / injection / harness checklist
- **references/recursive-research-improvement-loop.md** — saturation sweep pattern, implementation triage order, adversarial loop discipline
- **references/python-plugin-refactor-adversarial-checks.md** — 10-vector adversarial checklist for Python plugin refactors: closure capture, eviction ordering, atomic write helper, docstring placement, return value, early-return paths, numeric clamping, global shadowing, exception re-raise chain, preserved comment blocks. Includes baseline-failure diff snippet.
- **references/reasoning-type-taxonomy.md** — 9-type reasoning taxonomy; Hermes gap map (causal, EBP, lookahead, abductive, social, ethical, analogical, inductive); adversarial attack vectors for reasoning implementation review; FLARE planning-vs-reasoning distinction
- `references/ai-agent-spec-adversarial-review.md` — attack-vector checklist for AI agent system specs
- `references/financial-research-report-adversarial-checks.md` — Financial research report attack vectors (Sharpe body-vs-table, leverage, FX)
- `references/philosophy-intellectual-history-adversarial-synthesis.md` — Philosophy / intellectual history attack vectors (genealogy-as-causation, authority laundering)
- `references/hermes-to-cowork-adversarial-checks.md` — Hermes→Cowork port checks
- `references/legal-tech-product-name-verification.md` — legal-tech product-name verification
- `references/meta-review-pattern.md` — meta-review pattern
- `references/nii-pull-forward-model.md` — NII pull-forward model
- `references/pitfall-changelog-docs.md` — changelog re-litigation pitfall
- `references/research-basis.md` — research basis notes
- `references/scientific-paper-adversarial-synthesis.md` — scientific-paper adversarial synthesis
- `references/skill-library-audit.md` — skill-library structural defect classes A–F

## System/Infra Adversarial Pass Pattern (Sep 2026)

When reviewing live system changes (sysctl, systemd, shell, kernel tuning) rather than
code/docs, load `references/system-infra-adversarial-pass.md`. Do not treat incident notes
or dated metrics in that file as timeless.

Math-to-code pipeline checks (authority laundering, CP k==n, LTL schema, Beta cold-start):
already covered in `references/math-research-pipeline-adversarial-checks.md` — do not
duplicate that procedure in the skill body.

## Pre-Task Goal Structure Audit (Interconnects.ai post-incident, Aug 2026)

Before executing a subagent task, verify the task specification doesn't create implicit misaligned sub-goals. The Aug 2026 Anthropic/OpenAI production incidents showed alignment failures arise from goal-structure misspecification, not capability failures.

Check:
1. Does the task's stated objective have implicit sub-objectives that could conflict with the session goal?
2. If the subagent partially succeeds, do the intermediate states serve the original intent?
3. Are success criteria specific enough that the agent can't declare victory on a proxy metric?

Flag tasks where sub-goals could diverge from session intent before execution — don't rely on post-hoc review.

## Skill Security Statistics (SkillSec-Eval, arXiv:2607.13987)

Public marketplace audits report **up to ~25%** of published skills with security-critical defects — marketplace prior (327-skill corpus), not applicable as a base rate for this user's first-party skills.

Lifecycle stages (trust boundaries) — attack each when reviewing skills or skill batches:

1. **Admission** — repository intake (syntax rules miss semantic-intent attacks; hybrid rules+LLM MAR ~7.9% vs rules-only ~52.9%)
2. **Retrieval** — semantic search / skill router (Sybil clones, keyword stuffing)
3. **Planner selection** — which skill the planner picks (fake recommendation, misleading description)
4. **Execution** — privileged sinks; string taint is insufficient (~23% residual ASR under paraphrase)
5. **Evolution** — updates inherit prior trust unless re-admitted

Do **not** add a second SkillSec-Eval screening stack. Use ClawSentry/FSPR + `tools_allowed` + PoisonedEvolution (`arXiv:2608.05563`). Flag marketplace/untrusted skills at every stage above; a body-hash scan covers admission only.

## Consilience — seek disagreement before voting (arXiv:2608.20564)

Low disagreement is not coverage.

When reducing MULTI-AGENT verdicts: require 2 independent reasoning chains before consensus. For solo code review: this skill operates alone; do not spawn a second agent just to satisfy 2-chains.

- Independent means different evidence or a different causal chain — not two paraphrases of one argument
- If two reviewers (or two chains) agree without independent paths, count them as **one vote**
- Spawn a challenge / steelman pass before accepting. Do not tally unanimous first-round agreement as confirmation
- Pair with `hermes-swarm-consensus` copying-behavior diversity gate when aggregating subagent review verdicts

If swarm consensus is in play, the diversity gate in hermes-swarm-consensus takes precedence for vote admission. Do not define a separate vote protocol here.

## Task-Adaptive Rubric Selection (AdaRubric, arXiv:2603.21362)

**Core principle:** Derive evaluation dimensions from the task type BEFORE scoring. Never use a fixed checklist for all tasks — a fixed rubric fails to capture task-specific quality dimensions, achieving only r=0.63 vs r=0.79 with human judgment (AdaRubric, +0.16 over best static baseline).

**Reconciliation with the Code Review Completion Checklist:** The Code Review Completion Checklist (§ Code Review Completion Checklist above) IS the AdaRubric instantiation for the Code/implementation task type — apply it as-is when task type = Code/implementation. For config, skill/doc, research, and multi-agent task types, derive dimensions from the map below instead; the Code Review axes (test coverage, side effects) are inapplicable there.

**Step 0 — state the task type and activate dimensions:** At the start of each adversarial review, explicitly name the task type and list the active dimensions before beginning any scoring.

**Dimension map:**

| Task type | Active dimensions |
|---|---|
| Code / implementation | Correctness, Error Handling, Side Effects, Test Coverage |
| Config / skill / doc | Coherence, Coverage, Trigger Accuracy, No Dead Content |
| Research / analysis | Evidence Quality, Grounding, Novelty, Transferability |
| Multi-agent / delegation | Isolation, Provenance, Convergence Quality, Conformity Check |

**DimensionAwareFilter rule:** If ANY single dimension scores FAIL or LOW, the overall verdict is **FAIL** regardless of other dimensions scoring PASS. Strong dimensions cannot mask a weak one. This is the primary guard against rubric gaming — a code change that is correct but has no error handling for external calls is a FAIL, not a 75% PASS.

**AdaRubric derivation pattern (for task types not in the map above):**
1. Read the task description
2. Identify 3–5 properties a human expert would check for this specific task type
3. State those as explicit dimensions before scoring — do not attempt to score first and discover dimensions from failures

**Application:** After stating the task type and dimensions, run each dimension as an explicit sub-verdict (PASS / FAIL / LOW) before rolling up the overall verdict. A review that does not name its active dimensions before scoring is incomplete by this standard.

Reference: arXiv:2603.21362, AdaRubric: Task-Adaptive Evaluation Rubrics, 2026. Pearson r=0.79 with human judgment.

## Theory-Grounded Adversarial Review

### CTL Model Checking as Code Property Checklist (Huth-Ryan Ch 3)

**Theory:** Computation Tree Logic (CTL) expresses properties over all execution paths of a program. Key operators: AF(φ) = "all paths, eventually φ"; AG(φ) = "all paths, globally φ".

**Hermes rules:**
- Frame code correctness properties as CTL formulas for the review checklist:
  - AF(result_returned) = every execution path eventually returns a value (no infinite loops or missing returns)
  - AG(no_secret_in_output) = globally, no secret value appears in any output or log
  - AF(resource_released) = every resource opened is eventually closed
- A review that does not check these properties for critical functions is incomplete.

**Citation:** Huth & Ryan — *Logic in Computer Science* (2nd ed.), Ch 3 (Computation Tree Logic).

### D-Separation for Spurious Metric Correlations (Pearl Ch 1)

**Theory:** Two variables A and B are d-separated given C if all paths between them in the causal graph are blocked by C. D-separation implies conditional independence: A ⊥ B | C.

**Hermes rules:**
- Flag spuriously correlated review metrics: if A and B are d-separated given C, their correlation is spurious (both caused by C, not causally related to each other).
- Example: test coverage and bug count may both be caused by code churn (C), not causally linked — improving coverage alone may not reduce bugs.
- Before recommending metric-based fixes in a review, perform a quick causal structure check: is there a plausible common cause?

**Citation:** Judea Pearl — *Causality* (2nd ed.), Ch 1 (Introduction to Probabilities, Graphs, and Causal Models — d-separation).
