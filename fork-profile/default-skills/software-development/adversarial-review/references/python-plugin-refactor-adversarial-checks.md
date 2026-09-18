# Python Plugin Refactor — Adversarial Attack Vectors

Use this checklist when cold-reviewing a Python plugin after a refactor that:
- Extracted closures from a `register(ctx)` function to module-level helpers
- Split a large hook function into smaller focused functions
- Extracted shared boilerplate into a helper (e.g. atomic file write)
- Consolidated LRU eviction logic across multiple dicts

For each finding: state severity (HIGH/MEDIUM/LOW), exact location (function + line or quoted span), and verdict (confirmed / false_positive / need_more_context).

---

## A. Closure capture → explicit parameter

When a function is moved from inside `register(ctx)` to module level, it must receive `ctx`, `agent`, `session_id` as explicit parameters rather than capturing them from the enclosing scope.

Verify:
- Every reference to `ctx` in the extracted function is via the explicit `ctx` parameter, not a free variable
- Every reference to module-level globals (`_fired`, `_session_messages`, `_complexity_buffers`, `_intent_applied`, `_MAX_SESSIONS`, etc.) is a clean global access — no local variable shadows the global with the same name
- No path in the extracted function accidentally references a variable from the OLD enclosing scope that no longer exists at call time

---

## B. Eviction ordering after consolidation

When LRU eviction for multiple session dicts is consolidated into one manager function (e.g. `_touch_session`):

Verify:
- The manager function is called BEFORE any helper that uses those dicts on the same code path
- The eviction while-loop for every dict is present in the manager function (not just move_to_end)
- The eviction while-loops that were removed from the helper functions are GONE (not duplicated)
- The move_to_end calls in helper functions are kept (they are separate from eviction)

Failed example: `_touch_session` added `while len(_complexity_buffers) > _MAX_SESSIONS: ...` but the eviction in `_apply_adaptive_effort` was only partially removed, leaving both active and causing double-eviction on some paths.

---

## C. Atomic write helper correctness

When an atomic JSON write pattern (mkstemp + fdopen + json.dump + os.replace + os.unlink) is extracted to a shared helper:

Verify:
- The helper re-raises on failure (does NOT swallow exceptions)
- Both callers use the helper, not the old inline pattern
- Any assignment that was inside the old try block (e.g. `_last_hint_key = key`) is now AFTER the helper call, not lost
- The outer try/except in each caller correctly handles the re-raise (logs it at appropriate level, does not silently swallow)

---

## D. Docstring placement

Python only recognizes the first string literal in a function body as the docstring. A string literal after any other statement (including a try block) is an inert expression.

Verify:
- Every function’s docstring appears on the line immediately after the `def` signature, before any code
- No `"""..."""` literal appears after a try/except block mid-function

---

## E. Return value and discarded results

When a large function is extracted and given a return value:

Verify:
- If the caller discards the return value (fire-and-forget), confirm nothing downstream in the same turn needed that value
- If the return value was used before extraction (e.g. `session_type` fed into a trailing call), the extracted caller either passes it back or the trailing call was also moved inside the extracted function

---

## F. Early return paths in extracted functions

The most common logic error when splitting a large function:

Verify:
- Every early `return` that existed in the original block still exits the extracted function at the same logical point
- Trailing code that appeared AFTER the original block does not now execute inside the locked-path (early-return) branch of the extracted function

Failed pattern: in the original, the locked-type path returned early, skipping a trailing `_apply_adaptive_effort`. After extraction, the early return is inside the new function but the trailing call is also inside it — the early return now skips it correctly only if the trailing call is AFTER, not inside, the outer try block.

---

## G. Numeric clamping — zlib and ratio signals

When a compression ratio or MDL proxy is computed as `compressed_len / raw_len`:

Verify:
- Empty string is handled before the zlib call (zlib adds ~8 bytes of header to an empty input, producing ratio >> 1.0)
- The return value is clamped to `[0, 1]` with `min(1.0, max(0.0, ratio))`
- Tests assert `== 0.0` for empty input, not just `>= 0.0` (the latter passes the old broken 8.0 value)

---

## H. Global state shadowing in extracted functions

Module-level globals with names like `_fired`, `_session_messages` must be accessed as true globals in extracted module-level functions.

Verify:
- No local variable in the extracted function has the same name as a module-level global it is supposed to access
- `global` declarations are not needed (functions read globals automatically in Python; only writes need `global` if the name isn’t already a global in the function)

---

## I. Exception re-raise propagation chain

When a helper re-raises, check the full call chain:

Verify:
- Caller 1’s outer try/except does not have a bare `except: pass` that silently absorbs the re-raise
- Caller 2 (if any) has the same check
- Logging level is appropriate (warn or error for write failures, debug for fail-open soft failures)

---

## J. Preserved comment blocks

When extracting a large function, all inline comment blocks (SPIKE notes, `# why:` rationale comments, `# TODO:` markers) must be preserved in the extracted function.

Verify:
- SPIKE comment blocks are present verbatim in the extracted function
- All `# why:` comments are present and adjacent to the code they annotate
- No TODO markers were lost

---

## Running the check

```bash
# Compile check
python -m py_compile <plugin_file>

# Targeted test — run the plugin’s own suite, not the full tree
python -m pytest tests/plugins/<plugin_name>/ -q

# Full suite with pre-existing failure baseline
git stash && python -m pytest tests/plugins/video_gen/test_fal_plugin.py -q 2>&1 | grep FAILED > /tmp/pre_existing.txt && git stash pop
python -m pytest tests/ -q 2>&1 | grep FAILED > /tmp/post_refactor.txt
diff /tmp/pre_existing.txt /tmp/post_refactor.txt  # should be empty or only regressions in plugin files you changed
```
