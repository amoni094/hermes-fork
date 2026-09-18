---
name: ponytail-yagni
tier: global
description: >
  Use when enforcing YAGNI/laziness discipline on agent tasks: run the 7-rung laziness ladder before any implementation step to prevent over-engineering. Inspired by DietrichGebert/ponytail (58k stars). Load before any coding, refactoring, or architecture task where scope creep is a risk.
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [yagni, laziness, over-engineering, scope, planning]
  related_skills: [grill-me, complexity-gated-planning, spike]
triggers:
  - Agent is about to add a feature, abstraction, or mechanism not explicitly requested
  - Task scope is creeping beyond what the user actually asked for
  - A proposed solution feels over-engineered relative to the problem size
related_skills:
  - verification-before-completion
  - plan
---

# Ponytail YAGNI Enforcement

Inspired by the ponytail project (DietrichGebert/ponytail) — a cross-agent laziness-ladder
plugin that fires before every tool use and forces you to choose the simplest adequate
solution, not the most elegant one.

## Core principle

Over-engineering is the default failure mode of capable AI agents. The ladder below
is a forcing function: work your way UP from rung 1 and stop at the first rung that
is sufficient. Do not skip to rung 5 because it feels cleaner.

## Academic grounding for the laziness ladder (non-English sources, 2025-2026)

### OAP — Open Agent Passport: declarative pre-action authorization (arXiv 2603.20953)
The PreToolUse interception pattern has been formally studied and measured:
- **53ms median enforcement latency** (N=1,000 tool calls) — negligible overhead
- **Social engineering success: 74.6% without OAP → 0% with OAP policy**
- Architecture: declarative YAML policy → cryptographically signed audit record
- Key improvement over ad-hoc Python conditionals: policy rules are declarative,
  auditable, and versioned — the 7-rung ladder becomes a YAML policy file, not code

OAP YAML policy template (maps each rung to a policy rule):
```yaml
policy:
  - id: rung-0-necessity
    rule: "action MUST address a requirement explicitly stated in the current task"
    action: block
  - id: rung-1-existing
    rule: "IF tool=write_file AND path matches existing file, REQUIRE read_first=true"
    action: challenge
  - id: rung-3-destructive
    rule: "IF tool IN [terminal, patch, write_file] AND scope NOT IN [single_file, single_function]"
    action: require_explicit_scope
  - id: rung-7-minimum
    rule: "implementation MUST pass ponytail minimum-viable-change check"
    action: log
```
(OAP DOI: https://doi.org/10.5281/zenodo.18901596)

### ePCA — executable Proof-Constrained Action (arXiv 2605.29251, USTC)
Chinese institution (Benlong Wu, Weiming Zhang, Kejiang Chen, Han Fang, Nenghai Yu — USTC):
- Forces agents to formalize intentions into first-order logical constraints BEFORE
  executing physical operations. Neural-symbolic isolation architecture.
- **Zero attack success rate, zero false positive rate**
- Rung 0 addition: before any of the 7 rungs fires, require the agent to emit a
  typed predicate:
  ```
  {action: "write", target: "<path>", reason: "<justification>", scope: "single_file"}
  ```
  Validate predicate structure before semantic evaluation. Malformed = reject.

### TS-Guard/TS-Flow (arXiv 2601.10156, PKU/SenseTime)
Yutao Mou et al. (Peking University / SenseTime), GitHub: https://github.com/MurrayTom/ToolSafe
- **TS-Guard**: RL-trained multi-task model, detects unsafe tool invocations via action-
  attack correlation analysis BEFORE execution, <100ms
- **TS-Flow**: guardrail + feedback-driven reasoning loop
- **65% reduction** in harmful tool invocations, **+10%** benign task completion under
  prompt injection
- Maps to the ponytail ladder: TS-Guard's "action-attack correlation" = "Is this change
  defensive/needed-now?" (rung 3/4). TS-Flow's feedback loop = post-rung-rejection reason injection.

### Tsinghua counterpoint: calibration is critical (arXiv 2603.01853)
Tsinghua paper shows "giving agents more freedom with tools outperforms pre-programmed
pipelines by +10.7%". YAGNI enforcement should not block clearly low-risk tasks.
Apply fast-pass at rung 1 for tasks that are: read-only, scoped to a single known file,
and reversible. Fast-pass skips rungs 2-6 and goes directly to rung 7.

## The 7-rung laziness ladder

Before writing any code or proposing any architecture, ask in order:

1. **Does it need to exist at all?**
   - Is this actually required by the current task, or am I gold-plating future needs?
   - If not needed now, STOP. Do not build it.

2. **Can the user/system handle it manually?**
   - Is a one-off manual step acceptable? Document it instead of automating.
   - Cost of manual: low. Cost of wrong automation: high.

3. **Does something already do this?**
   - Check existing tools, skills, scripts, libraries before writing new code.
   - Prefer configuration over new code. Prefer existing skill patch over new skill.

4. **Can it be a dumb script?**
   - A 10-line bash/python script beats a 200-line framework integration.
   - No classes, no abstractions — just sequential logic that works.

5. **Can it be a simple function?**
   - One pure function with clear inputs/outputs. No side effects, no global state.
   - Test it inline. Add structure only when the second function appears.

6. **Can it be a simple module?**
   - A small cohesive file/module with a clear single responsibility.
   - Still no framework, no plugins, no registries.

7. **Only now: a proper system**
   - Multiple modules, plugin architecture, config files, abstractions.
   - Justify why rungs 1-6 were insufficient before proceeding here.

## When to apply this

- Before writing any implementation code
- Before proposing a new skill (is a patch to an existing skill sufficient?)
- Before proposing a new cron job (is a one-off terminal command enough?)
- Before proposing a new MCP server (does an existing tool cover it?)
- Before creating a new database table/entity type (does an existing one fit?)
- Any time you notice yourself thinking "this would be cleaner if..."

## Application within Hermes

Map the ladder to Hermes primitives:

| Rung | Hermes equivalent |
|---|---|
| 1: Not needed | Skip it entirely |
| 2: Manual | Tell the user, document in memory |
| 3: Already exists | Check skill library + existing tools first |
| 4: Dumb script | terminal() one-liner or ~/.hermes/scripts/ bash file |
| 5: Simple function | Single-file Python in ~/.hermes/scripts/ |
| 6: Module | Patch an existing skill vs. creating a new one |
| 7: System | New skill + cron + MCP integration |

## Checklist before any implementation

```
[ ] Rung 1: Does this need to exist at all? (justify if yes)
[ ] Rung 2: Can the user handle this manually once?
[ ] Rung 3: Does an existing tool/skill already do this?
[ ] Rung 4: A 10-line script instead of new architecture?
[ ] Rung 5: A pure function instead of a class hierarchy?
[ ] Rung 6: A patch to an existing skill instead of a new one?
[ ] Rung 7 (only if all above are no): now design a proper system
```

## Pitfalls

- **Abstraction addiction**: Interfaces and base classes are not "clean" if they're
  premature. A copy-paste that works beats a premature abstraction that misleads.
- **"While I'm in here"**: The most dangerous phrase in software. Every "while I'm at
  it" addition should go through the ladder from rung 1.
- **Framework gravitational pull**: Every popular framework makes rung 7 feel like
  rung 3. Check if you're adding a framework dependency vs. a 10-line function.
- **Hermes-specific**: New cron jobs, new skills, new MCP servers, new memory stores
  all have maintenance overhead. The existing set is already large. Default to patching
  before adding.
- **Deletion > Addition**: From Denuto's Ponytail pattern — prefer deleting an existing
  abstraction over adding a new one. A codebase with fewer moving parts is a codebase
  that's easier to audit. Every addition is a future deletion problem.

## Adversarial check on proposed implementations

Before finalizing any proposal, adversarially ask:

- What is the simplest thing that could possibly work?
- Am I solving the stated problem or the problem I imagine will come next?
- If this broke tomorrow, would the user notice or care?
- What is the cost of being wrong about needing this?
