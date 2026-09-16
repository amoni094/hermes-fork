---
name: plan
related_skills:
  - workflow-map
  - complexity-gated-planning
  - isolated-workspace-preflight
  - subagent-driven-development
  - test-driven-development
  - requesting-code-review
  - verification-before-completion

tier: global
provides: [planning]
triggers:
  - User says 'write a plan', 'plan this out', or 'make a plan before we start'
  - Need to produce an actionable markdown plan in .hermes/plans/ before any execution
  - Need to write bite-sized steps, exact paths, and completion criteria into a plan file before acting
  - Want to separate planning from execution — plan first, execute later
description: >
  Use when writing a markdown plan to .hermes/plans/ with no execution. Bite-sized tasks, exact paths, complete code. Not for deciding whether to plan (use complexity-gated-planning). Not for five-stage task routing (use problem-solving-router).
version: 2.0.0
author: Hermes Agent (writing-craft adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, plan-mode, implementation, workflow, design, documentation]
    related_skills: [workflow-map, complexity-gated-planning, isolated-workspace-preflight, subagent-driven-development, test-driven-development, requesting-code-review, verification-before-completion]
ssl_scheduling:
  triggers:
    - User says 'write a plan', 'plan this out', or 'make a plan before we start'
    - Task is large enough to require bite-sized steps, exact paths, and completion criteria
    - Need to separate planning from execution — plan first, execute later
  preconditions:
    - User has not yet asked for execution (plan mode only)
    - Sufficient context about the task goal and constraints exists
  estimated_steps: 6
ssl_structural:
  tools_used: [write_file, read_file, search_files, terminal]
  subtasks:
    - Clarify scope, constraints, and success criteria
    - Break task into bite-sized numbered steps with exact paths
    - Specify completion criteria per step
    - Write plan to .hermes/plans/<slug>.md
    - Present plan for user approval before any execution
ssl_logical:
  side_effects:
    - Creates a markdown plan file in .hermes/plans/
  resources:
    - .hermes/plans/ directory
  risk_level: low
---

# Plan Mode

Use this skill when the user wants a plan instead of execution.

## Core behavior

For this turn, you are planning only.

- Do not implement code.
- Do not edit project files except the plan markdown file.
- Do not run mutating terminal commands, commit, push, or perform external actions.
- You may inspect the repo or other context with read-only commands/tools when needed.
- Your deliverable is a markdown plan saved inside the active workspace under `.hermes/plans/`.

## Output requirements

Write a markdown plan that is concrete and actionable.

Include, when relevant:
- Goal
- Current context / assumptions
- Proposed approach
- Step-by-step plan
- Files likely to change
- Tests / validation
- Risks, tradeoffs, and open questions

If the task is code-related, include exact file paths, likely test targets, and verification steps.

## Save location

Save the plan with `write_file` under:
- `.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md`

Treat that as relative to the active working directory / backend workspace. Hermes file tools are backend-aware, so using this relative path keeps the plan with the workspace on local, docker, ssh, modal, and daytona backends.

If the runtime provides a specific target path, use that exact path.
If not, create a sensible timestamped filename yourself under `.hermes/plans/`.

## Interaction style

- If the request is clear enough, write the plan directly.
- If no explicit instruction accompanies `/plan`, infer the task from the current conversation context.
- If it is genuinely underspecified, ask a brief clarifying question instead of guessing.
- After saving the plan, reply briefly with what you planned and the saved path.

---

# Writing the Plan Well

The rest of this skill is the craft of authoring a *good* implementation plan — the content that goes inside the markdown file above.

## Overview

Write comprehensive implementation plans assuming the implementer has zero context for the codebase and questionable taste. Document everything they need: which files to touch, complete code, testing commands, docs to check, how to verify. Give them bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume the implementer is a skilled developer but knows almost nothing about the toolset or problem domain. Assume they don't know good test design very well.

**Core principle:** A good plan makes implementation obvious. If someone has to guess, the plan is incomplete.

## When a Full Implementation Plan Helps

**Always use before:**
- Implementing multi-step features
- Breaking down complex requirements
- Delegating to subagents via subagent-driven-development

**Don't skip when:**
- Feature seems simple (assumptions cause bugs)
- You plan to implement it yourself (future you needs guidance)
- Working alone (documentation matters)

## Bite-Sized Task Granularity

**Each task = 2-5 minutes of focused work.**

Every step is one action:
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step

**Too big:**
```markdown
### Task 1: Build authentication system
[50 lines of code across 5 files]
```

**Right size:**
```markdown
### Task 1: Create User model with email field
[10 lines, 1 file]

### Task 2: Add password hash field to User
[8 lines, 1 file]

### Task 3: Create password hashing utility
[15 lines, 1 file]
```

## Plan Document Structure

### Header (Required)

Every plan MUST start with:

```markdown
# [Feature Name] Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

### Task Structure

Each task follows this format:

````markdown
### Task N: [Descriptive Name]

**Objective:** What this task accomplishes (one sentence)

**Files:**
- Create: `exact/path/to/new_file.py`
- Modify: `exact/path/to/existing.py:45-67` (line numbers if known)
- Test: `tests/path/to/test_file.py`

**Step 1: Write failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 2: Run test to verify failure**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: FAIL — "function not defined"

**Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 4: Run test to verify pass**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Writing Process

### Step 1: Understand Requirements

Read and understand:
- Feature requirements
- Design documents or user description
- Acceptance criteria
- Constraints

### Step 2: Explore the Codebase

Use Hermes tools to understand the project:

```python
# Understand project structure
search_files("*.py", target="files", path="src/")

# Look at similar features
search_files("similar_pattern", path="src/", file_glob="*.py")

# Check existing tests
search_files("*.py", target="files", path="tests/")

# Read key files
read_file("src/app.py")
```

### Step 3: Design Approach

Decide:
- Architecture pattern
- File organization
- Dependencies needed
- Testing strategy

### Step 4: Write Tasks

Create tasks in order:
1. Setup/infrastructure
2. Core functionality (TDD for each)
3. Edge cases
4. Integration
5. Cleanup/documentation

### Step 5: Add Complete Details

For each task, include:
- **Exact file paths** (not "the config file" but `src/config/settings.py`)
- **Complete code examples** (not "add validation" but the actual code)
- **Exact commands** with expected output
- **Verification steps** that prove the task works

### Step 6: Review the Plan

Check:
- [ ] Tasks are sequential and logical
- [ ] Each task is bite-sized (2-5 min)
- [ ] File paths are exact
- [ ] Code examples are complete (copy-pasteable)
- [ ] Commands are exact with expected output
- [ ] No missing context
- [ ] DRY, YAGNI, TDD principles applied

## Principles

### DRY (Don't Repeat Yourself)

**Bad:** Copy-paste validation in 3 places
**Good:** Extract validation function, use everywhere

### YAGNI (You Aren't Gonna Need It)

**Bad:** Add "flexibility" for future requirements
**Good:** Implement only what's needed now

```python
# Bad — YAGNI violation
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.preferences = {}  # Not needed yet!
        self.metadata = {}     # Not needed yet!

# Good — YAGNI
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
```

### TDD (Test-Driven Development)

Every task that produces code should include the full TDD cycle:
1. Write failing test
2. Run to verify failure
3. Write minimal code
4. Run to verify pass

See `test-driven-development` skill for details.

### Frequent Commits

Commit after every task:
```bash
git add [files]
git commit -m "type: description"
```

## /wayfinder — Fog-of-War Planning Pattern (Latent Space, Aug 20 2026, Sweep 20) <!-- why: upfront comprehensive plans are brittle on greenfield tasks; incremental fog-of-war exploration with a map document scales to overnight multi-agent runs -->

"Skills ARE context management" (Matt Pocock, 220k GitHub stars). A skill defines what context the agent needs — every skill design decision is a context management decision.

**Fog-of-war**: don't plan everything upfront. Agent explores like an RTS map — each decision reveals the next. Plan only for the current visible area.

**Map document**: a persistent markdown file tracking explored territory, decisions made (not to re-explore), current frontier, and open decisions. This IS the session handoff artifact for AFK/overnight runs.

**Ticket types** (spawn from the map):
- `grill` → clarify before building (use `grill-me` skill)
- `prototype` → throwaway spike to push the fog (use `spike` skill)
- `research` → information gather (use `domain-research-synthesis`)
- `task` → concrete build item once fog is clear (use `complexity-gated-planning`)

**Ubiquitous language**: define domain terms precisely in the map document once. Consistent leading words reduce hallucination — the map's terminology becomes the domain language for the entire task.

Hermes: the map document lives in `.hermes/plans/` and persists to Obsidian for multi-session AFK runs.

## Common Mistakes

### Vague Tasks

**Bad:** "Add authentication"
**Good:** "Create User model with email and password_hash fields"

### Incomplete Code

**Bad:** "Step 1: Add validation function"
**Good:** "Step 1: Add validation function" followed by the complete function code

### Missing Verification

**Bad:** "Step 3: Test it works"
**Good:** "Step 3: Run `pytest tests/test_auth.py -v`, expected: 3 passed"

### Missing File Paths

**Bad:** "Create the model file"
**Good:** "Create: `src/models/user.py`"

## Integration with Other Skills

After plan is written and before implementation starts:
  - Run select-frameworks to determine reasoning gates for the implementation phase:
    ```
    python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
      --task "<plan goal>" --level <L>
    ```
    Embed the primary framework list in each subagent context packet.
  - For multi-phase plans, embed subplan-verify checkpoints at phase boundaries.
    `--plan` / `--subplan` MUST be a JSON list of step strings or objects with a
    `text`/`step`/`name` field. Example:
    ```
    python3 ~/.hermes/scripts/working-memory.py subplan-verify \
      --session SESSION --subplan '["implement parser","run tests","write report"]' \
      --current-step "run tests"
    ```
    Invalid JSON or a non-list that cannot be wrapped → exit 2 BLOCK.
    Constraint violation = do not advance to next phase; re-plan the current step.

**complexity-gated-planning:** Use this first to decide whether a full written plan is warranted, or whether a lightweight checklist / direct execution is enough. Reserve this full plan format for medium-to-high complexity work.

**isolated-workspace-preflight:** When the plan implies risky or multi-file repo changes, note whether the implementer should start in Hermes worktree mode or another isolated workspace before editing.

**verification-before-completion:** Every plan should include concrete verification steps that produce fresh evidence, not just implementation steps.

**requesting-code-review:** Use this after implementation, before commit/push, when the plan results in code changes that need an independent quality pass.

After saving the plan, offer the execution approach:

**"Plan complete and saved. Ready to execute using subagent-driven-development — I'll dispatch a fresh subagent per task with two-stage review (spec compliance then code quality). Shall I proceed?"**

When executing, use the `subagent-driven-development` skill:
- Fresh `delegate_task` per task with full context
- Spec compliance review after each task
- Code quality review after spec passes
- Proceed only when both reviews approve

## Remember

```
Bite-sized tasks (2-5 min each)
Exact file paths
Complete code (copy-pasteable)
Exact commands with expected output
Verification steps
DRY, YAGNI, TDD
Frequent commits
```

**A good plan makes implementation obvious.**
