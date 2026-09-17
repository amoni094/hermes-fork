---
version: 1.2.0
name: hermes-skillspector-guard-maintenance
triggers:
  - The skillspector_guard cron job times out or produces stale cached reports
  - The skillspector guard script is not reusing cached output and runs too slowly
  - Fixing or verifying the local skillspector_guard cron/script behavior
  - Skillspector audit reports are wrong, empty, or timing out
  - The guard flagged/quarantined a skill that looks like a false positive
  - Need to gate skillspector quarantine behind an adversarial-review confirmation
  - last-summary.json or state.json shows a quarantined skill still present in skills/
description: >
  Use when: Fix, verify, and safely operate the local skillspector_guard cron/script — including the propose/confirm/reject quarantine workflow that gates destructive moves behind adversarial review, and the cache-reuse performance fix. SCOPE: cron script only — not a general skill-library audit (use hermes-skill-library-consolidation-audit for that).
created_by: agent
related_skills:
  - autonomous-agent-loop-design
  - verification-before-completion
---

# Hermes Skillspector Guard Maintenance

Use when the local `skillspector-guard` cron job or `skillspector_guard.py --enforce` script starts timing out.

## Symptom
- Cron job `skillspector-guard` shows `error: Script timed out after 120s`.
- Direct run of `python ~/.hermes/scripts/skillspector_guard.py --enforce` hangs or times out.

## Root cause pattern
The guard script may only reuse cached scan reports for unchanged skills when they are baseline-approved or allowlisted. That causes unchanged flagged/non-approved skills to be rescanned on every run, which grows linearly with the skill count and can push the script past the cron timeout.

## Fix workflow
1. Read `~/.hermes/scripts/skillspector_guard.py`.
2. Find the `can_reuse_cache` logic in the main loop.
3. If cache reuse is gated on `previous_approved` or allowlisted hashes in addition to unchanged file hash + existing report, remove that extra gate.
4. The conservative target behavior is:
   - if `refresh_baseline` is false,
   - and cached result exists,
   - and cached hash matches current hash,
   - and cached report file exists,
   - then reuse cache.
5. Re-run the script directly:
   - `python ~/.hermes/scripts/skillspector_guard.py --enforce`
6. Verify it exits 0 and still performs real enforcement when needed.
7. Re-run the cron job and verify `last_status: ok`.

## Example patch shape
Old behavior:
- unchanged cached result reused only if baseline-approved OR allowlisted

Desired behavior:
- unchanged cached result reused for any unchanged skill with an existing cached report

## Verification
- Direct script run finishes within normal time.
- Cron `skillspector-guard` returns `execution_success: true`.
- `~/.hermes/skills-security/last-summary.json` is updated.
- If a genuinely new risky skill exists, quarantine still happens.

## SkillSentry + Self-Harness: Trace-Based Monitor Refinement (arXiv:2608.09253, 2606.09498)

**SkillSentry (arXiv:2608.09253):** Mine runtime guidance from skill docs + success/fail traces, wrap execution in a monitor, iteratively refine the guidance DSL. Directly maps to Hermes skill reliability.

Pattern:
1. Initialize monitors from SKILL.md (extract pre/post conditions, prohibited tool sequences)
2. Wrap skill invocation: check conditions before and after each tool call in the skill body
3. On failure: mine the failure trace for the missed condition, propose a monitor refinement
4. Gate refinements behind the propose/confirm workflow (never auto-apply from a failure trace alone)

**Self-Harness (arXiv:2606.09498):** Weakness mining from traces, minimal harness patches, regression-gated acceptance. Up to 132% relative pass-rate gains. Key discipline: patches must pass regression on existing passing tasks before acceptance.

For skillspector: after a skill shows repeated failures in session history, run:
```
1. session_search(query='<skill_name> failure', role_filter=['tool']) to extract fail traces
2. Identify the earliest divergence from expected behavior in each trace
3. Propose a monitor condition that would have caught the divergence
4. Submit as a skill patch via propose/confirm workflow
5. Verify the patch does not break the 3 most recent passing traces
```

**Maintenance cost note:** monitors derived from skill docs require updates when skills evolve. Tag each monitor condition with the SKILL.md version it was derived from. Flag monitors as stale when their source version diverges from current SKILL.md hash.

## Description–body semantic alignment (CDH, arXiv:2608.12273; CPI, arXiv:2609.02564)

When scanning a skill, check that SKILL.md description/trigger semantics align with the body's first 2–3 tool calls. A description that matches user intent while the body detours through unrelated benign skills is Convergent Detour Hijacking — output may still be correct (+66.91% tokens, +92.45% latency, 80.02% coordinator selection). Covert Policy Injection (arXiv:2609.02564) is the same surface with a hidden objective instead of a cost detour.

Flag description–body mismatch as a guard finding (do not quarantine solely on this signal; route to adversarial-review). Also flag: trigger-uniqueness overlap without explicit routing; dependency-chain provenance (entry skill plus `depends_on` / loaded skills). See `hermes-agent-skill-authoring` § Skill Security Threat Model. <!-- why: per-skill content scans miss trajectory detours -->

## Skill lifecycle threat taxonomy (arXiv:2607.13987 SkillSec-Eval)

2607.13987 is a lifecycle taxonomy (repository admission, semantic retrieval, planner selection, execution, skill evolution) — not a first-N-tools check. Scan those stages separately; a per-skill body hash does not cover retrieval/planner/evolution attacks.

## ColluSkill — Cross-Skill Composition Attack + ChainGuard Defense (arXiv 2608.09732)

Compositional attack: decomposes malicious intent into individually-benign sub-skills.
96.0% success against 6 skill scanners checking skills in isolation.
ChainGuard defense reduces attack success to 22.5% while passing 99.5% of benign workflows.

For Hermes skill audit (add to skillspector scan):
1. Identify skill co-invocation clusters (which skills are commonly called together)
2. For each cluster: inspect the combined capability — does A+B enable something neither
   permits individually? (e.g., skill A reads files, skill B sends data — combined = exfiltration)
3. Flag artifact flows that traverse trust boundaries (file content → network calls)
4. At skill invocation time: if 2+ skills are loaded together, check combined capability against
   a policy list of forbidden compositions

Implementation: add a `forbidden_compositions` check to skillspector-guard.
Pattern is directly extensible from the existing individual-skill scanner.

## Pitfalls
- Do not disable enforcement just to make the timeout disappear.
- Do not remove quarantine logic.
- Do not invalidate cache reuse for unchanged flagged skills; that is the main performance bug.
- Keep the change minimal so enforcement semantics remain intact.

## Quarantine safety: propose / confirm / reject (adversarial-gated)

`--enforce` must NEVER directly move a skill into quarantine. It should only
STAGE a proposal. This guard against false positives requires a three-step
architecture (already implemented as of 2026-07-06; verify it's intact if the
script gets touched again):

1. `--enforce` calls `propose_quarantine()` for any result where
   `should_quarantine()` is true. This writes an entry to
   `skills-security/pending_quarantine.json` (the `PENDING_PATH` file) via
   `load_pending()`/`save_pending()`. No file is moved. The result is surfaced
   in the run summary as `pending_quarantine`, not `quarantined`.
2. Before acting on a pending proposal, run an adversarial-review pass (use
   the `adversarial-review` skill methodology — self-contradiction / false
   external-transmission flags / broken-reference checks) against the
   `report` path recorded in the proposal. Do not skip this step even when
   the guard's own confidence score looks high; the built-in scanner has a
   known false-positive class (see below).
   Use `python3 ~/.hermes/scripts/adversarial_quarantine_review.py <rel_path>`
   (or `--all-pending`) to automate the first pass: it re-reads each flagged
   finding in its surrounding source context and classifies it
   LIKELY_FALSE_POSITIVE / NEEDS_HUMAN_REVIEW / LIKELY_TRUE_POSITIVE using
   signals like negation/cautionary language nearby, conditional framing
   (if/when/verify), and whether the skill has any executable scripts at all
   (a finding inside prose-only markdown with no executable component is a
   strong false-positive signal). It writes verdicts to
   `skills-security/reports/adversarial/<rel_with_underscores>.json` and
   never touches `pending_quarantine.json`/`allowlist.json` itself — it's an
   input to the human decision, not a substitute for manually re-reading at
   least the HIGH/CRITICAL findings before confirming or rejecting.
3. Only after that review:
   - True positive → `python skillspector_guard.py --confirm-quarantine <rel_path>`.
     This calls `confirm_quarantine()`, which re-validates the skill's hash
     against the pending proposal's hash before calling `quarantine_skill()`
     (the only place that actually does `shutil.move`). If the hash changed
     since the proposal (skill was edited), it refuses and asks for a re-scan.
   - False positive → `python skillspector_guard.py --reject-quarantine <rel_path> --reject-reason "..."`.
     This calls `reject_quarantine()`, which adds the skill's hash to
     `allowlist.json` (so it won't be re-proposed) and clears the pending
     entry. Nothing is moved.
4. `prune_stale_pending(pending, results)` runs on every invocation and drops
   any pending proposal whose skill vanished or whose hash no longer matches
   what's on disk — stops a stale proposal from being confirmed against an
   already-changed file.

Never bypass this and call `quarantine_skill()` directly, and never restore
the old behavior where `--enforce` executed `should_quarantine()` → move in
one step. That was the exact bug that produced the false-positive quarantine
this pattern was built to prevent.

## PoisonedEvolution: Trajectory Poisoning Defense (arXiv:2608.05563, Aug 2026)

Self-evolving skill systems are vulnerable to trajectory poisoning: 3 consistent
poisoned records in a 30-record batch (10% support) achieve 91% Skill Embedding Rate
across 6 LLM evolvers. The bottleneck is Evolution Attribution — behavior must appear
causally useful, recurrent, and generalizable for a skill to be promoted.

**Required SKILL.md frontmatter fields (add when auto-promoting skills):**
```yaml
source_episodes: []          # session IDs that contributed evidence
evidence_count: 0            # number of distinct sessions (not records)
trust_level: experimental    # experimental | validated | production
failed_trajectories: []      # session IDs where skill invocation failed
```

**Minimum evidence threshold:** Never auto-promote a skill from fewer than 5
*distinct session* trajectories (not 3 from the same session).

**Validation gate:** Before writing a skill to disk, run it against held-out
validation tasks declared in `constraints: [test_tasks]` frontmatter.

**Causal framing audit:** Auto-flag skills whose `description:` uses strong causal
language ("always", "will", "guaranteed") without corresponding `constraints:`
evidence — matches the attacker's promotion heuristic.

**SkillsBench findings (arXiv:2602.12670, Jun 2026 update):** Skills raise pass rate
from 33.9% to 50.5% (+16.6pp). Authoring constraint (not a skillspector scan rule):
skills with ≤3 procedural modules outperform larger bundles. Split oversized skills via
`hermes-agent-skill-authoring`; do not quarantine on module count.

## SkillReact: Compositional Risk Assessment (arXiv:2606.00448, May 2026)

Individual skills may be safe in isolation but hazardous when composed. SkillReact
evaluates 211,575 individually-safe skill pairs from 1,520 ClawHub skills and finds
18.2% of flagged pairs contain genuine compositional risk (population-weighted validity).
Per-skill scanning misses all of these — every flagged pair is individually safe.

**Forbidden capability patterns (10 total; primary subset):**
| Combined capability | Pattern |
|---|---|
| Data exfiltration | `file_read + network_out` |
| Credential leak | `credential_access + network_out` |
| Remote code exec | `shell_exec + network_out` |
| Arbitrary write | `file_write + shell_exec` |

**SkillReact 3-component framework:**
1. Deterministic static check: capability union against forbidden patterns
2. LLM-assisted adjudication: ~1 in 5 static flags is a real risk (18.2%)
3. Exploitability harness: tests whether model actually issues the tool calls

**Model disposition finding:** Haiku-4-5 issues full download-then-execute on 36/39 trials;
Sonnet-4-6 refuses outright; Opus-4-7 stops at download. Compliance is HIGHEST with no
skills installed — composition fixes which capabilities are reachable; the model decides use.

**SKILL.md frontmatter `capabilities:` field (add to all new skills):**
```yaml
capabilities:
  - file_read          # can read files from disk
  - network_out        # makes outbound HTTP requests
  # etc. — name each permission class the skill exercises
```
This enables static capability-union checks at skill-load time. The skillspector
adversarial_quarantine_review.py should eventually parse this field for pairwise scans.

**SkillTV-Bench (arXiv:2608.05573, Aug 6 2026):** trajectory-level evaluation
benchmark for agent skill use — tests whether agents apply skills correctly across
multi-step trajectories, not just single-turn recall. The right evaluation frame
for skillspector workflows: trajectory success rate, not per-skill flag accuracy.

**What this means for skillspector:** a skill that passes the solo scan can still
trigger a compositional risk when loaded together with another skill. The current
per-skill scanner cannot catch this class of vulnerability.

**Risk patterns to check at compose-time** (union of SkillReact forbidden capabilities + compose-time signals):
| Pattern | Example | Detection signal |
|---|---|---|
| Permission escalation / data exfil | skill-A reads filesystem; skill-B sends HTTP | `file_read + network_out` |
| Credential leak | env/key read + outbound HTTP | `credential_access + network_out` |
| Scope amplification / RCE | user-input parse + shell | `shell_exec + network_out` or `file_write + shell_exec` |
| Authority confusion | role/persona skill + irreversible action | persona keyword + mutating tool |

**Practical Hermes guard (pairwise check at skill-load time):**
When the agent loads ≥2 skills for a task, before executing, check if any pair
matches a pattern above. If so, log a COMPOSITION_RISK warning and require
explicit user acknowledgment before executing irreversible actions.

The adversarial_quarantine_review.py script should eventually be extended with a
pairwise scan mode: given a proposed skill pair (A, B), output whether they have
co-present risk signals from the table above.

## SHE: 4-Artifact Harness for Agent Safety Evolution (arXiv:2608.09885, Aug 2026)

Static safety rules fail as agent capabilities expand. SHE evolves four artifacts
in response to observed failures:

| Artifact | Contents | Update trigger |
|---|---|---|
| System prompt | Core role, scope, hard prohibitions | New capability or expansion |
| Rule bank | Ranked do/don't rules with confidence scores | Observed violation or near-miss |
| Safety memory | Episodic log of past violations + resolutions | Every violation, never evicted |
| Tool policy | Per-tool permission table (allow/deny/audit) | Tool schema change or new tool |

**Key insight:** rule bank and tool policy evolve independently — adding a new tool
only requires updating the tool policy row for that tool, not the system prompt.

**Hermes adaptation:**
- **Rule bank** → `safety_rules:` block in SKILL.md frontmatter with `id`, `rule`,
  `confidence`, `source` fields
- **Safety memory** → Hindsight entries tagged `safety`, `context="safety_incident"`;
  never evict; query before ambiguous tool sequences
- **Tool policy** → `tool_policy.yaml` in skills root listing allow/deny/audit per
  tool per skill category (audit = log before execute, don't block)
- **Evolution trigger:** after every SkillSpector violation find, propose rule bank
  confidence updates and safety memory additions - queue for human review before applying.
  Safety rule writes are high-risk mutations; human review is not optional.

## Canary Tools: Tool Schema Testing Checklist (arXiv:2608.04719, Aug 2026)

When adding or reviewing tool schemas, verify against the 6 canary failure types:

| Type | Test | Check |
|---|---|---|
| Semantic decoy | Does any tool name closely resemble another with different purpose? | Rename or add `when_not_to_use:` |
| Parameter trap | Are param names unique across tools? Same name different type? | Add type annotations |
| Capability mirage | Does the description claim something the tool can't do? | Remove false capability claims |
| Prerequisite blindness | Does this tool require another tool to run first? | Add `requires:` to frontmatter |
| Temporal decoy | Is this tool only valid in specific system states? | Add `preconditions:` block |
| Granularity trap | Is the tool too coarse (does too much) or too fine (too narrow)? | Split or merge accordingly |

**SkillSpector integration:** Flag any skill that introduces new tool calls without a canary-check annotation in its verification section. CSR varies 36× across models — capability mirages uniquely trap frontier models (Claude Opus 4.8 has lowest CSR).

## Auton/AgenticFormat: `constraints:` Frontmatter Block (arXiv:2602.23720, Feb 2026)

Constraints embedded in natural language skill bodies are overridden by
instruction-following failures. Explicit `constraints:` frontmatter survives them.

**Add to any skill with hard operational limits:**
```yaml
constraints:
  max_steps: 12
  max_tokens_per_step: 2000
  prohibited_sequences:
    - [web_search, memory_write]    # must have human review between search and write
    - [browser_navigate, terminal]  # browser + terminal same step = high risk
  required_before_completion:
    - "contradiction_check_passed"
    - "source_verified"
  output_format: "structured_json"
```

**SkillSpector integration:** flag any skill with `tool_call` patterns in the body
but no `constraints: max_steps` — unconstrained tool-using skills are a drift risk.

## Known false-positive class in SkillSpector's own scanner

SkillSpector's "Data Exfiltration / External Transmission" check fires
(confidence ~0.5, severity MEDIUM per hit, but can sum to CRITICAL/100) on any
skill that documents legitimate external API base URLs — e.g. a
routing/config skill that lists `https://api.openai.com/v1`,
`https://api.cerebras.ai/v1`, `https://api.sambanova.ai/v1`,
`https://api.mistral.ai/v1` as *reference documentation*, not as code that
actually exfiltrates data. A skill whose whole purpose is documenting
provider routing/base_url configuration will always trip this. Treat this as
the default false-positive shape: reject-quarantine (allowlist) it once
confirmed no actual secrets/keys/PII are embedded in the flagged text — do
not treat "URL literal appears in markdown" alone as a true positive.

## Pitfall: stale `quarantined_to` survives in cached state

`result_from_cache()` (used whenever a skill's hash hasn't changed since last
scan) copies `quarantined_to` forward verbatim from `state.json`'s
`last_results` cache. If a `quarantined_to` path was ever written into state
(e.g. from a run before this propose/confirm/reject fix existed, or from a
bug), and the skill's hash is unchanged since then, every future run will
keep reporting that skill as quarantined in `last-summary.json` even though
the skill is untouched and still live on disk, and even though the recorded
quarantine directory doesn't exist. Symptom: a skill directory that
obviously still exists under `skills/<category>/<name>/` is nonetheless
listed under `"quarantined"` in `last-summary.json` with a `to` path that
404s on disk. Fix: clear the stale `quarantined_to` field for that skill's
entry in `state.json` `last_results` (set it back to `null`) once you've
confirmed via `ls`/`find` that the referenced quarantine directory doesn't
actually exist — don't just trust the summary output.

## Pitfall: patching state.json from a stale read clobbers concurrent cron writes

`state.json` is mutated by the `skillspector-guard` cron job (runs every
240m by default) as well as by any manual `--enforce`/`--confirm-quarantine`/
`--reject-quarantine` invocation. If you read the file, then later patch it
based on that earlier read, the cron job may have re-scanned the same skill
in between (e.g. because its content changed) and written a genuinely new
hash/allowlisted/severity — your patch will silently overwrite that live
update with stale data if the old_string still happens to match nearby
unrelated text. Concrete case (2026-07-06): a skill's SKILL.md content was
edited, the guard cron re-scanned it, correctly recomputed a new hash and
flipped `allowlisted` to false — then an unrelated fix patched `state.json`
using an old cached read and reverted the entry back to the previous
(allowlisted, old-hash) state, undoing a correct security re-flag.

The patch tool surfaces this: watch for
`"_warning": "... was modified since you last read it on disk ..."` in the
response. Treat that warning as a hard stop, not a note — re-read the
specific key/section fresh, diff it against what you were about to write,
and only proceed if your intended change is still correct against the
current content. For `state.json` specifically, prefer re-reading the exact
skill's block via `search_files` (grep for the skill's rel-path key) over
trusting an earlier full-file read, since the file is large and frequently
touched by the background cron.

## Pitfall: rejecting a batch of pending proposals can surface a NEW pending item — loop until truly empty

`--enforce` re-scans on every invocation. Rejecting/allowlisting a batch of pending
proposals and then re-running `--enforce` to confirm `pending_quarantine` is empty can
itself surface a fresh proposal that wasn't in the original batch (e.g. a skill whose
scan was previously deprioritized behind the ones you just resolved, or one that crossed
a score threshold only after cache invalidation). Do not treat one round of
reject-quarantine + `--enforce` as the end state. The correct loop is:

1. Read `pending_quarantine.json` / the run summary.
2. Adversarially review every entry (`adversarial_quarantine_review.py --all-pending`).
3. Confirm or reject each one.
4. Re-run `--enforce` and re-check `pending_quarantine` again.
5. Repeat 1-4 until a `--enforce` run produces zero new pending entries.

Only then is the queue actually drained. Stopping after step 3 the first time through
is the most common way this task looks "done" while a fresh proposal sits unreviewed.

## agentdescent L0/L1/L2 Three-Layer Governance (github.com/Birfy/agentdescent, Aug 2026)

Parallel async skill evolution framework with 18 algorithm ports (EvoSkill, SkillOpt, GEPA, ADAS).
The governance architecture is directly applicable to safe skill library evolution:

| Layer | Contents | Update policy |
|---|---|---|
| L0 — Frozen | Safety oracle, hard prohibitions, non-negotiable constraints | Never auto-updated; requires human approval |
| L1 — Slow harness | Core skill structure, quarantine rules, composition checks | Updated only after adversarial review + 5+ session evidence |
| L2 — Fast skills | Individual skill bodies, trigger lists, routing_signals | Auto-updatable with propose/confirm gate (existing workflow) |

**Key mechanism: Beta-posterior acceptance** — new skill variants are accepted only when the
Beta distribution over observed success/failure rates has posterior mean > current variant's
mean. Prevents premature skill replacement when a new variant has too few trials.

**ROLL-Flash staleness control** — async diffs from parallel evolution are tagged with a
staleness score. Diffs older than `max_staleness` (default: 3 ticks) are discarded without
merging. Prevents stale evolution results from overwriting more recent live state.

**Hermes adaptation:**
- L0 = `constraints:` frontmatter block + `forbidden_compositions` policy (existing)
- L1 = skillspector-guard quarantine rules + composition-risk patterns (existing)
- L2 = individual SKILL.md updates via skill_manage (existing propose/confirm workflow)
- Beta-posterior: before promoting a skill variant, require evidence from ≥5 distinct
  sessions where the NEW variant was used and succeeded (not 5 uses of the old variant).
  This is stricter than the current "5 distinct sessions" rule which counts any usage.
- Staleness: if a skill update was proposed >7 days ago with no confirming evidence since,
  discard the proposal and re-evaluate from scratch. <!-- why: stale proposals are based on
  a task distribution that may no longer match current runtime usage -->

## skill-curator: Deletion-Regret Accounting (github.com/choeyunbeom/skill-curator, Aug 2026)

MSc dissertation artifact. Empirical result: **62% smaller skill library, 16% cheaper
at task time, zero deletion regret** on InfiAgent-DABench benchmark. Key techniques:

**1. Behavioural deduplication (execute-based, not text-similarity)**
Text similarity between SKILL.md files is a poor dedup signal — two skills can be
textually different but behaviourally identical (same tool calls in different order, same
outcome). Dedup should test observable behaviour, not textual similarity.

For Hermes: two skills are candidates for merge if they recommend the same primary tool
sequence on the same task category. Flag for human review when:
- Both skills have `provides:` tags with >50% overlap
- Both skills load the same set of tools in their examples
- Embedding cosine similarity > 0.80 (existing ToolScope pattern)

**2. Deletion-regret accounting (replay pruned skills before committing deletion)**
Before deleting or merging a skill, replay a random sample of tasks from the past 30 days
against both the current library and the library-minus-the-skill. If task success rate
drops, the skill has non-zero regret and must NOT be deleted.

Practical implementation for skillspector prune workflow:
```
Before confirming skill deletion:
1. Identify last 10 sessions where the skill was loaded (from .usage.json or session_search)
2. Would those tasks have succeeded without this skill? (manual spot-check 3 of 10)
3. If any spot-check is ambiguous: keep the skill, add a deprecation note instead
4. Only delete when all 3 spot-checks confirm the skill's capability is covered elsewhere
```

**3. Health judged against deployment-time schema, not authoring-time schema**
Key finding: "skills degrade silently because they were authored for a previous API/tool
schema." A skill that passed health checks when written may be broken today because
a tool it calls changed its parameter schema.

For skillspector audit: when scanning a skill, verify its tool_call examples against the
CURRENT tool schema (not the schema at authoring time). Add to canary checklist:
- Does this skill's example call match the current tool parameter names?
- Does it reference a tool that no longer exists?
- Does it use a deprecated parameter pattern? <!-- why: authoring-time health ≠ deployment-time health -->

## AEVAL: Executor/Grader Separation for Honest Skill Evaluation (arXiv:2607.16345, Sweep 15)

AEVAL replaces anecdotal "run the skill, see if it works" evaluation with a deterministic test pipeline.

**Key finding: agents self-correct silently during execution**, then grade their own patched output
as passing. Without executor/grader separation, self-correction inflates pass rates to near-100%
on tasks where the first-attempt output would have failed — hiding the real skill quality.

**The silent self-correction pattern:**
1. Skill runs → error occurs → agent silently retries / patches in-loop
2. Second attempt succeeds → agent grades output "passed"
3. Reported: 100% pass rate. Reality: skill fails on first-attempt cold start.

This matters for skill evaluation, skill health checks, and the canary testing pattern:
a skill that "passes" with silent self-correction is unreliable when deployed in a context
where the agent CAN'T self-correct (e.g. as a cron job, as a leaf subagent with restricted tools).

**AEVAL's fix: first-attempt grading with separate executor and grader.**
```
Executor: [isolated run, no tool access after first failure, no retry]
Grader: [separate model call, different context, grades first-attempt output ONLY]
```

**Hermes adaptation for skillspector canary testing:**

When evaluating a skill's health (step in canary checklist or periodic audit):
1. Run the skill task with a MOCK environment that does NOT allow retry after first tool failure
2. If the skill tool call fails, the skill fails — do not allow silent in-loop correction
3. Grade only the first-attempt output; if it passes grading → skill is healthy
4. If the skill only passes with retry → mark skill as "fragile-on-cold-start";
   add a pitfall note: "skill relies on in-loop retry; may fail in no-retry contexts"

**For Hermes cron-job skills specifically:**
Cron jobs are isolated-run contexts with no human oversight — exactly the scenario where
silent self-correction breaks down. Before promoting a skill to cron use, run AEVAL-style
evaluation: does it pass WITHOUT retry? If not, it's not cron-safe.

**Grade the first-attempt trace, not the final output:**
When reviewing a skill's test run log, look for the FIRST tool call output before any retry —
not the end state. The end state may look fine. The first-attempt state reveals true reliability.

## Circular Skill Dependency Detection (Cordis, Aug 2026)

Cordis §6.5 shows that bidirectional / circular component dependencies cause both
components to stay permanently INACTIVE — detectable at load time, not at runtime.
The same failure mode exists in Hermes skill loading.

**Symptom:** Skill A has `skills-to-load-first: [B]`; Skill B has `skills-to-load-first: [A]`.
At load time, each waits for the other → confused loading order, partial instruction
sets, emergent misbehavior that looks like a model reasoning error.

**Detection script (run during skillspector audits):**
```python
import yaml, os, sys
from pathlib import Path

skills_root = Path.home() / ".hermes/skills"
deps = {}
for skill_md in skills_root.rglob("SKILL.md"):
    try:
        text = skill_md.read_text()
        fm = yaml.safe_load(text.split("---")[1])
        name = fm.get("name", skill_md.parent.name)
        deps[name] = (fm.get("skills-to-load-first") or []) + \
                     (fm.get("depends_on") or []) + \
                     (fm.get("related_skills") or [])
    except Exception:
        pass

# DFS cycle detection
def has_cycle(node, visited, stack):
    visited.add(node); stack.add(node)
    for nbr in deps.get(node, []):
        if nbr not in visited:
            if has_cycle(nbr, visited, stack): return True
        elif nbr in stack:
            # illustrative — shows the closing edge of the cycle, not the full path
            print(f"CYCLE EDGE: {node} -> {nbr}"); return True
    stack.discard(node); return False

visited, stack = set(), set()
for node in deps:
    if node not in visited:
        has_cycle(node, visited, stack)
```

**Fix for cycles (Cordis §6.5 prescription):** factor the shared state into a third
skill C that A and B both reference unidirectionally. C depends on neither; A and B
depend on C only. No cycle.

**Note:** `related_skills` in frontmatter is advisory (informational); only
`skills-to-load-first` and `depends_on` are structural loading dependencies.
Cycles in `related_skills` alone carry no loading-order risk; cycles in loading deps are bugs.

## Skill Permission Declaration (arXiv:2608.13574 Agentao, Aug 2026) <!-- why: prevents implicit permission escalation when skills are loaded without declaring which tool surfaces they require -->

Each skill should declare which tool surfaces it requires in frontmatter. The guard verifies that loaded skills don't escalate beyond declared permissions.

**Add to SKILL.md frontmatter for any skill using tools:**
```yaml
capabilities:
  - terminal          # runs shell commands
  - file_write        # writes files to disk
  - browser           # uses browser_navigate/browser_click etc.
  - web_extract       # fetches external URLs
  - memory_write      # writes to Hindsight or Graphiti
  - credential_access # accesses .env, API keys, secrets
  - network_out       # makes outbound HTTP calls directly
  # omit capabilities not used; minimal declaration is correct
```

**Guard check (add to skillspector audit):** When ≥2 skills are loaded together, check the union of their `capabilities:` against the forbidden compositions table (SkillReact patterns above). A skill that declares only `file_write` but whose body also uses `web_extract` is a mismatch — flag for correction.

Source: Denuto `docs/agents/architecture-principles.md`

## Tier-1 vs Tier-2 Enforcement Gate Distinction (Denuto Pattern)

> **"A non-negotiable with no gate is a wish, not a contract."**

### Tier-1 — Enforced Invariants

Rules that have a named enforcing gate. If the gate doesn't exist, it's Tier-2.

Example Tier-1 rules with gates:
- "skill_manage creates require ≤59 char description" → GATE: `skill_manage` API enforces at write time
- "trajectory-risk-guardrail fires before any irreversible action" → GATE: `trajectory_risk_guardrail.py` pre-flight check
- "improvement proposals rate-limited to 5/hour" → GATE: `improvement_governance.py` check_rate_limit()
- "shadow path never raises" → GATE: `suppress(Exception)` wraps all shadow calls

**Format for Tier-1 rule in a skill**:
```
**[TIER-1]** Rule description
Gate: <exact command or function that enforces this>
```

### Tier-2 — Operating Posture (Document, Don't Claim Enforcement)

Rules without a gate. Honest acknowledgement that they are aspiration, not contract.

**Format for Tier-2 rule in a skill**:
```
**[TIER-2 / GATE GAP]** Rule description
Gate: None yet. Add a test/script to promote to Tier-1.
```

### Marking GATE GAP in Skills

When a skill asserts something should always happen but has no mechanism enforcing it:
1. Add `**GATE GAP**: <description of missing enforcement>` inline
2. Add to `## Known Gaps` section at bottom of skill
3. Create a tracking entry in `~/.hermes/logs/improvement-proposals.jsonl`

**Do NOT** remove GATE GAP markers without first creating the gate.

### Guard Script Verification

```bash
# Verify the skillspector guard is active
python ~/.hermes/scripts/skillspector_guard.py --check 2>&1 | head -20

# Enforce guard constraints
bash ~/.hermes/scripts/skillspector_guard_enforce.sh

# Check for skills with Tier-1 rules lacking gates
grep -r "GATE GAP" ~/.hermes/skills/ | wc -l
```

See also: `hermes-improvement-governance` (risk gating), `hermes-system-audit` (tiered enforcement audit).
```

**Guard check (add to skillspector audit):** When ≥2 skills are loaded together, check the union of their `capabilities:` against the forbidden compositions table (SkillReact patterns above). A skill that declares only `file_write` but whose body also uses `web_extract` is a mismatch — flag for correction.

**Nightshift audit discipline (reinforces Agentao replay subsystem pattern):** Nightshift/cron agents should emit structured replay logs so any session can be audited or re-run from a checkpoint. Skills that run in cron contexts should include `cron_safe: true` in frontmatter — only promote to cron use after AEVAL-style first-attempt evaluation confirms no retry dependency.

## Verification checklist for this class of fix
- `python3 -c "import ast; ast.parse(open('skillspector_guard.py').read())"` → `SYNTAX_OK`.
- `python3 skillspector_guard.py --help` exits 0 and lists `--confirm-quarantine`/`--reject-quarantine`.
- `python3 skillspector_guard.py --enforce` (dry run) exits 0; check
  `pending_quarantine.json` gained/kept only entries whose skill dir still
  exists on disk.
- Cross-check `last-summary.json`'s `"quarantined"` list against
  `ls ~/.hermes/skills-quarantine/` — every entry's `to` path must actually
  exist. If not, it's stale cached state, not a real quarantine (see pitfall
  above).
