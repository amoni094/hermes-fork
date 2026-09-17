---
name: theory-grounded-codebase-improvement
version: 1.0.0
author: Hermes Agent
description: "Use when applying formal theory to a codebase."
keywords:
- theory
- research
- adversarial
- parallel-agents
- legal-tech
platforms:
- linux
---

# Theory-Grounded Codebase Improvement

Use when the user asks to apply formal theory (cognitive science, causal inference,
deontic logic, information theory) to a production codebase, with recursive adversarial
pass and coherence audit before PR.

Deliverables: N new theory-grounded pure-stdlib modules, cold adversarial math review,
all critical/high findings fixed, PR with full theory provenance.

## Step 0: Codebase reconnaissance (before recommending anything)

Scan the source tree BEFORE proposing research categories:

```python
import os, re

# 1. Enumerate modules by size
for root, dirs, files in os.walk("src"):
    dirs[:] = [d for d in dirs if d not in {"__pycache__"}]
    for f in files:
        if f.endswith(".py"):
            print(os.path.getsize(os.path.join(root, f)), os.path.join(root, f))

# 2. Scan for theory already present
for pat in [r'Pearl|Dung|Kahneman|Shannon|Wald',
            r'KL.diverg|SPRT|conformal|Jaccard|Wasserstein',
            r'Nash|Allen.interval|CTL|LTL|active.learn']:
    pass  # count hits per file
```

Spot-check hits for false positives: 'ctl' in 'control' is not CTL model checking;
'temporal' in a filename might just be deadline strings. Sample context around each
match before concluding the category is covered.

Only recommend categories confirmed absent AND valuable to the domain.

## Step 1: Triage and rank categories

Score each candidate:
- Domain fit: does the theory address a real gap in current logic?
- Integration fit: does existing infrastructure make composition cheap?
  (causal engine composes with trace logs; deontic composes with Dung argumentation)
- Implementation cost: pure stdlib feasible without heavy deps?

## Step 2: Parallel subagent implementation — one domain per agent

One subagent per domain cluster. Each creates ONE src file + ONE test file.
Zero modifications to existing files.

Context packet per subagent MUST include:
- Exact theory citations with chapter/section for every function
- Import path of any existing module the new one composes with; instruct subagent
  to verify the import BEFORE implementing: `python -c "from src.x import Y"`
- Pure stdlib constraint (see below)
- Target test count (>= 40 per module)
- Output file: `/tmp/impl_<domain>_result.json`
- Branch name — new files only; subagents must not touch existing files

## Step 3: Test and integrate

1. Run FULL suite (not just new tests) to catch cross-module regressions
2. Update `__init__.py` to re-export all new engines
3. Fix import failures before committing

Record baseline test count before dispatch; verify new count = baseline + new tests.

## Step 4: Cold adversarial review (wait for all reports before fixing)

Dispatch 3 cold adversarial subagents concurrently:
- Reviewer A: math bugs in modules 1-2 (formulas, algorithm correctness)
- Reviewer B: edge cases in modules 3-4 (crashes, contracts, silent misbehaviour)
- Cohesion auditor: theoretical coherence, integration gaps, citation accuracy, domain fit

No coaching or prior-context injection. Reviewers read source files directly.

Do NOT start fixing until ALL reports arrive. Partial fixes hide bugs the remaining
reviewer would have caught.

## Step 5: Triage and fix

Verdict per finding: confirmed / false_positive / need_more_context.

Fix order: CRITICAL > HIGH > MEDIUM. Apply all confirmed findings in the parent
session (not a new subagent). See `references/systematic-bug-classes.md` for the
6 bug classes cold adversarial review catches that self-review misses.

## Step 6: Commit and PR

Commit message:
```
fix: Apply adversarial review findings (all critical + high)

CRITICAL fixes:
- <module>: <what was wrong, what the fix is>
HIGH fixes: ...
Tests: N new regression tests. Full suite: M passing, 0 failing.
```

PR body must include:
- Theory table: module → theory source → corpus citation
- Math/CS corpus alignment table: formula → corpus reference
- Adversarial review summary: N critical, M high found; all fixed
- Test count: new tests + full suite total

## Pure stdlib constraint (mandatory for standalone reasoning modules)

- stdlib only: math, dataclasses, enum, collections, itertools, re
- Implement Pearson r, KL divergence, Jaccard, Wasserstein-1 by hand
- Validate: `python -c "import <module>"` with clean venv — no transitive deps
- Tests: pytest only, no hypothesis/faker

## See also

- `references/systematic-bug-classes.md` — 6 bug classes cold reviewers catch
  that self-review misses
