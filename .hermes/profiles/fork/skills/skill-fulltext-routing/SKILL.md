---
name: skill-fulltext-routing
description: Use when routing among many skills. Full skill text beats description-only routing.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - skill router misses the right skill
  - progressive disclosure hiding skill bodies
  - SkillRouter / SkillsBench routing
  - large overlapping skill registry
  - NOT for writing SKILL.md structure (use hermes-agent-skill-authoring)
metadata:
  hermes:
    tags: [skills, routing, retrieval, progressive-disclosure]
    related_skills: [hermes-semantic-skill-routing, compositional-skill-routing, hermes-agent-skill-authoring]
---

# Full-Text Skill Routing

Source: arXiv:2603.22455 — SkillRouter.

## Finding

On a SkillsBench-derived registry (about 80K overlapping skills), hiding the skill body and routing on name+description only drops Hit@1 by 31-44 points. Full skill text is a first-class routing signal, not metadata.

A compact retrieve-and-rerank (1.2B) beat larger pipelines while using 13x fewer parameters.

## Hermes rule

1. Index bodies (or a structured slice: Overview + When to Use + pitfalls), not descriptions alone.
2. Progressive disclosure is for injection after routing, not for the router itself.
3. Keep routing descriptions short (SkillReducer, arXiv:2603.29919: 48% description compression, less-is-more) but do not starve the index.
4. Overlapping triggers need explicit negative routing ("Not for X, use Y").

## Procedure

1. Embed query against skill body excerpts (first ~2k tokens + headings).
2. Rerank top-k with a small model or lexical overlap on triggers.
3. Inject only the winning skill(s) into the messages layer; keep the system-prompt catalog short.

## Pitfalls

- Description-only omni-index looks cheap and silently misroutes on overlapping skills.
- Compressing descriptions for the catalog is good; deleting body from the index is not.

## Verification

- [ ] Router had access to body text or a body excerpt, not only YAML description
- [ ] Injected skills are a subset of routed winners (no dump of the full library)
