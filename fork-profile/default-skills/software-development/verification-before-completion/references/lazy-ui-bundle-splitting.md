# Lazy UI bundle splitting: verification and interpretation

Use when a React/Vite UI is split with `React.lazy`, `Suspense`, route-level `dynamic import()`, or a tab/panel extracted into a deferred chunk.

## What changed in this session

A large generated data payload was making the initial dashboard bundle too large. The fix was to move the heavy Polly Tracker tab into its own lazily loaded module so the main app shell no longer imports the generated dataset up front.

## Verification pattern

1. Confirm the entry shell no longer statically imports the heavy dataset/module.
2. Confirm the tab/route registration now renders a `Suspense` fallback around a lazy import.
3. Update UI tests that click into the lazy surface:
   - replace synchronous `getBy*` assertions with `findBy*` for elements inside the lazy subtree
   - keep the interaction itself synchronous if the tab button is already present
4. Re-run tests.
5. Re-run the production build.
6. Read the emitted chunk sizes and separate two questions:
   - Did the entry chunk shrink?
   - Which deferred chunk now carries the heavy payload?

## Interpretation rule

If the warning moves from the entry bundle to a lazy chunk, that is still a real improvement for users who do not open that surface. Report both facts:
- initial path got smaller
- deferred path may still need another split or data externalization

Do not claim the warning is solved unless the oversized deferred chunk is also addressed or intentionally accepted.

## Common pitfall

After adding `Suspense`, tests may only see the fallback text (for example "Loading …") and fail to find the real control. That usually means the feature wiring is correct but the assertion is too early.

## Next-step options when the deferred chunk remains too large

- split summary cards/search index from detail payload
- lazy-load secondary panels inside the already-lazy feature
- move generated data from bundled TS/JS into fetched JSON
- revisit bundler chunking rules only after data-shape fixes, because payload size often dominates over code structure
