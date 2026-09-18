---
# ── REQUIRED FIELDS ──────────────────────────────────────────────────────────
name: my-skill-name               # lowercase, hyphens only, ≤64 chars
description: >
  Use when <trigger condition>. <one-line behavior summary>.
  Triggers on `code-symbol`, 'natural phrase', or specific user phrasing.
  Keep ≤1024 chars (MAX_DESCRIPTION_LENGTH enforced by validator).

# ── RECOMMENDED FIELDS ───────────────────────────────────────────────────────
version: 1.0.0                    # SemVer: bump minor for new sections, patch for fixes
author: Hermes Agent              # who wrote / maintains this skill
license: MIT
platforms: [linux, macos, windows]

triggers:                         # bullet list of routing signals (model-readable)
  - Concise trigger condition 1
  - User says "exact phrase" or asks about topic X
  - Situation where this skill applies but a more specific skill does not

metadata:
  hermes:
    tags: [tag1, tag2, tag3]      # short snake-case tags for indexing
    related_skills: [other-skill] # skills that complement or overlap this one
    # Optional docs-only hint (Hermes does NOT auto-route on this field):
    # model: grok-4.5             # see claude-routing-hierarchy; not a live lever
    # user-invocable: false       # set true only if this skill should never be auto-routed
    # argument-hint: '[--flag]'   # document slash-command argument syntax

# ── SSL FRONTMATTER (optional, additive) ─────────────────────────────────────
# SSL = Scheduling-Structural-Logical (arXiv:2604.24026)
# These three blocks disentangle machine-usable evidence from natural language.
# All ssl_ blocks are optional; omit any block you can't fill accurately.

ssl_scheduling:
  # WHEN to invoke this skill and what must be true first.
  triggers:
    # More precise than the top-level triggers — written for automated routing.
    - Condition that unambiguously fires this skill
    - Another distinct firing condition
  preconditions:
    # State that MUST be true before the skill can succeed.
    - Required tool or binary is installed
    - Required file or service exists / is reachable
    - User has provided necessary context (e.g. repo URL, issue number)
  estimated_steps: 5              # rough integer step count for cost/budget estimation

ssl_structural:
  # HOW the skill executes — tools it calls and major phases it goes through.
  tools_used:
    # List every Hermes tool this skill meaningfully relies on.
    - terminal
    - read_file
    - write_file
    - search_files
    - web_search
    - web_extract
    - browser_navigate
    - skill_manage
    # (remove tools that don't apply)
  subtasks:
    # Named phases in execution order. Keep to 3-7 items.
    - Phase 1 — discovery / reconnaissance
    - Phase 2 — core action
    - Phase 3 — verification
    - Phase 4 — cleanup or report

ssl_logical:
  # WHAT changes — side effects, consumed resources, and risk classification.
  side_effects:
    # Every observable state change this skill may produce.
    - Creates file at <path>
    - Calls external API <name>
    - Modifies config at <path>
    - Runs test suite (read-only intent)
  resources:
    # Files, directories, services, or external systems this skill touches.
    - ~/.hermes/skills/
    - External service / API name
    - Local database or config file path
  risk_level: low                 # low | medium | high
  # low    = read-only or creates new files only, fully reversible
  # medium = modifies existing files, calls external APIs, pushes to remotes
  # high   = destructive operations, production systems, irreversible changes
---

# Skill Title

One-sentence summary of what this skill does and when to use it.

## When to Use

<!-- Describe the triggering scenarios in natural language. -->
<!-- Complement the frontmatter triggers — don't just repeat them verbatim. -->

- Scenario A
- Scenario B

**Don't use when:**
- Counter-trigger A (use [other-skill] instead)

## Core Principle / Overview

<!-- The key idea or mental model behind this skill. -->
<!-- Keep it short — one paragraph or a brief list. -->

## Steps

<!-- Numbered steps for the main workflow. -->

1. **Step one** — what to do and why
2. **Step two** — with exact commands or tool calls shown inline
3. **Step three** — verification step

## Pitfalls

<!-- Gotchas, failure modes, and "don't do this" guidance. -->
<!-- This section often has the highest signal-to-noise ratio. -->

- **Pitfall name** — what goes wrong and how to avoid it
- **Another pitfall** — detection signal and fix

## Examples

<!-- Optional: show 1-2 concrete invocations or outputs. -->

## References

<!-- Optional: links to docs, related skills, external resources. -->
- Related skill: [other-skill]
- Docs: https://...
