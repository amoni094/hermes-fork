---
name: verification-before-completion
description: "Use before claiming a task is done: require fresh evidence, independent readback after delegated work, and explicit proof commands."
version: 1.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [verification, completion, evidence, testing, delegation]
    related_skills: [workflow-map, requesting-code-review, risk-based-review, plan, systematic-debugging, subagent-driven-development]
---

# Verification Before Completion

Use this as the canonical final completion gate before you say any version of:
- "done"
- "fixed"
- "implemented"
- "tests pass"
- "deployed"
- "configured"
- "ready"

If you are still choosing the overall workflow, load `workflow-map` first. If you are already in a review pipeline, this is the last gate, not the whole process.

Core rule: never make a completion claim without fresh evidence gathered in this session.

## Fast path
1. Restate the exact claim.
2. Choose the narrowest proof.
3. Run it now.
4. Independently verify any delegated or background work.
5. Report the result with a compact `Verified by:` line.

For the compact version of this skill, see `references/fast-verification-matrix.md`.
For the shortest finish-line rules, see `references/finish-line-rules.md`.

## What counts as evidence

At least one of these must exist, and it must match the claim:
- test command output
- build command output
- runtime/manual verification output
- git diff plus readback of the changed files
- independent verification of delegated work
- direct inspection of config/state after a change

Stale evidence does not count. If the change happened after the last verification command, verify again.

## Required workflow

1. Restate the claim you are about to make.
2. Choose the narrowest command or inspection that can prove it.
3. Run it now.
4. If delegation or a background worker made the change, independently inspect the artifact yourself.
5. If a broad mechanical edit caused collateral damage, restore the damaged subtree to the last known-good state first, then re-apply only the minimal intended changes.
6. If the user asks whether a prior task was finished and to continue if not, do a resumptive state check before claiming either status: inspect repo status/diff, check live processes/services, hit the health/status endpoint the user would rely on, and identify which subcomponents are already healthy vs still degraded.
7. For recursive hardening or cleanup passes, verify after each batch, not just at the end: run the narrow compile/lint/test/validator checks that cover the touched files, then re-check the aggregate guardrail output.
8. If the remaining findings change class from straightforward defects to semantic detections, false-positive-ish pattern matches, or explicit opt-in behavior, stop and say that plainly instead of forcing the count to zero.
9. Only then respond with the result and the proof.

## Claim-to-proof mapping

### "Repository behavior / does it do X everywhere?"
Required proof:
- inspect the implementation, not just README or tests
- trace the behavior across all materially distinct paths (for example: core path, legacy path, fallback path, OCR path, worker path)
- name the concrete files/functions that establish the conclusion
- distinguish universal behavior from path-specific behavior
- if the repo mixes representations, say so explicitly instead of forcing a single summary

Example questions:
- "Does this app use Markdown for document ingestion everywhere?"
- "Is JSON the canonical format across all pipelines?"
- "Do all uploads pass through the same sanitizer?"

### "Tests pass"
Required proof:
- run the relevant test command now
- prefer the project-declared script or documented runner invocation exactly as defined in `package.json` / repo docs, rather than assuming flags from a different test runner
- if you need extra flags, confirm they belong to the actual runner in this repo before using them
- report the exact command and the real outcome

Common failure pattern:
- the repo uses Vitest, npm, pnpm, cargo, pytest, etc.
- the agent appends a familiar flag from another runner/toolchain (for example Jest's `--runInBand`)
- verification fails for the wrong reason and wastes a pass

### "Build succeeds"
Required proof:
- run the build command now
- if warnings matter, say so

### "Browser compatibility / works for non-local users"
Required proof:
- inspect the actual build/config inputs that define browser support (`vite.config.*`, bundler plugins, Browserslist targets, TS target/lib, documented runtime engines)
- verify dependency completeness from the package manifest and lockfile, not just a passing local install
- run the project's refresh/test/build flow after the compatibility edits so the portability work is validated against the real artifact set
- if the app claims Chrome/Firefox/Edge support, verify the built or preview-served HTML exposes the expected modern/legacy loader paths (for example Vite legacy polyfill/entry tags) and, when full browser automation is unavailable, at least probe the served HTML with representative browser user agents
- if an audit or platform-specific vulnerability remains, call it out explicitly instead of overstating completeness

### "File/config was updated"
Required proof:
- read the edited file or diff it
- cite the path
- if syntax-sensitive, rely on write/patch syntax checks or run a parser/linter/test

### "UI surface / tab / route / feature exists"
Required proof:
- inspect the concrete registration point, not just surrounding discussion or generated data
- cite the file and the exact structure that makes it visible (for example tab list, route table, nav config, component switch, exported type)
- if the feature was part of interrupted work, distinguish clearly between "implemented now", "planned earlier", and "partially scaffolded"
- when possible, pair the code readback with a narrow runtime check so you do not confuse dead code with user-visible behavior
- if the surface was moved behind `React.lazy` / `Suspense` or route-level dynamic import, make the runtime proof wait for the lazy content rather than asserting synchronously against the fallback shell

Common failure pattern:
- a tab or route exists and the click/navigation succeeds
- the test still uses synchronous `getBy*` assertions immediately after the interaction
- only the Suspense fallback is mounted, so verification fails even though the feature is wired correctly
- fix by using async queries such as `findByRole` / `findByText` for the lazy-loaded content

Common failure pattern:
- prior discussion or a handoff summary mentions the feature as planned work
- nearby files changed for related functionality
- the agent answers as if the feature shipped without checking the actual tab/route registration

### "Delegated task succeeded"
Required proof:
- do not trust the subagent summary by itself
- read back the files, inspect the diff, fetch the URL, or check the returned ID/status yourself

### "Service is running"
Required proof:
- use a health check, process check, port check, or log signal
- do not rely on "started successfully" text alone if the service may crash immediately after

### "Seeder / cache refresh fixed the health check"
Required proof:
- verify the writer actually refreshed BOTH the canonical data key and the health/freshness metadata key the health endpoint reads
- inspect the live health response shape before probing leaf fields; many endpoints expose checks under a nested object like `checks.<name>` rather than top-level keys
- if health still shows `STALE_SEED` or `EMPTY` after a successful seed, inspect the naming contract, not just the payload write
- compare the seeder's domain/resource naming (or equivalent helper arguments) against the health check's expected `seed-meta:*` key
- for optional or sparse sources, verify the no-credential / no-record path publishes an empty-but-fresh payload when the seeder already models zero records as valid, instead of exiting early and leaving health stuck on `EMPTY`
- independently read back the canonical key, the `seed-meta:*` key, and the live health endpoint before claiming the seed path is fixed

Common failure pattern:
- the seeder writes the main payload successfully
- verification stops after confirming the payload key exists
- the health endpoint reads a different freshness/meta key namespace, so status stays stale/empty

### "Configured in Hermes"
Required proof:
- inspect the relevant config file, skill listing, tool listing, cron listing, or status/doctor output
- prefer Hermes-native checks when available
- for plugin-style CLIs, verify both the command exit status and the persisted installed-state view (`plugin inspect`, `plugin list`, lockfile/config readback) before claiming success
- if an install path has both an interactive convenience verb and a non-interactive primitive, prefer the primitive for reproducible verification and reruns
- after granting scopes or trust, read back the trust state and granted scopes explicitly rather than assuming the prompt response means the plugin is invokable
- when a platform or optional integration has both env/credential presence and a separate enabled/disabled config flag, verify and report BOTH states; do not collapse `credential present` into `integration enabled`

Common failure pattern:
- `hermes config check` or env inspection shows a platform variable is present
- the persisted config keeps that platform disabled or intentionally dormant
- the agent writes docs or status text saying the integration is `enabled`
- fix by reading both the env/config-check surface and the concrete `config.yaml` enabled flag, then describe the intended posture precisely (`enabled`, `disabled`, `dormant`, or `credentials present but disabled`)

- after granting scopes or trust, read back the trust state and granted scopes explicitly rather than assuming the prompt response means the plugin is invokable
- if an optional integration is unhealthy but current user dependency is unknown, do not silently disable it and then report the estate as cleaned up; document the live risk and separate "safe to fix now" from "needs an explicit keep-or-retire decision"

Common failure pattern:
- a plugin subcommand prints plausible JSON or human-readable output
- the dispatcher then exits non-zero due to a trust, subject-digest, or post-dispatch failure
- the agent reports success from stdout alone instead of treating the non-zero exit as a blocker and verifying installed/trusted state independently

### "System/package updates are done"
Required proof:
- rerun the native updater or status command after the update pass, not just the initial update command
- for image-based systems (for example rpm-ostree), verify both whether a new deployment was staged/applied and whether a reboot is required
- for mixed package managers, verify each manager independently (for example system image, Flatpak, language/tool managers, npm globals)
- when one manager reports partial failure, name the blocked package/source and do not collapse the result into "everything updated"
- when Flatpak or another CDN-backed updater fails on a subset of objects, probe the exact failing summary/object URL over the relevant network paths (for example VPN tunnel vs physical interface) before assuming repo corruption; if the same URL succeeds on LAN but fails through the tunnel, report a network-path blocker rather than a package-state blocker
- if catalog/listing views still advertise updates but a targeted update on the same refs returns "Nothing to update", treat that as metadata lag or listing drift unless a direct install/update command proves otherwise
- for app-store style systems, read back concrete installed versions for any package that previously failed or looked ambiguous

Common failure pattern:
- one broad update pass prints mostly-successful output
- a later verification call reveals a transient network/TLS failure for one package or remote
- the agent reports blanket success instead of partial completion plus blocker

Common failure pattern:
- a listing command (`remote-ls --updates`, GUI badge, cached catalog) still shows updates
- the targeted updater for those exact refs returns `Nothing to update`
- the agent reports stale catalog output as pending real work instead of distinguishing metadata drift from actionable updates

### "Recommendation / ranking / refresh logic is fixed"
Required proof:
- verify the live output surface the user actually consumes (API/HTML/UI), not just a helper function in isolation
- confirm the feed returns the target count after the change, or explicitly report the current ceiling if the unseen pool is smaller than the display target
- check exclusion rules against the backing state store (for example DB-rated IDs vs live recommendation IDs) so you prove there is no overlap with already-seen/rated items
- when you add new candidate types or fallback pool entries, perform one temporary end-to-end mutation through the normal save path (for example POST a rating for a newly surfaced item), verify the backing store row was written correctly, then clean up the temporary fixture so state is restored
- for recency-weighted ranking, inspect at least one returned item's explanation/score fields or equivalent evidence so you can confirm the recent/30-day/lifetime signals are actually flowing into the live result
- if you add diversity guards, inspect the returned mix for domination by one seed/source type and say plainly what caps are enforced

Common failure pattern:
- helper function output looks correct in-process
- the running service was not restarted or the live API still serves stale logic
- verification stops before checking DB overlap or the new candidate type's save path

### "Hardening / guardrail cleanup is complete"
Required proof:
- rerun the checker or validator after the final edits
- inspect the checker/validator diff itself if you changed the guardrail logic
- verify that any new parser/library dependency is installed by CI or clearly declared
- if the result improved to zero warnings or suppressions, confirm the remaining findings were fixed or correctly reclassified — not accidentally hidden by an over-broad heuristic
- for secure-by-default changes with an escape hatch, read back the user-facing help/docs/output and confirm the opt-in path is still discoverable

### "Classifier / router / scoring heuristic is fixed"
Required proof:
- verify the lowest-level parse or feature-extraction path directly before trusting downstream classification (for example nested frontmatter, parsed metadata, tokenization, or normalized fields)
- add or update a synthetic regression fixture that exercises the intended signal
- rerun the relevant automated test suite after the scoring change
- verify at least one real representative artifact from the installed corpus, not just a tiny fixture, because heuristic weight changes often pass tests while over-correcting live classification
- read back the generated explanation/reason field, not only the top-line class, so you can confirm which signals actually won
- if a real artifact flips to an implausible class after the change, narrow generic alias matching before adding more score weight

Common failure pattern:
- the parser bug is fixed and the new fixture passes
- generic substring or alias matching still leaks extra scores in the live corpus
- the classifier appears green in tests but routes a representative real artifact to the wrong family
- fix by probing parsed structure directly, checking the real generated reason field, and tightening generic matches before increasing weights further

## Delegation rule

If `delegate_task` or a spawned Hermes process reports success, you must verify the externally visible result before telling the user it succeeded.
Examples:
- file write -> read the file
- git change -> inspect diff/status
- web action -> fetch page or response
- service change -> health check
- cron job -> list job and inspect fields

## Reporting format

When concluding, include a compact evidence line:
- Verified by: `<command or inspection>`

For generated-data dashboards or refresh pipelines, preserve verification order when the UI depends on generated artifacts:
1. syntax/compile check the refresh or generator scripts
2. run the data refresh/generation command
3. run tests against the refreshed tree
4. run the production build
5. inspect a sample of generated output for fallback/noise issues before claiming the feature is really usable
- for ranking/summary surfaces fed by scraped or generated data (dashboards, trackers, social/post lists), verify that the displayed ranking is backed by real accessible signals rather than placeholder or login-walled pages. If a platform is login-walled, degrade to another accessible source instead of presenting profile/login pages as if they were actual posts.
- when a UI lane is explicitly about latest posts/activity, inspect the generated artifact and confirm it contains post/video/reel-level items rather than account/profile/about pages. If only account/profile summaries are available, leave that lane empty or relabel it — do not silently populate a "latest posts" surface with profile metadata.
- if the UI has a second nearby fallback lane such as "official/public items" or "announcements", verify that the same profile/account metadata is not leaking in there either when the user's complaint is about post-level summaries. Read back a concrete example record in the generated artifact and confirm both lanes are either post-level or empty; removing the fallback only in the visible "latest posts" lane is not sufficient.
- for live table parsing or irregular HTML sources, verify one or two concrete rows manually against the generated output before claiming extracted metrics are correct; do not rely on heuristic column guesses when the page layout can be expanded or colspan-heavy.


Reference: `references/classifier-heuristic-verification.md` for parser/routing/scoring changes where a fixture can pass while live classification still over-corrects.
Reference: `references/seed-health-key-alignment.md` for cache/health verification when a seed job reports success but health remains stale or empty.
Reference: `references/recursive-hardening-stop-conditions.md` for multi-batch hardening/cleanup passes where the right finish line is "remaining findings changed class," not necessarily zero.
Reference: `references/generated-data-verification-order.md` for generated-asset repos where refresh output, tests, and build must be verified in dependency order and fallback data quality should be sampled, not just compiled.
Reference: `references/browser-compat-and-portability-checks.md` for repos that must work beyond the current machine and need explicit browser/dependency portability proof.
Reference: `references/lazy-ui-bundle-splitting.md` for React/Vite lazy-tab verification, test updates, and how to interpret post-split chunk output.
Reference: `references/plugin-cli-state-vs-stdout.md` for plugin/extension installs where stdout looks successful but the authoritative proof is the native inspect/list/lockfile state plus the command exit code.
Reference: `references/flatpak-vpn-path-isolation.md` for Flatpak/Flathub failures that reproduce only on one network path (for example a VPN tunnel) and need object-level curl checks bound to specific interfaces.

Examples:
- Verified by: `pytest tests/api/test_auth.py -q` -> 12 passed
- Verified by: `read_file(path="~/.hermes/config.yaml")` confirmed `approvals.mode: smart`
- Verified by: `git diff --stat` and readback of `src/app.py`

## Failure mode

If verification fails or cannot be run:
- say exactly what is unverified
- show the blocking error
- do not upgrade the status to success

Good:
- "I made the change, but I could not verify the build because `npm test` fails earlier on a missing dependency."

Bad:
- "Should be fixed now."

## Completion checklist

Before final answer, check:
- [ ] every success claim has fresh evidence
- [ ] delegated work was independently checked
- [ ] the proof is proportional to the claim
- [ ] errors or unverified parts are called out explicitly

## Pitfalls

- verifying too broadly instead of the exact requirement
- quoting old test output after additional edits
- trusting subagent summaries without readback
- claiming deploy/config success after only writing a file
- for plugin or extension systems, treating stdout as proof even when the CLI exits non-zero or the trust/installed-state readback disagrees
- stopping after a file edit when the user asked to run or verify something
- after broad multi-file edits, forgetting to re-run a narrow syntax/build check on the touched subset before continuing
- after reading a file with pagination or a partial window, patching it without first re-reading the full file
- after a scripted mass-edit introduces syntax or indentation regressions, trying to hand-repair the fallout indefinitely instead of restoring the damaged subtree and re-applying a smaller verified patch
- in recursive hardening passes, chasing a lower warning count after the remaining findings have become semantic/intended cases rather than safe cleanup candidates
- after each cleanup batch, forgetting to re-run both the narrow touched-file proof and the top-level guardrail/validator that tells you whether the nature of the remaining work changed
- leaving guardrails noisy after a hardening change; if risky behavior is now explicit opt-in, update the checker so CI distinguishes opt-in patterns from unconditional defaults
