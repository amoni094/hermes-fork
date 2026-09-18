# Nanochat Autoresearch Patterns (Karpathy, Mar 2026)

## Context
Karpathy ran an autonomous agent loop on nanochat (minimal GPT training framework) for 2 days. The agent found 20 improvements a human missed in months, cut training time from 2.02h → 1.80h (then 1.65h in round 2).

**Why it worked:**
- Measurable objective: CORE score (numeric, computable in-repo)
- Cheap surrogate: trained on d12 (tiny model, 45min per trial) before scaling to d24/d26
- Reference material: gave the agent a working modded-nanogpt repo to learn from
- Uninterrupted duration: 2-day background run without human steering
- Eval as infrastructure: existing pytest-style tasks/ dir (tasks/arc.py, tasks/mmlu.py)

## Repo Structure (Nanochat)

```
nanochat/
├── .claude/
│   └── skills/
│       └── read-arxiv-paper/
│           └── SKILL.md     # Domain-specific: architecture, key files, conventions
├── nanoGPT/              # Reference implementation (what agent learned from)
├── train.py              # Entry point
├── tasks/
│   ├── arc.py            # Eval task (CORE score computed here)
│   ├── mmlu.py
│   └── ...
├── config.yaml           # Hyperparameters (agent's search space)
└── README.md             # baseline metrics
```

## Agent Loop Shape

```
Round 1 (2 days):
  for trial in range(N):
    1. Read current config + results
    2. Hypothesize change (read reference nanoGPT, find idea)
    3. Patch config.yaml
    4. Run train.py on d12 (45 min)
    5. Check tasks/arc.py result vs baseline
    6. Accept (commit) or reject (revert)
  Output: 20 improvements, new config

Round 2:
  1. Load improved config from Round 1
  2. Run same loop on d24/d26 (slower, more expensive)
  3. Find more improvements specific to larger scale
```

## Critical Success Factors

### 1. Surrogate is runnable, not hypothetical

**Good:** Train on d12 (45 min), verify on d24 (cost-contained)  
**Bad:** "Will probably work on full dataset" (no eval)

Surrogate must:
- Finish in <1 hour (or cron becomes impractical)
- Use real train/eval code, not mocked
- Report the same metric as full run

### 2. Baseline is documented

```
# README.md
## Baseline (commit abc1234)
- d12: 2h02m, CORE=0.642
- d24: 5h18m, CORE=0.681
- d26: 12h05m, CORE=0.687
```

Agent needs to know when an improvement is real. Without baseline, it optimizes noise.

### 3. Search space is constrained

Don't say "improve anything." List what the agent can actually change:

```yaml
# config.yaml (agent modifies only these)
learning_rate: 6e-4          # [1e-5, 1e-2]
batch_size: 64               # [32, 128]
warmup_tokens: 375e6         # [0, 1e9]
final_lr_ratio: 0.1          # [0.01, 0.5]
weight_decay: 0.1            # [0, 0.3]
num_workers: 4               # [0, 8]
```

Clear ranges force the agent to reason, not flail.

### 4. Reference code is version-pinned and runnable

Agent learned by reading nanoGPT. If the repo is stale or incompatible, agent wastes time. Pin it:

```
# .claude/skills/read-arxiv-paper/SKILL.md
Reference repo: nanoGPT (karpathy/nanoGPT @ commit 8e6cfbbf)
- Contains working training loop, data pipeline, baseline results
- Read before proposing hyperparameter changes
```

### 5. Loop runs unattended with clear exit condition

```
# Cron job config
schedule: "every 45 minutes"
repeat: 30  # ~45 hours = 2 days
condition: "exit if 3 consecutive trials show <0.5% improvement"
```

No human checking email every 2 hours. Agent runs to completion or timeout.

## Hermes Adaptation

For Hermes tasks (not training frameworks):

**Surrogate example:** Lint one file before all files  
**Baseline:** Current pass rate (e.g., "50 lint errors across codebase")  
**Search space:** Config options, rule sets, thresholds (not "improve code quality vaguely")  
**Reference:** Link to a clean, well-linted file from the same project  
**Exit condition:** "Stop if 10 consecutive trials find no new errors"

## What NOT to do

- Don't run without a baseline. "Better than nothing" is noise.
- Don't give the agent prose instructions ("make this faster"). Give it numbers ("reduce p95 latency from 450ms to <400ms").
- Don't run expensive full-scale first. Start cheap.
- Don't skip the eval. If running the agent doesn't involve executing tests, the loop is broken.
- Don't run indefinitely. Set `repeat` or a stop condition. Autonomous means "without human steering," not "forever."

## Metrics that work well for autonomous loops

- **Pass/fail counts:** pytest --tb=no returns exit code 0 (all pass) or counts failures. Easy to track.
- **Numeric KPIs:** latency percentiles, error rates, coverage %, token usage, training time.
- **Static analysis results:** lint errors, security warnings, code complexity scores (tools like semgrep, pylint report counts).
- **Benchmark scores:** CORE (MMLU+ARC combined), throughput ops/sec, F1 on validation set.

Metrics that DON'T work:
- "Quality" (unmeasurable)
- "Better code" (subjective)
- "More readable" (undefined)
- Human judgment (requires steering, breaks autonomy)
