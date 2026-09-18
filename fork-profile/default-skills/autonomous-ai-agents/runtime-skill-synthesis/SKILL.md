---
name: runtime-skill-synthesis
description: Use when crystallizing skills from execution traces.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
trust_level: experimental
related_skills:
  - skillopt-continuous-improvement
  - self-improve-agent
  - hermes-agent-skill-authoring
  - hermes-skill-library-consolidation-audit
  - trajectory-research-synthesis-to-skills
triggers:
  - crystallize a skill from this session / execution trace
  - admit or reject a trace2skill candidate
  - merge overlapping skills
  - recursive skill library refinement
  - track Pass^k / consecutive skill success
  - ARISE post-execution skill generation
  - SkillAlchemy admission gate
counter_triggers:
  - For SCORE→DIAGNOSE of an existing skill use skillopt-continuous-improvement (it proposes only — edits need self-improve-agent for human approval)
  - For human-gated post-task lessons without crystallization use self-improve-agent
  - For SKILL.md frontmatter/format use hermes-agent-skill-authoring
metadata:
  hermes:
    tags: [skills, synthesis, ARISE, SkillAlchemy, EvoAgent, merge, prune]
    related_skills:
      - skillopt-continuous-improvement
      - self-improve-agent
      - hermes-agent-skill-authoring
      - hermes-skill-library-consolidation-audit
ssl_scheduling:
  triggers: [crystallize skill from trace, merge overlapping skills, admit skill candidate, Pass^k tracking]
  preconditions: [session id or two SKILL.md paths, skill_manage available]
  estimated_steps: 6
ssl_structural:
  tools_used: [terminal, skill_view, skill_manage, session_search, read_file]
  subtasks: [Harvest, Crystallize, Admit, Failure-patch, Merge/prune, Pass^k]
ssl_logical:
  side_effects: [pending-improvements files, skill-failures jsonl, skill-quality jsonl, skill_manage patches]
  resources: [~/.hermes/scripts/trace2skill.py, ~/.hermes/skill-failures, ~/.hermes/skill-quality, ~/.hermes/cache/pending-improvements]
  risk_level: medium
---

# Runtime Skill Synthesis

Closed loop the literature specifies and Hermes previously only described: crystallize skills from traces (ARISE), admit them on contrastive evidence (SkillAlchemy), patch from failure traces (EvoAgent), merge/prune overlap (recursive library refinement), and promote on consistency not one-shot success (TRACE Pass^k).

Not for SkillOpt scoring of existing skills (use skillopt-continuous-improvement); not for SKILL.md format (use hermes-agent-skill-authoring); not for post-task lesson extraction without crystallization (use self-improve-agent).

Autonomous/cron runs: stage only. Interactive: propose and wait for explicit user confirmation before skill_manage create/patch/promote. An interactive session is not human approval. Do not auto-apply `skill_manage create/patch/delete` from cron/ralph/subagent. Stage with `~/.hermes/scripts/stage-improvement.sh`.

## When to Use

- A task succeeded with a novel 5+ tool-call workflow not covered by an existing skill
- `trace2skill.py` wrote a candidate under `~/.hermes/cache/pending-improvements/`
- Two skills fire on the same task class or share most steps/triggers
- A loaded skill failed or needed user correction
- Promoting `experimental` → `validated` → `production`

Don't use for: scoring an existing SKILL.md (skillopt), format-only authoring, or one-off lessons that are not procedures.

## Analogical SOP Retrieval (SimCRAFT, arXiv:2608.30277)

Before implementing a novel plan: run `session_search(query=task_summary)` to find structurally similar past tasks. If found: extract the SOP pattern (which steps worked, which failed) and adapt — do not copy verbatim, map the structure to the current context.
Priority: do this at L2+ tasks before plan-from-memory.

## Evo-Harness: One-Shot Skill Compilation (arXiv:2608.15071, EMNLP 2026)

Source: Evo-Harness, EMNLP 2026 Main. One-shot context-to-harness compilation: distill noisy single-shot executions into reusable skill harnesses. Online harness learning on a frozen agent — the agent improves by updating the structured harness, not its weights.

**When:** After completing a novel task for the first time (no existing skill already covers it).

**Procedure:**
1. **Extract lessons** from the execution trace — what steps, tool choices, and decision patterns were applied
2. **Filter for transfer:** keep broadly-useful insights; discard task-specific artifacts (specific file paths, user names, one-off configs, environment-specific workarounds)
3. **Validate cross-domain transfer:** mentally test whether the lesson applies to 2+ *different* task types (e.g., does "always verify write before claiming done" apply to git ops AND file patching AND API calls? Yes → keep. Does "use path /var/home/rainbow/proj/x.py" apply broadly? No → discard)
4. **Add to harness only if the cross-domain test passes.** Single-domain lessons stay in Hindsight or ERRORS.md — not in a reusable skill

**Anti-pattern:** Adding task-specific facts to a reusable skill pollutes it with noise that degrades future routing accuracy (mismatches between trigger description and skill content). The skill library becomes a log of incidents rather than a library of procedures.

**Admission gate (arXiv:2608.29596):** Before a newly synthesized skill is used in production, it must pass `adversarial-review` with AdaRubric `skill/doc` dimensions (Coherence, Coverage, Trigger Accuracy, No Dead Content). A skill that fails any dimension is held as `draft`, not admitted. This gate applies in addition to the SkillAlchemy contrastive-evidence admission checklist (step 3 above) — both must pass before `skill_manage create` with `trust_level: experimental`.

**Signal:** This pattern is why skills must contain "how-to-do-X-class-of-tasks" not "what-happened-in-task-Y". A skill that records *what happened* instead of *the general pattern* will misfire on every future task where the specifics differ — which is every future task.

<!-- why: Evo-Harness (EMNLP 2026) shows that frozen agents improve via harness updates only when the harness captures transferable structure; task-specific artifacts added to a shared harness cause capability regression on other task types by polluting skill routing signals -->

## Pipeline

Run steps in order. Stop at the first failed gate. Completion criterion for the whole pipeline: every admitted or merged skill has `trust_level`, at least one `source_episodes` id, and a Pass^k log path.

### 1. Harvest (ARISE) <!-- rationale: ARISE arXiv:2603.16060 — post-execution crystallization raises OOD performance; success-only informal "offer to save" overfits -->

After a completed task, trigger crystallization only when ALL of:

- 5+ tool calls (drop trivial traces; SWE-Prime)
- At least one recovery (retry, fallback, or user correction) OR the workflow is clearly new
- Outcome was success (or a corrected success). Pure failures go to step 4, not new-skill create
- No existing skill already covers the procedure (`skills_list` + `skill_view` on the closest name)

If an existing skill covers it: skip create, go to step 4 (patch) or step 6 (Pass^k).

Get the session id (`hermes session list` or the current session) then:

```bash
python3 ~/.hermes/scripts/trace2skill.py SESSION_ID
# writes ~/.hermes/cache/pending-improvements/skill-candidate-<sid>-<ts>.md
```

If a second session solved the same problem, intersect before admitting:

```bash
python3 ~/.hermes/scripts/trace2skill.py --merge FILE1 FILE2
```

Keep only shared steps as universal rules. File-unique steps become `If <condition>:` conditionals (SkillAlchemy evidence-supported scope). Done when a candidate file exists or harvest correctly skipped.

### 2. Crystallize check

Open the candidate. Reject immediately if:

- Name collides with an existing skill (patch that skill instead)
- Steps invent tools/commands not in the trace
- Trigger would also fire the closest sibling skill (osmosis)

Otherwise continue to admission. Done when the candidate is either rejected with a one-line reason or passed to step 3.

### 3. Admit (SkillAlchemy) <!-- rationale: arXiv:2608.23417 — human briefs miss implicit requirements; admit only evidence-supported scope -->

ALL boxes required. One miss = reject or stage, never `skill_manage create`.

- [ ] **Contrastive evidence:** 2+ real traces/sessions. Named at least one case where the obvious procedure would have failed, and wrote that implicit requirement into `## When to Use` or `## Pitfalls`.
- [ ] **Scope:** every universal step appears in 2+ traces. Single-trace steps are conditional, not rules.
- [ ] **Overlap audit:** not DUPLICATE of a live skill (run step 5 classify). If OVERLAP, merge into the dominant skill instead of creating.
- [ ] **Transfer:** procedure is a subtask class, not a single ticket. Prefer ≥3 related task types; otherwise keep `tier: task` and do not promote past `experimental`.
- [ ] **Frontmatter on create:** `trust_level: experimental`, `source_episodes: [<session-id>]`, `failed_trajectories: []` (fill from harvest if the trace had recoveries).

Create only after the checklist passes AND the user types an explicit yes. Autonomous/cron runs: stage only. Interactive: propose and wait for explicit user confirmation before skill_manage create/patch/promote. Interactive presence is not approval.

### 4. Failure-trace patch (EvoAgent) <!-- rationale: arXiv:2604.20133 + 2608.02636 — all 11 successful repairs used failed trajectories; success-only updates are insufficient -->

When a loaded skill fails or needs significant correction, log first — always, even if you will not patch yet. Pass the skill name as argv (do not put `$SKILL.jsonl` inside a Python string; `$SKILL` does not expand there). Get session id from `hermes session` / the current session, not `os.environ['SESSION_ID']`.

```bash
mkdir -p ~/.hermes/skill-failures
# Replace SKILL_NAME with the loaded skill's name; SESSION_ID from `hermes session`.
python3 -c "
import json, datetime, pathlib, sys
skill = sys.argv[1]
session = sys.argv[2]
p = pathlib.Path.home()/'.hermes'/'skill-failures'/(skill + '.jsonl')
p.parent.mkdir(parents=True, exist_ok=True)
rec = {
  'date': datetime.date.today().isoformat(),
  'session': session,
  'task': '<brief>',
  'failure_mode': '<what went wrong>',
  'correction': '<what worked>',
  'paired_success_session': '<id or empty>'
}
with p.open('a') as f:
    f.write(json.dumps(rec)+'\n')
print('logged', p)
" SKILL_NAME SESSION_ID
```

Then pair with the latest **success** for the same skill/task type (`session_search` or `~/.hermes/skill-quality/<skill>.jsonl`). The patch is the contrastive delta only: what the success did that the failure did not. Do not rewrite adjacent sections.

- Autonomous/cron runs: stage only (`~/.hermes/scripts/stage-improvement.sh`) — never direct apply.
- Interactive: propose the patch and wait for explicit user confirmation before `skill_manage create/patch/promote`.
- Also append the session id to `failed_trajectories` in frontmatter when patching (after yes).

Done when the jsonl line exists. Do not patch in the same turn without an explicit user yes.

### 5. Merge / prune overlapping skills <!-- rationale: AutoRefine arXiv:2601.22758 — without prune+merge, repos bloat 4.5× and utilization crashes 0.71→0.08; cosine-only merge is unsafe (opposites can score 0.96) -->

**MDL Skill Deduplication Gate (SCAFFOLD, arXiv:2609.05511):** Before creating a new skill, check for behavioral equivalence — not just semantic similarity. Two skills are behaviorally equivalent if:
  1. Their trigger conditions cluster to the same user intent (cosine > 0.80 is a hint, not the decision)
  2. Their tool-call skeleton has ≥70% step overlap (same tools in same order, different parameters only)

If both conditions hold: extend the existing skill rather than creating a new one. The SCAFFOLD MDL criterion shows that skill deduplication via behavioral equivalence checking prevents library collapse (monotonic gains across 5 iterations without collapse when MDL gate is active; collapse occurs without it).

**Implementation check (before step 3 SkillAlchemy create):**
```bash
# Get trigger clusters for candidate skill
python3 ~/.hermes/scripts/skill-router-index.py --query "<trigger text>" --top 3
# If top match cosine > 0.80: read that skill and compare tool-call skeletons manually
# If ≥70% skeleton overlap: patch the existing skill, do not create a new one
```

Cosine > 0.80 / 0.92 is a **candidate hint**, not a merge decision.


**Detect candidates** (any one is enough to audit):

- Same category and overlapping `triggers:`
- Both listed in each other's `related_skills` and bodies restating the same steps
- Same recent tasks loaded both (`session_search`)
- Consolidation audit / skillspector flagged a near-duplicate

**Classify** by reading both SKILL.md files (required LLM audit, ToolScope-style):

| Class | Meaning | Action |
|---|---|---|
| DISTINCT | different contracts | keep both; add negative routing |
| COMPLEMENT | same family, different contract | keep both; tighten umbrella/router |
| OVERLAP | shared core, unique edges | merge into dominant |
| DUPLICATE | same contract | merge; deprecate absorbed |

**Pick dominant:** `production` > `validated` > `experimental`; then higher real use; then newer `last_validated`. Never absorb a production skill into an experimental one.

**Merge content:**

1. Union unique pitfalls (dropping a pitfall is a SkillEvo regression).
2. Shared steps stay universal; unique steps become conditionals.
3. Union then dedupe triggers; add a negative routing sentence for the absorbed name.
4. Set on dominant: `supersedes: [absorbed-name]`.
5. Set on absorbed: `superseded_by: dominant-name`, `lifecycle_stage: deprecated`. Do **not** delete in the same pass.
6. Make `related_skills` bidirectional on the dominant and remaining siblings.
7. Archive the absorbed skill only after the dominant has Pass^k ≥ 3 on the shared task class.

Autonomous loops stage the merge; they do not `skill_manage delete`.

Done when classification is recorded and either (a) both kept with negative routing or (b) dominant patched + absorbed marked deprecated.

### 6. Pass^k tracking (TRACE) <!-- rationale: arXiv:2608.22793 — Pass@1 overstates reliability; production needs consecutive independent successes -->

After each skill-using task, append one outcome. Pass the skill name as argv (do not use a literal `$SKILL.jsonl` inside Python). Session id from `hermes session` / the current session, not `os.environ`.

```bash
mkdir -p ~/.hermes/skill-quality
python3 -c "
import json, datetime, pathlib, sys
skill = sys.argv[1]
session = sys.argv[2]
outcome = sys.argv[3]
task_class = sys.argv[4]
p = pathlib.Path.home()/'.hermes'/'skill-quality'/(skill + '.jsonl')
p.parent.mkdir(parents=True, exist_ok=True)
rec = {
  'date': datetime.date.today().isoformat(),
  'session': session,
  'outcome': outcome,  # pass or fail
  'task_class': task_class
}
with p.open('a') as f:
    f.write(json.dumps(rec)+'\n')
" SKILL_NAME SESSION_ID pass TASK_CLASS
```

Streak = consecutive `pass` from the tail, reset on `fail`. Independent attempts only (different sessions, not retries inside one session).

| trust_level | required streak | extra gate |
|---|---|---|
| experimental → validated | Pass^3 | `source_episodes` has ≥3 distinct sessions |
| validated → production | Pass^5 | ≥1 `failed_trajectories` entry and a patch from it (AUSO) |

A single Pass@1 never promotes. A fail logs to skill-failures (step 4) and resets the streak.

Do not silently bump `trust_level`. Log the streak. Propose promotion only when the table gates pass, then wait for explicit user yes before any frontmatter write. Autonomous/cron: stage the promotion; never apply.

Done when the jsonl line is present. Promotion is not applied in the same turn without an explicit user yes.

## Monthly refinement pass

When running skillopt or consolidation-audit, add:

1. `ls ~/.hermes/skill-failures/` — skills with ≥3 fails in 30 days are repair-first.
2. Overlap audit on pairs the scorer or skillspector flagged (step 5).
3. Streak check on `~/.hermes/skill-quality/*.jsonl` for overdue promotions or reset-and-repair.
4. Pending candidates: `ls ~/.hermes/cache/pending-improvements/skill-candidate-*.md` through step 3.

## Common Pitfalls

- **Cosine merge:** high embedding similarity ≠ same contract. Always classify before merging.
- **Create vs patch:** overlapping candidate → merge/patch, not a third sibling.
- **Immediate patch without pair:** EvoAgent needs the success/fail delta, not a guess from the fail alone.
- **Auto-delete absorbed skills:** deprecation first; delete only after Pass^k on the dominant.
- **Pass@1 promotion:** one good run is not `validated`.
- **Autonomous apply:** cron/ralph/subagent stages; it does not `skill_manage create/patch/delete`.

## Verification Checklist

- [ ] Harvest skipped or produced a candidate from a real session id
- [ ] Admission checklist completed (pass or explicit reject reason)
- [ ] Failures have a jsonl line under `~/.hermes/skill-failures/`
- [ ] Outcomes have a jsonl line under `~/.hermes/skill-quality/`
- [ ] Merge classified DISTINCT/COMPLEMENT/OVERLAP/DUPLICATE before any body edit
- [ ] No `skill_manage delete` without prior `superseded_by` + Pass^k on dominant
- [ ] Autonomous path used `stage-improvement.sh`
