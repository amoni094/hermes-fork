---
name: verification-before-completion
related_skills:
  - workflow-map
  - requesting-code-review
  - risk-based-review
  - plan
  - systematic-debugging
  - subagent-driven-development
  - agent-task-signoff
  - subagent-output-contract
depends_on: [test-driven-development, requesting-code-review, hermes-coding-review-loop]

tier: global
provides: [task-verification, completion-proof, readback-check]
triggers:
  - About to claim a task is done and need fresh evidence before declaring completion
  - A subagent claims it succeeded and the parent must independently verify the claim
  - Need explicit proof of work (read-back, test run, file stat) before closing a task
  - User says 'check it actually worked' or 'verify before marking done'
description: >
  Use when: Use before claiming a task is done: require fresh evidence, independent readback after delegated work, and explicit proof commands.
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [verification, completion, evidence, testing, delegation]
    related_skills: [workflow-map, requesting-code-review, risk-based-review, plan, systematic-debugging, subagent-driven-development, agent-task-signoff, subagent-output-contract]
ssl_scheduling:
  triggers:
    - About to claim a task is done and need fresh evidence before declaring completion
    - A subagent claims success and the parent must independently verify
    - Need explicit proof of work (read-back, test run, file stat) before closing a task
    - User says 'check it actually worked' or 'verify before marking done'
  preconditions:
    - Implementation or delegation step has been completed
    - There is a clear expected outcome to verify against
  estimated_steps: 4
ssl_structural:
  tools_used: [terminal, read_file, search_files, browser_snapshot]
  subtasks:
    - Define expected outcome and verification criteria
    - Run independent read-back or test command (fresh state, no cache)
    - Compare actual output against expected outcome
    - Report PASS/FAIL with evidence before marking done
ssl_logical:
  side_effects:
    - Runs test suites or verification commands (read-only intent)
    - May produce a verification report in the session
  resources:
    - Target files or services being verified
    - Test runner / CI configuration
  risk_level: low
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

<!-- metacognition wiring: see adaptive-agent-reasoning skill -->
Run the metacognitive abstain check before any irreversible delivery:
  python3 ~/.hermes/scripts/metacognitive-harness.py abstain-check --action 'deliver final answer' --confidence C
Use working-memory.py verify-gate for constraint evidence audit. See adaptive-agent-reasoning for full exit code semantics.


## Fast path
1. **Run `diff-impact.py`** to estimate blast radius and confidence. Load the suggested skill hooks.
2. Restate the exact claim.
3. Choose the narrowest proof.
4. Run it now.
5. Independently verify any delegated or background work.
6. Report the result with a compact `Verified by:` line.

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
9. For security hardening that must stay usable: default TLS on with explicit `--insecure`; unique `tempfile.mkdtemp` not `/tmp/foo.txt`; do not default `--force`; harden automation/CI/defaults before restricting legitimate content. Re-run the repo's canonical validator (not a duplicated inline variant). If a paginated read was truncated, re-read the whole file before overwrite.
10. Only then respond with the result and the proof.

## CatchBench PRE / LIVE / POST failure catch (arXiv:2608.22808) ★ HIGH <!-- why: most failures are catchable earlier than POST; audit info-state, not just finished traces -->

CatchBench scores the same auditor questions under three information states. Hermes should
catch failures at the earliest state that has enough evidence:

| State | When | What to check |
|-------|------|----------------|
| **PRE** | before irreversible work | declared config/toolsets/scope; missing acceptance criteria; wrong workdir; NL deny rules that are not enforced |
| **LIVE** | mid-run (prefix of trace) | repeated same-tool/same-args ≥3; goal drift; empty subagent returns; staleness/gen_gap spikes on recalled facts |
| **POST** | before claiming done | external proof of side effects; claim-to-proof map; independent re-read of artifacts |

Rule: if a failure is visible at PRE or LIVE, do not wait for POST. PRE catches are cheapest.
LIVE catches use trajectory prefix (StepShield-compatible). POST is mandatory for external
side effects even when PRE/LIVE looked clean.

**Companion skill for cross-platform/multi-layer work:** Load `skill_view(name='adversarial-review')` when porting code across platforms (Hermes ↔ Cowork), refactoring multi-file configs, or reviewing agent specs. It catches self-contradictions, portability gaps, and broken references that functional verification alone misses.

**SQA two-framing check for multi-agent outputs (arXiv:2606.08021):** Before accepting any subagent's deliverable as verified, apply two lightweight adversarial framings:
1. "What could go wrong with this output even if it looks correct?"
2. "Is this output within the original task scope — or did the subagent over-reach or under-deliver?"
These two questions catch the majority of subagent failures that single-frame verification misses. Takes <30 seconds and costs one short model call.

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
- if the subagent's own verification step failed or was blocked (e.g. its terminal command hit a policy gate), that does not invalidate the deliverable — but it does mean you inherited the verification duty. Do it yourself with a different tool before reporting success.
- for generated Office documents (.docx/.xlsx/.pptx) and notebooks (.ipynb), prefer `read_file` over shelling out to `python-docx`/`unzip`/`openpyxl` via `terminal`/`execute_code` — it auto-extracts readable text (flagged `extracted_document: true`) with no dependency install and no shell needed. Read head and tail (or a paginated middle sample) to confirm real, substantive content, not just file existence. See `references/office-file-verification-without-shell.md`.
- if a verification command is blocked by a user policy/consent gate, do not retry the same or a rephrased command — switch immediately to a different verification tool (e.g. `read_file` instead of `terminal`+`unzip`). Retrying a blocked command wastes turns and triggers tool-loop warnings.

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

- if an optional integration is unhealthy but current user dependency is unknown, do not silently disable it and then report the estate as cleaned up; document the live risk and separate "safe to fix now" from "needs an explicit keep-or-retire decision"

Common failure pattern:
- a plugin subcommand prints plausible JSON or human-readable output
- the dispatcher then exits non-zero due to a trust, subject-digest, or post-dispatch failure
- the agent reports success from stdout alone instead of treating the non-zero exit as a blocker and verifying installed/trusted state independently

### "All steps of a recovered/interrupted multi-part task are complete" (research sweeps, multi-agent pipelines, resumed work)
Required proof:
- do not trust an INDEX.md/README/handoff-note's narrative summary of what was covered — it describes what the *last* subagent/session believed it did, not what the *original* task required
- find the actual source-of-truth requirements list (the spec's own self-identified gap list, the original TODO/checklist, the task's stated scope) and diff it item-by-item against what the deliverables actually contain
- read the substantive files themselves (not just their own internal "Summary"/self-report preambles, which are also self-reported claims) to confirm each topic was actually covered, not merely mentioned in a table of contents
- report a concrete count: "X of Y required items covered" plus which specific items are missing, rather than a binary "yes it's done" / "no it's not"

Common failure pattern:
- an index file lists several deliverable files and describes them in prose that sounds comprehensive
- the underlying spec or task itself enumerated a longer checklist (e.g. 15 self-identified gaps) than the index's summary implies
- the agent answers "yes, complete" from the index's narrative alone instead of cross-checking the original checklist against the actual research/deliverable files
- fix: always locate and diff against the original enumerated list before confirming completeness of recovered or multi-stage work

### "Credential / API key is missing" (compaction, summarizer, background-model, or subprocess error message)
Required proof:
- do not accept an error string like "no API key was found" or "provider X is set but no key configured" as proof the credential is actually absent — subprocess calls (context summarizers, auxiliary/compression models, background cron agents) can fail to inherit env or hit a transient provider issue for reasons unrelated to whether the key exists
- verify directly: confirm the variable is present in the relevant `.env`/config file, then make a live probe call to the provider's own endpoint (e.g. `curl` its models/health endpoint with the key) and check the HTTP status
- if the live probe succeeds, treat the original error as transient/subprocess-specific and say so explicitly — do not "fix" or rewrite a config that is already correct
- when displaying partial/redacted credential values for diagnostic purposes, verify the redaction actually redacts BEFORE running it — a `sed` substitution that doesn't match the real output format silently passes the raw secret through verbatim into terminal output and your own context window. Prefer verification commands that never echo the full value at all (check only the HTTP status code, or use explicit substring truncation like `${VAR:0:4}...`) over "pipe to sed and hope it matches"

Common failure pattern:
- a background compression/summarization step reports a missing provider API key
- the agent either takes the claim at face value and starts editing config, or tries to verify by printing a "redacted" version of the key using a sed/grep pattern that doesn't actually match the key's real format, leaking the raw secret into its own context
- fix: test the credential live against the provider's endpoint, and design the verification command so it structurally cannot leak the secret even if the redaction step is wrong (check exit status / HTTP code, never the payload)

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
Reference: `references/repo-hardening-low-friction.md` for security hardening that must stay usable (TLS default, unique temps, explicit opt-in for `--insecure`/`--force`, harden automation before content).

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

## Pre-Execution Tool Call Argument Validation (arXiv:2608.10430, Aug 2026)

Before executing any tool call with irreversible effects (file writes, API calls, memory deletes), validate each argument against conversation context. The latent critic paper (2608.10430) shows argument-level hallucination is the primary failure mode, not action selection.

Checklist for high-risk tool calls:
- file write: Is the path grounded in a file actually mentioned or read this session?
- API/external call: Is the identifier (URL, key, ID) drawn from confirmed context, not synthesized?
- delete/overwrite: Is the target explicitly confirmed within the last 3 tool results?
- date/time argument: Can it be traced to a literal from this session, not interpolated from general knowledge?

If any argument fails this check, state the uncertainty explicitly before proceeding — do not silently pass ungrounded arguments.

## SemaPLC — External-Check-Gated Completion (arXiv:2608.18565, Sweep 20 addendum) <!-- why: model self-judgment of "done" is unreliable; only external check confirmation counts as completion -->

SemaPLC's strict completion rule: a task is complete only when **logged external checks confirm it** across three axes:
1. **Specification check**: does the output satisfy the stated requirements? (not "does it look right to me?")
2. **Compilation/syntax check**: does it parse/run without error? (exit code 0)
3. **Behavioral check**: does it produce the correct output on a live test case?

The model is explicitly forbidden from declaring completion based on its own assessment. Applies directly to Hermes:
- Terminal commands: exit code 0 + expected output visible in result, not "I ran it and it looked correct"
- File writes: `verified: true` from `write_file`, not "I wrote the file"
- Skill patches: `success: true` from `skill_manage`, then `grep` confirmation of the new text
- Cron jobs: `cronjob action='list'` shows the job with correct schedule, not "I created the job"

When the external check fails after model self-declared completion: treat this as a bug in the completion declaration, not just a task failure — the process broke down.

## Context reduction vs verification

Do not treat context compression as a verification strategy. Layer rules live in `hermes-context-hygiene`. Here: never claim a compressed/summarized trajectory is proof; verify the artifact or end-to-end outcome. Unit tests on intermediate steps can pass while the overall trajectory is wrong.

## Cross-Contextual Consistency Check (arXiv:2608.10315, Aug 2026)

For complex factual claims or high-stakes tool call arguments: before finalizing, run a paraphrase-verify loop. Rephrase the key claim in a different surface form and evaluate whether the answer is consistent. Inconsistency signals unstable beliefs requiring human review.

Trigger when:
- Answer depends on information retrieved from context more than 3 turns ago
- A tool call argument is a date, path, identifier, or precise value derived from reasoning
- The task involves an irreversible binary decision (deploy/rollback, delete/keep)

Implementation (no extra tool calls): After forming the answer, restate the core claim as a question ("Does this confirm X?") and check if the answer holds under skeptical inversion. If the claim doesn't survive, flag explicitly before completing.

## False-Success Detection and Boundary Check (arXiv:2606.09863)

Before declaring completion, run boundary-check to confirm the action is actually done and in-scope:
  ```
  python3 ~/.hermes/scripts/metacognitive-harness.py boundary-check \
    --task "<what was declared done>" --action "<last action taken>" \
    --prior-actions '["<a1>","<a2>"]'
  ```
  Exit 0: complete and in-scope. Exit 1: incomplete steps remain. Exit 2: OVER_ACTION. Exit 3: SCOPE_CREEP.

For attribution claims ("X fixed Y"), check false-attribution first:
  ```
  python3 ~/.hermes/scripts/critique-bank.py false-attribution \
    --claim "<fix X resolved Y>" --context "<evidence>"
  ```
  HIGH risk = do not report as fixed; re-verify independently.

## False-Success Detection (arXiv:2606.09863)

Agents claim task completion when actually stuck in a silent failure loop. Before claiming task complete, verify:
1. Output state is actually different from input state (not a no-op)
2. Verification is on the ACTUAL artifact, not the last tool call's return value
3. At least one independent readback confirms the change (file size, test result, etc.)
4. If output matches a prior failed attempt's output: re-examine, not just re-claim

For tool/MCP tasks: verify path-agnostic checkpoints (intermediate effects), not only the final output. A correct final answer reached via wrong tool path may hide a latent bug.

## Completion checklist

Before final answer, check:
- [ ] every success claim has fresh evidence
- [ ] delegated work was independently checked
- [ ] the proof is proportional to the claim
- [ ] errors or unverified parts are called out explicitly
- [ ] false-success checks above passed (state actually changed; artifact readback; not a repeat of a prior fail)

## pass@k vs pass^k Verification Framing

Distinguish these two reliability models when designing verification:

**pass@k** — at least 1 of k attempts succeeds. Use when:
- You just need it to work once (demo, one-shot migration, spike)
- Failure is cheap to retry
- Consistency across runs is not a requirement

**pass^k** — ALL k of k attempts must succeed. Use when:
- The system must be reliable for every user / every run
- Downstream consumers depend on consistency
- A single failure breaks a pipeline

One-shot verification (run it once, it passed) = pass@1, which is weak evidence of pass^k reliability.
For production behavior claims, require at least pass^3 (three independent passing runs) before calling it reliable.

Implication for agentic loops: a subagent that "succeeded" on one run is pass@1 evidence. Do not upgrade it to a reliability claim without multiple independent confirmations.

## Verifier design (agentic loops)

The verifier determines loop success more than the model does.
Stack verifiers deterministic-first to prevent the model gaming softer checks:

1. Deterministic gate (schema validation, constraint violations, known invalid states, compiler/linter, tests)
2. LLM-as-judge ONLY for things that passed the deterministic gate

A model can talk its way around an LLM judge. It cannot talk its way around a failing test or a schema rejection.

For uncertain outcomes (verifier score in a "middle band"), flag for human review rather than auto-retrying or auto-approving.
- Clear fails: auto-retry
- Clear passes: auto-approve
- Ambiguous middle ~20%: human in the loop

Metric that matters in loops: cost per successful verified outcome, not cost per run. Retry budget should be sized against this, not against per-run latency.

### Continuous verification scoring (LLM-as-a-Verifier, arXiv:2607.05391)

For ambiguous cases, replace binary pass/fail with a continuous score via decomposed criteria:
- Score each criterion independently (1-10), aggregate to [0,1]
- Three scaling axes: granularity (more criteria), repetition (N independent evals), decomposition
- Aggregate by simple mean of criterion scores; default accept threshold 0.6 unless the task has a calibrated bar
- There is no in-tree `nesy.py` / `LLMVerifier` — do not call a fictional helper. Paper: arXiv:2607.05391

### ATP admission control for irreversible steps

Before irreversible actions (deploy, delete, external API), gate via `mnemosyne-atp-safety`. Do not restate ATP protocol here.

### Delivery verification — shell command output proves completion

Delivery-first guardrails (from Reasonix Evidence Ledger, 2026): certain shell
patterns structurally cannot serve as delivery verification even when they print
plausible output. Block these before treating a verification command as proof:

| Pattern | Why it fails as verification |
|---|---|
| `echo $?` after a command | Masks the real exit status — `echo` always exits 0, hiding whether the prior command succeeded |
| Mixed mutation + verification in one command | `git push && echo "deployed"` — if push fails partway, the echo may still run; also mixes a write with a read in a single atomic-looking step |
| Opaque inline interpreter in delivery context | `node -e "..."` or `python -c "..."` — embeds a program in the command string; the command's exit status reflects the interpreter's parse, not the logical delivery |
| `echo "success"` unconditionally | Not a verification command — it always succeeds regardless of what happened |

**Rule:** a verification command is only valid if:
1. Its exit code is the direct output of the thing being verified (not an echo wrapper)
2. It is a read-only inspection of state, not a mutation paired with a print
3. It does not embed arbitrary code in an inline interpreter string

**Corrected patterns:**
```bash
# Wrong: masks exit status
some_command && echo $?

# Right: use directly
some_command
echo "exit: $?"  # only valid if you capture $? immediately after the command

# Wrong: mixed mutation + verification
deploy.sh && curl https://example.com/health

# Right: separate steps
deploy.sh
curl https://example.com/health  # verify separately, in a second terminal() call

# Wrong: opaque inline interpreter as verification
node -e "require('./app'); console.log('ok')"

# Right: use an explicit test command declared by the project
npm test
# or
node --check app.js  # syntax only
```

This applies whether verification is in a `terminal()` call, a cron job script, or
a subagent tool invocation. Delivery is not proven until a clean, non-masked,
read-only inspection confirms the expected state exists.

## Pitfalls

- Parser fixed but live classifier still wrong (pathological verification sequence): Parser fix passes fixtures but generic alias scoring still dominates live corpus. 4-step recovery: (1) confirm fixture passes, (2) run against live corpus sample (10+ items), (3) check if the classifier component (not just parser) was updated, (4) run end-to-end integration test against real input. A parser fix that passes a fixture without live corpus validation is incomplete verification.
- Bundle warning moved from entry to lazy chunk IS a real improvement: report both before/after warning locations explicitly. A warning moving from entry-point chunk to a lazy-loaded chunk means the critical path is fixed even if the warning persists. Do not treat a relocated warning as the same unresolved issue. Verify: confirm the entry chunk no longer contains the warning.
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
- trusting a subprocess/background-agent error message (compaction summarizer, cron job, auxiliary model call) about a missing credential without a live probe; the fix is often not needed at all once the credential is tested directly
- verifying a credential by echoing a "redacted" copy through a sed pattern that doesn't actually match — check status codes only, never pipe the raw secret through a substitution you haven't confirmed matches
- retrying the same (or a reworded) terminal command after it was blocked by a user policy/consent gate instead of switching tools immediately; a blocked command is not a transient error and repeating it just burns turns and triggers loop warnings
- reaching for `execute_code`/`terminal` + a library install (`python-docx`, `openpyxl`, `unzip`) to inspect a generated Office document when `read_file` already auto-extracts it — the extra dependency is unnecessary risk and cost for a check `read_file` does natively
- taking an index/handoff-note's narrative summary of "what was covered" at face value for recovered or multi-stage work; always diff against the original enumerated checklist (spec's own gap list, task's stated scope) item-by-item before confirming completeness
- closing a bug as fixed without checking if it's an instance of a class — when a defect has siblings (same pattern elsewhere in the codebase), don't close until you've swept and fixed or tombstoned all siblings (see isa skill's Class Sweep Rule)
- reading suspect code before reproducing the bug — reproduce first, then read; skip only for pure-additive work or when repro would cause damage, and document the bypass

Plugin/CLI, recursive hardening, generated-data order, office files, Flatpak/VPN, seed-health, and browser-compat procedures live in `references/` — do not duplicate them here. Fast path: `references/fast-verification-matrix.md`.

Delegated summaries are not evidence. Same rule as **Delegation rule** above: independently inspect the artifact (stat/readback/fetch/query/exit_code).

## Completion-time extras (do not fork a second verification religion)

These sharpen POST; they do not replace CatchBench PRE/LIVE/POST or the claim-to-proof map.

**TrAC (arXiv:2608.00422):** after one complete trace, re-elicit a short answer conditioned on that trace. Any factual divergence vs the original claim → re-verify. Cost: 1 extra call vs 8 for self-consistency.

**Deterministic recompute (arXiv:2608.02464):** before "done", reconstruct claimed outputs from actual tool results and confirm required tool categories ran. Claim ≠ reconstruction → FAIL. On fail: rollback to last clean state and re-run the failed sub-sequence — do not "fix in place". Crash tests miss the dominant class (incorrect functionality: API/config/parse/serialize).

**Prior-failure recall:** before "done", search `session_search` / `hindsight_recall` for this task's prior failures (top-3 rank, never an absolute cosine cutoff). There is no `unified_recall` helper. If a prior failure mode is in the top-3, check this completion actually avoids it.

**Schema-derived smoke tests** after tool/skill/config changes belong in `evaluation-driven-development` (Agent Seer, arXiv:2608.26133) — not a second completion gate here.
