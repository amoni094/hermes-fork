---
name: grill-me
description: >
  Use when: Before starting a task, force a round of sharp clarifying questions to surface fuzzy specs, ambiguous interfaces, missing constraints, and hidden dependencies. Inspired by Matt Pocock's /grill-me technique and used in Squid's /night pipeline. This is the boundary between vibe coding and agentic coding.
version: 1.1.0
triggers:
  - "grill me on this"
  - "grill this spec"
  - "what questions do you have before starting"
  - "ask me everything you need to know"
  - "pressure-test this plan before starting"
  - "what's unclear before you build this"
related_skills:
  - complexity-gated-planning
  - subagent-driven-development
  - autonomous-agent-loop-design
---

# Grill Me

Before starting complex or ambiguous work, run a focused clarification pass that
surfaces everything fuzzy BEFORE the first line of code is written.

> "The /grill-me conversation is the line between vibe coding and agentic coding."
> — Paul Iusztin, Squid

## When to Use

Run grill-me when ANY of these apply:
- The spec is high-level or uses vague terms ("make it better", "improve the flow")
- There are interface decisions that will be hard to change later (schemas, APIs, contracts)
- The feature involves new external dependencies or libraries
- Multiple approaches are plausible and the spec doesn't specify constraints
- The task touches security, auth, or data persistence boundaries
- The user hasn't specified success criteria (how will we know it's done?)

Skip grill-me for:
- Simple, concrete tasks with unambiguous instructions
- Bug fixes where the root cause is already identified
- Tasks you've done before with the same setup

## Material Ambiguity Gate (run before Step 2)

Before generating questions, scan the request for named-but-unverified referents:
any noun that refers to something specific ("the video", "the flywheel we discussed",
"the JSON from last time", "the service we set up") that you have not located on record.

Named-but-unverified referents are always material — the answer changes what gets built.

For each one found, add a targeted question. Hard limit: 3 questions total from this gate.
Locate the referent on record (quick check: session_search, file search, prior context) before asking;
only ask if you genuinely cannot resolve it in one search call. Never infer and build on a referent you haven't confirmed.

These questions count toward the 3-8 total in Step 2. If the referent gate uses 3 questions,
you still have room for 0-5 more content questions. Total cap from Step 2 remains 8.

If no referents are ambiguous, skip this gate and proceed to Step 2 normally.

## How to Run

### Step 1 — Read the full spec

Ingest the complete request, feature description, or task. Read relevant existing files,
ADRs, glossary, and CLAUDE.md/AGENTS.md if they exist.

### Step 2 — Generate sharp questions

Produce 3-8 pointed questions targeting exactly what's fuzzy. Questions must be:

**Sharp** (not generic): "Will this API be called externally or only by internal services?"
NOT "What should the API look like?"

**Consequential**: the answer will materially change the implementation
**Non-obvious**: don't ask for information clearly stated in the spec
**Specific to interfaces**: focus on schema choices, boundary contracts, modularization
  decisions, and dependencies that are hard to change later

Question categories to check:
1. **Interface contracts** — input/output schemas, API shapes, data formats
2. **State and persistence** — what gets stored, where, how long, ownership
3. **Error handling** — what happens when X fails? silent or loud? retry or fail-fast?
4. **Scope boundaries** — what is explicitly OUT of scope for this change?
5. **Success criteria** — how do we verify it's working? what test signals completion?
6. **Performance constraints** — are there latency, concurrency, or throughput requirements?
7. **Security boundaries** — who has access? what inputs are untrusted?
8. **Dependencies** — new libraries? new services? breaking changes to callers?

### Step 3 — Present questions and wait

Present the questions as a numbered list. Wait for answers before starting implementation.

Do NOT:
- Answer your own questions with assumptions
- Start building while waiting
- Present more than 8 questions (forces prioritization)
- Include obvious questions just to seem thorough

### Step 4 — Refine and proceed

After receiving answers:
- Confirm understanding: restate the task with the clarifications incorporated
- Flag any remaining ambiguities as explicit assumptions (not hidden ones)
- Update the spec/task doc if one exists
- Then proceed to implementation

## Example Questions (good)

For a "add user authentication" feature:
1. Is this a new auth system or integrating with an existing identity provider (e.g., OAuth, SAML)?
2. What is the session invalidation model — server-side sessions, JWTs, or cookies?
3. Which routes/endpoints should remain publicly accessible after auth is added?
4. What is the expected failure behavior for expired tokens — redirect to login or return 401?
5. Does this need multi-factor authentication in scope, or is that a later feature?

## Example Questions (bad — too vague)
- "Can you clarify what you mean?" ← not specific enough
- "What should the code look like?" ← too open-ended  
- "Is performance important?" ← almost always yes, this adds nothing

## Integration with /night Pipeline

## Mandatory Pre-Dispatch Gate (Dibran Mulder "Lights Out", Aug 11 2026)
Source: https://dibranmulder.github.io/2026/08/11/lights-out-03-running-the-nightshift/

grill-me should be MANDATORY before any autonomous agent dispatch (delegate_task/cron), not
optional. Production data: pre-flight adversarial questioning + decomposition reduces mid-task
surprises by ~60% in overnight autonomous agent runs.

Wayfinder companion step — after grill-me resolves ambiguities:
1. Decompose into sub-tasks each with: goal, acceptance_criteria, rollback_condition
2. Document conservative assumptions explicitly in the spec
3. Agent receives pre-flight-checked spec, not raw user text

Anti-pattern ("casino developer"): human pressing Enter in real-time to approve each step.
Not scalable for overnight autonomous work; use timeout=deny HITL instead (see mnemosyne-atp-safety).

In multi-agent workflows, run grill-me after the product manager produces the task plan
and before the software engineer begins implementation. The grill-me conversation ensures:
- Every acceptance criterion is verifiable
- Interface decisions are explicit before code is written
- The tester knows what "passing" means before tests are written

The human approves the plan AFTER grill-me, not before — this ensures grill-me's answers
are incorporated into the final plan.
