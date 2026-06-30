# Browser compatibility and portability checks

Use when a repo must work for users beyond the current machine.

Checklist
- Read `package.json`, lockfile, bundler config, TS target/lib, and any Browserslist file.
- Prefer explicit browser targets over vague claims like "modern browsers".
- Ensure the compatibility tooling itself is declared as dependencies/devDependencies and committed in the lockfile.
- Add runtime engine requirements (`engines`) when the toolchain has a real Node/npm floor.
- Re-run the real project flow after edits: refresh/generate if applicable, tests, then production build.
- Inspect preview/build output for compatibility artifacts (for Vite legacy builds: `vite-legacy-polyfill`, `vite-legacy-entry`, legacy chunk files).
- If full browser automation is blocked, use representative Chrome/Firefox/Edge user-agent probes against preview HTML as a fallback verification step.
- Report remaining audit findings precisely, especially if they are dev-only or platform-specific.

Recent example pattern
- Add `@vitejs/plugin-legacy` plus explicit Chrome/Firefox/Edge targets.
- Commit a `.browserslistrc`.
- Lower TS/browser target only as far as needed for the promised browser floor.
- Document Node/npm requirements and browser support in README.
