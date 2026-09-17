# Low-friction repo hardening patterns

Use when a session involves security hardening of a codebase, CI, or helper scripts and the user wants the system to remain usable.

Key patterns from a successful pass:

1. Prefer safe-by-default, explicit opt-out
- For HTTP tooling, default to TLS verification on.
- If labs or self-signed targets must still work, add an explicit `--insecure` flag rather than hard-coding `verify=False`.
- Only suppress urllib3 insecure-request warnings inside the explicit insecure path.

2. Replace predictable temp paths
- Avoid fixed paths like `/tmp/foo.txt` for captures, outputs, and intermediate artifacts.
- Prefer `tempfile.mkdtemp(...)` or similar unique temp directories and place outputs underneath them.
- This reduces collisions, accidental clobbering, and cross-run leakage while preserving usability.

3. Move risky runtime flags behind operator intent
- Do not enable flags like `--force` by default when they trade safety/stability for convenience.
- Add an explicit CLI flag or function parameter so the operator opts in deliberately.

4. Harden automation before content
- In educational or offensive-security repos, avoid over-restricting legitimate content.
- Prefer hardening the surrounding automation and defaults first: validator correctness, GitHub Actions permissions, SHA pinning, concurrency, and low-noise CI checks.

5. Verification pattern after hardening
- Re-run the repo's canonical validator, not a duplicated inline variant.
- Compile or syntax-check every touched script (`python -m py_compile` or equivalent).
- When edits touch many helper scripts, validate the touched subset immediately after each batch so a bad mass-edit is caught before it spreads.
- If a broad rewrite corrupts multiple files, restore the affected subtree to the last known-good state and re-apply the intended hardening as smaller verified edits instead of chasing cascading syntax fallout.
- If the hardening changes a risky pattern from unconditional to explicit opt-in, update the repo guard so CI stops warning on the new opt-in form while still catching unconditional defaults.
- Inspect the final diff to confirm the patch stayed small and targeted.
- Report both what changed and what was intentionally left for a later pass.

6. Partial-read hazard
- If you inspected a file with a paginated or truncated view, re-read the whole file before overwriting it.
- Do not patch from a partial snippet when exact indentation or import placement matters.

Good summary framing for future sessions:
- Say whether hardening is actually needed.
- Separate mandatory low-friction fixes from optional follow-up work.
- Explain why each change preserves usability instead of just increasing restrictions.
