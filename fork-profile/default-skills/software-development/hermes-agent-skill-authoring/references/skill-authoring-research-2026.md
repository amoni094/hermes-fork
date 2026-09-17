# Skill Authoring Research Findings (Sweeps 20, 25, 29)

Extracted from `hermes-agent-skill-authoring/SKILL.md` so the skill body stays under the 500-line procedural budget. Sweep 33 remains inline.

HASTE (arXiv:2608.20888) and RethinkSkill (arXiv:2608.20777) UNTRUSTED crash-dump attributions were removed, not archived.


---

## PoisonedEvolution — Memory Poisoning in Self-Improving Agents (arXiv:2608.21230, Aug 2026) ★ HIGH <!-- rationale: memory poisoning defense -->

**PoisonedEvolution** is a memory poisoning attack on self-improving agents.

**Defense:**
- Cross-verification before write (see Memory Poisoning Write Gate)
- Write-path filtering: reject memories that:
  - Contain sensitive data (PII, passwords, API keys)
  - Make absolute claims without evidence
  - Introduce new entities without context
- Use `hermes-skillspector-guard-maintenance` to scan for poisoned skills
- Set `trust_level: experimental` on auto-patched skills and review after 5+ distinct sessions

Covered inline by Skill Security Threat Model (arXiv:2607.13987). Kept here as the original sweep note.


---

## TRACE Skill Bank Consistency — Pass^k Metric (arXiv:2608.22793, Aug 2026)

**TRACE** finds that frontier models have a large gap between Pass@3 (can solve at least once) and Pass^k (solves consistently across trials).

**Hermes implementation:**
- Validate skills with `Pass^k` — does the skill produce correct behavior on k consecutive independent attempts?
- Practical k=3 for `trust_level: validated`, k=5 for `trust_level: production`
- After any skill execution failure, record the failure trace and pair with the most recent success trace
- Update the skill based on the contrastive difference


---

## SkillAlchemy — Admission-Centered Skill Creation (arXiv:2608.23417, Aug 2026)

**SkillAlchemy** discovers implicit requirements missed by the brief via contrastive evidence.

**Hermes implementation:**
- When authoring a new skill, ask: "What does the brief leave implicit that would cause failure?"
- Find 2+ real examples of the skill being invoked, identify cases where the obvious procedure would have failed, and extract the implicit requirement
- Document implicit requirements in the skill's `## When to Use` section
- Example: a "write a PR description" skill must reference the linked issue number and label each change type — this is an implicit requirement not in the brief


---

## EvoAgent — Failure-Trace Skill Updates (arXiv:2604.20133, Jun 2026)

**EvoAgent** extends skill versioning with failure-recovery updates.

**Hermes implementation:**
- When a task fails or requires significant human correction WHILE a skill was loaded, append a failure trace entry AND update the skill immediately in the same session
- Log the failure:
```bash
echo '{
  "date":"'"$(date -I)"'",
  "session":"'$SESSION_ID'",
  "task":"<brief task description>",
  "failure_mode":"<what went wrong>",
  "correction":"<what the correct approach was>"
}' >> ~/.hermes/skill-failures/<skill-name>.jsonl
```
- Immediately patch the skill body with the failure insight using `skill_manage(action='patch')`
- This is more reliable than success-only updates because it isolates the causal difference


---

## Natural-Language Workflow Procedures as a Skill Interface (arXiv:2608.21341, Aug 2026) <!-- rationale: justifies the SKILL.md-as-procedure approach with academic validation and identifies the exact failure mode it prevents -->

ArXiv:2608.21341 validates the SKILL.md architectural approach empirically: "natural-language workflows offer a software-like interface for agents: domain experts can write reusable procedures, and agents can execute them reliably."

**Key findings applicable to Hermes skill authoring:**

1. **Procedure-as-interface pattern**: NL workflow procedures act as a stable interface between domain knowledge (what to do) and agent execution (how to call tools). The procedure author need not know tool APIs; the agent need not know domain semantics. Skills are the interface layer.

2. **Reuse beats re-generation**: agents that re-derive procedure from scratch on each task underperform agents that retrieve and follow a stored procedure, even when the stored procedure is imperfect. A mediocre procedure retrieved reliably beats no procedure derived optimally — the retrieval reliability matters more than procedure quality for common cases.

3. **The failure mode NL procedures prevent**: "specification ambiguity collapse" — when agents must interpret an underspecified goal, they default to high-confidence-but-wrong interpretations. A NL procedure with explicit decision points eliminates this by making the agent pause at ambiguity rather than guess.

**Hermes mandates from this:**
- Skills must include explicit decision points: "If X, do Y; if Z, do W" at any juncture where the agent might guess
- Procedures that are retrieved reliably (clear trigger) are more valuable than procedures that are occasionally perfect
- The `routing_signals` frontmatter field is more important than previously thought — it directly determines retrieval reliability

**Procedure completeness test**: after writing a skill, ask: "Can an agent with no background knowledge follow this procedure to a correct result?" If domain knowledge is required to fill in gaps, add decision branches or reference files. This is the "domain expert writes once, agent executes reliably" contract.

Reference: arXiv:2608.21341, Aug 2026.


---

## Runtime Assurance & Versioning Schema (Aug 2026)

### SkillSentry — Precondition/Postcondition DSL (arXiv 2608.09253)
Adding a `runtime_checks` block to SKILL frontmatter improves task success by 24.1% on average.
The block encodes preconditions (must pass before executing), postconditions (verify after
completion), and failure_traces (auto-populated pitfalls from historical failures).

Example frontmatter addition:
```yaml
runtime_checks:
  preconditions:
    - "target file exists and is readable"
    - "no background process already running for this task"
  postconditions:
    - "output file present and non-empty"
    - "no new errors in terminal output"
  failure_traces:
    - "tool call timed out: increase timeout parameter"
```

### OpenLoopEvolve — Versioned Loop Policies (arXiv 2608.09380)
Skills are loop policies — formalize versioning with lineage and Champion-Challenger rollback:
- Add `parent_version` field to frontmatter when patching a skill
- After patching: run comparative cron tasks comparing new vs parent version success_rate
- If new version success_rate < parent by >5%, revert via `skill_manage(action='patch')`
  restoring old_string; log event to `~/.hermes/skills/.version_log.jsonl`

### RADEG — Pre-Execution Utility Gating (arXiv 2608.09168)
Add a lightweight surrogate gate between skill_view and execution:
- Log (query, skill_name, task_outcome) triples to Hindsight after each task
- After 20+ examples: build logistic classifier on query-skill embedding similarity + recency
- If predicted utility < 0.3: surface a note before loading full skill body
- Update surrogate from task outcomes; no retraining of retriever or agent required

### SkillReason — Capability-Trace Retrieval (arXiv 2608.08640)
At successful skill completion, store a capability trace in Hindsight:
- Prompt Claude: "In 2 sentences, what reasoning capability did this skill enable?"
- Tag result: `capability_trace`, skill_name, task_type
- At retrieval: augment query with matched capability traces before skill routing
- Dramatically improves recall for implicit/underspecified requests (SOTA on 61,228-skill bench)


---

## Skill-Induced Failure Prevention (arXiv:2608.11888 + 2608.12851) — Safety-First Authoring <!-- rationale: prevents seemingly-relevant skills from causing MORE failures than no skill -->

Empirical findings from 307 skill-induced failure cases and lifecycle analysis of unsafe skill evolution:

**Three failure modes to avoid at authoring time:**

1. **Irrelevance is not the primary hazard.** Seemingly relevant skills cause the MOST functional failures (125 cases). A skill that half-matches the task causes the agent to misimplement or omit required elements. Write clear out-of-scope boundaries in `## When to Use > Don't use for:` — skills that can't say what they're NOT for are dangerous.

2. **Excessive verification is the #1 efficiency regression.** 67 of 182 regression cases were caused by skills that turned validation checklists into mandatory heavy pipelines. RULE: Verification steps in a skill should be OPTIONAL checkpoints, not unconditional gatekeepers. Phrase as: "If X is uncertain, verify by Y" — not "Always verify by Y".

3. **Unsafe skill misevolution** (arXiv:2608.12851): successful trajectories from compromised inputs become persistent unsafe policy after the input disappears. Carryover Attack Surface Rate rises from 16% to 35.3% after just 3 malicious exposures. Guard against this:
   - Skills must only be updated via `skill_manage` from the parent (human-supervised) session
   - Set `trust_level: experimental` on any auto-patched skill; as a manual discipline, note the patch source in a `## Patch history` comment and review after 5+ distinct sessions before treating as `validated` <!-- note: no automated enforcement; this is curator discipline -->
   - Scan incoming patch content: if a skill body references tool patterns that weren't in the trigger context, flag for human review

**Inline safety check (add to authoring checklist):**
- [ ] Skill body's first tool calls match its declared trigger semantics (CDH check)
- [ ] Verification steps are conditional, not mandatory
- [ ] Skill has clear "Don't use for" counter-triggers
- [ ] `trust_level` is set appropriately for auto-promoted skills


---

## Muscle Memory Compilation (arXiv:2608.08995) — Two-Stage Trigger Matching

"Muscle Memory for Agents" argues skills (compiled specialists) outperform retrieval for recurring workflows. Key architectural insight: skills should have two-stage trigger matching:

1. Stage 1 — Context match: Does the current task context pattern match this skill's known trigger context? (Broad gate)
2. Stage 2 — Contract match: Does the specific task contract (inputs, required output, constraints) satisfy the skill's specialization? (Narrow gate)

This prevents osmosis (skills activating on loose context match) and missed invocations (skills not firing on tight contract match). In practice for Hermes: skill triggers should specify both the context signal ("Use when: [situation]") AND the contract constraint ("Input: [what is available], Output: [what is required]"). Skills without a clear contract are candidate for osmosis regressions per Regression Tax.


---

## Regression Tax (arXiv:2607.22520) — Three Failure Modes to Avoid

Skills can hurt as well as help. In ~6,000 agent runs across office automation benchmarks, regressions offset 59% of gross gains. Best-performing skill libraries win primarily by regressing less, not gaining more.

Three regression mechanisms to avoid when authoring:

1. Skill-description osmosis: The skill description sits in context on every step even when never invoked. A single biased phrase in the description can flip the agent to a wrong interpretation on tasks it otherwise solves correctly. RULE: Keep trigger descriptions neutral and minimal — they describe when to invoke, not how to execute.

2. Grounding displacement: The skill's procedure overrides how the agent reads its inputs. Skills heavy on "how to compute" cause the agent to skip correctly locating the right source. RULE: Start skills with explicit grounding guidance ("first verify you have the right table / file / cell range") before procedural steps.

3. Verification displacement: Procedural steps suppress the agent's native output self-checks. RULE: End every skill with an explicit verification step ("verify the result matches the expected format and source").

Skill reliability depends more on grounding + verification than on procedural choice.


---

## Cross-Platform Skill Standards (agentskills.io + mvanhorn/last30days-skill, Aug 2026)

Two community patterns worth tracking for Hermes skill quality:

**agentskills.io index.json standard**: an emerging cross-platform skill distribution format (compatible with Claude Code, OpenClaw, Codex, Hermes) where each skill publishes an `index.json` with a MITRE-style hierarchical taxonomy label (e.g. `"taxonomy": "research/web/multi-platform"`). The taxonomy enables skill-routing by category before loading full content — maps to Hermes `skills_list(category=)` filtering. Useful reference when authoring skills that might be shared across agent platforms.

**.skillignore pattern**: per-skill privacy/noise contract file (analogous to `.gitignore`) that specifies which files, paths, or content classes the skill should exclude from processing. Prevents a skill from ingesting credentials, private config, or irrelevant noisy files. Hermes approximation: document in the skill's frontmatter which file patterns are out of scope, rather than relying on the skill body to handle exclusions ad hoc.

**Pre/post execution hooks**: the `last30days-skill` architecture includes a `hooks/` directory with pre-skill-execution and post-skill-execution scripts for enrichment pipelines (e.g. post-hook writes enriched output to Obsidian). Hermes doesn't natively support skill hooks, but the pattern is achievable via the skill body itself — document pre/post steps explicitly in the skill procedure rather than embedding them in tool calls.


---

## StagedWorkspace — Versioned Workspace Contracts for File-Editing Skills (arXiv:2608.18050, Aug 2026)

StagedWorkspace (+8.3–12.1 OfficeQA Pass@1, +4.7–9.2 APEX rubric score) establishes workspace-state contracts as a distinct experimental variable in knowledge-work agent evaluation. The core principle: bind parsed records and review diffs to **content hashes** as the files evolve.

**Implications for skill design**:
- Skills that edit files should explicitly version the artifact: capture a hash of the input file before edits, verify the hash after edits match expectations, and record (hash_before, hash_after, change_description) as a structured diff. This makes the edit auditable and rollback-safe.
- Dual parsed/native access: maintain both a human-readable parsed view and direct file access. Skills that only do one lose information — parsed-only loses binary metadata; native-only requires re-parsing every time.
- Evaluation: when testing a file-editing skill, versioned workspace-state is an independent variable — same task + same model + different workspace state can yield different outcomes. Document which workspace state the skill was validated against.

**Hermes translation**: `patch` tool already provides the diff. Add content-hash capture to high-stakes file edits: `terminal("sha256sum <file>")` before and after, log both hashes to Hindsight. For skills that operate on user documents (docx, pdf, xlsx), record `{file: path, hash_before: x, hash_after: y, change: desc}` as a Hindsight event.

Reference: arXiv:2608.18050, "StagedWorkspace: A Versioned Workspace for Knowledge-Work Agents", Aug 2026.


---

## Demystifying Agent Skills — When Skills Help vs. Fail (arXiv:2608.14036, Sweep 20 addendum) <!-- why: skills are assumed to help; controlled experiments show they fail predictably when representation, retrieval difficulty, or cross-framework robustness are wrong -->

Controlled experiments across benchmarks, harnesses, and LLMs isolating the failure conditions of agent skills:

**When skills help:**
- Structured representation with outcome annotations (what happened + what to do next time) > raw procedure text
- Retrieval difficulty is LOW — the right skill is clearly the right skill for this task; no ambiguity about which skill applies
- Same harness the skill was designed for — cross-framework transfer degrades performance

**When skills fail (and the fix):**
- **Wrong representation**: skills written as abstract principles fail; skills written as concrete step sequences with worked examples succeed
  - Fix: every skill section should have at least one worked example with tool calls and expected output
- **High retrieval difficulty**: when multiple skills could plausibly apply, retrieval picks the wrong one
  - Fix: triggers must be mutually exclusive — if two skills both match "write a plan", one needs a narrower trigger condition
- **Cross-framework brittleness**: skills assume a specific harness structure (tool names, output shapes); when Hermes updates its tool API, skill instructions silently become wrong
  - Fix: skills must reference current tool names/parameters as of their last update; add version comment when a skill depends on a specific tool API shape

**Contrastive study design**: to test whether a skill is working, compare task success WITH the skill vs. WITHOUT the skill on the same task type. If the gap is < 2 steps, the skill may be dead weight.


---

## Skill Distribution Boundary Design (Zenn.dev/heftykoo, JP, Aug 21 2026, Sweep 20) <!-- why: copying skills/MCP before designing distribution boundary leads to trust contamination and scope creep -->

Japanese practitioner insight: before publishing or sharing skills/MCP tools, explicitly define the "distribution boundary" — what trust assumptions, secrets, and scope are embedded in the skill, and whether they are appropriate for the consuming agent.

Distribution boundary checklist for any skill:
1. Does the skill embed hardcoded paths, user-specific config, or localhost references? (Non-distributable by default)
2. Does the skill assume specific credentials or API keys? (Must be parameterised or stripped before sharing)
3. Does the skill's scope match the consuming agent's privilege level? (Don't give a low-trust subagent a skill with admin-level tool calls)
4. Does the skill assume side effects in a specific environment? (Add explicit `platforms:` frontmatter and a warning)

When distributing to subagents via delegate_task:
- Never pass skills that embed credentials or private paths directly
- Use `context` field to pass environment-specific parameters separately from skill logic
- Apply the least-privilege principle: subagent should only receive skills matching its `enabled_toolsets`


---

## Cross-Task Skill Transfer — Subtask > Task Induction (arXiv:2608.20274, Sweep 20) <!-- why: task-level induction regresses below no-memory baseline; subtask-level raises above -->

Comprehensive controlled study: how skills are induced shapes whether they transfer.

Two key axes: granularity (subtask-level vs task-level) and format (text vs code).

Findings:
- Task-level skills mostly reduce performance BELOW the no-memory baseline
- Subtask-level skills raise performance above baseline on average
- Text skills transfer better than code skills across tasks

Skill Utility Score = Specificity x Abstractness:
- Specificity: how closely a skill matches real tasks (too high = brittle)
- Abstractness: how evenly relevance spreads across tasks (too low = one-shot)
- Neither alone predicts success; their product does and correlates with task success

Hermes mandates:
1. Prefer subtask-level procedure decomposition over single-task solution capture
2. Express steps in text (procedural prose), not as code blocks encoding the core logic
3. Check utility score heuristic before finalising: too vague = add concrete trigger examples; too narrow = generalise trigger to cover the task class
4. Target: specific enough to retrieve correctly, abstract enough to transfer across 3+ related task types


---

## GitSkills Dataset — Empirical SKILL.md Patterns (arXiv:2608.10906)

Analysis of 3.79M SKILL.md files across 282K public repos (July 2026). Key empirical findings:

- **~50% duplication rate** (1.87M distinct hashes from 3.79M files) — skills spread by
  folder-copy with no package manager. Implies local skill libraries accumulate silent dupes
  over time. A periodic content-hash dedup pass over ~/.hermes/skills/ is warranted.
- **Trigger strings ≤60 chars are most effective** — confirms Hermes's 57-char rule.
- **Security anti-pattern found at scale:** secrets and tool tokens embedded directly in
  skill YAML frontmatter (API keys in `env:` fields). Never embed credentials in SKILL.md.
  Use environment variables or ~/.hermes/config.yaml instead.
- **Skills without `name:` field cause silent discovery failures** — always set name in frontmatter.
- **Maintenance gap:** skill files are rarely updated after creation; contradiction with external
  dependencies goes undetected. See SkillDrift section below.

**Hermes action:** Run `~/.hermes/scripts/skillspector-guard.py` periodically to catch stale
triggers and duplicate skill names. Future: add a content-hash dedup step to the guard script.


---

## routing_signals Frontmatter Field (skill-architecture-research-2026.md, arXiv:2603.22455)

**The body-hiding problem:** Hermes's 57-char description limit means the system-prompt skill
index shows only name + truncated description — exactly the "body-hidden" condition in which
SkillRouter finds a 31–44 pp routing accuracy drop vs. full-body retrieval at scale.

With 170+ skills in the library, routing is in the degradation zone. Fix: add a `routing_signals`
field to SKILL.md frontmatter with 200–400 chars of task vocabulary not in the description.

```yaml
routing_signals: >
  Use for: git worktree isolation, branch hygiene, pre-push verification gates, CI red-green
  checks, multi-file patch sequences, rollback planning, stash management, merge conflict
  resolution, feature branch lifecycle.
```

Rules for `routing_signals`:
- Include trigger phrases the description can't fit: synonyms, alternative phrasings, domain jargon
- Include anti-patterns ("do NOT use when X") to reduce false positive loads
- 200–400 chars — long enough to matter, short enough to keep context cost low
- Add when creating or significantly revising any skill; audit existing skills during monthly review

**Staleness gate:** Add `last_validated: "YYYY-MM-DD"` to frontmatter. Flag for review if
missing and the skill references versioned tooling (CLI flags, API endpoints, model names).

**Skill health dimensions (arXiv:2605.13716 SkillOps):** Five-dimension skill technical debt:
  utility        : does the skill produce correct task outcomes? (A/B vs no-skill baseline)
  compatibility  : does the skill compose without conflict with co-loaded skills?
  trigger coverage: do the trigger phrases match the real invocation surface?
  risk exposure  : does the skill have an adversarial or near-miss failure path?
  recency        : are model names, APIs, tool signatures still live?

When creating or auditing a skill, score each dimension (pass/fail/unknown) and add a
`skill_health` block to frontmatter for any skill rated critical (safety, routing, memory):
```yaml
skill_health:
  utility: pass         # confirmed beats no-skill on 3 task types
  compatibility: pass   # no conflict edges with co-loaded global skills
  trigger_coverage: partial  # "system update" still ambiguous vs OS-update trigger
  risk_exposure: low
  recency: pass         # model names verified 2026-08-30
  last_scored: "2026-08-30"
```

SkillAxe quality axes (arXiv:2606.10546): quality impact, trigger precision, instruction
compliance, solution-path coverage. A skill that scores low on trigger precision degrades
the entire session (it fires on wrong queries and injects irrelevant context).

```yaml
last_validated: "2026-08-18"
```

Quick staleness audit (>90 days without last_validated + versioned tool references):
```bash
python3 -c "
import glob, re, datetime
threshold = datetime.date.today() - datetime.timedelta(days=90)
for f in glob.glob('/var/home/rainbow/.hermes/skills/**/*.md', recursive=True):
    if '/references/' in f: continue
    txt = open(f).read()
    lv = re.search(r'last_validated:\s*[\"\']([\d-]+)', txt)
    has_versioned = any(x in txt for x in ['hermes config', 'hermes cron', '--model', 'claude-', 'anthropic.com'])
    if has_versioned and (not lv or datetime.date.fromisoformat(lv.group(1)) < threshold):
        print(f'STALE: {f}')
"
```


---

## Extended Frontmatter Fields — TMLR Lifecycle Survey (arXiv:2607.10113, skill-architecture-research-2026.md)

Priority 2 — lifecycle management (add to skills created or significantly revised):
```yaml
lifecycle_stage: trusted     # experimental | trusted | deprecated | archived
invocation_cost: low         # low | medium | high (rough token cost estimate)
```

Priority 3 — composition hints (SkillX 3-tier model, arXiv:2604.04804):
```yaml
skill_tier: functional       # strategic | functional | atomic
composes_with: []            # skills this skill delegates to or chains with
fallback_skills: []          # try these if this skill's approach fails
```

Priority 4 — lineage and failure logging:
```yaml
supersedes: []               # skills this replaces/absorbed
failure_log_path: null       # e.g. ~/.hermes/skill-failures/<name>.jsonl
```

**related_skills bidirectionality rule:** if skill A lists skill B in `related_skills`,
skill B must also list skill A. Violations cause silent routing asymmetry — skill B is
never surfaced when the user's task would naturally lead from A.


---

## TRACE Skill Bank Consistency — Pass^k Metric (arXiv:2608.22793, Aug 2026) <!-- why: Pass@N (can solve once) is not the right metric; Pass^k (solves consistently) is what production reliability requires -->

TRACE (TRAjectory-Contrastive Evolution) finds that frontier models have a large gap between Pass@3 (can solve at least once) and Pass^k (solves consistently across trials). The gap is the reliability problem.

**TRACE mechanism:** Iteratively improves a skill bank without modifying model weights. Each skill encodes a self-contained set of tool-use rules and behavioral guidelines. Contrastive trajectory pairs (pass vs. fail on the same task) drive skill body updates — the skill learns from both success and failure paths simultaneously.

**Pass^k as a skill quality metric for Hermes:**
When evaluating whether a skill is working, a single successful use (Pass@1) is insufficient. A skill should be validated with `Pass^k` — does it produce correct behavior on k consecutive independent attempts? Practical k=3 for `trust_level: validated`, k=5 for `trust_level: production`.

**Contrastive update protocol (approximate TRACE for Hermes):**
1. After any skill execution failure, record the failure trace in `~/.hermes/skill-failures/<name>.jsonl`
2. Pair with the most recent SUCCESS trace for the same skill/task type
3. Ask: "What did the success trace do differently from the failure trace?" → the answer is a targeted patch to the skill body
4. This is more reliable than either success-only or failure-only updates because it isolates the causal difference

**Consistency first, performance second:** TRACE finds that improving consistency (Pass^k) is the higher-value metric for production agents. Skills should be authored to maximize consistent behavior on repeated invocations rather than peak performance on a single attempt. This means:
- Explicit preconditions (so the skill only fires when it will succeed)
- Clear postconditions (so the agent knows when the skill has actually completed)
- Limit-awareness: the skill should recognize and refuse to proceed when constraints cannot be met, rather than attempting and failing

Reference: arXiv:2608.22793, "TRACE: A Self-Evolving Skill Bank for Consistent, Limit-Aware Agents", Aug 2026.


---

## SkillAlchemy — Admission-Centered Skill Creation from Open-World Sources (arXiv:2608.23417, Aug 2026) <!-- why: human-authored skills are biased toward known cases; contrastive evidence from sources reveals implicit requirements human authors miss -->

SkillAlchemy: given a skill brief and source materials, discovers implicit requirements missed by the brief via contrastive evidence, scopes procedures to evidence-supported ranges, and compiles an admission-gated skill package.

**Contrastive evidence for implicit requirements (apply at skill authoring time):**
When authoring a new skill, don't only ask "what does this skill need to do?" — ask "what does the BRIEF leave implicit that would cause failure?" Method: find 2+ real examples of the skill being invoked, identify cases where the obvious procedure would have failed, and extract the implicit requirement from that failure.

Example: a "write a PR description" skill brief seems complete. Contrastive evidence: looking at cases where PR descriptions were rejected reveals an implicit requirement — the description must reference the linked issue number and label each change type. That requirement isn't in the brief but is essential.

**Evidence-supported scope (anti-overgeneralization gate):**
Before adding a step to a skill, ask: "what is the evidence-supported scope of this step?" A step derived from a single case applies to a narrow scope; a step derived from 10+ cases can be stated as a general rule. Mark single-case steps as conditional: "If [specific condition], then [step]" rather than as universal rules. SkillAlchemy calls this "admission-centered" — only admit procedures whose scope is justified by the evidence.

**Grammar-guided skill package (for complex skills):**
For skills that compose multiple sub-procedures, make the composition grammar explicit in the frontmatter:
```yaml
composes_with: [skill-a, skill-b]  # which sub-skills this skill may invoke
fallback_skills: [skill-c]          # if main path fails, try this
```
This makes the composition auditable and prevents silent dependency drift.

Reference: arXiv:2608.23417, "SkillAlchemy: Admission-Centered Framework for Source-Grounded Skill Creation", Aug 2026.


---

## Failure-Trace Skill Updates — EvoAgent Pattern (arXiv:2604.20133, Jun 2026) <!-- why: success-only skill updates miss failure modes; failure-trace ingestion is the only reliable improvement path (all 11 successful repairs used failure trajectories) -->

EvoAgent (Focus Technology, v3) extends skill versioning with failure-recovery updates:
skills must be updated from BOTH success traces AND failure traces, not just the latter.

**Failure-trace update trigger (add to skill update workflow):**
When a task fails or requires significant human correction WHILE a skill was loaded,
append a failure trace entry AND update the skill immediately in the same session:

```bash
# 1. Log the failure
echo '{
  "date":"'"$(date -I)"'",
  "session":"'$SESSION_ID'",
  "task":"<brief task description>",
  "failure_mode":"<what went wrong>",
  "correction":"<what the correct approach was>"
}' >> ~/.hermes/skill-failures/<skill-name>.jsonl

# 2. Immediately patch the skill body with the failure insight
# skill_manage(action='patch', name='<skill-name>', old_string='...', new_string='...')
```

**Skill versioning — EvoAgent usage-count weighting for routing:**
Skills with high usage counts should be weighted MORE in routing decisions:
track in frontmatter: `usage_count: N` (increment after each successful load).
The routing score at 170+ skills: `score = 0.5 * semantic_sim + 0.3 * success_rate + 0.2 * log(usage_count + 1)`.
This matches EvoAgent's empirical finding that usage frequency is a strong proxy for
skill quality in production workloads.

**Two-tier skill retrieval (SkillRL arXiv:2602.08234):**
Distinguish general heuristics (always applicable, load unconditionally) from
task-specific heuristics (load only when the task context matches):
```yaml
retrieval_tier: general    # general | task-specific
# 'general' skills: adversarial-review, verification-before-completion, trajectory-risk-guardrail
# 'task-specific' skills: gold-class, obsidian, xlsx, pdf  — only when task matches exactly
```
SkillRL shows: separating these tiers reduces token footprint while improving reasoning utility.
General skills should be small and stable; task-specific skills can be larger/more specialized.

**Post-execution skill crystallization (ARISE arXiv:2603.16060):**
After any task that succeeds unusually well — the "I wish I'd had a skill for this" moment —
trigger skill generation from the successful trace BEFORE ending the session:
1. Ask: "What recurring procedure did I just discover that wasn't in a skill before?"
2. If yes: extract the core steps from the current session trace → draft a skill
3. Quality gate: the skill must generalize to ≥3 distinct task types beyond this one
4. Set `trust_level: experimental` and `source_episodes: [<current_session_id>]`

This formalizes what Hermes does informally ("offer to save as skill") into a triggered,
structured crystallization step. ARISE shows this raises OOD task performance most —
the skill bank grows toward generalization, not overfitting.

**Operational pipeline:** do not improvise harvest/admit/merge here. Load `runtime-skill-synthesis`
(`trace2skill.py` → SkillAlchemy admission → EvoAgent fail-log → overlap classify → Pass^k).
The four questions above are the authoring-time intent; that skill is the runtime procedure.


---

## Skill Failure Logging — Most Valuable Repair Input (arXiv:2608.02636, HKUST KnowComp)

42 runs show: ALL 11 successful skill repairs used failed trajectories as input.
Success-only feedback is insufficient. Hermes has no per-skill failure log currently.

**Lightweight implementation:** when a skill is loaded and the task fails or requires
significant correction, append a one-line JSONL entry:
```bash
echo '{"date":"2026-08-18","session":"<id>","task":"<brief>","failure":"<mode>"}' \
  >> ~/.hermes/skill-failures/<skill-name>.jsonl
```
Point `failure_log_path` in frontmatter to this file. The curator (or skillopt cron) reads
failure logs during maintenance to identify which skills most need targeted repair.


---

## Catastrophic Remembering prevention (arXiv:2608.11095)

Empirical study of 1,867 repos shows skill files grow 226% over their lifetime, gaining ~5 net
instructions per commit. Older instructions have logarithmically lower deletion probability.
The fix: **rationale comments**. Every non-trivial rule must include an inline comment or
narrative explaining *why* the rule exists and what failure it prevents. Rules with no rationale
are deletion candidates in the next consolidation pass.

**Mandatory rule (authoring):** Every rule or step added to a skill MUST include an inline rationale comment: `<!-- why: prevents [specific failure mode] in [session/task type] -->`. Rationale enables O(1) deletion audit vs O(2^n) without rationale. (arXiv:2608.11095: +23.1% instruction-following in ablation over 1867 repos). <!-- why: prevents un-auditable sediment growth in skill-authoring sessions -->

Compatible legacy forms still count as rationale (do not rewrite just to change syntax):
- HTML: `<!-- why: prevents [specific failure] in [session/task type] -->` (preferred)
- Trailing: `# rationale: <one-line reason>`
- Prose: a "Rationale:" sentence immediately after the rule

Example:

    Never use cosine alone for dedup  <!-- why: prevents false merges in memory-dedup sessions; cosine-only balanced accuracy caps at 0.70 -->

**Deletion audit procedure (SkillOpt pass):** Check each rule: does the rationale still apply? Stale rationale → delete the rule. Missing rationale → flag as deletion candidate. Vacuous rationales ("to improve quality", "legacy workaround") count as stale. <!-- why: prevents O(2^n) keep-vs-delete combinatorial explosion when reviewing long-lived skills -->

**SkillDrift check:** Flag rules lacking rationale as pruning candidates during consolidation audit.


---

## SkillDrift — Procedural Skills Go Stale (Taktile, Jul 2026)

Procedural skills reference external tools, APIs, and configs that change. Without freshness
contracts, a skill's steps quietly stop working. Pattern: add a `freshness:` block to any
skill whose steps reference external endpoints or CLI versions:

```yaml
freshness:
  check: weekly
  stale_signal: "CLI version mismatch or API 404"
  last_verified: 2026-08-12
```

Hermes implementation: add `last_verified:` and `stale_signal:` to frontmatter of skills
that wrap specific CLI versions or external APIs (firecrawl-research, huggingface-hub,
graphiti-mcp-setup, etc.). Flag for re-verification when the external dep releases.


---

## Procedural Anchoring Priority — Demystifying Agent Skills (arXiv:2608.14036, Aug 2026) <!-- why: prevents routing skills as knowledge stores when stabilization is the primary mechanism -->

Controlled experiments across 8,135 trial records (4+ frameworks, 6 benchmarks) on how and why agent skills actually work.

**Core finding:** Skills stabilize execution (procedural anchoring) — they do NOT primarily inject missing knowledge.
- **Procedural anchoring:** 65.7% of successful skill cases — noisy trajectories become structured plans
- **Explicit knowledge injection:** only 4.5% of successful skill cases
- Skills improve over Workflow Memory by +6.06 points in matched comparisons

**Retrieval precision collapse:** As skill pool grows from 5 → 100 skills, actual-use precision falls **29.6% → 3.3%**. Confusable distractors impair offline skill identification but downstream success remains stable — exact ground-truth invocation is neither sufficient nor necessary.

**Three failure modes for skills:**
1. **Brittle assumptions** — skill body assumes a specific execution context that no longer holds
2. **Stale procedure** — steps worked in one harness/framework but not another
3. **Context drift** — skill is retrieved but the task context mismatches the skill's implicit preconditions

**Hermes authoring rules from this:**
- Write skills to **stabilize action sequences**, not to store knowledge facts (facts go to Hindsight/Graphiti)
- Procedural anchoring = the primary value. If a skill has no clear action-sequence structure, it is likely providing near-zero benefit
- On retrieval precision collapse: for pools >20 skills, rely on semantic embedding routing (not keyword) — precision collapses only with weaker retrieval strategies
- Add a **`## Assumed Context`** subsection to skills with brittle assumptions: document what execution environment, tool versions, or states must hold for the skill to apply
- Skills with `capabilities: [file_read, shell_exec]` are at higher risk of brittle assumptions — document the precondition explicitly


---

## Tool-Count Fallacy + Downstream Data Fragmentation (Zenn.dev/JP, Aug 2026) <!-- rationale: adding more skills doesn't fix accuracy because the bottleneck is downstream data fragmentation, not skill quality -->

"ツールを100個並べてもAIエージェントは賢くならない" (Adding 100 tools doesn't make an agent smarter)

**Four structural problems persist regardless of skill/prompt quality when skills fan out to disparate APIs:**

1. **Fusion burden**: the LLM must fuse heterogeneous response formats on-the-fly every turn — structural mismatch between APIs compounds token cost and error rate
2. **Entity aliasing**: the same real-world entity has different identifiers across systems (user_id vs email vs username); the agent must resolve silently on every call, and fails silently when it guesses wrong
3. **Variable API latency**: the slowest API gates the entire response; more skills = more APIs = higher expected gate latency
4. **Tool-count context degradation**: each additional tool schema in context degrades tool-selection accuracy — empirically confirmed, consistent with context-contamination literature

**Implication for skill authoring:** These four problems are NOT fixable by better skill descriptions. The root cause is data fragmentation, not skill quality. Before authoring a new skill that calls multiple external APIs, ask:

> "Can this data be pre-integrated into Graphiti before inference, so the skill reasons over unified facts rather than routing live calls?"

If yes: integrate first, then author a simpler skill that reads from Graphiti. The skill's job is to reason, not to assemble.

**Skill reachability as a named anti-pattern:** skills that exist but are never routed to are operational dead weight. Name: "skill sink" — skills with no successful routing in 60+ days. Mitigation: `skillspector-guard.py` periodic audit + reachability test.

**Minions pattern (from same source):** for deterministic work (data fetch, calculation, format conversion), use a Postgres job queue and call a script — not an LLM sub-agent. LLM sub-agents are for judgment only. Skills that encode deterministic logic are candidates for rewrite as scripts called from a simpler skill.

Reference: Zenn.dev "ツールを100個並べてもAIエージェントは賢くならない" + Velog.io/@okorion/GBrain, Aug 2026.


---

## Agent Skills Standard (agentskills.io / Anthropic, Aug 2026)

The emerging cross-vendor skill standard at agentskills.io defines a formal schema for portable
agent skills. Key additions beyond current Hermes SKILL.md format:

```yaml
input_schema:          # Explicit JSON Schema for what the skill consumes
  type: object
  properties:
    query: {type: string, description: "The user's question or task"}
  required: [query]

output_schema:         # What the skill guarantees to produce
  type: object
  properties:
    result: {type: string}
    citations: {type: array, items: {type: string}}
```

**Hermes guidance:** When writing skills that will be called programmatically (by agents or cron),
add `input_schema` and `output_schema` to the frontmatter. This enables automated skill routing
(the dispatcher can verify outputs match expectations) and is forward-compatible with the
emerging standard. Skills called by humans via slash-commands do NOT need this — keep it
for machine-invocable skills only.


---

## Sweep 29 Additions (Aug 2026)

### Credential Leak via Skills (ASE 2026 arXiv:2604.03070) ★ HIGH
73.5% of SkillsMP credential leaks come from debug logging tool outputs into LLM context.
89.6% are immediately exploitable. Mandatory rules:
1. Never log API keys/tokens in skill docs or examples.
2. Remove `print(token)` / `console.log(key)` patterns from skill examples.
3. `am-sentry.py --verbose` now scans for credential patterns (Sweep 29).
4. Forks defeat remediation — leaked creds in git history of a skill remain exposed.

### SPT: Reference Insert at Mention Site (arXiv:2608.26563) ★ HIGH
Skills pre-train better when references inserted at mention sites, not dumped at end.
Pattern: `Use [XYZ (arXiv:XXXX.XXXXX)](url) which does Y` at first mention.
Not: `See References at end of skill.`

### SkillShield: Security Skills in System Prompt (arXiv:2608.25817) ★ MED
Security skills synthesized offline and included in system prompt reduce malware severity
3.37→0.58 with only 0.14% benign refusal rate. Enforcement via context, not sidecar classifiers.


---

## Sweep 29 Batch 2 Additions (Aug 2026)

### SWE-Prime Quality Filter: Keep Only Successful, Non-Trivial Trajectories (arXiv:2608.27449) ★ MED

When compiling skill trajectories from session history (preact-trajectory-compilation):
1. Filter to successful completions only (exit_code=0 + test pass or user confirms)
2. Drop trivially short trajectories (< 5 tool calls) — no generalizable pattern
3. Require at least one non-trivial recovery (retry after error, plan change, tool fallback)
4. Tag with complexity_class: [simple, with_recovery, with_verification, with_subagent]
5. Prefer trajectories with verification steps over those that just run-to-end

Rationale: SWE-Prime shows that quality filtering on training data (not quantity)
drives most of the performance gain. Same applies to ICL trajectories injected into skills.

### Knowledge Card Citation Format for Skill Injections ★ HIGH

When injecting retrieved facts into a skill response, use card format:
```
[FACT: <one-line claim> | SOURCE: <session:id:N-M or URL> | CONF: 0.87 | SCOPE: workflow]
```
Not raw chunked memory. The claim+source+confidence tuple is the atomic unit.
Never inject raw search results as facts — they lack the evidence_span binding.
