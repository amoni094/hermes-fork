---
name: compositional-skill-routing
description: Use when a task needs multiple skills. Decompose, retrieve per subtask, then compose.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - task needs more than one skill
  - SkillWeaver / CompSkillBench
  - iterative skill-aware decomposition
  - composing MCP / tool skills into a DAG
  - NOT for single-skill load (use skill-fulltext-routing)
metadata:
  hermes:
    tags: [skills, routing, composition, decomposition]
    related_skills: [skill-fulltext-routing, hermes-semantic-skill-routing, workflow-map]
---

# Compositional Skill Routing

Source: arXiv:2606.18051 — SkillWeaver: Decompose, Retrieve, and Compose.

## Finding

Real tasks need several skills. Naive LLM decomposition only hits 34% category recall at the step level. One round of skill-aware decomposition (retrieve available skills, then re-decompose) lifts accuracy 51% to 68%. Correct granularity is the prerequisite for retrieval.

Context savings: retrieve per subtask instead of stuffing the library (over 99% context reduction in the paper).

## Procedure

1. Draft atomic sub-tasks (too coarse is the common failure).
2. Retrieve candidate skills per sub-task (full-text index — see skill-fulltext-routing).
3. If a sub-task matches nothing well, re-split or rephrase it against the skill catalog — do not force a bad skill.
4. Compose a DAG: depends_on order, no composite skill before its prerequisites.

## Pitfalls

- One-shot decomposition that names capabilities Hermes does not have.
- Loading every maybe-relevant skill just in case (destroys the context saving).

## Verification

- [ ] Each loaded skill maps to a named sub-task
- [ ] At least one decompose-then-retrieve feedback loop if the first pass was sparse
