---
name: recursive-pr-review-loop
version: 1.0.0
author: Hermes Agent
description: "Use when running recursive PR review until saturation."
keywords:
- pr
- review
- adversarial
- saturation
- graphql
- thread-resolve
platforms:
- linux
triggers:
  - User asks to recursively review open PRs until clean or merged
  - User says 'keep reviewing until approved' or 'fix all PR comments'
  - Running a background autonomous loop that monitors PRs every N minutes
related_skills:
  - pr-review-multi-open
  - adversarial-review
  - github-operations
---

# Recursive PR Review Loop

The class of task: keep all open PRs clean by (a) fixing every reviewer thread as it
arrives and (b) running cold adversarial passes after each fix cycle until two consecutive
passes are both fully clean. This is a loop, not a one-shot review.

## Termination criterion: two-consecutive-clean

Stop when:
1. All open PRs have 0 unresolved threads (verified by fresh GraphQL fetch after each push), AND
2. Two consecutive cold adversarial passes both return `pass` with zero CRITICAL/HIGH/MEDIUM findings.

A single `pass` is NOT sufficient — the second reviewer sees the post-fix commit and can
catch regressions the first round missed. Two consecutive clean checks at different HEAD
commits is the signal.

A `conditional_pass` with only LOW findings is not saturation; run one more round.

## Thread fetch and resolve

Fetch unresolved threads per PR:
```bash
gh api graphql -f query='query($pr:Int!){repository(owner:"OWNER",name:"REPO"){pullRequest(number:$pr){reviewThreads(first:30){nodes{isResolved id comments(first:1){nodes{body}}}}}}}' -F pr=<N> | python3 -c "
import sys, json
d = json.load(sys.stdin)
ts = d['data']['repository']['pullRequest']['reviewThreads']['nodes']
open_t = [t for t in ts if not t['isResolved']]
print(len(open_t), 'unresolved')
for t in open_t:
    print(' ', t['id'], t['comments']['nodes'][0]['body'][:120])
"
```

Resolve after pushing fix:
```bash
for tid in PRRT_kwDO...; do
  gh api graphql -f query="mutation { resolveReviewThread(input: {threadId: \"$tid\"}) { thread { isResolved } } }" >/dev/null && echo "resolved $tid"
done
```

Pitfall: thread IDs (e.g. `PRRT_kwDORF5oBs6i1ZWL`) change per PR and per push. Always
re-fetch after each commit. Never reuse IDs from a prior check.

Pitfall: GraphQL thread resolution and REST thread reply are separate API calls. A reply
does not resolve; a resolve does not reply. Call both explicitly per thread.

## Adversarial pass pattern

### Severity floor progression

Each round's severity floor should drop: CRITICAL → HIGH → MEDIUM → LOW → info → pass.
If a severity reappears after being absent in the prior round, it is a regression
introduced by the fix — treat it as a new finding, not an oscillation.

### Parallel surface split for large codebases

For repos with 5+ distinct module clusters, split into two parallel cold reviewers:

- **Surface A** — core algorithms (math-grounded: interval algebra, d-separation, defeasible
  proofs, SDL logic). Focus: correctness against primary sources and edge cases.
- **Surface B** — pipeline integration (data flow, threshold semantics, boundary contracts,
  eval metrics). Focus: wiring correctness and invariant contracts.

Dispatch both concurrently. Apply Surface A findings first (algorithm bugs have higher
blast radius than wiring bugs).

### Reviewer prompt class-name verification — never skip

Before dispatching a cold reviewer with concrete Python class names, constructor signatures,
or mathematical assertions, verify each against live code:

```bash
python3 -c "import sys; sys.path.insert(0,'src'); import <module>; print([x for x in dir(<module>) if not x.startswith('_')])"
```

A wrong class name causes every reviewer check to fail with ImportError — the round is
wasted. A wrong mathematical assertion (e.g. `D∘D = all-12 relations` when correct is
`{DURING}`) produces a false negative: reviewer says code is wrong when it is correct.

The same rule applies to cron job prompts — verify before scheduling.

### Docstring–code direction mismatch is a HIGH finding

A docstring that describes the OPPOSITE operation from what the code does is HIGH severity
even when the code is correct. Readers build a wrong mental model. Check: for any function
that mutates a graph (backdoor criterion, intervention calculus), verify the docstring
naming matches the code's actual edge direction (outgoing vs incoming) and graph notation.

## Autonomous cron loop

For loops that must run beyond the current session, schedule with:
```
cronjob_manage(action='create', schedule='every 10m', name='<name>', prompt='...')
```

The cron prompt must:
- Track a consecutive-clean counter: read/write `/tmp/pr_clean_counter.txt`
- Stop when counter reaches 2: write `/tmp/pr_loop_done.txt` and exit early
- Re-fetch thread IDs fresh each run (IDs change per push)
- Use `deliver=local` in CLI sessions; `deliver=telegram` for user notification
- Verify all Python class names and mathematical assertions against live code before scheduling
- Include concrete commands (gh auth, targeted pytest suite) — cron has no session context

## Pitfalls

- New reviewer threads appear after each push (automated reviewers re-scan on push).
  Re-check all PRs for unresolved threads after every push, not just at the start.

- Two-consecutive-clean requires two separate commits, not one. The second round must
  review the post-first-fix commit to confirm no regressions were introduced.

- `gh pr view --comments` and GraphQL `reviewThreads` are separate surfaces. Empty
  `--comments` output does NOT mean no review threads. Always run the GraphQL query.

- Bug class: conformal `tau=-inf` coverage check. When calibrate_conformal_threshold
  returns `-inf` (undersized calibration), conformal_coverage_check must return
  `empirical_coverage=1.0`. `sum(s <= -inf)` = 0 is the wrong answer. Fix: add an
  `if math.isinf(tau) and tau < 0` short-circuit before the sum.

- Bug class: budget accumulator corruption by negative inputs. A greedy selection loop
  that adds `candidate.hours` to a running total without validating sign drives the total
  negative, allowing over-budget candidates to pass. Validate `hours >= 0` and finite
  up-front before entering the selection loop.

- Oscillation signal: if round N fix introduces the bug round N-1 fixed, the root design
  is wrong. Find the structurally correct solution; do not patch back and forth.

- strands/optional-dep collection errors are pre-existing. Run targeted test suites
  over changed directories only, not `pytest tests/` which hits unrelated import failures.
