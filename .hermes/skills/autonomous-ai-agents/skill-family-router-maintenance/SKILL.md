---
name: skill-family-router-maintenance
triggers:
  - a skill family or category is being mistaken for a specific action skill
  - the router is loading the wrong skill or the umbrella skill is being used as a terminal action
  - skill routing is producing incorrect or ambiguous matches
  - a skill family lacks a top-level loadable entry point and needs an umbrella router
description: "Use when a skill family/category is being mistaken for a non-loadable namespace and you need to add or repair an umbrella router skill plus the surrounding docs/prompts."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, maintenance, routing, documentation, hermes]
    related_skills: [writing-skills, hermes-agent, verification-before-completion]
related_skills:
  - autonomous-agent-loop-design
  - verification-before-completion
  - writing-skills
  - hermes-agent
---

# Skill Family Router Maintenance

Use this when:
- a prior run failed because `skill_view(name="...")` targeted a category/namespace rather than a real skill
- a skill family exists as many child skills but lacks a top-level entry point
- docs or prompts ambiguously refer to a category as if it were loadable
- you want a stable router skill that loads first and then points to the right specialized child skill

## Goal

Turn an ambiguous skill family into an explicit, loadable routing surface.

## Pressure scenario

Baseline failure:
- the agent calls `skill_view(name="family-name")`
- Hermes returns `Skill 'family-name' not found`
- `skills_list(category="family-name")` reveals the family exists only as child skills
- future sessions repeat the same mistake because docs still talk about the family only as a category

## Workflow

1. Confirm the failure mode.
   - reproduce with `skill_view(name="family-name")` if safe
   - run `skills_list(category="family-name")`
   - inspect the on-disk layout under `~/.hermes/skills/<category>/`

2. Decide whether a router skill is appropriate.
   - create one if the family has multiple child skills and users/agents may reasonably ask for the family by name
   - skip if the family is intentionally just an internal directory with no user-facing top-level meaning

3. Create the router skill.
   - name it exactly as the family/category when possible
   - explain when to use it
   - include fast-routing rules to the most relevant child skills
   - state clearly that it is a router, not the final destination for most tasks

4. Patch nearby local skills.
   - update any local skills that refer to the family ambiguously
   - especially patch dispatcher/orchestration/authoring skills that are likely to load the family
   - add wording like: load `family-name` first when the user asks generally, then route to the concrete child skill

5. Patch repo docs/catalogs if present.
   - bundled skills catalog
   - optional skills catalog
   - skill-authoring guidance if it discusses categories
   - localized mirrors if the repo maintains them

6. Verify readback.
   - `skill_view(name="family-name")` must succeed
   - `hermes skills list` should show the new top-level skill
   - read back patched docs/skills to confirm the new wording landed where intended

## Router skill content checklist

Include:
- clear trigger conditions
- list of likely child skills
- selection heuristics for common user phrasings
- explicit clarification that the family name is both a category and a loadable umbrella skill, if true
- completion rule telling the agent to route onward when a child skill clearly applies

## Good patch targets

Look first at:
- orchestration skills
- delegation/subagent skills
- skill-authoring skills
- family-specific command-reference skills
- docs/reference/skills-catalog.md
- docs/reference/optional-skills-catalog.md
- localized catalog copies

## Verification commands

Typical proof:
- `skill_view(name="family-name")`
- `skills_list(category="family-name")`
- `hermes skills list | grep family-name`
- `read_file(...)` on the patched docs/skills

## Pitfalls

- creating the router skill but forgetting to patch the docs that caused the confusion
- patching only English docs when localized mirrors are present and user-facing
- making the router too generic and not routing to child skills explicitly
- treating the category label itself as proof that a loadable skill exists
- claiming success without verifying `skill_view(name="family-name")` now works

## Completion rule

Do not call this complete until:
- the router skill loads successfully
- at least the most relevant local skill/doc references are patched
- the catalog/authoring surfaces no longer imply the family is only a category
