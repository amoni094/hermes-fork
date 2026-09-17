# Sweep 30 — arXiv >2608.27454, Aug/Sep 2026

Cutoff after Sweep 29: **2608.27454**. New cutoff after Sweep 30: **2608.27454** (unchanged; multi-source sweep surfaces older IDs from new sources — no new IDs above 2608.27454 found)  
Sources: arXiv cs.AI/CL/MA/LG/IR/SE, Semantic Scholar, OpenAlex, AMiner (zh), J-STAGE (ja), HAL (fr), CyberLeninka (ru), HuggingFace Papers, Papers With Code.

## HIGH Priority — Implemented

| arXiv ID | Title | Target | Status |
|---|---|---|---|
| 2608.02464 | TrajectorysentinelL: Echo-State-Network failure detection + rollback/replay | agent-runtime-loop-patterns, verification-before-completion | Done |
| 2608.23552 | Prime Agent: Harness separation (exec/recovery/verify/resource) + Continual Harness + recursive subagent typed JSON comms | autonomous-agent-loop-design | Done |
| 2602.21806 | Framework Bugs v4: 76% Incorrect Functionality; root causes API(31%)/config(22%)/parsing(18%)/trace(14%) | agent-task-signoff | Done |

## MED Priority — Recorded (next sweep)

| arXiv ID | Title | Target | Status |
|---|---|---|---|
| 2608.16447 | HaReCAP: Compile frequent leaf decisions into one-step reflex rules; 14-20% token reduction | agent-runtime-loop-patterns | Noted |
| 2608.20314 | MidTool: Tool affordance recognition + argument grounding + workflow composition + error recovery via mid-training | model-selection notes | Noted |
| 2601.12294 | ToolPRMBench: Step-level PRMs for tool-using agents; specialized PRMs outperform general ones | evaluation-driven-development | Noted |

## Summary of Changes

### agent-runtime-loop-patterns
Added TrajectorysentinelL section: echo-state-network 1-class failure classifier (fits on CPU in <1s),
CUSUM change detector for drift, rollback+replay recovery pattern (45% failure recovery,
52%→73% success lift). Key Hermes implication: deterministic recomputation replaces LLM judge.

### verification-before-completion
Added Sweep 30 section: TrajectorysentinelL deterministic verification checklist —
recompute expected tool outputs, verify required calls made, compare pre/post state hashes.
Rollback entry point: last verified tool output, not start of session.

### autonomous-agent-loop-design
Added Prime Agent section: harness-four-responsibilities pattern (exec/recovery/verify/resource),
Continual Harness (persistent REPL across trajectories), recursive subagent typed JSON comms.
Hermes mapping: delegate_task output_schema validation, background terminal as persistent REPL,
hard-stop guard at N iterations.

### agent-task-signoff
Added Framework Bugs v4 section: framework-bug row added to sign-off table checklist.
Four checks: API contract, config match, serialization boundary, trace fidelity.
Required for any agentic run using 2+ distinct tools or 2+ sequential tool calls; N/A allowed for single-tool tasks with one-line justification.

## Sweep Notes

- Sweep script now covers HuggingFace Papers, Papers With Code, Crossref, Korean (RISS via OpenAlex Korean-lang filter) — new sources added in this sweep cycle
- arXiv HTML search now runs all 5 queries per category (was 3); Semantic Scholar all 5 (was 2)
- Multilingual queries expanded: Chinese 6 queries, Japanese 4, French 4, Russian 4
- Raw sweep output: 420 unique papers (before agent-relevance filtering); 75 after filtering
- Dominant noise sources: Crossref medical/physics papers (remove by adding domain filter to crossref fetch)
- Action item for sweep 31: tighten Crossref query to `agent OR "LLM" OR "language model"` and add `field_of_study=computer-science` filter
