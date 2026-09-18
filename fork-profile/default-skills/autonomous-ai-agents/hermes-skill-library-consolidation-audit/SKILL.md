---
author: Hermes Agent
description: 'Use when: running a broad architecture audit or skill library consolidation pass. Systematic Hermes-wide audit:
  skill duplication, dead references, description format, security-queue backlog, config/cron consistency.'
license: MIT
metadata:
  hermes:
    related_skills:
    - hermes-skillspector-guard-maintenance
    - skill-family-router-maintenance
    - hermes-context-hygiene
    - hermes-config-repo-audit
    - hermes-agent
    - skillopt-continuous-improvement
    - hermes-semantic-skill-routing
    tags:
    - hermes
    - skills
    - consolidation
    - architecture
    - audit
    - deduplication
    - config
    - cron
name: hermes-skill-library-consolidation-audit
related_skills:
  - hermes-skillspector-guard-maintenance
  - skill-family-router-maintenance
  - hermes-context-hygiene
  - hermes-config-repo-audit
  - hermes-agent
  - skillopt-continuous-improvement
  - hermes-semantic-skill-routing

platforms:
- linux
- macos
- windows
triggers:
- user asks for an overall Hermes architecture/consolidation pass across skills, config, and cron
- user asks to remove duplication/redundancy or resolve conflicts across the skill library
- a compaction handoff or prior session references a broad "clean up everything" pass with no concrete task content
- suspect skill cross-references (related_skills, skill_view calls in prose) point at renamed or removed skills
- need to verify the skill library, config.yaml, and cron jobs are internally consistent after a burst of skill edits
- a skill cluster audit subagent returns a findings report revealing stale content, broken paths, or description-format violations across multiple skills
version: 1.0.0
---


# Hermes Skill Library Consolidation Audit

Use this for a broad "architecture pass" across the live `~/.hermes/` environment —
not for fixing one skill or one script. This is the class-level procedure; individual
symptom-specific skills (skillspector guard internals, session hygiene, config-repo
drift) stay separate and this skill points to them at the right step.

## When the request includes "research X and implement improvements"

When the user's request is scoped as "research [topic] and implement anything useful" — combining external discovery (arXiv, GitHub, social media, multilingual sources) with local implementation — treat these as two distinct sequential phases, NOT as "audit the local system":

1. **Phase 1 — External research first**: dispatch parallel subagents to sweep arXiv, GitHub, Hacker News, Reddit, and non-English sources (CNKI, J-STAGE, CyberLeninka) across the relevant topic clusters. Each subagent writes a structured report file to `/tmp/`. Do NOT begin local implementation until Phase 1 reports land.

2. **Phase 2 — Implement from findings**: read the research files, cross-reference against what's already in the skill library (check existing reference files before declaring something new), then implement only the genuinely new findings as skill patches or new reference files.

**Anti-pattern to avoid**: interpreting "research memory topology and implement improvements" as a prompt to run a local memory/skill audit. A local audit is a *different* task class (hermes-config-repo-audit, adversarial-audit) that does not require external research. If the request contains "research [topic]", external sweeps come first.

Scooping — what counts as a research sweep: arXiv (English + Chinese institution queries), GitHub trending, Hacker News, Reddit r/MachineLearning / r/LocalLLaMA, and at least one non-English source per topic (CNKI via web_search, J-STAGE, CyberLeninka). Minimum 3 parallel subagents for independent topic clusters.

### Ad-hoc in-session sweep: use execute_code, not subagents

For ad-hoc "research X and implement" work (not the weekly cron pipeline), run the sweep
as a Python loop in `execute_code` — NOT as delegated subagents. Benefits: no stream-stall
risk, full parent visibility, convergence detection (loop until delta=0 new IDs).
Estimated 3x faster than delegation.

Saturation rule: stop when a wave returns 0 new IDs OR all new IDs are non-HIGH. Do not
run a confirmation wave — if wave N returned nothing HIGH, wave N+1 with the same queries
will also return nothing.

Implementation grouping: batch HIGH findings by target-cluster (not by paper), at most one
agent per target skill. Run the pre-dispatch scope conflict check (`dispatching-parallel-agents`)
before dispatching to prevent concurrent-write interleave.



## Research-to-implementation discipline (critical pitfall — validated Aug 2026)

When the task is "research X and implement improvements", skill patches alone are
documentation — not implementation. The distinction matters:

**Documentation only (no runtime effect):**
- Patching SKILL.md with research findings / adding references/*.md summaries
- Only applies when a future session explicitly loads that skill

**Real runtime changes:**
- Code: `~/.hermes/scripts/*.py` — l1-extract, l1-promote, audit scripts
- Config: `hermes config set ...` — compression, agent loop, auxiliary models
- AGENTS.md additions — always-injected, affects every session immediately
- New cron jobs — run independently of any session

**Checklist:** For each research finding, ask: does it need a code/config/AGENTS.md
change to take effect? If yes, make that change and verify (`hermes config get`,
`python3 script.py --dry-run`). Skill patch is secondary, not the primary deliverable.

**Aug 2026 examples:**
- RecMem recurrence gate → l1-promote.py code change (verified --dry-run) ← REAL
- 35% compression floor → AGENTS.md addition ← REAL
- micro_compact/proactive_prune → `hermes config set` ← REAL
- Tool Attention patterns → skill doc only (only active when skill loaded) ← DOC ONLY

## skill_prune_audit.py — operational script (added Aug 2026)

`~/.hermes/scripts/skill_prune_audit.py` — monthly library health check.
Cron: `skill-prune-audit` (job f8aa4b717a18), 1st of each month 09:00, no-agent.
Silent when healthy; prints report when prune/merge candidates exist.

```bash
python3 ~/.hermes/scripts/skill_prune_audit.py           # 60-day stale window
python3 ~/.hermes/scripts/skill_prune_audit.py --days 30
python3 ~/.hermes/scripts/skill_prune_audit.py --json    # machine-readable
```

## Skill size audit — inline bloat detection (added Aug 2026)

SKILL.md has a 100KB hard limit. Skills that accumulate inline knowledge banks,
code blocks, and pitfall narratives hit this limit silently until a write fails.
The fix is extracting large self-contained sections into references/ files and
replacing them with 2-3 line pointers.

Thresholds:
- < 30KB: healthy, no action
- 30-50KB: monitor — check if any section > 5KB is genuinely procedural or is a knowledge bank
- 50-80KB: extract — identify the largest self-contained section (code blocks, paper lists,
  pitfall narratives, stats tables, project layouts) and move to references/
- > 80KB: urgent — skill writes may fail; extract immediately

Quick size scan:
```bash
find ~/.hermes/skills -name 'SKILL.md' | xargs wc -c | sort -rn | head -20
```

Line count + arXiv section count is a faster research-dump detector:
```python
import re, pathlib
for p in sorted(pathlib.Path("/var/home/rainbow/.hermes/skills").rglob("SKILL.md")):
    if ".archive" in str(p): continue
    text = p.read_text(errors="replace")
    lines = text.count("\n")
    arxiv_sections = len(re.findall(r'^###.*arXiv', text, re.M | re.I))
    refs = len(list(p.parent.glob("references/*.md")))
    if lines > 800 or arxiv_sections > 5:
        print(f"{lines:4d}L {arxiv_sections:3d} arXiv ### {refs:2d} refs  {p.parent.name}")
```
Skills with > 10 arXiv `###` subsections and 0 refs are immediate extraction candidates
regardless of line count.

Extraction rule: a section belongs in references/ if it is:
1. A knowledge bank (paper lists, stats tables, property data, project layouts)
2. A large code recipe (>50 lines) that is looked up, not executed step-by-step
3. A pitfall catalogue that is consulted reactively, not followed sequentially
4. Any section already partially duplicated in an existing references/ file

Keep inline: trigger conditions, numbered procedural steps, quick-reference checklists,
single-command snippets, 5-bullet pitfall summaries (pointers to full catalogue in refs/).

When extracting:
- Use `scripts/extract_skill_section.py` (bundled) for reliable extraction with byte-count reporting
- Or manually: write section to references/[descriptive-name].md, replace inline with a one-line pointer
- Keep pointer compact: `*[Section title] — see references/[file].md. [1-sentence summary.]*`
- Verify final SKILL.md is under 50KB (49206 bytes = just under the 50000 threshold)
- The skill_prune_audit.py script also flags skills >50KB in its monthly report

Extraction script (Aug 2026, bundled):
```bash
python3 ~/.hermes/skills/autonomous-ai-agents/hermes-skill-library-consolidation-audit/scripts/extract_skill_section.py \
  ~/.hermes/skills/<category>/<skill>/SKILL.md \
  "Section Header Partial" \
  extracted-section.md \
  "*Section title — see references/<extracted-section>.md.*"
```

## When the request includes "do an overall architecture pass, consolidate everything
conflicts" is a *class* of request, but it is also exactly the kind of vague instruction
that can arrive attached to a hallucinated compaction summary (see
`hermes-context-hygiene`'s fallback-handoff section). Before running any of the audit
below:
1. Verify any specific nouns from a prior/compacted summary (repo paths, file names)
   against real system state — do not assume a summary's invented specifics are real.
2. If genuinely ambiguous which surface the user wants improved (security flags vs.
   skill duplication vs. config/cron vs. all three), ask with concrete options rather
   than guessing scope for a multi-hour recursive pass.

## Dynamic Skills 8-Stage Lifecycle (arXiv:2607.10113, TMLR 2026)

Survey: "Dynamic Agent Skills: A Lifecycle Survey and Taxonomy of Evolving Skill Libraries"
(Yubo Li, TMLR 2026). 124 papers, 2023–2026. Key finding: admission and repair are the
most repeatedly important stages; verifier quality materially affects skill-aware RL;
flat retrieval degrades at scale. GitHub: arxiv.org/abs/2607.10113

The 8-stage lifecycle defines what a production skill system should implement — use this
as the gap analysis framework when auditing the Hermes skill library:

| Stage | What it does | Hermes current state | Gap |
|-------|-------------|---------------------|-----|
| 1. Evidence acquisition | Collect task trajectories and outcomes that could become skills | Partial: session_search + l1-extract | No systematic outcome tagging |
| 2. Admission | Decide whether a skill candidate should enter the library | Manual: skill_manage(create) | No automated admission threshold or quality gate |
| 3. Verification | Test the skill against known cases before accepting | None | No test harness for skill correctness |
| 4. Indexing | Organize skills for efficient retrieval at scale | Partial: YAML frontmatter + flat semantic search | No capability tree; degrades at 170+ skills |
| 5. Execution | Run the skill in context | Done: skill_view → follow instructions | N/A |
| 6. Monitoring | Track skill usage, success, failure rates | Partial: .usage.json (counts only) | No success/failure tracking per invocation |
| 7. Repair | Fix skills that have degraded, changed context, or produce errors | Manual: skill_manage(patch) | No automated repair trigger |
| 8. Governance | Access control, versioning, deprecation, rollback | Partial: curator adopt | No rollback, no versioning, no deprecation policy |

**Most critical gap for Hermes today (admission + repair):**
- Admission: when should a skill be created vs added to an existing one? Current answer
  is ad-hoc. The lifecycle survey recommends an explicit threshold: create only when
  3+ distinct task types would benefit, and the content cannot fit as a patch to an
  existing skill.
- Repair: skills degrade silently when environments change. Current practice: user
  reports a problem → agent patches. Proactive trigger: any skill not used in 60+ days
  that references versioned tooling should be flagged for review.

## EvoAgent Evolutionary Metadata (arXiv:2604.20133, Sweep 22)

EvoAgent (2026): 3-stage skill matching + evolutionary metadata on every skill artifact.
Hermes approximation — add these fields to SKILL.md frontmatter when creating or auditing skills:

```yaml
# EvoAgent-style evolutionary metadata (optional but recommended for production skills)
birth_version: "1.0.0"          # version when skill was first created
last_validated: "2026-08-24"    # date skill was last confirmed correct on a real task
validated_by: "task_run"        # task_run | manual_review | eval_harness
superseded_by: ""               # if non-empty, this skill is deprecated — load the named one instead
maturity: "validated"           # experimental | validated | production (from AUSO lifecycle)
```

**3-stage matching** — when selecting which skill to load for a task:
1. **Semantic match**: embedding similarity on name + description (current Hermes routing)
2. **Structural match**: check `triggers:` block for explicit task-type alignment
3. **Evolutionary match**: prefer `maturity: production` or `validated` over `experimental`; prefer more recently `last_validated` when two skills are otherwise equivalent

**Practical use in audits**: when the skill-prune-audit flags a skill as stale (60+ days unused), check `last_validated` and `maturity`. If `maturity: experimental` and never validated, it's a prune candidate. If `maturity: production` but `last_validated` is old, it needs a repair pass before the next use.

**Anti-pattern**: creating a skill, using it once successfully, and never updating `last_validated` or promoting `maturity`. The skill looks experimental forever and gets deprioritised by routing.

**Six-type skill artifact taxonomy** (from the survey):
1. **Declarative** — factual knowledge (what is X, how does X work)
2. **Procedural** — step-by-step instructions (how to do X)
3. **Conditional** — branching procedures (if X then Y, else Z)
4. **Template** — reusable patterns with variable slots
5. **Composite** — skill that invokes other skills (see AgentSkillOS)
6. **Executable** — code or script artifacts

Hermes SKILL.md files are predominantly Procedural (#2) and Conditional (#3). The Declarative
type (#1) is currently handled by reference files (references/*.md). Template (#4) and
Composite (#5) are underused — SkillComposer and AgentSkillOS patterns could improve this.

**Use this framework when:**
- Deciding whether to create a new skill or patch an existing one (admission gate)
- Auditing skills that haven't been used in 60+ days (monitoring → repair trigger)
- Planning any significant reorganisation of the skill library (indexing gap)

## AutoRefine Bloat Law: Why Prune+Merge Is Non-Optional (arXiv:2601.22758)

AutoRefine empirical result (2026): without periodic prune+merge cycles, skill
repositories **bloat 4.5× while utilization drops from 0.71 to 0.08**. This is not
a slow degradation — it accelerates as the library grows because routing noise
compounds. The pass rate *drops* (35.6%→31.1%) while the library inflates.

The dual-form approach: skills have a "dense" (full body) and "sparse" (summary)
form. The sparse form is used for routing; the dense form is loaded on invocation.
Hermes approximates this with the 57-char description (sparse) + full SKILL.md (dense).

**Practical rule for Hermes:** Any skill not invoked in 60+ days AND with a close
semantic neighbour (cosine similarity > 0.80) is a prune+merge candidate. At 170 skills
with an estimated 15-20 never-used, running prune+merge now prevents the 4.5x inflection.

Audit trigger: when total skill count passes 150, schedule a prune+merge pass. At 170,
we're past that threshold — the next audit should include a dedicated merge pass.

## Rethinking Self-Evolving: Failure Trajectories Are Load-Bearing (arXiv:2608.02636)

HKUST KnowComp finding (Jul 2026, 42 feedback runs × 14 settings):
- Evolution is sparse: only 55/388 candidates establish validation bests
- **All 11 successful skill repairs used failed task trajectories** — success-only
  feedback is insufficient for repair
- Test-time scaling (Sequential Refinement) CANNOT match persistent skill evolution:
  skills +32 pts vs Sequential Refinement +0 pts on SpreadsheetBench

**Practical consequence for Hermes skill repair:**

When a skill is being patched because it "didn't work" on a task, the repair needs
the failure description, not just the desired outcome. The pattern:

```
skill_manage(action='patch', ...,
  # Document WHAT FAILED, not just the fix:
  # old_string: the text that caused the failure
  # new_string: the corrected version
  # Include in the patch body: what task failed, what the error was
)
```

If you only know "the skill gave wrong results" without the failure trace, the patch
will be underspecified and likely to fail in the same way again.

**Implication for skill authoring:** when creating a skill from a successful task run,
also document the pitfalls that required correction mid-task — those are the failure
trajectories that make the skill reputable. A skill with zero documented pitfalls is
probably under-captured.

## Master research synthesis reference files

These three filenames were historically cited as living under `~/.hermes/skills/autonomous-ai-agents/references/`:
`hermes-improvement-master-2026.md`, `runtime-architecture-research-2026.md`, `hermes-improvement-aug2026-sweep2.md`.
**They are not on disk.** Do not `skill_view` or `read_file` them. Load this skill's own `references/` files instead (listed at the end) before a new consolidation pass.

## The five audit surfaces, run in this order

Before starting: if this pass was triggered from a vague compaction summary, verify any specific nouns (repo paths, file names) against real system state before acting on them.

### 0. Skill description format audit (new — from LobeHub deep-review pattern)

**Scale finding (Aug 2026):** When `find ~/.hermes/skills -name 'SKILL.md' | wc -l` returned
184 (up from 170), a format scan found ~125 of 184 skills missing "Use when" in their
description. This is the primary routing signal the model uses to decide whether to load a
skill. Missing it means those skills are essentially invisible to automatic routing and can
only be triggered by exact trigger-string matches. At this prevalence, the gap is not a
per-skill cosmetic fix — it is a systematic routing degradation that needs a bulk-fix pass.

**Bulk-fix approach** (do not hand-edit 125 skills one at a time):
1. Extract all descriptions with the script below.
2. Group by category — some categories (research, devops) have a dominant pattern that can
   be batch-applied ("Use when researching X").
3. Use skill_manage(action='patch') only for skills where the existing description
   clearly maps to a "Use when" form. For ambiguous skills, add "Use when [current
   description reformatted as trigger]." as a prefix without changing the rest.
4. Do not change trigger blocks, only description field values.
5. The first 57 chars of the description is the routing window — keep the "Use when"
   clause within that window so it appears in the system-prompt index.

Run before diving into per-surface checks. Extracts all descriptions and flags format violations:

```bash
for f in ~/.hermes/skills/**/SKILL.md(N); do
  echo "=== $(dirname $f | xargs basename) ==="
  python3 -c "
import sys, re
content = open('$f').read()
parts = content.split('---')
if len(parts) < 3: sys.exit()
import yaml
fm = yaml.safe_load(parts[1])
desc = fm.get('description', '')
user_inv = fm.get('user-invocable', True)
has_use_when = 'Use when' in desc or 'use when' in desc
has_triggers_on = 'Triggers on' in desc or 'triggers on' in desc
if not has_use_when:
    print('  MISSING: Use when clause')
if not has_triggers_on and user_inv:
    print('  MISSING: Triggers on clause (model-invocable skill)')
if len(desc) > 800:
    print(f'  LONG description: {len(desc)} chars')
"
done
```

Flag descriptions that:
- Have NO `Use when` clause (model can't decide when to load it)
- Have NO `Triggers on` clause AND are not `user-invocable: false` (no routing signal)
- Exceed 800 chars (approaching the 1024 limit with little room)

Skills with `user-invocable: false` are slash-command-only — they don't need `Triggers on`.
Don't normalize a description by removing trigger keywords just to fit a template — keywords ARE the routing signal.

See also:
- `references/research-autonomous-agents-audit-aug2026.md` — Full Aug 2026 audit of all
  research/ and autonomous-ai-agents/ skills: CRITICAL/HIGH/MEDIUM/LOW findings, cross-cutting
  chain status (safety stack, memory topology, research pipeline, web extraction), reference
  file orphan map, and priority remediation order. Load before any pass touching these categories.
- `references/research-pipeline-audit-checklist.md` — when the audit scope is the
  `research/` skill category: trigger overlap checks, fallback chain consistency, absorbed-
  technique quality criteria, reference file duplication pairs, `arxiv-sweep-findings`
  structural integrity rules, missing-skill disk check, and knowledge-bank creep detection.
  Validated Aug 2026.
- `references/research-implement-adversarial-pipeline.md` — full validated pattern for
  the research→implement→adversarial→verify pipeline, with Aug 2026 findings, REAL vs
  DOC-ONLY change classification, adversarial subagent context packet, and the 21-check
  verification script. Load this when the request is "research X and implement improvements".
- `software-development/adversarial-review/references/skill-library-audit.md` for bulk frontmatter extraction scripts and trigger coverage auditing (coverage counts, collision checks, broken ref checks). Step 0 here adds the *format quality* pass (Use when / Triggers on clauses); that reference handles *structural presence* (triggers block exists or not).
- `references/four-pass-audit-pattern.md` in this skill for a worked example and Python template for the four-pass audit methodology (broad detect → triage → fix + refine → final clean). This pattern minimizes false positives and verifies fixes before stopping.

## Four-pass audit methodology
Pass 1 - Broad detect: run all queries permissively; expect ~40% FP rate; zero false negatives.
Pass 2 - FP triage (mandatory before patching): check each finding against live state; classify REAL | FP-SCOPE | FP-ALREADY-FIXED | FP-INTENTIONAL.
  Regex pitfall: strip fenced code blocks from description before checking Use when:
  desc_no_code = re.sub(r'```.*?```', '', desc, flags=re.DOTALL)
  Also: user-invocable: false skills never need Use when - exclude them.
Pass 3 - Fix + refine: patch only REAL findings; re-run duplicate-key + block-scalar detectors after each batch.
Pass 4 - Final clean: re-run ALL queries library-wide from scratch; done only when HIGH=0, MEDIUM=0.

### 1. Security queue (skillspector_guard)
Delegate to `hermes-skillspector-guard-maintenance` for the mechanics.
NOTE: `hermes-skillspector-guard-maintenance` is NOT curator-managed (created_by=None).
Autonomous sessions cannot patch it. To update it, run `hermes curator adopt hermes-skillspector-guard-maintenance` in a foreground session first, then patch. Key point for
the consolidation pass specifically: **loop, don't do one round**. Reject/confirm the
current `pending_quarantine` batch, then re-run `--enforce` — this can surface a new
pending item. Repeat until an `--enforce` run yields zero new pending entries before
calling this surface done.

**Batch-reject pattern for large pending queues (19+ proposals, all FP):**
```python
for skill, reason in reject_map.items():
    terminal(f'python3 ~/.hermes/scripts/skillspector_guard.py --reject-quarantine "{skill}" --reject-reason "{reason}"')
# Then verify:
terminal('python3 ~/.hermes/scripts/skillspector_guard.py --enforce 2>&1 | grep pending_quarantine')
```
NEEDS_HUMAN_REVIEW with TP=0 across all findings + no executable scripts in the skill
= almost certainly FP. Apply domain knowledge (is this a config/doc skill that mentions
API URLs? → URL-in-docs FP). Do not wait for LLM confirmation to reject these.

## Recommended frontmatter schema extensions (Aug 2026 research)

Based on arXiv:2605.16508 (routing at scale), arXiv:2606.03056 (SkillDAG), arXiv:2602.20867 (security):

```yaml
# Standard fields (required)
name: skill-name                 # lowercase, hyphens, max 64 chars
description: >                   # MUST start with "Use when" within first 57 chars
  Use when <gerund phrase>. <rest of description>.
triggers:
  - "exact phrase that triggers this"
related_skills:
  - skill-name                   # flat list (current) OR typed edges (future):
  # - name: skill-name
  #   edge_type: depends_on | composes_with | conflicts_with | supersedes

# Recommended new fields (Aug 2026)
scope: [category-name]           # skill directory category, enables 2-level routing pre-filter
trust: core                      # core | community | user — supply-chain audit tier
routing_signals: >               # 200-400 chars: dense keyword bag for sub-description routing
  key phrases, technical terms, trigger keywords not captured in description
last_validated: "2026-08-10"     # ISO date, for staleness tracking in prune audit
```

**Priority when adding new fields:**
1. `scope:` — highest impact on routing accuracy at 150+ skills (add to all skills)
2. `trust: core` — needed for security audit classification (add to all bundled skills)
3. `routing_signals:` — add only for under-triggered skills (not loading when they should)
4. `last_validated:` — add when patching any skill, update when verifying still works
5. `edge_type` in related_skills — future, not yet implemented in routing

### Provenance field standard (TencentDB Team Memory, Aug 2026)

Shared skills that contain errors propagate that error to ALL agents that load them.
Add `provenance:` metadata to catch contaminated skills early:

```yaml
provenance:
  author: hermes-agent          # who created/last-substantively-modified this skill
  last_verified: "2026-08-12"   # date the skill was last confirmed correct in production
  review_status: approved       # approved | draft | deprecated | contaminated
```

**Contamination audit step** (add to each consolidation run):
- Check skills recently patched (in last 7 days) for plausible errors before they propagate widely.
- If a skill's `review_status` is `draft` and it's been loaded in production, upgrade to `approved`
  or flag for manual review.
- If a skill produces wrong results in a session, set `review_status: contaminated` immediately
  and patch before next use. Do not silently ignore skill-level errors.

### 2. Duplicate skill names
```python
import glob, re
base = "/var/home/rainbow/.hermes/skills"
names = {}
for path in glob.glob(base + "/**/SKILL.md", recursive=True):
    content = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'^name:\s*(\S+)', content, re.M)
    if m:
        names.setdefault(m.group(1).strip('"\''), []).append(path)
dupes = {k: v for k, v in names.items() if len(v) > 1}
print(dupes)
```
A skill name appearing twice in the same category-listing render (e.g. system-prompt
`available_skills` block showing "claude-code" twice with different descriptions) can
be a stale render artifact rather than a real registry conflict — cross-check with
`skills_list(category=...)` (the live tool call) before treating it as a duplicate to
merge. Only the filesystem + live `skills_list` together are ground truth.

Confirmed Sep 2026 instance: `humanizer` exists at both `creative/humanizer/` and as
a top-level `humanizer/` directory. The top-level copy is in `skills.disabled` in
config.yaml. Keep `creative/humanizer`; treat the top-level as superseded. Do not
enable both simultaneously — they share the same `name: humanizer` field and will
collide in the router.

### 3. Dead cross-references
Skills reference each other via `related_skills:` frontmatter and inline
`skill_view(name="...")` prose mentions. These rot when a skill is renamed or removed.
Use `scripts/skill_xref_audit.py` (bundled with this skill) to find every reference
that doesn't resolve to a real `name:` in any SKILL.md on disk. Run it, then for each
hit:
- if it's a real dead reference (renamed/removed skill) → patch the referencing file
  to point at the current name, or drop the reference if nothing fits
- if it's a placeholder in generic authoring-template prose (`family-name`,
  `other-skill`, `specific-skill`) → leave it, it's not a real link
- if it's a deliberate illustrative example in a walkthrough → leave it

### 3b. Graph-of-Skills dependency metadata (aug 2026)

Skills can carry `depends_on`/`provides` YAML frontmatter (arXiv:2604.05333 pattern).
This enables transitive dependency resolution — load only the prerequisite chain instead
of all skills flat.

**Frontmatter convention (add to any skill where dependency is real and obvious):**
```yaml
depends_on: [skill-a, skill-b]   # exact skill directory names — prerequisites
provides: [capability-x, cap-y]  # free-form kebab-case capability tags
```

**Graph-walk script (live, Aug 2026):**
```bash
python3 ~/.hermes/scripts/skill-graph-walk.py <skill-name>
# Prints topological load order: deps first, target last
# Exits nonzero with fuzzy match hint if skill not found
# Does NOT support --list or --graph flags — positional arg only
```

As of Aug 2026, 21 skills have this metadata (research and software-development
categories). During any consolidation pass, look for skills with obvious real
dependencies (not speculative) and add these fields to grow the coverage.

**A^2E graph analysis findings (spike 001, Sep 2026 — 217 skills, 771 edges):**
- `related_skills` edges are symmetric (A→B and B→A both appear) — a cycle detector
  treating these as directed edges will report false cycles (9 SCCs found, 129 members).
  Treat `related_skills` as undirected for cycle analysis; only `depends_on` is directed.
- 40 active orphan skills (zero inbound AND zero outbound edges). Priority targets for
  wiring: skills with obvious functional relationships (e.g. router-admin-automation ↔
  tplink-ax55-router-automation; reddit-reading ↔ rss-feeds; vera-schema-therapy ↔
  autonomous-agent-loop-design).
- 0 broken refs — all `related_skills` and `depends_on` targets resolve to real SKILL.md
  files. Healthy baseline as of Sep 2026.
- Top-5 by degree (in+out): verification-before-completion (63), autonomous-agent-loop-design
  (38), plan (37), grounded-citations (34), subagent-driven-development (34). These are hub
  skills — high degree is expected and correct; don't mistake high centrality for bloat.

**Orphan detection script:**
```python
import glob, re, yaml
from collections import defaultdict
base = "/var/home/rainbow/.hermes/skills"
adj = defaultdict(set)
nodes = {}
for f in glob.glob(base + "/**/SKILL.md", recursive=True):
    if '/.archive/' in f or '/.curator/' in f: continue
    parts = open(f, errors='replace').read().split('---')
    if len(parts) < 3: continue
    try:
        fm = yaml.safe_load(parts[1]) or {}
        name = fm.get('name')
        if not name: continue
        nodes[name] = f
        for edge in (fm.get('related_skills') or []) + (fm.get('depends_on') or []):
            adj[name].add(edge)
    except: pass
# Build reverse
rev = defaultdict(set)
for src, targets in adj.items():
    for t in targets:
        rev[t].add(src)
orphans = [n for n in nodes if not adj[n] and not rev[n]]
print(f"Orphans ({len(orphans)}): {sorted(orphans)}")
```

See also: `hermes-semantic-skill-routing` (documents convention spec + integration
with context packets; note that skill is NOT curator-managed — use
`hermes curator adopt hermes-semantic-skill-routing` before patching it).

### 3c. Post-patch structural integrity scan (mandatory after bulk patch sessions, Aug 2026)

After any session applying 5+ skill_manage patches, run the `\n`-escape scan. Corruption
occurs when patches join content across newline boundaries — producing YAML-valid single-line
sections that render as unreadable walls of text. Found in 6 files in one session (Aug 2026).

```python
import glob
for f in glob.glob("/var/home/rainbow/.hermes/skills/**/*.md", recursive=True):
    if '.archive' in f or '.curator' in f:
        continue
    for i, line in enumerate(open(f).read().split('\n'), 1):
        if len(line) > 300 and line.count('\\n') > 2:
            print(f"{f}:{i} ({len(line)} chars)")
```
Exception: `\n` inside JSON/YAML string literals in code-block examples is intentional.
Fix: `line.replace('\\n', '\n')` and write back.

Run this scan as the final step of any consolidation pass, BEFORE the verification checklist.

**Extended YAML structural integrity scan** (run alongside the `\n`-escape scan, catches
four additional regression classes confirmed in Aug 2026 pass-2 audit):

```python
import glob, yaml, re
base = "/var/home/rainbow/.hermes/skills"
for f in glob.glob(base + "/**/SKILL.md", recursive=True):
    if '/.archive/' in f or '/.curator/' in f: continue
    try:
        parts = open(f, errors='replace').read().split('---')
        if len(parts) < 3: continue
        fm_text, data = parts[1], yaml.safe_load(parts[1]) or {}
        name = data.get('name', f)
        # Duplicate top-level keys
        for key in ['name', 'description', 'related_skills']:
            if len(re.findall(rf'^{key}:', fm_text, re.M)) > 1:
                print(f"DUPE_KEY '{key}': {name}")
        # Block scalar containing list items (looks like related_skills but is text)
        for k, v in data.items():
            if isinstance(v, str) and '\n- ' in v:
                print(f"BLOCK_SCALAR_LIST '{k}': {name}")
        # Concatenated skill names in related_skills
        for entry in (data.get('related_skills') or []):
            if isinstance(entry, str) and ' ' in entry.strip():
                print(f"CONCAT_ENTRY '{entry}': {name}")
        # Skills only in metadata.hermes (not visible to router)
        top = set(data.get('related_skills') or [])
        meta = set((data.get('metadata') or {}).get('hermes', {}).get('related_skills') or [])
        if meta - top:
            print(f"META_ONLY_REFS {meta-top}: {name}")
    except Exception as e:
        print(f"PARSE_ERR {e}: {f}")
```

See `references/pass2-yaml-patch-regression-patterns-aug2026.md` for concrete examples,
root causes, and fixes for each of these four failure modes.

### 4. Config/cron consistency
- `config.yaml` `skills.disabled` list: check for exact-string duplicates (`list.count(x)
  > 1`) — a real defect. Do NOT flag a disabled-but-not-on-disk name as broken; disabled
  lists intentionally include skills for platforms/scopes not present on this machine
  (e.g. macOS-only tools on a Linux box) — that's scope filtering, not an orphan.
- `hermes cron list --all`: check every job's `Last run` status is `ok` (not stale
  error), and that no two jobs have genuinely overlapping purpose/schedule producing
  redundant work. `deliver: local` on every job is *expected* on a CLI-only profile
  (see AGENTS.md) — not a defect to fix.
- **Skill pipeline tables must be cross-checked against live cron output (Aug 2026).** Skills that document cron schedules (e.g. `hindsight-stack-operations`'s L1 Memory Pipeline table) go stale when cron jobs are edited. After any cron job schedule change, grep every skill that mentions the job ID or job name and verify the schedule values match `hermes cron list`. Confirmed instance: `hindsight-stack-operations` stated l1-promote-periodic was "every 180m" after it was changed to "190m (kind=once, Repeat:∞)". Command: `grep -rl 'l1-promote-periodic\|a08989147b29' ~/.hermes/skills/` to find all affected skill files.
- **Script helper files can contradict SKILL.md after a fix pass (HIGH — Aug 2026).** When fixing dead routing in a SKILL.md body, also audit every file under `scripts/` for the same skill. Helper scripts often contain runtime JSON output strings or docstrings that reference disabled skills — and those strings are what an agent sees in tool call output, not the SKILL.md body. Concrete instance: `pdf/SKILL.md` was correctly fixed to say `ocr-and-documents` is disabled and give alternatives, but `pdf/scripts/pdf_read.py` still emitted `"Use the ocr-and-documents skill for OCR."` in its JSON output on scanned PDFs — contradicting the skill body. An agent following the tool output would still hit the dead end. **Rule:** For any disabled-skill routing fix, grep the corresponding `scripts/` directory too: `grep -rn '<disabled-skill-name>' ~/.hermes/skills/<category>/<skill>/scripts/`

- **MCP server routing cross-check (HIGH)**: after any audit pass, verify that every retrieval surface named in a skill's decision-order table matches live config. Disabled MCP servers (`enabled: false`) silently fail when called — skills that still list them as active routes mislead future agents. Check with: `grep -A3 'qmd:\|mempalace:\|graphiti:' ~/.hermes/config.yaml | grep enabled`. If a server is disabled, strike through its row in the skill's routing table and redirect to the next fallback. Confirmed instance: `hermes-memory-surface-selection` listed `qmd` as surface #3 while `qmd: enabled: false` in config — corrected Aug 2026.
- Run `hermes doctor` and `hermes config check` at the end regardless of what else was
  touched; both should exit clean.

### 4b. MCP routing consistency check (MANDATORY)
Covered by the MCP server routing cross-check bullet in §4 above. Do not skip it. Disabled MCP servers (`enabled: false`) silently fail; strike them from skill routing tables and name the next fallback.

## Verification (must pass before calling the pass complete)
- `hermes doctor` — if it reports large WAL, run `hermes doctor --fix` first (resolves in <60s). Then verify exit 0, "All checks passed".
- `hermes config check` exit 0
- `python3 ~/.hermes/scripts/skillspector_guard.py --enforce` exit 0 AND
  `pending_quarantine` empty in `last-summary.json`
- `scripts/skill_xref_audit.py` shows zero real (non-placeholder) broken refs
- `hermes cron list --all` shows all jobs `[active]` with `last run: ok`
- MCP routing check: `grep -A3 'qmd:\|mempalace:\|graphiti:' ~/.hermes/config.yaml | grep enabled` — every skill routing table updated to match. See `references/mcp-routing-consistency-check.md` for the full procedure and check commands.

## Routing-signal health check: "Use when" coverage

Run alongside the scale threshold check. The "Use when" clause in the description field
is the primary signal the model uses for automatic skill routing. Without it, the skill
can only be triggered by exact trigger-string matches — it's functionally invisible to
probabilistic routing.

Expected healthy state: > 90% of model-invocable skills have "Use when" in description.
Danger threshold: < 70% coverage means routing is degraded library-wide.

Quick check:
```bash
python3 -c "
import glob, yaml, re
base = '/var/home/rainbow/.hermes/skills'
total, missing = 0, []
for path in glob.glob(base + '/**/SKILL.md', recursive=True):
    if '/.archive' in path or '/.curator' in path: continue
    try:
        parts = open(path, errors='replace').read().split('---')
        if len(parts) < 3: continue
        fm = yaml.safe_load(parts[1]) or {}
        if fm.get('user-invocable') is False: continue
        total += 1
        desc = fm.get('description', '') or ''
        if 'use when' not in desc.lower():
            missing.append(fm.get('name', path))
    except: pass
print(f'Coverage: {total-len(missing)}/{total} ({100*(total-len(missing))//total}%)')
print(f'Missing ({len(missing)}): {missing[:10]}...' if len(missing)>10 else f'Missing: {missing}')
"
```

When coverage drops below 70%, treat the bulk-fix described in Section 0 as HIGH
priority before any other audit work — routing noise at that scale degrades ALL skills,
not just the ones with missing clauses.

## Scale thresholds: when to escalate from flat to structured retrieval
Based on the 2026 TMLR lifecycle survey (arXiv:2607.10113, 124-paper audit):
- **< 64 skills**: flat system-prompt index is fine (~96-98% routing accuracy)
- **64–128 skills**: flat retrieval starts degrading (78% accuracy at 128)
- **> 128 skills**: structured retrieval required (tree → DAG) to avoid 64% accuracy floor
- **Hermes at 170 skills** is in the degradation zone. The skill-library audit pass should
  include a retrieval structure check: are category trees being used for pre-filtering?

Additionally: without periodic prune+merge, libraries bloat 4.5× and skill utilization
drops from 0.71 to 0.08 at moderate scale (AutoRefine, arXiv:2601.22758). Maintenance
is survival, not cosmetic.

See `references/skill-architecture-research-2026.md` for the full 2026 research synthesis
(SkillRouter, SkillRet, AgentSkillOS, SkillX, SAGE, security findings, and recommended
Hermes frontmatter extensions).

## Cross-cutting chain audit (Aug 2026 — add to every category-level pass)

When auditing `research/` or `autonomous-ai-agents/` categories, verify these four chains are internally consistent — every member skill should document its position and route to adjacent members:

### 1. Safety stack: TRG → mnemosyne-atp-safety → VBC → agent-task-signoff
Check each safety-relevant skill (autonomous loops, harness design, self-improvement, nightshift) for:
- Does it reference all four members? Or just TRG + mnemosyne (common gap)?
- Does the `autonomous-ai-agents` umbrella route to `agent-task-signoff`? (Was missing Aug 2026)
- Do `self-improve-agent` and `harness-first-agent-design` reference the stack? (Missing Aug 2026)

### 2. Memory topology: Hindsight → Graphiti dual-write → MEMORY.md → system prompt
Check each memory skill for:
- Does it document the l1-graphiti-write.py dual-write leg, not just Hindsight→MEMORY.md?
- Are Ollama-as-embedder references updated to OpenAI text-embedding-3-small? (Ollama removed 2026-07-12)
- Does `agent-memory-consolidation` cover the dual-write? (Was missing Aug 2026)

### 3. Research pipeline: arxiv → domain-research-synthesis → arxiv-sweep-findings → skill patches
Check:
- Does `arxiv` body route to `arxiv-sweep-findings`? Or only in `related_skills`?
- Does `domain-research-synthesis` body describe the → patch endpoint?
- Does `arxiv-sweep-findings` reference `arxiv` as upstream? (Was absent Aug 2026)
- Is the `hermes curator adopt` prerequisite for blocked patches documented in upstream skills?

### 4. Web extraction fallback chain: web_extract → firecrawl-research → defuddle → blocked-page-recovery
Check:
- Does `defuddle` describe itself as step 3, not "first-pass extraction"? (Was wrong Aug 2026)
- Is the chain documented in each member's body, not just in `academic-literature-review`?
- Does `firecrawl-stealth-fallback` (in autonomous-ai-agents/) correctly describe how it wraps steps 2-3?

### 5. Memory retrieval quality: world-bridge anchor gap (arXiv:2607.24368)
InMind finding: implicit-association queries succeed at 14.4% without world-bridge anchors vs 84% with them. This is a write-time omission, not a retrieval algorithm problem.
Audit check for memory-write skills: do write instructions include 5-8 domain anchor objects per fact?
Verification: grep -l 'connects_to\|anchor terms\|world-bridge' ~/.hermes/skills/ -- search recursively

### Reference file orphan check
For each skill with a `references/` directory:
```bash
find ~/.hermes/skills -name '*.md' -path '*/references/*' | grep -v '/.archive/' | \
  sed 's|/references/.*||' | sort -u | while read dir; do
    skill="$dir/SKILL.md"
    if [ -f "$skill" ] && ! grep -q 'references/' "$skill" 2>/dev/null; then
      echo "ORPHAN_REFS: $dir"
    fi
done
```
True orphans (dated Aug 2026 snapshot — re-run the scan; do not treat as current): `anthropic-agent-api-patterns`, `dispatching-parallel-agents`, `workflow-map`.
Large-collection partial orphans: `academic-literature-review` (40+ files, ~5 named), `hermes-obsidian-sync` (23 files, ~4 named), `domain-research-synthesis` (25+ files, ~6 named).

## Semantic redundancy scan: keyword-overlap + trigger-text cross-check (Aug 2026)

Pure name-similarity misses most real overlaps; keyword overlap on trigger text +
manual trigger-text cross-check is the validated two-phase approach:

**Phase 1 — Keyword-overlap scan (within category):**
```python
import glob, os, re, yaml
from itertools import combinations

base = "/var/home/rainbow/.hermes/skills"

def keywords(text):
    stop = {'use','when','the','a','an','and','or','for','to','in','on','with',
            'as','is','are','at','of','it','this','that'}
    return set(re.findall(r'\b[a-z]{4,}\b', (text or '').lower())) - stop

skills = {}
for f in glob.glob(base + "/**/SKILL.md", recursive=True):
    if '/.archive/' in f or '/.curator/' in f: continue
    try:
        parts = open(f, errors='replace').read().split('---')
        if len(parts) < 3: continue
        data = yaml.safe_load(parts[1]) or {}
        name = data.get('name', os.path.basename(os.path.dirname(f)))
        cat  = f.replace(base+'/', '').split('/')[0]
        desc = data.get('description', '')
        skills[name] = {'cat': cat, 'desc': desc}
    except: pass

pairs = []
by_cat = {}
for n, info in skills.items():
    by_cat.setdefault(info['cat'], []).append(n)

for cat, names in by_cat.items():
    for a, b in combinations(names, 2):
        ka, kb = keywords(skills[a]['desc']), keywords(skills[b]['desc'])
        overlap = ka & kb
        if len(overlap) >= 3:
            pairs.append((len(overlap), cat, a, b, sorted(overlap)))

for score, cat, a, b, kws in sorted(pairs, reverse=True)[:20]:
    print(f"[{score}kw] {cat}/ -- {a} / {b} -- shared: {', '.join(kws[:6])}")
```

**Phase 2 — Trigger-text cross-check (for each flagged pair):**
Pull the actual description fields and judge manually. Threshold: ≥ 3 keyword overlap
is a candidate, NOT a confirmed redundancy. Most pairs at 3-4 overlap are format
overlaps (e.g. "create, edit, read" shared by docx/pdf/xlsx) not semantic duplicates.

**Decision rubric:**
| Evidence | Verdict |
|----------|---------|
| Same primary tool sequence + same task outcome | TRUE REDUNDANCY — merge candidate |
| One points to the other in its trigger ("not for X; use Y for that") | INTENTIONALLY SPLIT — keep both, confirm cross-refs |
| Same keywords from generic shared domain (file format, OS, "create/read/edit") | FORMAT OVERLAP — ignore |
| Both cover different scenarios of a larger class | COMPLEMENTARY — note in related_skills |

**Aug 2026 validated outcome (159-skill pass, 25 flagged pairs, 0 true redundancies):**
All pairs were intentionally split or format overlaps:
- hermes-swarm-consensus / merge-reconciler: explicitly split, each references the other
- silverblue-system-update-trigger / hermes-agent-independent-update-protocol: different scenarios
- risk-based-review / adversarial-review: risk-based picks depth; adversarial IS the method
- powerpoint/docx/pdf/xlsx: keyword overlap is "create, read, edit" — distinct file formats
- hermes-operating-pattern / hermes-cron-and-agents: umbrella + focused child, each points to the other

Key lesson: 159-skill library with 25 keyword-flagged pairs produced 0 merge actions.
The library was structurally well-organized despite appearing disorganized. Redundancy scans
produce many false alarms; trust the trigger-text cross-check over the overlap score alone.

## Pitfalls
- **Bulk description patcher: "Use when" past the 57-char window (Aug 2026).** Any script
  that prefixes "Use when" to an existing description must verify the phrase lands within
  the first 57 chars of the *final* string — not just that it's present. Long existing
  preambles (e.g. "Eliminate the dispatch→wait→synthesise..." prefix) can push "Use when"
  past char 57, making it invisible to the router even though the YAML is valid. The fix:
  after any bulk patch run, immediately execute the 57-char window verification query
  (see Section 1b above). Skills flagged by it need full description rewrites: "Use when
  <trigger-phrase>" in chars 0–57, verbose context moved to the skill body. This was
  caught by the adversarial pass in Aug 2026 — 15 of 125 bulk-patched descriptions had
  this defect.

- **l1 pipeline: new metadata fields need downstream stripping (Aug 2026).** When new
  metadata fields are added to staging.md format (e.g. `[type=X] [valid_from=ISO]`),
  every downstream consumer of staging.md must be updated to strip those fields before
  using the fact text. The gap: `cron_l1_retain.py` parsed staging.md lines by stripping
  `[timestamp]` and `[score=N]` only — new `[type=X] [valid_from=Y]` fields would have
  been ingested as literal fact text into Hindsight. Pattern to verify: after adding any
  new `[field=value]` token to the staging.md line format, grep `cron_l1_retain.py` (and
  any other staging consumer) for the field name — if absent, add a strip regex before
  the text is used. Canonical strip block location: just after the `[score=N]` strip.

- Treating a security scanner's severity_counts (CRITICAL/HIGH/MEDIUM/LOW) as
  "issues to fix" without checking whether they're pre-existing allowlisted false
  positives — read `allowlist.json` and `last-summary.json`'s `allowlisted` array
  first; re-flagging the same known-FP skill every pass wastes the whole audit.
  See `hermes-skillspector-guard-maintenance`'s "Known false-positive class" section.
- Stopping the security-queue step after one reject/confirm round (see above).
- Assuming a disabled-skill list entry with no matching file is an orphan bug —
  check whether it's legitimate platform/scope filtering first.
- Over-trusting a rendered system-prompt skill catalog over live `skills_list()` /
  filesystem truth when hunting duplicates.
- Not looping the whole four-surface pass: a "recursively fix until clean" instruction
  means re-verify after fixes, not one linear pass with no final re-check.

- **.archive is already excluded — do not recommend it as an action item (Aug 2026).**
  `EXCLUDED_SKILL_DIRS` in `skill_utils.py` (line ~32) already filters `.archive` from
  the system prompt index and the skills_list() live tool. The 195-skill count from a
  raw `os.walk` includes archive; the live prompt index uses the live count (~173).
  When a subagent or audit pass recommends "exclude .archive from the skill index",
  reject it — it is already done. The real count to track is the live `skills_list()`
  count, not the filesystem walk count.

- **Delegation task log tails are truncated — use summary files instead (Aug 2026).**
  Logs at `.hermes/cache/delegation/live/deleg_*/task-N.log` truncate large `execute_code`
  outputs with `(+NNNN chars)` markers. The full structured report from a completed subagent
  is in `subagent-summary-N-<timestamp>.txt` one level up (in `cache/delegation/`, NOT
  inside `live/`). Pattern to find: `glob.glob('.hermes/cache/delegation/subagent-summary-N-*.txt')`.
  For in-progress tasks, check for `final    |` marker in the log; if absent, the task
  is still running.

- **Adversarial audit can misread internally consistent dual-gate patterns (Aug 2026).**
  The hindsight-stack-operations skill states both "do NOT gate on cosine alone" AND
  "use cosine > 0.85 dual gate". An automated adversarial audit flagged this as a
  contradiction. It is not: the two statements are complementary — dual-gate means
  cosine > 0.85 AND LLM equivalence check, while "cosine alone is insufficient" warns
  against using only the cosine. Before "fixing" a reported contradiction in a skill,
  read both statements in full context — literal contradiction and rhetorical complement
  can look identical to a pattern-matcher.

## Pre-dispatch intelligence checklist (when delegating to an orchestrator)

When this audit is being handed off to a delegate_task orchestrator, gather all
ground truth in the SAME parent turn (batch reads concurrently) before dispatching.
The orchestrator gets a context packet, not live tool access — stale data causes
workers to duplicate or skip work the concurrent session already did.

```bash
# 1. Identify which skills are actually over threshold right now
find ~/.hermes/skills -name 'SKILL.md' ! -path '*/.archive/*' \
  | xargs wc -c | sort -rn | awk '$1 > 50000 {print $0}'

# 2. References inventory per oversized skill
for skill in <list-from-step-1>; do
  dir=$(find ~/.hermes/skills -name 'SKILL.md' -path "*$skill*" -exec dirname {} \;)
  echo "$skill: $(wc -c < $dir/SKILL.md)B, $(ls $dir/references/ 2>/dev/null | wc -l) refs"
done

# 3. Security queue — know the FP class before delegating
python3 ~/.hermes/scripts/skillspector_guard.py --enforce 2>&1 | grep PENDING

# 4. Cron health + hermes doctor — confirm clean baseline
hermes cron list --all 2>&1 | grep -E 'last run|Name:'
hermes doctor 2>&1 | tail -3

# 5. "Use when" coverage check
python3 -c "
import glob, yaml
base = '/var/home/rainbow/.hermes/skills'
total, missing = 0, []
for path in glob.glob(base + '/**/SKILL.md', recursive=True):
    if '/.archive' in path or '/.curator' in path: continue
    try:
        parts = open(path, errors='replace').read().split('---')
        if len(parts) < 3: continue
        fm = yaml.safe_load(parts[1]) or {}
        if fm.get('user-invocable') is False: continue
        total += 1
        desc = fm.get('description', '') or ''
        if 'use when' not in desc.lower(): missing.append(fm.get('name', path))
    except: pass
print(f'Coverage: {total-len(missing)}/{total}')
print('Missing:', missing)
"
```

**Concurrent session guard:** when another session is actively patching the same
skills, instruct the orchestrator/workers to check file size BEFORE extracting:
```bash
size=$(wc -c < ~/.hermes/skills/<category>/<name>/SKILL.md)
[ "$size" -lt 51200 ] && echo "already under 50KB — skip" && exit 0
```

## Standing skillspector FP rule: external API URLs in skill docs

These are **always false positives** — do not route to adversarial review first.

The skillspector scanner flags external HTTPS URLs in `.md` files as "Data
Exfiltration / External Transmission" at CRITICAL or HIGH severity. When ALL of
the following are true, batch-reject without per-item review:

- All `components` entries in the report show `"executable": false`
- All flagged files are `.md` type (not `.py`, `.sh`, `.js`)
- The URLs are known research/infrastructure APIs (arXiv, Semantic Scholar,
  OpenAlex, Firecrawl, GitHub API, etc.) or documented Hermes services

Confirmed FP class (Aug 2026, batch of 19 pending quarantine items):
- `api.semanticscholar.org` in academic research procedure docs
- `arxiv.org` in literature review references
- `api.firecrawl.dev` in web extraction skill docs
- `api.openalex.org` in research discovery docs
- GitHub API URLs in github-operations skill docs

**Batch-reject command (copy verbatim):**
```bash
for skill in <list-from-enforce-output>; do
  python3 ~/.hermes/scripts/skillspector_guard.py \
    --reject-quarantine "$skill" \
    --reject-reason "False positive: external API URLs in documentation/procedures, not executable data exfiltration code. Non-executable .md files documenting legitimate external APIs (arXiv, Semantic Scholar, GitHub, Firecrawl, etc.)."
done
python3 ~/.hermes/scripts/skillspector_guard.py --enforce 2>&1 | grep PENDING
```

Run `--enforce` again after the loop — it may surface a second batch that was
behind the first (loop until PENDING count is zero).

## Reference file orphan audit — full-library parallel dispatch (Sep 2026)

When the task is "audit all reference files and ensure they are implemented", the correct
approach is a two-phase pipeline — NOT sequential reading of each file:

**Phase 1 — Orphan scan (single execute_code call):**
```python
import glob, os
from collections import defaultdict

skills_base = "/var/home/rainbow/.hermes/skills"
all_refs = glob.glob(skills_base + "/**/references/*.md", recursive=True)
all_refs = [f for f in all_refs if '/.archive/' not in f and '/.curator/' not in f]

orphaned = []  # refs whose filename does not appear anywhere in parent SKILL.md
for ref_path in all_refs:
    basename = os.path.basename(ref_path)
    parent_skill = ref_path.replace('/references/' + basename, '/SKILL.md')
    if os.path.exists(parent_skill):
        skill_content = open(parent_skill, errors='replace').read()
        if basename not in skill_content:
            size = os.path.getsize(ref_path)
            parts = ref_path.replace(skills_base+'/', '').split('/')
            category, skill = (parts[0], parts[1]) if len(parts) >= 3 else ('unknown', parts[0])
            orphaned.append((size, category, skill, basename, ref_path))

orthaned.sort(reverse=True)  # largest first = most content to absorb
by_skill = defaultdict(list)
for size, cat, skill, name, path in orphaned:
    by_skill[(cat, skill)].append((size, name, path))

print(f"Total orphaned: {len(orphaned)} across {len(by_skill)} skills")
for (cat, skill), refs in sorted(by_skill.items()):
    print(f"  [{cat}/{skill}] {len(refs)} orphaned")
```

**Phase 2 — Cluster and dispatch parallel subagents:**
Group orphaned files by category into 3-5 clusters (not one per file). Each cluster
gets its own subagent with:
- Exact skill names (for skill_manage)
- Exact file paths
- Explicit absorption criteria: ABSORB (pitfalls/procedures not in SKILL.md) vs SKIP
  (pure dated logs, already-covered content) — but even SKIPs get cited in References

Critical subagent instruction: even SKIPped files must have their filename added to
the References section of the parent SKILL.md. "Orphaned" means uncited, not just
unabsorbed. The goal is zero filename-missing-from-parent, regardless of whether
content was absorbed.

**Cluster sizing guide:**
- agent-memory-consolidation alone warrants one subagent if it has 15+ orphaned files
- Combine multiple small-orphan skills (1-3 each) into one subagent batch
- Target 8-20 ref files per subagent for manageable context
- Separate by category to keep context packets coherent

**Post-completion adversarial pass:**
After all absorption subagents finish, dispatch a single cold adversarial subagent
per modified skill cluster to check:
- New content doesn't contradict existing SKILL.md rules
- Absorbed bullets are concrete (not generic advice)
- No duplicate content introduced
- SKILL.md size within bounds (wc -c; target <80KB, urgent >80KB)

## Reference file absorption triage (Aug 2026 workflow)

When the task is "implement high-value reference files into skills", use structured
triage rather than reading every file:

**Step 1 — Score by type before reading.** Four types worth absorbing (RUNBOOK > PITFALL > CONFIG > PATTERN).
Skip: dated audit logs (audit-YYYY-*.md), pure literature dumps, content already in skill body.

**Step 2 — Absorption check before patching.** Grep 2-3 key phrases from the ref against parent SKILL.md:
```bash
grep -c 'key_phrase_1\|key_phrase_2' ~/.hermes/skills/<category>/<skill>/SKILL.md
```
Count > 0: verify it's real absorption, not just a keyword mention.

**Step 3 — Self-tagged references are highest priority.** Check first:
```bash
grep -rl "next edit opportunity\|incorporate.*SKILL\|absorb.*at.*opport" ~/.hermes/skills/
```
These are deliberate debt markers left by prior sessions — absorb before everything else.

**Step 4 — Check non-skill surfaces too.**
- `~/.hermes/TOOLS.md` — frequently stale (removed tools, wrong ports, wrong API endpoints). Fix it.
- `~/.hermes/decisions/*.md` — often contain actionable patterns worth absorbing into skills
  (e.g. a "DECLINED" tool assessment still contains an extractable pipeline pattern)
- `~/.hermes/memory-facts/staging.md` — if non-empty after promote ran, the l1 pipeline is broken

What's worth absorbing vs skipping:
- ABSORB: concrete commands not yet in skill, error messages + fixes, config key inventory with defaults, runtime API quirks
- SKIP: generic best-practice advice, point-in-time audit statistics, session-specific timestamps

## Reference files masquerading as skills / unabsorbed research audit (Aug 2026)

A recurring concern: reference files filed under `references/` contain research findings
that were never implemented anywhere — "pretending" to be done because they're stored.

### Quick diagnostic (run in execute_code)

```python
import glob, os, re

skills_base = "/var/home/rainbow/.hermes/skills"

# 1. Orphaned refs — not cited in parent SKILL.md body
all_refs = glob.glob(skills_base + "/**/references/*.md", recursive=True)
all_refs = [f for f in all_refs if '/.archive/' not in f and '/.curator/' not in f]

for ref_path in all_refs:
    basename = os.path.basename(ref_path)
    parent_skill = ref_path.replace('/references/' + basename, '/SKILL.md')
    if os.path.exists(parent_skill):
        skill_content = open(parent_skill, errors='replace').read()
        if basename not in skill_content:
            print(f"ORPHANED: {ref_path.replace(skills_base+'/', '')}")

# 2. Research dump classification
dump_patterns = [r'-papers-\d{4}', r'-research-\d{4}', r'-sweep-', r'-aug\d{4}', r'-jul\d{4}', r'sweep\d+', r'findings-\d{4}']
for ref_path in all_refs:
    basename = os.path.basename(ref_path)
    if any(re.search(p, basename, re.I) for p in dump_patterns):
        content = open(ref_path, errors='replace').read()
        has_impl = bool(re.search(r'IMPLEMENTED|✅|applied.*hermes|hermes config set|l1-promote|l1-extract', content, re.I))
        recs = re.findall(r'(RECOMMEND|ACTION:|TODO:|should implement|patch.*skill)', content, re.I)
        if recs and not has_impl:
            print(f"UNABSORBED RECS ({len(recs)}): {ref_path.replace(skills_base+'/', '')}")
```

### What the Aug 2026 pass found

Stats: 460 ref files across 82 skills. Of those, 53 are research-dump type (sweep/papers/findings
in name). Most are cited in their parent SKILL.md and have implementation markers. The real
issues were narrower:

**Orphaned refs (17 total — not cited in parent SKILL.md):**
- `agent-memory-consolidation/adversarial-audit-findings-2026-07-03{a,b,c,d}.md` — 4 audit logs
- `hermes-config-repo-audit/runtime-audit-2026-08-14.md` — recent audit, not yet linked
- `agent-runtime-loop-patterns/agent-runtime-sweep-aug14-2026.md` — new sweep, not linked
- llm-agent-memory-pipeline-research/agent-memory-sweep-aug14-2026.md
- Full list is not stored in this skill; re-run the Phase 1 orphan scan.

**Genuinely unimplemented findings:**
- `agent-memory-consolidation/references/agent-skill-management-research-2026.md` contains
  5 paper-validated techniques never implemented in skillspector_guard.py or skill_prune_audit.py:
  four-tier pruning matrix, cosine 0.92 merge gate, capability guard rule,
  compositional pairwise safety, full SKILL.md text as routing signal.
  Re-read that source file for implementation notes.

**False alarms (the majority):**
- High citation rate (26/27 in llm-agent-memory-pipeline-research) is typical — most ref files
  ARE cited in SKILL.md bodies
- Research dumps with "implemented" markers or paper text containing action-words register
  false positives in naive grep-for-RECOMMEND checks
- Priority 3 items in llm-agent-memory-pipeline-research are explicitly deferred, not forgotten

### Rule: how to tell real vs pretend implementation

| Signal | Real | Pretend |
|--------|------|---------|
| Code in `~/.hermes/scripts/*.py` implements the finding | ✅ | |
| `hermes config set` was run | ✅ | |
| AGENTS.md addition | ✅ | |
| SKILL.md has "✅ IMPLEMENTED" + date | Likely ✅ | |
| Ref file filed under references/ with no code change | | ❌ |
| SKILL.md section says "see references/<file>.md" for a technique | | ❌ (doc only) |

## Completion rule
This pass is done only when all five verification checks above pass in the same
final round — not when each surface individually looked clean at some earlier point
in the session.

**Recursive stopping rule (Aug 2026):** when the user says "fix until no HIGH/MEDIUM",
run the full structured audit loop — detect → triage → fix → re-audit — and stop only
when a complete fresh pass returns HIGH=0, MEDIUM=0. Each cycle must re-run ALL
checks, not just the ones that had findings. A clean pass on a subset is not done.

## False-positive triage (mandatory before fixing — Aug 2026)

After collecting findings, triage each one against live system state before patching.
Several classes of finding are routinely false positives:

| Finding class | FP check |
|--------------|----------|
| MCP routing (skill says surface X is active) | `grep -A3 'qmd:\|mempalace:' ~/.hermes/config.yaml \| grep enabled` — if `enabled: false`, read the skill body; it may already mark it disabled |
| Cron schedule mismatch | Read both the skill body AND `hermes cron list` — skill may already document the correct value |
| Chain position error (e.g. "step 2 vs step 3") | Read the full chain section in the skill body; position wording may be intentional |
| "Use when" missing | Check `user-invocable: false` in frontmatter — these are slash-command skills that don't need the clause |

Rule: verify a finding against live state before spending a patch on it. Triage reduces a
14-finding list to 5 real ones. Document false positives as cleared in the audit pass log.

## Known Category Misplacements (Sep 2026 — not yet moved)

These skills are in the wrong category. They were identified during the Sep 2026
architecture audit but NOT moved (moving requires hermes CLI and was out of scope).
Note them during any future reorganisation pass. **Do not relocate in a docs-only
audit** — path churn breaks skill_view, related_skills, and cron skill lists.

| Skill | Current category | Should be |
|-------|-----------------|----------|
| `gold-class` | research/ | productivity/ |
| `stay-in` | research/ | productivity/ |
| `suggest-music` | research/ | productivity/ |
| `product-availability-search` | research/ | productivity/ |
| `hermes-research-ops` | autonomous-ai-agents/ | research/ |
| `hermes-obsidian-sync` | autonomous-ai-agents/ | note-taking/ |
| `vera-schema-therapy` | autonomous-ai-agents/ | (standalone or superpowers/) |
| `firecrawl-stealth-fallback` | autonomous-ai-agents/ | research/ |
| `nodejs-lsp-process-management` | devops/ | software-development/ |
| `bash-wizard-generator` | devops/ | software-development/ |
| `hermes-cron-and-agents` | software-development/ | autonomous-ai-agents/ |
| `hermes-operating-pattern` | software-development/ | autonomous-ai-agents/ |
| `hermes-observability-and-task-ledger` | software-development/ | autonomous-ai-agents/ |
| `hermes-memory-capture-and-bridge` | software-development/ | autonomous-ai-agents/ |
| `hermes-semantic-skill-routing` | software-development/ | autonomous-ai-agents/ |
| `information-theory-for-agents` | software-development/ | autonomous-ai-agents/ |
| `officecli` | software-development/ | productivity/ |
| `document-layout-design` | software-development/ | productivity/ |
| `context-safe-pdf-edits` | software-development/ | productivity/ |
| `requesting-code-review` | software-development/ | github/ |

To move: `hermes skills move <name> <new-category>` (requires foreground session).
Do NOT attempt to move by renaming directories — the skill registry won't update.

## Full-system scope trigger

When the user says "audit everything" or "the knowledge corpus as a whole" or "runtime,
topology, ontology, memory — all of it", the scope extends beyond skills to:

- **Runtime services**: Hindsight (9177), Graphiti-MCP (8765), FalkorDB (6379), SearXNG (8888), Firecrawl (3002), PG-Hindsight (5433) — check all ports reachable
- **Cron job/script consistency**: every cron job's `Script:` exists on disk, last run is `ok`, no orphaned scripts
- **WAL/DB health**: `hermes doctor` — if it reports large WAL, run `hermes doctor --fix` (resolves in <60s)
- **Skill category placement**: spot-check known skills are in expected directories
- **Skill name collision**: no two SKILL.md files share the same `name:` field
- **Config/MCP coherence**: disabled MCPs not referenced as active in skill routing tables

Batch all runtime/topology checks concurrently (socket probes, script existence, cron list,
doctor) in a single `execute_code` call to minimize round-trips.
## Ghost-dir cleanup: removing empty category skeleton dirs (Aug 2026)

After the ghost-file check identifies dirs without SKILL.md, remove them and
clean up any now-empty category parent dirs:

```bash
# Remove ghost skill dirs (dirs with no SKILL.md)
for d in \
  "/var/home/rainbow/.hermes/skills/<category>/<ghost1>" \
  "/var/home/rainbow/.hermes/skills/<category>/<ghost2>"; do
  rm -rf "$d"
done

# Remove orphaned category-level DESCRIPTION.md if no skills remain
# Then try to remove the now-empty category dir
rmdir /var/home/rainbow/.hermes/skills/<category> 2>/dev/null \
  && echo "Removed empty <category>/" \
  || echo "<category>/ not empty, kept"
```

**Pattern from Aug 2026:** mlops/ category had 3 ghost subdirs (evaluation/, inference/,
models/) and only a DESCRIPTION.md at category level — no real skills. After removing
the subdirs, removed DESCRIPTION.md and rmdir'd mlops/ entirely. Similarly,
autonomous-ai-agents/ouroboros/ and autonomous-ai-agents/references/ were ghost dirs
removed in the same pass.

**Safe to batch when:** all targeted dirs were confirmed ghost by the SKILL.md scan
(no SKILL.md found). Never rm -rf a dir without verifying it has no SKILL.md first.

**Verify after:**
```bash
# Re-run the ghost scan to confirm zero remaining
python3 -c "
import glob, os
base = '/var/home/rainbow/.hermes/skills'
for d in glob.glob(base + '/*/*/'):
    if not os.path.exists(os.path.join(d, 'SKILL.md')) and '/.archive/' not in d:
        print('GHOST:', d)
"
```

## Ghost-file check (add to every cluster audit pass)

Manifest entries (skill system-prompt index, `related_skills` blocks) can reference
skills that no longer exist on disk — "ghost files". They cause silent routing failures
that are impossible to diagnose from normal operation.

**Index-vs-disk divergence** is a distinct but related problem: a skill can appear in the
system-prompt index (listed in `available_skills`) but have no SKILL.md on disk. This
happens when a skill was deleted without registering the `absorbed_into` record, or was
planned but never created. The audit manifest (the list of files to read) is NOT ground
truth — always probe disk before batch-reading.

**Pre-read disk probe (run before any cluster batch-read):**
```python
import glob, os
base = "/var/home/rainbow/.hermes/skills"
for cat in ["research", "productivity", "note-taking", "email", "devops",
            "software-development", "autonomous-ai-agents", "github"]:
    for skill_dir in sorted(glob.glob(f"{base}/{cat}/*/")):
        if not os.path.exists(os.path.join(skill_dir, "SKILL.md")):
            print(f"MISSING SKILL.md: {skill_dir}")
```

**Aug 2026 confirmed ghosts in research/productivity/devops cluster (5 skills):**
`recent-news-briefing`, `signal-oriented-research-briefing`, `wallust-desktop-theme-integration`,
`wayland-session-troubleshooting`, `waybar-popup-menu-debugging` — all absent from disk,
all listed in audit manifest. See `references/research-productivity-devops-cluster-audit-aug2026.md`
for full details and per-ghost fix plan.

**Detection:** When reading a cluster, any `read_file` returning `File not found` is a
ghost. Also run:
```bash
grep -rn '<suspected-ghost-name>' ~/.hermes/skills/ --include='*.md'
```
to find all `related_skills` and prose references to the ghost.

**Fix:** Either create the skill (if content was never written) or add an "Absorbed into
`<target-skill>`" note at the top of the absorbing skill's SKILL.md. Then grep and
remove/update all `related_skills` pointers to the ghost name.

**Aug 2026 confirmed ghosts in software-dev/github cluster (5 total):**
`github-auth`, `github-pr-workflow`, `github-code-review`, `github-pr-followup-automation`,
`codebase-inspection` — all absent from disk, all absorbed (undocumented) into
`github-operations`. See `references/software-dev-github-cluster-audit-aug2026.md`.

## Duplicate YAML key pattern (structural defect)

A SKILL.md frontmatter can contain the same key twice (e.g. `name:` appearing at lines 3
and 26). YAML spec: second value silently wins. The defect is invisible at read time but
causes the skill to be indexed under the wrong name if values ever diverge.

**Detection:** After any bulk-edit pass, run:
```python
import glob, re
for f in glob.glob('/var/home/rainbow/.hermes/skills/**/SKILL.md', recursive=True):
    parts = open(f, errors='replace').read().split('---')
    if len(parts) < 3: continue
    fm_text = parts[1]
    for key in ['name', 'description', 'version', 'author']:
        count = len(re.findall(rf'^{key}:', fm_text, re.M))
        if count > 1:
            print(f"DUPE KEY '{key}' ({count}x): {f}")
```

**Aug 2026 confirmed instance:** `requesting-code-review` had `name:` at both line 3 and
line 26. Fix: remove the second occurrence.

**Aug 2026 regression pattern:** A round-1 fix that *adds* a key (e.g. `name:`) without
removing the stale pre-existing occurrence leaves a duplicate. The new entry goes at the
top of the frontmatter; the old entry remains buried in the metadata tags block or lower.
YAML picks the last value — same string usually, so no immediate breakage, but it confuses
validators and future patchwork. Always grep the full frontmatter for the key before
adding: `grep -n '^name:' SKILL.md`. If it already appears, do NOT add a new one —
correct the existing entry instead.

## Block-scalar list-item embedding (structural defect introduced by patching)

A block scalar YAML value (key using `>` or `|`) absorbs EVERYTHING indented below it
until a new top-level key begins. If list items (`- item`) are placed below a block scalar
without outdenting to the parent level, they become literal text inside the scalar — not
YAML list elements.

**Example of the defect (from self-improve-agent, Aug 2026):**
```yaml
boundary_note: >
  Some text here.
  - trajectory-risk-guardrail     ← these look like list items but are TEXT
  - verification-before-completion
  - agent-task-signoff
```
The three skill names parse as a single prose string, not as skill references. Any
skill the patch intended to add to `related_skills` via this mechanism is silently
lost.

**Detection:**
```python
import glob, yaml
for f in glob.glob('/var/home/rainbow/.hermes/skills/**/SKILL.md', recursive=True):
    parts = open(f, errors='replace').read().split('---')
    if len(parts) < 3: continue
    data = yaml.safe_load(parts[1]) or {}
    for key, val in data.items():
        if isinstance(val, str) and '\n- ' in val:
            print(f"POSSIBLE embedded list in block scalar '{key}': {f}")
```

**Fix:** Move the intended list items out of the block scalar body and into a proper
top-level YAML list key (`related_skills:`, `counter_triggers:`, etc.).

## Two-skills-concatenated-as-one-string in list (structural defect)

When a patch adds a list entry by appending to an existing list item line rather than
adding a new `  - item` line, two skill names end up as a single string in one list slot.
Hermes will never resolve the second name.

**Example of the defect (from scoped-pr-fix-and-verification, Aug 2026):**
```yaml
related_skills:
  - github-issue-to-pr
  - github-operations
  - split-ci-workflow-change-and-draft-pr verification-before-completion  ← ONE string
```
`verification-before-completion` is unreachable from this skill.

**Detection:**
```python
import glob, yaml
for f in glob.glob('/var/home/rainbow/.hermes/skills/**/SKILL.md', recursive=True):
    parts = open(f, errors='replace').read().split('---')
    if len(parts) < 3: continue
    data = yaml.safe_load(parts[1]) or {}
    rs = data.get('related_skills', [])
    for entry in (rs or []):
        if isinstance(entry, str) and ' ' in entry.strip():
            print(f"CONCATENATED ENTRY '{entry}': {f}")
```

**Fix:** Split the single string into two separate `  - skill-name` entries.

## metadata.hermes.related_skills vs top-level related_skills

Hermes skill routing reads the **top-level** `related_skills:` list in SKILL.md
frontmatter. The `metadata.hermes.related_skills:` field (nested under `metadata:`)
is for indexing/tagging only — the router does NOT traverse it.

A patch that writes skill cross-references into `metadata.hermes.related_skills` instead
of the top-level list produces a "fix landed in wrong field" defect: the YAML is valid,
the reference appears to exist in the file, but Hermes never surfaces it as a routing link.

**Detection:** After any pass adding related_skills entries, verify with:
```python
import glob, yaml
for f in glob.glob('/var/home/rainbow/.hermes/skills/**/SKILL.md', recursive=True):
    parts = open(f, errors='replace').read().split('---')
    if len(parts) < 3: continue
    data = yaml.safe_load(parts[1]) or {}
    top = set(data.get('related_skills') or [])
    meta = set((data.get('metadata') or {}).get('hermes', {}).get('related_skills') or [])
    only_in_meta = meta - top
    if only_in_meta:
        name = data.get('name', f)
        print(f"{name}: skills only in metadata.hermes (not routed): {only_in_meta}")
```

**Aug 2026 confirmed instances:** `meeting-action-items` (document-to-action-items),
`autonomous-ai-agents` (11 routing entries), `merge-reconciler` (all 6 entries after
dedup removed the top-level block). Fix: copy the relevant skill names from the
`metadata.hermes.related_skills` list into the top-level `related_skills:` list.

## Known wrong category paths (do not move in a docs-only audit)

Canonical table: **Known Category Misplacements (Sep 2026 — not yet moved)** above.
Always probe disk before batch-reading. Do not relocate in a docs-only pass.

Use `find ~/.hermes/skills -name 'SKILL.md' | xargs grep -l 'name: <skill>'` to
locate any skill whose path is uncertain before including it in a batch-read manifest.

## Skill size extraction — three patterns (from references/skill-extraction-patterns.md)

When reducing a SKILL.md file (> 50KB), apply one of three patterns based on what currently exists:

1. **New extraction** (no ref file exists): write extracted section to `references/[name].md` via `write_file`, then replace inline section with a 1-sentence pointer + `See references/[name].md.`
2. **Existing-ref update** (ref file exists but is incomplete): add to the existing ref file; update the inline pointer to reflect new content
3. **Cross-skill reassignment** (content belongs in a different skill): move the section to that skill's references/, add a pointer there, replace inline with "See [skill-name]/references/[name].md"

Size thresholds: < 30KB healthy · 30–50KB monitor · 50–80KB extract now · > 80KB urgent (writes may fail)

What belongs in references/ vs inline:
- **Extract**: stats tables, project file trees, large pitfall narratives with code, paper lists, full code recipes > 50 lines
- **Keep inline**: numbered procedural steps, quick-ref checklists, single-command snippets, trigger conditions

## Skill size extraction — tool sequence (from references/skill-extraction-workflow.md)

1. Batch in one turn: `read_file(SKILL.md, limit=2000)` + `search_files(references/, '*', target='files')` — line count drives chunk strategy
2. Page through in 2000-line chunks; only read sections you plan to extract
3. Before extracting: check if an existing references/ file already covers it — if YES, replace inline with pointer only; do NOT rewrite the existing ref
4. Extract + replace: use the `patch` file-edit tool (not `skill_manage`) for find-and-replace on SKILL.md
5. After each replacement: `terminal("wc -c /path/to/SKILL.md")` — target < 50KB
6. Fire patches in sequence (each depends on prior file state); plan all upfront from one read

## Architecture cohesion (runtime wiring, not skill quality)

Distinct from library-quality audit: scripts, cron, and skills must actually call each other. Load `references/architecture-cohesion-audit-aug2026.md` when the user asks "does the architecture work cohesively."

- Cross-ref map: text-search both the stem and the full filename across `~/.hermes/scripts/`, SKILL.md files, and `hermes cron list` stdout. Stem-only regex misses `Path(__file__).parent / 'script.py'` and cron `Script:` fields.
- Legitimate orphans (do not treat as gaps): MCP launchers, login/manual scripts, on-demand tools with no cron. Real orphans: research scripts never referenced, lost cron, skill-documented scripts missing from the skill body.
- `state.db` has no `config` column — do not read cron job config from the database. Parse `hermes cron list` stdout (`Name:` / `Script:` / `Skills:`).
- Do not nest triple-quoted heredocs inside `execute_code` `terminal()` calls (outer `"""` collides with the heredoc closer). Use `write_file` + `terminal('python3 /tmp/script.py')`.
- `delegate_task` rejects goal text containing `<word>` as an unexpanded template marker (including `<10s>`, `<session_id>`). Use square brackets or plain text.

Dated workflow-chain findings (self-refs, disabled-skill metadata, fallback-chain order) live in `references/workflow-chain-audit-aug2026.md` — cite it; do not treat those snapshot defects as current without re-grepping.

## Sweep 21 Quality Gate Additions

### Skill freshness test (Trace2Skill / Zenn.dev Z21-1)
During audits, apply: "Can a fresh session reproduce the original task from this skill alone?"
If not, the skill is missing critical steps. Flag HIGH severity.

### Scale routing risk (SkillRouter, arXiv:2603.22455)
At ~80k skills, routing accuracy drops 31-44pp via name+description only.
Hermes is far below this now, but as library grows:
- Keep name+description tight (64/1024 char caps enforced)
- hermes-semantic-skill-routing becomes critical above ~500 skills
- Periodic audit criterion: can name+description alone distinguish this skill from its
  nearest semantic neighbor? If not, tighten the description.

### Capability degradation on skill updates (arXiv:2605.09315, GS013)
Skill patches for new distributions can silently break prior behaviors.
When auditing: verify that patched skills still satisfy their original trigger scenarios —
not just new ones.

---

## Known Category Misplacements (2026-09-09)

Do not "fix" these by rewriting triggers — they are directory-layout defects for the next reorganization pass. Trigger sharpening can reduce wrong-loads; it does not move the files.

- `research/gold-class` — cinema/session finder; belongs in leisure/entertainment, not research
- `research/stay-in` — movie/TV stay-in recommendations; belongs in leisure/entertainment, not research
- `research/suggest-music` — local music suggestions; belongs in leisure/entertainment, not research
- `autonomous-ai-agents/hermes-research-ops` — research pipeline job ops (status/re-run/apply); belongs with `research/` as a sibling of `hermes-research`, not under agent-orchestration

## Reference files

- `references/software-dev-github-cluster-audit-aug2026.md` — Aug 2026 cluster audit: software-development + github skills. Ghost files (5 confirmed), structural defects (duplicate YAML key, missing `name:` field), overlap map for the three review skills, handoff gaps, and the parallel batch-read audit methodology.
- `references/research-productivity-devops-cluster-audit-aug2026.md` — Aug 2026 cluster audit: research/, productivity/, note-taking/, email/, devops/ skills (58-skill pass). 5 ghost files confirmed, 10 bundled-skill structural defects flagged for foreground adoption, 7 overlap/consolidation findings, 38 clean skills listed. Includes index-vs-disk divergence check script.
- `references/agent-infra-cluster-audit-aug2026.md` — Aug 2026 cluster audit: autonomous-ai-agents + superpowers cluster (33 skills). Confirmed findings: stale local-LLM section in harness-first-agent-design, Ollama reference in hermes-semantic-skill-routing description, duplicate related_skills field in messaging-consent-boundaries, broken computer-use path in cluster manifest. Adopt candidates list included.
- `references/research-autonomous-agents-audit-aug2026.md` — Full Aug 2026 audit: research/ + autonomous-ai-agents/ categories, CRITICAL→LOW findings, cross-cutting chain status, orphan reference map, remediation order
- `references/multilingual-sweep-aug12-2026-findings.md` — Multilingual Community Sweep — Aug 12 2026 Findings
- `references/runtime-layer-audit-aug2026.md` — Runtime Layer Audit — August 2026
- `references/skill-extraction-patterns.md` — Skill Extraction Patterns (for large SKILL.md reduction)
- `references/skill-extraction-workflow.md` — Skill Size Extraction — Operational Workflow
- `references/skill-governance-contamination-2026.md` — Skill Governance, Provenance, and Contamination Detection (Aug 2026)
- `references/pass2-yaml-patch-regression-patterns-aug2026.md` — Pass-2 audit of 46 skills after a round-1 bulk fix: 7 regressions found (3 HIGH, 4 MED). Canonical examples of the four YAML patch failure modes: duplicate key not removed, block-scalar list-item embedding, two-skills-concatenated-as-one-string, fix landed in metadata.hermes instead of top-level. Includes validated Python detection queries for all four modes.
- `references/adversarial-pass-pitfalls-aug2026.md` — Confirmed false-positive classes and structural pitfalls from the Aug 18 2026 recursive adversarial pass: `\n` scan FP (code-block context awareness), root-level skill placement anti-pattern (depth-1 SKILL.md), L1 pipeline timing minimums (extract→promote ≥40m), three-check ghost taxonomy, and project-script-vs-Hermes-script triage rule.
- `references/workflow-chain-audit-aug2026.md` — Dated Aug 2026 cross-category workflow-chain findings register (self-refs, disabled-skill metadata, fallback-chain order). Re-grep before treating items as open.
- `references/architecture-cohesion-audit-aug2026.md` — Runtime cohesion procedure: cross-ref map, orphan classification, pipeline continuity, cron-list parsing, execute_code heredoc pitfall, delegate_task angle-bracket reject.
