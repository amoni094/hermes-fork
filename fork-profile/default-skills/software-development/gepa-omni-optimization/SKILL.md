---
name: gepa-omni-optimization
title: GEPA omni — LLM-based Text/Prompt/Skill Optimization
description: >
  Use when applying GEPA (Genetic-Pareto) and optimize_anything omni to optimize skills, system prompts, agent harnesses, and any text artifact that can be scored. Covers the single-optimizer loop, the omni meta-optimizer (parallel explore + hand-off to fresh engine), and concrete Hermes-specific applications: skill refinement, prompt optimization, agent architecture search.
keywords:
  - gepa
  - prompt-optimization
  - skill-optimization
  - text-optimization
  - evolutionary-search
  - meta-optimizer
  - omni
  - harness
  - evaluation-driven
triggers:
  - "Optimize this prompt/skill/system prompt"
  - "GEPA optimization"
  - "optimize_anything"
  - "Automatically improve agent harness"
  - "Run evolutionary search over skill variants"
  - "Tune a skill with test cases"
  - "Which optimizer should I use for this task"
  - "Meta-optimizer / omni pattern"
  - "Genetic prompt evolution"
  - "Score-guided skill improvement"
related_skills:
  - evaluation-driven-development
  - skillopt-continuous-improvement
  - self-improve-agent
  - knowledge-corpus-architecture
  - hermes-agent-skill-authoring
platforms: [linux, macos, windows]
version: 1.0.0
author: Hermes Agent
license: MIT
---

# GEPA omni — LLM-based Text/Prompt/Skill Optimization

GEPA (Genetic-Pareto) is a framework for optimizing any text artifact against a
scoring function using LLM-based reflection + Pareto-efficient evolutionary search.
The key results (CAIS 2026, arXiv 2605.19633):

- 32% → 89% ARC-AGI accuracy via agent architecture discovery
- 46.6% → 56.6% GPT-4.1-mini on AIME via prompt optimization
- 55% → 82% coding agent resolve rate via auto-learned skills
- 40% cloud scheduling cost reduction vs expert heuristics
- 35x fewer evaluations than RL (100-500 evals vs 5K-25K for GRPO)

The **omni** extension (blog post July 2026): no single optimizer wins everywhere.
GEPA wins 3/10 problems, AutoResearch 3/10, Meta-Harness 4/10 on Frontier-CS.
omni runs all three in parallel (fraction of budget each), takes the best candidate,
hands it to a fresh optimizer for the rest of the budget: +7.8 points vs best standalone.

## When to use GEPA/omni

Use when:
- You have a measurable quality signal for a text artifact (prompt, skill, code, config)
- You have 3-100 example inputs where you can compute a score
- Manual iteration is slow (>3 rounds of edit-test-check)
- The artifact is in a local optimum you can't escape by single-step edits

Don't use when:
- No measurement function exists (subjective quality only)
- You have <3 examples (prompt engineering by hand is faster)

## Cross-Tier Cost Reduction (arXiv:2608.10694, Aug 2026)

"Optimize Cheap, Deploy Strong: Cost-Aware Cross-Tier Transfer for Evolutionary Optimization"

Decouples the 3 LLM roles in evolutionary search:
- Answering/fitness calls (high-volume): cheapest tier (haiku-4-5)
- Reflection/variation operators (rare): strong model (sonnet-4-6)
- Deployment: apply cheaply-evolved prompt to strong target model

Results across 4 tasks, 11 models: matches same-tier optimization at 5.6-14x lower cost
(up to 54x where reasoning models emit long CoT on every fitness call). >96% of search
tokens land on cheap tier.

Hermes pattern:
1. Run fitness scoring via delegate_task with haiku as evaluator (set model in context)
2. Orchestrator (sonnet) handles mutation/crossover — it's already running on sonnet
3. After convergence, validate best candidate on sonnet before committing
4. Token savings: 80-95% of fitness budget moves to haiku tier
- The artifact is code with a correct/incorrect answer (use TDD instead)
- Single-pass LLM rewrite is sufficient

## The Core API (pip install gepa)

```python
import gepa.optimize_anything as oa

def evaluate(candidate: str) -> float:
    score, diagnostic = run_my_system(candidate)
    oa.log(f"Diagnostic: {diagnostic}")  # ASI: fed to the LLM proposer
    return score

result = oa.optimize_anything(
    seed_candidate="<your initial artifact>",
    evaluator=evaluate,
)
print(result.best_candidate)
```

For richer feedback (recommended):
```python
def evaluate(candidate: str) -> tuple[float, dict]:
    result = run_judge(candidate)
    return result.score, {
        "Error": result.stderr,
        "Output": result.stdout,
        "FailedCases": result.failed_cases[:5],  # most informative
    }
```

## Three Optimization Modes

| Mode | Use when | API |
|------|----------|-----|
| Single-task search | One problem, maximize score | `optimize_anything(seed, evaluator=f)` |
| Multi-task search | Many similar problems, one artifact | `optimize_anything(seed, evaluator=f, dataset=train, valset=val)` |
| Generalization | Learn a template that works across inputs | `optimize_anything(evaluator=f, dataset=train, valset=val, objective=...)` |

Multi-task is most useful for skills: you want a skill that works across a family
of related tasks, not just one specific example.

## omni: The Meta-Optimizer

When you don't know which engine will win:

```python
from gepa.optimize_anything import optimize_anything, OptimizeAnythingConfig

def evaluate(candidate: str) -> tuple[float, dict]:
    score, feedback = run_judge(candidate)
    return score, {"Feedback": feedback}

seed = open("seed.py").read()
task = dict(
    evaluator=evaluate,
    objective="Maximize score on this task.",
)

# Phase 1: parallel exploration with 1/3 budget each
r_gepa       = optimize_anything(seed, **task, config=OptimizeAnythingConfig(engine="gepa",        max_token_cost=7))
r_autores    = optimize_anything(seed, **task, config=OptimizeAnythingConfig(engine="autoresearch", max_token_cost=7))
r_metaharn   = optimize_anything(seed, **task, config=OptimizeAnythingConfig(engine="meta_harness", max_token_cost=7))

# Phase 2: best candidate, fresh optimizer for remaining budget
best = max([r_gepa, r_autores, r_metaharn], key=lambda r: r.best_score)
final = optimize_anything(best.best_candidate, **task,
                          config=OptimizeAnythingConfig(engine="gepa", max_token_cost=6))
```

gepa ships `optimize_best_of` and `optimize_adaptive_sequential` helpers that
implement this pattern in ~10 lines with budget tracking.

## Hermes-Specific Applications

### 1. Skill optimization (most common use case)
Goal: improve a SKILL.md so it scores higher on a set of test tasks.

```python
import subprocess, json, tempfile
from pathlib import Path

def evaluate_skill(candidate_skill_md: str) -> tuple[float, dict]:
    """Score a SKILL.md by running it on test tasks and measuring outcome."""
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write(candidate_skill_md)
        temp_path = f.name
    
    scores = []
    failures = []
    for test_case in TEST_CASES:
        # Load skill, run task, evaluate result
        result = run_task_with_skill(test_case["input"], temp_path)
        score  = score_result(result, test_case["expected"])
        scores.append(score)
        if score < 0.8:
            failures.append({"task": test_case["input"][:80], "got": result[:200]})
    
    avg = sum(scores) / len(scores)
    return avg, {"avg_score": avg, "failures": failures[:3]}

seed_skill = Path("~/.hermes/skills/my-skill/SKILL.md").expanduser().read_text()
result = oa.optimize_anything(seed_candidate=seed_skill, evaluator=evaluate_skill)
print(result.best_candidate)
```

### 2. System prompt optimization
Goal: find the best system-prompt variant for a recurring agent task.

```python
import anthropic

client = anthropic.Anthropic()

def evaluate_prompt(candidate_prompt: str) -> tuple[float, dict]:
    correct = 0
    examples = []
    for q, expected in BENCHMARK_QA:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=candidate_prompt,
            messages=[{"role": "user", "content": q}]
        )
        got = resp.content[0].text
        is_correct = expected.lower() in got.lower()
        correct += is_correct
        if not is_correct:
            examples.append(f"Q: {q[:60]} | Expected: {expected[:40]} | Got: {got[:40]}")
    
    score = correct / len(BENCHMARK_QA)
    return score, {"accuracy": score, "failures": examples[:3]}
```

### 3. Agent harness / architecture discovery
Goal: find the best harness (system prompt + tool selection + chain) for a task.

```python
def evaluate_harness(candidate_harness: str) -> tuple[float, dict]:
    """candidate_harness is a JSON or YAML describing the agent setup."""
    import yaml
    config = yaml.safe_load(candidate_harness)
    results = []
    for task in AGENT_BENCHMARK_TASKS:
        result = run_hermes_task(task, harness_config=config)
        results.append(score_agent_result(result, task))
    return sum(results)/len(results), {"per_task": results}
```

### 4. Skill trigger/routing optimization
Goal: optimize skill trigger sentences so the router matches the right skill.

```python
def evaluate_triggers(candidate_trigger_block: str) -> tuple[float, dict]:
    """Score how well the triggers match test queries."""
    triggers = [t.strip().lstrip("- ") for t in candidate_trigger_block.strip().splitlines() if t.strip()]
    correct = 0
    for query, expected_skill in ROUTING_TEST_CASES:
        matched = best_match_skill(query, triggers, skill_name="target-skill")
        if matched == expected_skill:
            correct += 1
    return correct / len(ROUTING_TEST_CASES), {"accuracy": correct/len(ROUTING_TEST_CASES)}
```

## The omni Pattern: What It Teaches for Hermes Agent Design

The core insight is that DIFFERENT OPTIMIZATION ENGINES have COMPLEMENTARY strengths:
- GEPA (reflective LLM proposer): best for structured code/config where targeted
  mutations beat broad exploration. Converges fast, plateaus early.
- AutoResearch (autonomous agent): best for open-ended problems needing exploration.
  Good at finding novel directions but can waste budget on dead ends.
- Meta-Harness (agent-based proposer, framework-owned loop): best for multi-step
  reasoning chains where each step needs verification.

This maps to Hermes delegation patterns:
- "Reflective proposer" = sonnet single-pass with ASI feedback
- "Autonomous agent" = delegate_task with a long-horizon subagent
- "Framework-owned loop" = parent controls iterations, delegates mutations

The composition insight: **when a subagent stalls, hand its best candidate to a
different subagent with a different approach.** This is a generalizable pattern
beyond just prompt optimization.

## Building an Evaluation Harness for a Hermes Skill

A practical harness for offline skill evaluation:

```python
#!/usr/bin/env python3
"""
Evaluation harness for skill optimization.
Usage: python3 eval_skill.py path/to/SKILL.md
"""

import sys, json, subprocess, tempfile
from pathlib import Path

# Define your test cases: what query maps to what expected outcome
TEST_CASES = [
    {
        "query": "Research Python web frameworks",
        "must_include": ["web_search", "web_extract"],
        "must_not_include": ["browser_navigate"],  # prefer web_extract
        "max_steps": 5,
    },
    # ... more cases
]

def score_task_trace(trace: dict, expected: dict) -> float:
    """Score a task execution trace against expected outcomes."""
    tool_calls = [step["tool"] for step in trace.get("steps", [])]
    score = 1.0
    
    for required in expected.get("must_include", []):
        if required not in tool_calls:
            score -= 0.2
    
    for forbidden in expected.get("must_not_include", []):
        if forbidden in tool_calls:
            score -= 0.15
    
    if len(tool_calls) > expected.get("max_steps", 10):
        score -= 0.1 * (len(tool_calls) - expected["max_steps"])
    
    return max(0.0, score)

def evaluate_skill_file(skill_path: str) -> tuple[float, dict]:
    """Run each test case with the given skill and return aggregate score."""
    skill_md = Path(skill_path).read_text()
    scores = []
    details = []
    
    for tc in TEST_CASES:
        # Simulate running the task (in practice, call hermes or a mock)
        trace = run_simulated_task(tc["query"], skill_md=skill_md)
        s = score_task_trace(trace, tc)
        scores.append(s)
        if s < 1.0:
            details.append(f"Task '{tc['query'][:40]}': {s:.2f}")
    
    avg = sum(scores) / len(scores)
    return avg, {"avg": avg, "per_task": details}

if __name__ == "__main__":
    skill_path = sys.argv[1]
    score, info = evaluate_skill_file(skill_path)
    print(json.dumps({"score": score, **info}, indent=2))
```

## Automated continuous improvement

The scan + optimization loop is automated via two components:

**Weekly scan cron** (job `d984a185e83a`, every Sunday 3am):
  - Runs `~/.hermes/scripts/omni_skill_scan.py` (no-agent mode, pure Python)
  - Scores all 165 non-plugin skills on 7 quality dimensions
  - Writes report: `~/.hermes/omni/scan-YYYY-MM-DD.md`
  - Writes candidate queue: `~/.hermes/omni/patch-queue.json`
  - Never modifies any SKILL.md — scan only

**Standalone evaluation harness** (`~/.hermes/scripts/gepa_skill_eval.py`):
  - Evaluates a single skill against test cases in `gepa_eval_cases.json`
  - Usage: `python3 gepa_skill_eval.py --skill ~/.hermes/skills/my-skill/SKILL.md [--optimize] [--omni]`
  - Implements the EDD + GEPA bridge; uses same 5-dimension scoring as omni_skill_scan
  - `--baseline` mode: score only (no gepa install required); `--optimize` mode: requires `gepa` pkg

**On-demand optimization** (manual, requires gepa installed):
  ```bash
  # After gepa becomes available:
  pip install gepa
  python3 ~/.hermes/scripts/omni_skill_scan.py --optimize --budget 2.0
  # Writes candidate files to ~/.hermes/omni/candidates/
  # Review each candidate, copy to SKILL.md if satisfied
  ```

**Human review gate**: the automation deliberately stops at candidate generation.

**Deterministic second-pass gate** (`~/.hermes/scripts/hermes-mutation-gate.sh <output-dir>`):
Validates candidate skill mutations before promotion. Checks: metrics.json (constraints_passed=true,
improvement>0), evolved_skill.md lint via lintlang (skipped if not installed), `hermes config check`.
NOTE: the gate also calls `qmd-local.sh` (QMD is currently disabled in config). QMD checks are
skipped silently when QMD is unavailable; the gate still passes without them.
No skill is ever auto-merged. Run `hermes cron list` to see the scan job status.

To check the current queue:
  ```bash
  cat ~/.hermes/omni/patch-queue.json | python3 -m json.tool | head -40
  ```

To run scan immediately (refresh report):
  ```bash
  hermes cron run d984a185e83a
  # OR
  python3 ~/.hermes/scripts/omni_skill_scan.py
  ```

## Pitfalls

- **Installing gepa**: `pip install gepa` works, but it pulls a large dependency
  tree (DSPy, litellm, etc.). Install in a virtual env, not system Python.
  `toolbox run pip install gepa` if using Fedora Silverblue toolbox.

- **ASI is the key ingredient**: Score-only feedback converges much slower than
  score + diagnostic. The oa.log() / side_info dict is not optional — budget 
  the same care for the evaluator's diagnostics as for the score function.

- **Budget management**: With max_token_cost, gepa converts LLM calls to USD
  estimates. Set conservatively. A typical skill optimization: 50-100 evals,
  ~$0.50-2 with sonnet-level models. Use haiku for cheap proposer iterations.

- **Evaluation must be deterministic (or nearly so)**: If your evaluator has
  high variance (LLM-as-judge with temperature > 0), the optimizer chases noise.
  Use temperature=0 for evaluation calls, or average 3 runs per candidate.

- **Skill files are long**: GEPA works best on <2000 token artifacts. For long
  skills, optimize individual sections (trigger block, pitfalls, steps) rather
  than the whole file at once.

- **Don't optimize a skill you've only used once**: You need 5+ real use cases
  to define meaningful test cases. GEPA on poorly-defined evals produces optimally
  useless artifacts.

- **The plateau-then-handoff is real**: If score stops improving after 10-15 iterations,
  save the best candidate and run a second optimizer from it. Don't keep burning budget
  on a stalled search.

- **gepa's .claude/skills/ directory**: The GEPA repo ships a Claude Code skill at
  .claude/skills/gepa-optimize-anything/. You can point a claude-code session at the
  gepa repo and it will load that skill automatically for optimization tasks.

## Quick-Start: Install and Test

```bash
# Install in toolbox
toolbox run pip install gepa

# Test with a simple text optimization
toolbox run python3 - <<'EOF'
import gepa.optimize_anything as oa

def evaluate(candidate: str) -> tuple[float, dict]:
    # Score: how many unique words, prefer precise over verbose
    words = candidate.split()
    unique = len(set(words))
    score = unique / max(len(words), 1)
    return score, {"words": len(words), "unique": unique}

result = oa.optimize_anything(
    seed_candidate="This is a test of the optimization system.",
    evaluator=evaluate,
    objective="Write a sentence with maximum vocabulary diversity.",
)
print(result.best_candidate)
EOF
```
