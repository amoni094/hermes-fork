---
name: brainstorming
provides: [reasoning]
related_skills:
  - using-superpowers
  - plan
  - complexity-gated-planning

triggers:
  - user says 'brainstorm', 'think through', 'what are my options', or 'explore ideas'
  - open-ended divergent thinking task is needed before committing to a plan
  - problem space is still unclear and 2-4 concrete options need to be surfaced
  - user wants to surface assumptions, constraints, and tradeoffs before implementation
description: Use when the user wants exploration, option generation, or requirements convergence before planning or implementation.
version: 1.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [brainstorming, requirements, clarification, ideation]
    related_skills: [using-superpowers, plan, complexity-gated-planning]
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