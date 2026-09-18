---
name: receiving-code-review
related_skills:
  - requesting-code-review
  - verification-before-completion
  - systematic-debugging

triggers:
  - Review feedback arrives from a human reviewer or CI check and needs rigorous evaluation
  - User says 'I got a review back', 'process the review comments', or 'what do I need to fix'
  - Need to evaluate review feedback before blindly implementing all suggested changes
  - Deciding which review comments to accept, push back on, or partially apply
description: Use when review feedback arrives and you need to evaluate it rigorously before implementing changes.
version: 1.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, feedback, verification, rigor]
    related_skills: [requesting-code-review, verification-before-completion, systematic-debugging]
---

# Receiving Code Review

Evaluate feedback technically before acting on it.

## Sequence

1. Read all feedback first.
2. Restate unclear items in technical terms.
3. Verify each claim against the actual codebase.
4. Implement only verified, understood changes.
5. Re-test after each meaningful fix.

## Rules

- no performative agreement
- no blind implementation
- ask for clarification before partial execution if items are ambiguous and coupled
- push back plainly when a suggestion is wrong for this codebase
- if external feedback conflicts with prior user decisions, stop and surface that conflict

## Good acknowledgement

Use short factual responses like:
- `Fixed: ...`
- `Verified; updating ...`
- `Need clarification on items 2 and 4 before changing code.`

Actions and proof matter more than social filler.