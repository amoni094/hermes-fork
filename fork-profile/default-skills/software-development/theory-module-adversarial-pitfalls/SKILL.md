---
name: theory-module-adversarial-pitfalls
version: 1.0.0
author: Hermes Agent
description: Use when reviewing theory modules. Cold review bug classes.
keywords:
- theory
- adversarial
- allen-algebra
- deontic
- causal
- active-learning
platforms:
- linux
---

# Theory-Module Adversarial Pitfalls

Use when implementing or reviewing theory-grounded modules (Allen interval algebra,
Pearl causal inference, SDL deontic logic, active learning acquisition functions)
using pure stdlib only. Companion to corpus-driven-module-engineering (default profile).

See `references/bug-classes.md` for the full catalogue with code patterns and fixes.

## Quick-reference checklist (run ALL on cold adversarial review)

1. Hand-authored tables -- verify every entry by ground-truth sampling (see bug-classes.md #1)
2. Entropy/log with eps -- assert boundary p=1.0 returns exactly 0.0, not negative (see #2)
3. SDL duality -- F(p)+F(~p) is a DUAL_OBLIGATION_CONFLICT via F(p)=O(~p) (see #3)
4. String condition matching -- normalise whitespace before == comparison (see #4)
5. First-match classifiers -- provide classify_all_X list variant; export from __init__ (see #5)
6. Backdoor criterion -- G_x^out (cut outgoing) is correct for d-sep test; G_x^in is for do-calculus (see #6)
7. execute_code truncation -- use terminal heredoc or write_file for scripts over ~200 lines (see #7)
8. CTD/Forrester shared predicate -- both must call one _is_contrary_to_duty_pair (see #8)
