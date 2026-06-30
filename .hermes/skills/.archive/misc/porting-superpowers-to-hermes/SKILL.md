---
name: porting-superpowers-to-hermes
description: Use when adapting an upstream Superpowers workflow or skill set into Hermes and you need a repeatable porting process.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [superpowers, hermes, porting, skills, harness]
    related_skills: [writing-skills, using-superpowers, hermes-agent]
---

# Porting Superpowers to Hermes

Reusable meta-skill for adapting upstream Superpowers content into Hermes.

## Invariants

1. Preserve upstream workflow shape whenever possible.
2. Keep skills action-oriented; avoid baking harness-specific tool names into shared logic unless the skill is explicitly Hermes-only.
3. Reuse existing Hermes skills instead of cloning them under a new name when behavior already matches.
4. Add the thinnest possible Hermes-specific wrapper for missing concepts.
5. Verify with live Hermes skill tooling, not just file presence.

## Procedure

1. Read the upstream skill or harness-porting doc.
2. Separate harness-agnostic behavior from harness-specific bootstrap/tool mapping.
3. Inventory existing Hermes skills that already satisfy part of the workflow.
4. Decide which names need true local wrappers for discoverability or compatibility.
5. Write concise Hermes-native skills plus any heavy references under `references/`.
6. Verify with `skills_list`, `skill_view`, and direct file inspection.
7. Patch stale or misleading descriptions immediately.

## Deliverables

- skill set under a coherent category
- explicit tool-mapping notes
- explicit bootstrap guidance
- verification proof that Hermes can discover and read the port

## Warning

Do not claim a true auto-bootstrap unless the harness really injects the bootstrap at session start. In Hermes, an explicitly preloaded bootstrap skill is honest; a fake automatic claim is not.
