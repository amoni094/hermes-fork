---
name: policy-dashboard-workflow
description: "Work effectively in the local-first policy-dashboard repo: refresh pipeline, generated data, UI, and portability verification."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [policy-dashboard, react, vite, data-refresh, generated-data, dashboard]
    related_skills: [verification-before-completion, requesting-code-review, subagent-driven-development]
---

# Policy Dashboard Workflow

Use this skill when working in `/var/home/rainbow/policy-dashboard`.

## What this repo is

A local-first React + TypeScript dashboard for Australian policy, legislation, polling, and macro signals.

Key moving parts:
- refresh scripts in `scripts/`
- generated data in `src/generated/` and `public/data/`
- UI surfaces in `src/`
- browser compatibility via `vite.config.ts`, `.browserslistrc`, and `@vitejs/plugin-legacy`

## Default collaboration patterns

Choose the pattern first.

- **Pipeline**: use for changes that span `scripts/* -> generated data -> React UI -> build/tests`.
- **Producer-Reviewer**: use for one-surface UI fixes or one-script fixes.
- **Fan-out/Fan-in**: use for audits across multiple signal lanes or source families.
- **Expert Pool**: use for portability, browser support, generated-data quality, or refresh resiliency reviews.

In this Hermes runtime, flatten hierarchical plans into parent-managed waves.

## Working rules

- Keep the repo portable; do not assume local private helpers exist.
- Optional helpers must degrade gracefully instead of breaking refresh entirely.
- For anti-bot- or WAF-protected sources, prefer compliant fallback lanes (search-indexed RSS/results, official feeds, or explicit link-outs) rather than implementing bypass logic.
- If a source is only link-accessible, make the UI copy say so plainly; do not label profile links as "latest posts" or imply scraped post bodies were captured.
- Do not claim a lane is correct unless generated rows, labels, and links actually match.
- For chart/ranking changes, verify visible ordering/counts against real generated rows.
- Avoid committing `__pycache__`, transient build noise, or unrelated generated churn.
- When the repo already has unrelated local modifications, stage and commit only the scoped files for the task; leave unrelated diffs untouched unless the user asked to sweep them in.

Reference: `references/blocked-source-fallbacks.md`.

## High-value task splits

### Refresh-pipeline change
- Worker A: source retrieval / parsing / fallback logic
- Worker B: generated artifact schema + freshness metadata
- Worker C: UI/data-contract assumptions + docs/tests
- Parent: run refresh, inspect output, then build/test

### UI feature change
- Worker A: component/state/render logic
- Worker B: CSS/layout/accessibility
- Worker C: data contract + sample generated output verification
- Parent: verify labels, counts, and source links remain truthful

### Browser portability change
- Worker A: Vite/Browserslist/legacy config
- Worker B: dependency completeness / install portability
- Worker C: build artifact and runtime smoke verification
- Parent: confirm output actually exposes compatible loader paths

## Verification order

Use this order whenever generated data may affect the UI:
1. Read back the changed files.
2. Run `npm run refresh:data` if scripts or generated data changed.
3. Run `npm run lint` before the heavier checks so simple issues fail fast.
4. Run `npm test` for touched UI logic when tests exist.
5. Run `npm run build`.
6. Inspect a sample of `src/generated/*.ts` or `public/data/*.json` before claiming success.
7. Check `git status --short` before commit so unrelated tracked or untracked files do not get swept into the change.

## Commands

```bash
npm install
npm run dev
npm run refresh:data
npm test
npm run build
npm run lint
```

## Pitfalls

- Saying a scrape/refresh succeeded without checking generated output.
- Verifying only helper functions, not the live artifact the UI consumes.
- Letting fallback data leak into misleading labels like "latest posts" when only profile metadata exists.
- Treating anti-bot resistance as an implementation target; in this repo the durable pattern is fallback lanes plus honest UI messaging, not bypass work.
- Claiming browser support from config alone without checking the build output.
