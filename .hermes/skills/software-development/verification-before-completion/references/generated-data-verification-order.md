# Generated data verification order

Use this in repos where scripts regenerate TypeScript/JSON/content consumed by the app.

Why:
- a refresh can succeed while tests/build still fail on downstream typing or syntax issues
- generated/search-indexed data can be technically valid but low quality or noisy
- verifying in the wrong order wastes passes and can hide which stage actually regressed

Recommended order:
1. Compile/syntax-check generator scripts first.
2. Run the refresh/generation command.
3. Run the repo's normal test script exactly as declared by the project.
4. Run the production build.
5. Sample generated artifacts for quality:
   - expected new fields present
   - fallback records clearly labeled
   - search-indexed/workaround lanes not dominated by generic homepages or irrelevant hits

Pitfalls:
- using test-runner flags copied from a different toolchain
- stopping after refresh succeeds
- treating generated output as verified without reading a representative sample
- confusing blocked-source workarounds with true first-party scraping support

Example class of repo:
- dashboards that refresh live/political/news data into `src/generated/*`
- static sites that materialize API data into checked-in assets
- apps where UI tests/build depend on generated type shape
