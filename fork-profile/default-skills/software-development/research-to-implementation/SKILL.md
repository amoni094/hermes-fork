---
name: research-to-implementation
version: 1.0.0
author: Hermes Agent
description: Use when implementing corpus research findings into Hermes.
keywords:
- research
- implementation
- corpus
- arxiv
- saturation
- adversarial
tags:
- research
- implementation
- arxiv
- hermes
platforms:
- linux
---

# Research-to-Implementation Cycle

For sessions where a corpus (arXiv sweeps, GitHub repos, book corpus) is analyzed
and findings are implemented across Hermes surfaces.

See `references/wiring-verification-checklist.md` for dead-code, dead-config, and
script-existence verification steps that must be run after every implementation.

## Surface priority order

Do NOT default to skill patches. Implement to the surface with the greatest live runtime
effect first:

  runtime code > config (if read) > scripts > plugin hooks > skills > memory

- **Runtime code** (`agent/*.py`): patch the code if the finding maps to compressor or
  dispatch logic. A skill that says "code should do X" when it doesn't is dead documentation.
- **Config** (`~/.hermes/profiles/fork/config.yaml`): ONLY add a key if the fork source reads
  it. Run `search_files(pattern='key', path='~/.hermes/hermes-fork/')` first. 0 results =
  do NOT add; document as planned-only in the observability skill instead.
- **Scripts**: create only when there is an actual invocation path (cron, skill step, CLI).
- **Plugin hooks**: implement in `__init__.py`, not just documented in a skill.
- **Skills**: patch rules and procedures. Not a substitute for real code.
- **Memory**: patch actual TTL scripts and provenance taggers.

## Wiring verification

After every implementation, verify the code is actually called. See
`references/wiring-verification-checklist.md` for the full procedure.

Short form:
- New fork function: `grep -rn 'fn_name' ~/.hermes/hermes-fork/agent/` must return a call
  site in a non-test file. Definition + test only = dead code.
- New config key: `grep -rn 'key_name' ~/.hermes/hermes-fork/` must return a .py reader.
  0 matches = remove the key.
- New TTL type: must appear in BOTH the constant definition AND the dispatch branch.

## Parallel subagent deduplication

When main session AND subagents both implement items from the same batch, duplication
is nearly certain. After every parallel batch:

1. **Same skill, two appenders**: `grep -c 'heading' ~/.hermes/skills/.../SKILL.md`
   Count > 1 = dedup needed. Assign each skill to ONE owner before dispatching.

2. **Same config key, two writers**: security gate blocks subagents (correct), but check:
   `grep -c 'key_name' config.yaml` — count > 1 = merge needed.

Post-batch step: run a dedup grep over all modified files before declaring the batch done.

## Subagent security gates on config

Subagents CANNOT write `~/.hermes/profiles/fork/config.yaml`. When a subagent needs
to add a config key, instruct it to write a staging file (`/tmp/config-additions.yaml`)
and surface changes as OPEN_ISSUES. Parent session applies via `terminal()` Python.
Never re-dispatch expecting the block to be bypassed.

## Stop-verb NLP pitfall (relevance scoring)

When scoring memory fact relevance via verb-overlap, exclude stop-verbs (run, use, set,
get, call, make, check, write, read, add, create, start, stop). Generic verbs appear in
almost every fact; including them inverts the ranking.

Fix: maintain `STOP_VERBS` set; `verbs_to_match = extracted_verbs - STOP_VERBS`.
Require at least one domain-specific verb in common before giving overlap credit.
Without a stemmer, normalize past tense (`-ed`, `-ing`, `-s`) before matching.

## Recursive research loop discipline

1. Research waves to saturation (<5 new implementable IDs AND all remaining are
   W-only or benchmark-only).
2. Triage all findings across ALL surfaces.
3. Implement in surface priority order.
4. Dispatch a COLD adversarial reviewer (different model+provider, no prior context).
   'Wait for it' — no fixes until the full report arrives.
5. Triage: ACCEPT / REJECT / PARTIAL per finding.
6. Apply all accepted fixes in one batch. Compile + test.
7. Re-dispatch if CRITICAL or MAJOR findings remain.

## Adversarial report triage

- Adversarial agent may flag issues the parent ALREADY fixed (stale-snapshot).
  Check timing: if fix predates reviewer dispatch, finding is a false positive.
- Apply HIGH fixes in the PARENT session, not a new subagent.
- Require three-way verdict: confirmed / false_positive / need_more_context.
