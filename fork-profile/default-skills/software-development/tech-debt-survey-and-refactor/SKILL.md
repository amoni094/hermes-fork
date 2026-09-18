---
name: tech-debt-survey-and-refactor
category: software-development
description: Use when surveying tech debt, running a structured code-quality audit with the 9-dimension taxonomy, or delegating refactor fixes.
tags: [refactoring, tech-debt, code-quality, delegation]
related_skills:
  - subagent-driven-development
  - adversarial-review
  - requesting-code-review
  - verification-before-completion
---

# Tech Debt Survey and Refactor

Use when the user asks for a tech debt survey, code quality review, or refactoring pass on a repo or module.

## Tech Debt Taxonomy (9 Dimensions with Rerun Reconciliation)

Use this structured taxonomy for any tech debt audit. Every finding must cite file:line and include severity + effort.

Orientation first (before any dimension):
- Stack truth: read the manifests (package/build/dependency files), never memory
- Churn ranking: `git log --format= --name-only | sort | uniq -c | sort -rn | head -30`
- Size ranking: largest source files by line count
- Gate inventory: test suites, typecheckers, linters, CI entry points that already exist

High-churn + high-size + low-test is the audit's priority corner.

The 9 dimensions:
| Dimension | What to look for |
|---|---|
| Architectural decay | cyclic imports, god modules, layers bypassed, boundary leaks |
| Consistency rot | competing patterns for the same job — two HTTP clients, three error styles |
| Type and contract gaps | untyped public surfaces, any-equivalents, implicit schemas parsed in many places |
| Test debt | untested high-churn paths, skipped or stub tests, assertions that cannot fail |
| Dependency and configuration debt | unpinned or abandoned dependencies, drifted config copies |
| Performance and resource debt | unbounded caches and queues, N+1 access patterns, sync work on hot paths |
| Error-handling and observability debt | swallowed exceptions, bare retries, failures invisible to logs or metrics |
| Security hygiene | credentials in the tree, injectable string building, permissive defaults |
| Documentation drift | READMEs and comments contradicting the code, dead runbooks, stale generated artifacts |

Severity/effort grading:
- Severity: critical (active correctness or security risk), high (costs every change), medium (costs some changes), low (cosmetic)
- Effort: S (one bounded change), M (a few files, one review), L (needs refactor-plan phases)
- Quick wins = severity >= medium AND effort = S
- critical/L finding routes to refactor-plan; never recommend a rewrite

Rerun reconciliation — on every rerun, every prior finding must be reconciled:
- RESOLVED: fixed with evidence
- CARRIED: still present, unchanged
- NEW: appeared since last audit
No finding is silently dropped.

Cleanup pass ordering (one smell category per pass, verify between passes — never bundle):
1. Dead code (deletion only, no renames or moves)
2. Duplicates (collapse each duplicated decision to one owner)
3. Naming and error handling (rename misleading, surface swallowed errors; no structural moves)
4. Needless abstraction (inline single-use helpers, collapse pass-through layers)
5. Boundary violations (repair with existing surface; boundary-CHANGING fix routes to refactor-plan)
6. Test reinforcement (add behavior locks, delete assert-nothing tests)

<!-- why: bundled passes cannot be reviewed for behavior preservation and reverting one mistake reverts all three -->

### 1. Read before surveying

Read every file in the target module fully before forming opinions. Use `read_file` in chunks for large files (>400 lines). Do not survey from memory or grep output alone — subtle issues (misplaced docstrings, scattered eviction loops, duplicated boilerplate) are invisible without full reads.

Files to read for a plugin/module audit:
- The main module file (all chunks)
- Any sub-modules it imports from within the package
- The test file(s) for the module
- Any eval or benchmark runner that exercises it

### 2. Classify each finding

For every issue found, classify:
- **Real** (clear payoff, low risk): structural problem that makes the code harder to read, test, or change. Report with effort estimate and risk level.
- **Borderline** (consider, don't rush): cosmetic or inconsistent but not harmful. Flag but do not block on it.
- **Not worth doing**: things that look odd but are intentional or would cost more to change than to leave. Say so explicitly.

Report all three buckets. "These 4 things are fine" is as useful as finding 6 bugs.

### 3. Present findings before acting

Present the full triage to the user before doing any fixes. Include:
- Item ID (RF-1, TD-1, etc.)
- One-sentence description of the problem
- The fix (concrete, not vague)
- Effort estimate and risk level
- Whether it is deferred and why

Wait for "do all" or explicit item selection before executing.

### 4. Partition fixes for parallel delegation

When delegating fixes in parallel:
- **One file per subagent.** Never dispatch two subagents that both write to the same file. They race; the last writer silently discards the other's work.
- If multiple independent fixes target the same file, serialise them in one subagent's goal or use sequential waves.
- Give each subagent the exact text to patch (not a paraphrase) and require `patch` tool, not `write_file`, on files >300 lines.

### 5. Verify after each wave

After any batch of fixes:
```bash
python -m py_compile <modified_file>
python -m pytest <relevant_tests> -q 2>&1 | tail -10
```
All tests must pass before committing. If a subagent reports tests passing but you did not run them yourself, run them from the parent session.

### 6. Commit

```bash
git add -A
git commit -m "refactor: <scope> — <what changed>"
git push fork <branch> --force-with-lease
```

Do not push until the user reviews, unless explicitly told otherwise.

## Refactoring Patterns (Python plugins)

### Extract long hook functions into module-level helpers

Hook functions that grow beyond ~80 lines typically bundle 2-3 unrelated concerns. Signs:
- Three distinct try-blocks with different logger.debug names
- A block that could be called independently (routing logic, classification, I/O)

Extract each concern into a module-level function (not a nested closure) so each can be unit-tested independently. Place new helpers just before the registration function. Pass shared objects (e.g. `ctx`, `agent`) as explicit arguments — do not close over them.

### Deduplicate atomic write boilerplate

If two or more functions share:
  mkstemp → fdopen → json.dump → os.replace → except: os.unlink + raise

Extract to a single `_atomic_json_write(path, payload)` helper. The boilerplate is fragile (file descriptor leak if the finally is missing) and must not live in two places.

### Centralise LRU eviction

When a module uses multiple global `OrderedDict` objects with LRU eviction, all `while len(d) > MAX: d.popitem(last=False)` loops must live in a single `_touch_session` (or equivalent) function. Scattered eviction in domain functions means dicts can temporarily exceed the cap and the invariant is not locally obvious.

## Edge Cases

### zlib on empty strings

zlib always emits an 8-byte header. `zlib.compress(b"")` returns ~8 bytes. A function returning `compressed_len / raw_len` without a guard on empty input returns `~8.0` instead of a value in `[0, 1]`, silently distorting any mean that uses it.

Fix:
```python
if not text:
    return 0.0
return min(1.0, max(0.0, len(zlib.compress(text.encode())) / len(text.encode())))
```

Test assertion must be `result == 0.0`, not `result >= 0` — the latter passes even when the bug is present.

### Python docstrings must be the first statement

A string literal placed AFTER any other statement (a `try` block, an assignment) is an inert expression — Python does not set `__doc__`. The docstring must be the first statement after the `def` line.

```python
# correct
def fn():
    """Docstring here."""
    try:
        ...

# broken — __doc__ is None
def fn():
    try:
        ...
    """Docstring here."""  # inert expression, not a docstring
```

## Pitfalls

- Read the full file before surveying. Bugs like scattered eviction, inert docstrings, and zlib empty-string overflow are invisible in grep output or partial reads.
- Do not dispatch parallel subagents to the same file. They race. Partition by file or serialise.
- Use `patch` tool, not `write_file`, on files >300 lines in subagent context. `write_file` clobbers the entire file; a missed read-before-write loses concurrent edits.
- Run `py_compile` + `pytest` from the parent session after each subagent wave, not just trusting the subagent's self-report.
- Test assertions for clamped-range functions must assert the exact clamped value, not just `>= 0`.
