---
name: brainstorming
description: Use when the user wants exploration, option generation, or requirements convergence before planning or implementation.
version: 1.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [brainstorming, requirements, clarification, ideation]
    related_skills: [using-superpowers, plan, plan]
---

# Brainstorming

Use this before planning when the problem space is still open.

## Goals

- surface assumptions
- generate 2-4 concrete options
- identify constraints, tradeoffs, and unknowns
- converge on one direction before implementation

## Hermes process

1. Restate the problem in one sentence.
2. Gather constraints from current files, repo state, and user request before asking anything avoidable.
3. Present a compact option set with tradeoffs.
4. Use `clarify` only when the choice meaningfully changes the build path.
5. End with a selected direction or a crisply framed decision still needed.

## Output shape

- Problem
- Constraints
- Options
- Recommendation
- Open decision, if any

## Red flags

Do not brainstorm forever. Once a path is good enough, switch to `plan`.