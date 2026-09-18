# Research Reference Log Sync — 2026-08-31

Pattern for keeping `~/hermes-config/research/` in sync with arXiv sweep findings.
This is the ONGOING SYNC pattern — distinct from initial creation (see SKILL.md §Adding a research/ directory).

## Trigger phrase

"make sure you keep the research reference log updated in hermes-config"
"update the research files in the git repo"
"sync research findings to hermes-config"

Note: user distinguishes "hermes-config" (the git repo at ~/hermes-config/) from
"~/.hermes/skills/research/arxiv-sweep-findings/" (the live sweep bank).
When told to update the research reference log, target the git repo — not the skill.

## Source of truth

ArXiv sweep findings: `~/.hermes/skills/research/arxiv-sweep-findings/references/`
Files: sweep-N.md for each sweep. Check the SKILL.md description for last sweep number
or read memory: "arXiv last=sweep N; cutoff <ID>+"

Git research files: `~/hermes-config/research/`
Files: agent-memory-systems.md, agent-optimization.md, multi-agent-workflows.md,
       neurosymbolic-ai.md, llm-routing-and-efficiency.md, README.md

## Step-by-step sync workflow

1. Read `~/hermes-config/research/README.md` — check "Last updated" date and arXiv cutoff.
2. List sweep files: `ls ~/.hermes/skills/research/arxiv-sweep-findings/references/`
3. Identify sweeps AFTER the last-updated date.
4. Read each new sweep-N.md in order (batch where possible).
5. For each HIGH/MED paper in the sweeps, map to the correct topic file (see table below).
6. Append an `## August <YYYY> Additions (Sweeps N–M, arXiv ≤<cutoff>)` section to each
   topic file that has new findings. Use one section per month-batch, not one section per sweep.
7. Update `research/README.md`:
   - Coverage dates: update "Last updated" and arXiv cutoff.
   - Add sweep range to the coverage dates line.
   - Extend Key Themes if a new cross-cutting pattern emerged.
8. Run `python3 scripts/validate_repo.py` from `~/hermes-config`.
9. `git add research/ && git diff --cached --stat`
10. Commit with format: `research: update reference log to <Month YYYY> (sweeps N-M, cutoff <ID>)`
    Multi-line body: topic file → what was added (paper names / arXiv IDs).

## Topic file → paper mapping rules

| Topic file | What goes here |
|---|---|
| agent-memory-systems.md | Memory architectures, WM/episodic split, context binding, retrieval routing, calibration of memory confidence, memory security, plan-from-memory |
| agent-optimization.md | Skill learning/evolution/lifecycle, harness design, self-improvement loops, harness failure recovery, observability, operator/executor split |
| multi-agent-workflows.md | Coordination topology, multi-agent safety, prompt injection, capability governance, handoff/constraint patterns, intent drift, authorization gaps, debug log exposure |
| llm-routing-and-efficiency.md | LLM routing, KV-cache, context compression, speculative decoding, CoT reduction, OODA/step-level guards, belief calibration, pre-execution guards, resource-aware scheduling, governance primitives |
| neurosymbolic-ai.md | NeSy paradigms, theorem proving, formal verification, constraint generation, symbolic feedback loops |

Papers that span two areas (e.g. a harness paper that also covers multi-agent safety):
put the primary finding in the most specific file, add a one-line cross-reference note in the other.

## Entry format per paper

```
### <ShortTitle> — <subtitle or key concept> (<arXiv ID or source>)
- **arXiv:** <ID> | <Month YYYY> [| <venue if known>]
- <1-2 sentence description of the finding. Focus on the mechanism, not the abstract.>
  <Optional second sentence: specific metric or comparison if it's meaningful.>
- **Application:** <how it maps to Hermes scripts/config/skills — be specific>
  [Config: `config.yaml: <key>`] [Script: `<name>.py`] [Skill: `<skill-name>`]
```

Skip papers marked SKIP in the sweep file. Include Noted papers only if they have
a concrete future evaluation trigger.

## README.md update format

Coverage dates block (replace entire block):
```
## Research Coverage Dates
- English academic: 2024–<Month YYYY> (arXiv cutoff <ID>)
- Non-English venues: 2023–<Month YYYY> (multilingual sweep through Sweeps N–M)
- arXiv sweeps: 8–<last_sweep> (cutoff <ID>+); sources: arXiv cs.AI/CL/MA/LG/CR/SE, GitHub trending,
  Hacker News, Zenn.dev, Habr, Juejin, ACL <YYYY>, ICLR <YYYY>
- Last updated: <Month YYYY>
```

Key Themes: extend an existing theme's subsection with "<Month YYYY> additions:" bullet list
when new sweeps add materially to that theme. Only add a new Key Theme block if the
new findings genuinely introduce a theme not already covered.

## Commit from this session (2026-08-31)

Sweeps applied: 26–29 (cutoff 2608.27454+)
Commit: 46d7863

Files updated:
- agent-memory-systems.md: Recuris WM split, BCIT context binding, GraphMemix query routing,
  calibration flag, Synapse plan-from-memory, failed-trajectory tagging, lemmalog (noted)
- agent-optimization.md: WikiSkill, PILOT live improvement, JIT-Agent, SKILL.state, CaSKG,
  AutoSaddler, CritICL, observer token overrun, SGA-MCTS planner/executor split
- multi-agent-workflows.md: Interaction Tax, Agent Mesh circuit-breakers, tool output
  authorization, intent drift detection, constraint weakening, handoff tax, NL permission
  4-tuples, debug log memory exposure
- llm-routing-and-efficiency.md: OODA-Tool, Paritok compression, belief miscalibration,
  StepGuard, PeakBench, Five Governance Primitives, HarnessLens, CatchBench PRE/LIVE/POST
- README.md: coverage dates → Aug 2026 (cutoff 2608.27454, sweeps 8–29), multi-agent
  safety theme additions block

## Common pitfalls

- Don't confuse the sweep bank (`~/.hermes/skills/research/arxiv-sweep-findings/references/`)
  with the git research log (`~/hermes-config/research/`). They serve different purposes:
  sweep bank = operational implementation log; git research log = sanitized knowledge export.
- Sweeps may have duplicate papers across runs (same ID applied in two sweeps). The git log
  only needs one entry per paper; skip duplicates.
- Papers marked SKIP in the sweep file are SKIP in the git log too — don't include them
  because the sweep triage was thorough.
- The sweep bank's "Applied" status refers to Hermes scripts/config, not to the git log.
  Papers implemented as config/scripts should still be documented in the git log (they're findings).
- After large sweep batches, use `grep -n '2608\.' research/*.md` to check for duplicate IDs
  before committing.
