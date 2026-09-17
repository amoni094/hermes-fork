---
name: isa
description: 'Use when defining done before building. Spec-as-test-suite.'
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [spec, verification, done-criteria, claims, falsifiers, intent-engineering]
    related_skills: [verification-before-completion, adversarial-review, plan, grill-me]
triggers:
  - User asks to define "done" before starting implementation
  - Task requires a spec or acceptance criteria before writing code
  - User says "spec", "define requirements", "what does done look like", or "ISA"
  - Building a falsifiable test suite from natural-language intent before implementation begins
  - NOT plan (which produces steps) — ISA produces done-criteria and falsifiers
related_skills:
  - verification-before-completion
  - plan
  - adversarial-review
  - grill-me
---

# ISA — Ideal State Articulation

## Overview

The ISA is a one-document spec where every claim names the probe that would falsify it.
The spec IS the test suite. Done = every claim closed on tool evidence of the right modality.

Adapted from LifeOS (Miessler, 2026). Core insight: most failed runs fail not in execution
but in direction — "done" was never written down precisely enough to check.

**A goal is not an ideal state.** A goal says where to go; an ideal state also says what
must not be destroyed getting there (Anti-claims, Constraints, Out of Scope).

## When to Use

- Before any substantial build or change (anything >30min of work)
- When a task is ambiguous — writing ISCs surfaces ambiguity cheaply before it's expensive
- When handing off work to a subagent — the ISA IS the brief
- After a run — reopen to record what you actually learned

Don't use for: trivial one-liners, direct lookups, pure research tasks where the output IS
the answer (use plan skill for multi-step tasks that don't need falsifiable claims).

## The ISA Format

```markdown
## Goal
<verbatim principal stated goal — immutable unless explicitly revised>

## Ideal State Criteria (ISCs)

- [ ] ISC-1: <claim> | falsifier: <tool/check that proves this false>
- [ ] ISC-2: <claim> | falsifier: <probe>

## Anti-claims (what must NOT happen)
- [ ] AC-1: <thing that makes the run a failure even if ISCs pass>

## Out of Scope
- <explicitly excluded — protects against scope creep>

## Constraints
- <invariants that must remain true throughout>

## Not Yet Specified (Fog)
- <genuine unknowns, stated as precise questions, not answers>

## Decisions
- <YYYY-MM-DD: what was decided and why — dead ends count>
```

## Writing ISCs — The Hard-to-Vary Standard

An ISC set is good when removing or weakening any claim changes what done means.

**Every ISC must name its falsifier.** A claim without a nameable probe is a wish:
- Wish: "the site feels fast"
- Claim: "p95 page load under 800ms, measured by the deployed probe"

**Universal claims beat example claims:**
- Example: "one test email arrived"
- Universal: "mail flows at baseline rate over the measured window"

**Evidence modality must match the claim:**
- file change → read the file back after writing
- code behavior → test output or grep
- HTTP endpoint → `curl -i` showing real status
- visual/UI → real browser screenshot
- deploy → live probe (not warm-cache T+0)

## Closing an ISC

An ISC closes when you have tool evidence of the right modality. "Should work" is forbidden.

On close: shrink evidence to a one-line provenance stub. Full proof lives in git or CI.

```
- [x] ISC-2: auth rejects expired tokens | falsifier: curl with expired token returns 401
      Evidence: commit a3f8c12, test test_auth.py::test_expired_token_rejected
```

## The ISA Lifecycle

```
SCOPE  → write Goal + ISCs before touching code. Flag fog honestly.
CLIMB  → build. Each probe either closes a claim or reveals a fog item.
         When a probe fails: is the code wrong, or was the claim wrong? Fix the right one.
VERIFY → every ISC needs closing evidence before calling done.
LEARN  → decisions, dead ends, discoveries go to Decisions.
         Changelog is git. ISA keeps the living surface only.
```

## Operating Rules

For ISA tasks at L2+, run select-frameworks before writing Ideal State Criteria to determine which reasoning constraints apply to the verification step:
  ```
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
    --task "<ISA goal>" --level <L>
  ```
  If boundary-check is in primary: run it before closing each ISC to confirm the action is complete and in-scope.

**Before building:**
1. Write Goal (verbatim user intent, immutable)
2. Write ISCs — at least one per major dimension of done
3. Write at least one Anti-claim
4. Write Out of Scope for anything adjacent the user didn't ask for
5. Surface fog rather than inventing false precision

**During build:**
6. Probe prerequisites before execution (tokens, logins, configs) — block if MISSING
7. Resolve material ambiguity first: up to 3 targeted questions when the answer changes what gets built. A named-but-unverified referent ("the video", "the service we discussed") is always material — find it on record or ask, never infer and build on.
8. Close each ISC with tool evidence as you go
9. Update the ISA when you discover something — fold in corrections, failed probes, new constraints

**Closing:**
10. Every ISC has closing evidence before claiming done
11. Evidence collapses to one-line provenance stubs
12. Decisions section captures what you learned — dead ends count
13. Fog that graduated or died moves to Decisions

## Where ISAs Live

Create the directory on first use: `mkdir -p ~/MEMORY/WORK/{slug}`

- Persistent projects: `~/MEMORY/WORK/{slug}/ISA.md`
- One-off tasks: `~/MEMORY/WORK/task-{slug}/ISA.md` or inline in the session note
- Subagent brief: paste the ISC list verbatim into the subagent's context packet

The `~/MEMORY/WORK/` tree is the canonical home. Create it on first use.

## Class Sweep Rule

When a bug or defect closes, first check: is this an instance of a class?
If yes, enumerate ALL siblings before closing:

```
CLASS-SWEEP: <what you searched for> — N siblings via <grep/glob>; M fixed, K tombstoned
```

A defect recognized as a class does not close until the sweep is done.
For rename/retire/bump/migrate tasks: run the enumeration at PLAN time, not after verification.

## Bug Repro Rule

A reported bug must be reproduced before its suspect code is read.
Bypass allowed for: pure-additive work, non-isolable architectural symptoms,
or when repro would cause damage (document bypass in Decisions).

## Common Pitfalls

- **Specifying HOW instead of WHAT** — ISCs describe outcomes. "Use Redis" is a constraint; "p95 cache hit >95%" is an ISC.
- **Closing on assertion, not evidence** — "should work" is not a closed claim.
- **Container sampling** — one passing test is not evidence the whole file passes.
- **Warm-cache temporal fidelity** — probe after state propagates (DNS/deploy/cache invalidation needs time).
- **Growing changelog in ISA** — it's a living surface, not a log. Keep decisions, delete stale evidence.
- **Fog as placeholder** — fog is for genuine unknowns. If you can name the falsifier, write the ISC.
- **No anti-claims** — every non-trivial run has implicit anti-claims. Make at least one explicit.

## Worked Example — Minimal ISA

```markdown
## Goal
Add rate limiting to /api/search: max 100 req/min per IP, 429 on excess.

## Ideal State Criteria

- [ ] ISC-1: requests beyond 100/min from one IP get 429 | falsifier: wrk load test from single IP exceeds limit, observes 429s
- [ ] ISC-2: requests within limit get normal response | falsifier: curl /api/search returns 200 with valid body
- [ ] ISC-3: rate limit resets after 60s | falsifier: sleep 61 && curl from throttled IP returns 200

## Anti-claims

- [ ] AC-1: /api/health NOT rate-limited | falsifier: wrk against /api/health at 200 req/min, zero 429s

## Out of Scope
- Auth-based rate limits
- Rate limit response headers

## Constraints
- No new runtime dependencies; use existing Redis

## Not Yet Specified (Fog)
- Q: Shared limits across load-balanced instances or per-instance?

## Decisions
- Redis sliding window (not token bucket) — simpler reset semantics
```

## CodeSpec Extension: Dual Executable Specs for Agent Feature Work

Source: arXiv:2607.26777 (CodeSpec, Chinese authors, outperforms Claude Code on FeatureBench at 70.7%)

For **long-horizon agent coding tasks** (10+ steps, feature development), pair ISCs with two
executable spec types instead of one:

**Architecture Spec** — verifies the implementation chain is complete:
- "Does this feature's call graph include all required sub-requirement implementations?"
- Written as: import graph coverage check, function existence assertions, interface contracts
- Runs at design time, before implementation; catches missing links early

**Behavior Spec** — verifies design-implementation consistency:
- "Does the implemented behavior match the design intent at each step?"
- Written as: behavioral assertions against the actual feature, end-to-end test cases
- Runs after each major implementation milestone, not just at the end

**When to use dual specs:**
- Feature spans 3+ files or modules (single test coverage may miss cross-module contracts)
- Implementation requires a multi-step agent trajectory (sub-agent coding loops)
- Changes are irreversible or expensive to roll back

**Mapping to existing ISA format:**
```markdown
## Dual Spec (for long-horizon agent tasks)

### Architecture Spec ISCs
- [ ] ARCH-1: feature X call graph includes Y, Z, W | falsifier: import graph walk misses any
- [ ] ARCH-2: interfaces between A→B→C match declared contracts | falsifier: type check fails

### Behavior Spec ISCs  
- [ ] BEHAV-1: end-to-end flow produces expected output | falsifier: integration test fails
- [ ] BEHAV-2: edge case Q handled consistently | falsifier: Q input returns unexpected state
```
