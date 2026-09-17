# Policy dashboard: policy pulse, poll comparables, and bounded social enrichment

Use this when updating a local political/news dashboard with generated TypeScript payloads and mixed live/static panes.

Key pattern
- Keep schema, generator, and UI changes aligned in one pass.
- For polling, carry both 2PP and primary-vote fields through the generated artifact.
- For policy pulse, promote official party announcements into the visible issue/policy lane instead of leaving them as a separate ingestion artifact.
- For social summaries, rank recent accessible posts by engagement where possible, but bound expensive enrichment to a ranked subset of profiles so refresh stays practical.

Concrete cues from this session
- Poll generator changes touched `scripts/refresh_live_data.py` and `src/types.ts` before the UI could cleanly separate 2PP and primary comparables.
- The polls UI then needed explicit sub-tabs plus a 30-day chart in `src/App.tsx`/`src/App.css`.
- The domestic policy pulse benefited from a distinct "Fresh party policy announcements" lane sourced from official covered-party items in generated live data.
- Polly/social refreshes remained portable by keeping optional heavier extraction paths opportunistic and by falling back in the UI to recent official/public items when social summaries were absent.

Verification order that worked
1. Refresh live generated data.
2. Refresh Polly/generated social data.
3. Run tests.
4. Run build.
5. Sample generated artifacts for the intended new fields/content, not just successful compilation.

Useful file cluster
- `src/App.tsx`
- `src/App.css`
- `src/types.ts`
- `scripts/refresh_live_data.py`
- `scripts/refresh_polly_data.py`
- `src/generated/liveData.ts`
- `src/generated/pollyData.ts`

Pitfalls
- Do not patch only the UI when the generated payload/schema still lacks the comparable fields.
- Do not let optional heavier social extraction turn the whole refresh into an unbounded crawl.
- Do not leave the social section empty-looking if the no-login post extractor yields nothing for a given profile; degrade to official/public items instead.
