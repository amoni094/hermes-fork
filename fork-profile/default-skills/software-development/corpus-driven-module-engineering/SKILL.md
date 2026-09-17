---
name: corpus-driven-module-engineering
version: 1.1.0
author: Hermes Agent
description: "Use when applying formal theory to a production codebase."
keywords:
- theory
- research
- adversarial
- parallel-agents
- legal-tech
platforms:
- linux
---

# Corpus-Driven Module Engineering

Use when the user asks to apply formal theory (cognitive science, causal inference,
deontic logic, information theory, interval algebra) to a production codebase, with
recursive adversarial pass and coherence audit before PR.

Deliverables: N new theory-grounded pure-stdlib modules, cold adversarial math review,
all critical/high findings fixed, PR with full theory provenance.

## Step 0: Codebase reconnaissance (before recommending anything)

Scan the source tree BEFORE proposing research categories:

```python
import os, re, subprocess

# 1. Walk src tree, collect file sizes
for root, dirs, files in os.walk("src"):
    dirs[:] = [d for d in dirs if d not in {"__pycache__"}]
    for f in files:
        if f.endswith(".py"):
            print(os.path.getsize(os.path.join(root, f)), os.path.join(root, f))

# 2. Scan for theory already present
for pat in [r'Pearl|Dung|Kahneman|Shannon|Wald',
            r'KL.diverg|SPRT|conformal|Jaccard|Wasserstein',
            r'Nash|Allen.interval|CTL|LTL|active.learn']:
    pass  # grep -rn pat src/ and count per file
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

## Step 2: Branch and baseline

```bash
git checkout -b feature/<theory-cluster-name>
python -m pytest <targeted_test_paths> -q  # record baseline count
```

Record baseline test count before dispatch; verify new count = baseline + new tests.

## Step 3: Parallel subagent implementation -- one domain per agent

One subagent per domain cluster. Each creates ONE src file + ONE test file.
Zero modifications to existing files.

Context packet per subagent MUST include:
- Exact theory citations with chapter/section for every function
- Import path of any existing module the new one composes with; instruct subagent
  to verify the import BEFORE implementing: `python -c "from src.x import Y"`
- Pure stdlib constraint (see below)
- Target test count (>= 40 per module)
- Output file: `/tmp/impl_<domain>_result.json`
- Branch name -- new files only; subagents must not touch existing files
- Instruction: use `from src.reasoning.X import ...` (never bare `from reasoning.X`)

## Step 4: Test and integrate

1. Run FULL suite (not just new tests) to catch cross-module regressions
2. Run across multiple PYTHONHASHSEED values to detect hash-dependent flakiness:
   `for s in 0 1 42 99 1234; do PYTHONHASHSEED=$s python -m pytest <paths> -q --tb=no 2>&1 | tail -1; done`
3. Update `__init__.py` to re-export all new engines -- use `write_file` for large
   multi-block rewrites; do NOT use `patch` to append multiple import blocks
4. Fix import failures before committing

## Step 5: Cold adversarial review (wait for ALL reports before fixing)

Dispatch 3 cold adversarial subagents concurrently:
- Reviewer A: math bugs in modules 1-2 (formulas, algorithm correctness)
- Reviewer B: edge cases in modules 3-4 (crashes, contracts, silent misbehaviour)
- Cohesion auditor: theoretical coherence, integration gaps, citation accuracy, domain fit

No coaching or prior-context injection. Reviewers read source files directly.

Do NOT start fixing until ALL reports arrive. Partial fixes hide bugs the remaining
reviewer would have caught.

## Step 6: Triage and fix

Verdict per finding: confirmed / false_positive / need_more_context.

Fix order: CRITICAL > HIGH > MEDIUM. Apply all confirmed findings in the parent
session (not a new subagent). See `references/systematic-bug-classes.md`.

## Step 7: Commit and PR

Commit message:
```
fix: Apply adversarial review findings (all critical + high)

CRITICAL fixes:
- <module>: <what was wrong, what the fix is>
HIGH fixes: ...
Tests: N new regression tests. Full suite: M passing, 0 failing.
```

PR body must include:
- Theory table: module -> theory source -> corpus citation
- Math/CS corpus alignment table: formula -> corpus reference
- Adversarial review summary: N critical, M high found; all fixed
- Test count: new tests + full suite total

## Pure stdlib constraint (mandatory for standalone reasoning modules)

- stdlib only: math, dataclasses, enum, collections, itertools, re
- Implement Pearson r, KL divergence, Jaccard, Wasserstein-1 by hand
- Validate: `python -c "import <module>"` with clean venv -- no transitive deps
- Tests: pytest only, no hypothesis/faker

## Critical pitfalls

**Dual-module import flakiness (PYTHONHASHSEED-dependent failures):**
Test files using `sys.path.insert(0, 'src')` + `from module import X` create a
second module instance separate from `from src.module import X` used by production
code. Enum members, frozenset keys, and dataclass identities differ between the two
instances -- membership checks silently fail under some hash seeds.
Fix: always use `from src.reasoning.X import ...` in test files; remove the
`sys.path.insert` workaround.

**Mutable `set` for node tracking breaks hash-seeded propagation:**
Using `set` for node ordering in constraint propagation makes iteration
PYTHONHASHSEED-dependent. Some orderings visit triples before their pair constraints
are initialised, leaving entries at the all-relations default. Use `list` with
explicit `in` membership checks so insertion order governs visit order.

**Never use `patch` to append large multi-line blocks to `__init__.py`:**
The `patch` tool embeds literal `\n` escape sequences when newlines appear in the
`new_string` argument, producing syntactically broken Python. For rewrites adding
4+ new import blocks, use `write_file` with the complete clean content.

**Test files must not access private internals with type assumptions:**
If `_nodes` changes from `set` to `list`, tests calling `net._nodes.add("X")` break
silently until run. Tests must use public APIs only; private-attribute access is
a contract violation that surfaces only on type refactors.

**Subagent tests must import via the same `src.` namespace as production code:**
Instruct every subagent: `from src.reasoning.X import ...` everywhere -- in test
files, `__init__.py`, and downstream modules. Mixing bare names with `src.` paths
creates two enum namespaces and hash-seed-dependent membership failures.

## See also

- `references/systematic-bug-classes.md` -- bug classes cold adversarial reviewers
  catch that self-review misses
