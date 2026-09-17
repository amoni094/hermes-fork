---
name: hermes-research-sweep-ops
description: 'Use when running the recursive research-implementation loop.'
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [research, sweep, interpreter, monitor, saturation, offset, implementation]
    related_skills:
      - hermes-research-pipeline-pitfalls
      - cs-interpreter-pitfalls
      - hermes-cs-research
      - hermes-math-research
triggers:
  - recursive research implementation loop
  - corpus saturation
  - monitor suite management
  - offset windowing for paper interpreter
  - monitor alarm calibration
related_skills:
  - hermes-research-pipeline-pitfalls
  - cs-interpreter-pitfalls
  - hermes-cs-research
  - hermes-math-research
---

# Hermes Research Sweep Operations

End-to-end procedure for the recursive research -> implementation loop:
run sweeps, interpret papers, implement scripts, add to monitor suite, saturate.

## Environment Split: Always Enforce

Two Python runtimes; never mix them:

  Monitor/utility scripts:  /usr/bin/python3  (numpy 2.4.6, scipy 1.18.1 available)
  Sweep/interpreter scripts: hermes-fork venv  (anthropic package; NO numpy)

```bash
# Monitors:
/usr/bin/python3 ~/.hermes/scripts/<monitor>.py --dry-run

# Interpreters:
cd ~/.hermes/hermes-fork && source venv/bin/activate && \
  python3 ~/.hermes/scripts/cs-paper-interpreter.py --all-categories ...
```

## --all-categories Required for Core Agent Papers

When running cs-paper-interpreter.py against hermes-research-latest.json, always pass
--all-categories. Core agent papers have category="arxiv-listing:cs.AI" (long-form);
the default CS_CATS filter drops every paper silently.

  SIGNAL of missing flag: "0 CS papers to interpret" with EXIT:0 and no warning.

## Core Corpus Window Saturation: --offset N Fix

The interpreter always takes the FIRST N papers by position. After the seen cache fills
the initial window, resetting the cache still produces the same 40 papers.

  FIX: Add --offset N to cs-paper-interpreter.py:

```python
# parse_args():
parser.add_argument('--offset', type=int, default=0)
# paper selection:
cs_papers = cs_papers[args.offset : args.offset + args.limit]
# skip seen-cache reset when offset > 0:
if args.offset == 0:
    seen_cache = {"seen": [], "last_updated": "..."}
```

Coverage pattern for 1268-paper corpus:

```bash
for offset in 0 40 80 120 160; do
  timeout 300 python3 ~/.hermes/scripts/cs-paper-interpreter.py \
    --input ~/.hermes/cache/research/hermes-research-latest.json \
    --all-categories --offset $offset --limit 40
done
```

Saturation confirmed: all offset windows return "0 unseen papers" in consecutive runs
(seen cache >= 640 for offsets 0-1239 against a 1268-paper corpus).

Math saturation differs: math-paper-interpreter.py uses a small rolling window (~29 seen)
so consecutive waves keep producing new ideas. Declare saturated only when multiple waves
produce 0 Stage 3 ideas with no new script names.

## Alarm Detection: Text Match, Not Exit Code

False positives fire when exit code is used alone -- exit 1 fires for both real alarms
and "insufficient data" (micro-sessions with <10 tool calls).

```python
alarm_line    = any(l.strip().startswith("ALARM: yes") for l in out.splitlines())
no_alarm_line = any(
    l.strip().startswith("ALARM: no") or "insufficient data" in l
    for l in out.splitlines()
)
alarm = alarm_line and not no_alarm_line
```

Every monitor must emit exactly one of:
  ALARM: yes -- <reason>              (unconditionally triggers)
  ALARM: no                           (unconditionally suppresses)
  ALARM: no -- insufficient data      (skips when session too small)

Never emit both on the same run. This pattern eliminated 9 false positives on first
real suite run against micro-sessions that legitimately had no data.

## Skill Dedup When Loading from Two Directories

Scripts iterating both ~/.hermes/profiles/fork/skills/ and ~/.hermes/skills/ produce
self-pairs when the same skill exists in both locations.

  SYMPTOM: Lowest-curvature pairs show skill-X <-> skill-X with C~=0.08.

```python
seen_names: set[str] = set()
for base in [SKILLS_DIR, ALT_SKILLS]:
    for md in base.rglob('SKILL.md'):
        name = md.parent.name
        if name in seen_names:
            continue
        seen_names.add(name)
        # load skill ...
```

Apply to every script that iterates both skill directories.

## Run-on-Demand Scripts Catalogue (2026-09-15)

Not in suite (need real session data or specific inputs). Call directly:

  free-energy-task-optimizer.py      -- Boltzmann routing; beta=10 suppresses delegate to 0.003
  belief-state-threshold-router.py   -- POMDP threshold tau=0.70; quoted-arg tasks -> direct
  recursive-reasoner-skill.py        -- S-AI-Recursive convergent belief accumulation; 5-step demo
  cost-cutoff-task-router.py         -- Value-tier routing; HIGH->subagent 0.55, LOW->direct 0.02
  coalitional-reviewer-panel.py      -- Shapley phi>=0.05 coalition cert; 5-reviewer panel
  relay-routing-capacity-allocator.py -- Decode-forward relay capacity; all DIRECT (overhead=0.05)
  boundary-aware-context-allocator.py -- CRB-guided budget; error/constraint blocks get floor 1.30
  filter-only-optimization-reducer.py -- Sparse active-constraint reduction; floor=0.02; 93% prune
  privacy-capacity-router.py         -- I(X;Y) vs I(X;Z) capacity/leakage routing
  horizon-constraint-validator.py    -- CBF-style safety; pass real plan file: --plan ~/.hermes/plans/X
  simulator-fisher-estimator.py      -- Fisher info on skill routing; zero-feature -> no_coverage

## Monitor Suite Architecture

Script: ~/.hermes/scripts/monitor-suite-runner.py
Cron: daily 7am (cron c7e4d8aa60d5)
All scripts use /usr/bin/python3.

Add to suite only when monitor has a working "insufficient data" guard. If the script
always fires on micro-sessions (<10 tool calls), leave it run-on-demand.

## Script Calibration Patterns

Real-options gate: DEFER_THRESHOLD=0.65; DEFAULT_HORIZON=2; V_wait *= sigma.
  Pitfall: threshold >0.85 defers all tasks; <0.60 commits even ambiguous ones.
  Pitfall: V_wait not scaled by sigma defers concrete tasks unnecessarily.

Fisher estimator: LOW_FISHER=1e-5. Uniform weights produce avg_fisher in [1e-5, 1e-4];
  zero-overlap queries produce 0.0. Threshold at 0.10 falsely flags everything.

Federated consensus JSD: cap to [0,1] with min(max(0.0, value), 1.0).
  Small vocabulary + float arithmetic can produce JSD > 1.0 without the cap.

## Stage 3 Ideation: Implementation Priority

Stage 3 fires on full-chain SKIPs. Priority order:
  1. [script] tagged -> implement as .py in ~/.hermes/scripts/
  2. [skill] tagged -> create only if class-level and non-trivial
  3. Duplicate names (underscore vs dash) -> skip; check both variants before implementing:
     artifact_name.py AND artifact-name.py

Idea queue totals (2026-09-15, post-session):
  Core agent: 340 (fully saturated, 1268/1279 papers), Math: 322+ (wave11 running), CS: 80
  Scripts: 90+ total; 53 in daily suite, 0 errors

## Monitor Session Coverage Fix

Monitors must scan BOTH session dirs (default profile + fork profile):

```python
SESSIONS_DIR  = HOME / ".hermes/sessions"
FORK_SESSIONS = HOME / ".hermes/profiles/fork/sessions"
# In glob:
files = sorted([f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")])
```

Applied to: session-stability, retrieval-saturation, regime-transition, sybil-risk,
relaxation-gap, state-concentration, quantization-state-divergence, performative-stability,
proportionality, prediction-tradeoff monitors (2026-09-15).

Sessions are *.jsonl -- never *.json (that matches only the routing index, not session files).

## Genuine Alarm Baseline (53-monitor suite, 2026-09-15, post-adversarial-fix)

~6 genuine alarms after adversarial fixes (4 permanent-fixture alarms retired/baseline-gated):
1. session-stability -- V_t=23 (tool-embedding variance)
2. retrieval-saturation -- hindsight_recall slope -0.037/call
3. consensus-convergence -- JS=0.693
4. absorption-capacity -- slope -0.077
5. spec-semantic-graph -- baseline-gated (alarms only on NEW issues >5 above baseline)
6. skill-graph-reachability -- baseline-gated (alarms only when dead-end count increases >5)

Retired as permanent fixtures (now run-on-demand or demo-fixed):
- magnitude-mirage: error metric corrected (gt_proxy not raw_sim); threshold reset needed
- plan-enforcement-gate: credential string removed from demo; no longer permanent alarm
- horizon-constraint-validator: run-on-demand for real plan files in ~/.hermes/plans/
- simulator-fisher-estimator: zero-feature -> no_coverage (not UNCERTAIN alarm)

29 adversarial issues fixed (6 ALARM_LOGIC, 6 THRESHOLD, 5 MATH, 3 DEAD_CODE, others).
Key math fixes: spatial-mixing abs(eigs) not abs(eigs.real); divergence-curvature unit
direction + keep sign; federated-consensus JSD cap log(k) not 1.0; radius-hierarchy
r_cov=max_pairwise/2 (distinct from r_pack).
