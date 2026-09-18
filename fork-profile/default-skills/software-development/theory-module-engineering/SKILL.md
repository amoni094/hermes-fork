---
name: theory-module-engineering
version: 1.0.0
author: Hermes Agent
description: "Use when building theory-grounded pure-stdlib modules."
keywords:
- theory
- research
- adversarial
- parallel-agents
- pure-stdlib
platforms:
- linux
---

# Theory-Grounded Module Engineering

Use when the user asks to apply formal theory (cognitive science, causal inference,
deontic logic, interval algebra, active learning) to a production codebase, with
recursive adversarial pass and coherence audit before PR.

Deliverables: N new theory-grounded pure-stdlib modules, cold adversarial math review,
all critical/high findings fixed, PR with full theory provenance.

## Step 0: Codebase reconnaissance (before recommending anything)

Scan the source tree BEFORE proposing research categories. Walk src/ to find module
sizes, then grep for theory author names and technique identifiers (Pearl, Dung,
Shannon, Allen, KL divergence, SPRT, conformal, Jaccard, Wasserstein, Nash, active
learning).

Spot-check hits for false positives: 'ctl' in 'control' is not CTL model checking;
'temporal' in a filename may just be deadline strings. Sample context around each
match before concluding a category is covered.

Only recommend categories confirmed absent AND valuable to the domain.

## Step 1: Triage and rank categories

Score each candidate:
- Domain fit: does the theory address a real gap in current logic?
- Integration fit: does existing infrastructure make composition cheap?
- Implementation cost: pure stdlib feasible without heavy deps?

## Step 2: Branch and baseline

```bash
git checkout -b feature/<theory-cluster-name>
python -m pytest <targeted_test_paths> -q  # record baseline count
```

## Step 3: Parallel subagent implementation -- one domain per agent

One subagent per domain cluster. Each creates ONE src file + ONE test file.
Zero modifications to existing files.

Context packet per subagent MUST include:
- Exact theory citations with chapter/section for every function
- Import path of any existing module the new one composes with; instruct subagent
  to verify the import BEFORE implementing
- Pure stdlib constraint
- Target test count (>= 40 per module)
- Output file: `/tmp/impl_<domain>_result.json`
- Explicit instruction: `from src.pkg.module import X` everywhere -- never
  `sys.path.insert` + bare module name (creates dual namespace, causes
  PYTHONHASHSEED-dependent frozenset membership failures)

## Step 4: Test and integrate

1. Run FULL suite (not just new tests) to catch cross-module regressions.
2. Verify hash stability across multiple PYTHONHASHSEED values:
   `for s in 0 1 42 99 1234; do PYTHONHASHSEED=$s python -m pytest <paths> -q --tb=no 2>&1 | tail -1; done`
3. Update `__init__.py` to re-export all new engines.
   Use `write_file` for large multi-block rewrites; do NOT use `patch` to append
   multiple import blocks (patch embeds literal \n sequences, breaking syntax).
4. Fix import failures before committing.

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

Commit message template:
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

## Pure stdlib constraint (mandatory)

- stdlib only: math, dataclasses, enum, collections, itertools, re
- Implement Pearson r, KL divergence, Jaccard, Wasserstein-1 by hand
- Validate: `python -c "import <module>"` -- no transitive deps
- Tests: pytest only, no hypothesis/faker

## Critical pitfalls

**Dual-module import flakiness (PYTHONHASHSEED-dependent):**
Test files using `sys.path.insert(0, 'src')` + `from module import X` create a
second module instance separate from `from src.module import X` used by production
code. Enum members and frozenset keys differ between instances -- membership checks
silently fail under some hash seeds. Fix: always use `from src.pkg.X import ...`
in test files; remove sys.path.insert.

**Mutable `set` for node tracking breaks hash-seeded propagation:**
Set iteration order is PYTHONHASHSEED-dependent. In constraint propagation algorithms,
some orderings visit triples before pair constraints are initialised, leaving entries
at all-relations default. Use `list` with `in` membership checks so insertion order
governs visit order.

**Never use `patch` to append large multi-line blocks to `__init__.py`:**
The patch tool embeds literal \n sequences when newlines appear in new_string,
producing syntactically broken Python. Use `write_file` with complete clean content
for rewrites adding 4+ import blocks.

**Test files must not access private internals with type assumptions:**
If `_nodes` changes from `set` to `list`, tests calling `net._nodes.add("X")` break.
Tests must use public APIs only.

**Subagent tests import via the same `src.` namespace as production code:**
Instruct every subagent: `from src.pkg.X import ...` everywhere. Mixing bare module
names with src. paths creates two enum namespaces and hash-seed-dependent membership
failures visible only in combined pytest runs.

## See also

- `references/systematic-bug-classes.md` -- 9 bug classes cold adversarial reviewers
  catch that self-review misses
