---
name: spike
provides: [reasoning]
triggers:
  - User says 'spike this', 'throwaway experiment', or 'validate before building'
  - Uncertainty about feasibility — test a hypothesis with a minimal prototype first
  - User says 'is this even possible', 'compare A vs B approach', or 'spike next'
description: >
  Throwaway experiments to validate feasibility before committing to a build.
  Use when: 'spike this', 'throwaway experiment', 'validate before building',
  'is this even possible', 'compare A vs B'. Not for production-path work
  (use workflow-map/plan/SDD), docs-only questions (just search), tracer-bullet
  code meant to survive, or before/after agent evals before merge (use
  evaluation-driven-development). Triggers on 'spike this', 'is X even feasible',
  'throwaway prototype', 'compare approaches'.
version: 1.2.0
author: Hermes Agent (adapted from gsd-build/get-shit-done)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [spike, prototype, experiment, feasibility, throwaway, exploration, proof-of-concept]
    related_skills: [subagent-driven-development, plan, verification-before-completion, workflow-map]
routing_signals: >
  Use for: throwaway experiments, feasibility questions, proof of concept, comparing
  approaches before building, 'is X even possible', 'quick prototype of Z',
  'before I commit to Y', 'spike next', time-boxed exploration, invalidation testing.
  Not for: production implementation (use workflow-map), reading docs to answer a
  question (just search), tracer-bullet code meant to survive, MVP scoping (use plan).
related_skills:
  - verification-before-completion
  - plan
  - subagent-driven-development
  - workflow-map
---

# Spike

Use this skill when the user wants to **feel out an idea** before committing to a real build — validating feasibility, comparing approaches, or surfacing unknowns that no amount of reading will answer. Spikes are disposable by design: throw them away once they've paid their debt.

## When NOT to use this

- The answer is knowable from docs or reading code — just search, don't build
- The work is production path — use `workflow-map` → `plan` or `SDD`, not spike
- The idea is already validated — jump straight to implementation
- You want code that survives into production — that's a tracer bullet, not a spike. Spikes are always thrown away.

## Time-box

<!-- why: spikes that grow past their time-box become shadow implementations that are hard to discard; agent-operable checkpoints catch overrun mid-session -->

Declare the time-box in the README header **before writing any code**. Record start with `date` so the overrun is detectable:

```bash
echo "Time-box start: $(date -Iminutes)  Budget: 1 day"
```

Default budgets (agent turns are a secondary proxy — use whichever expires first):

| Spike complexity | Default budget | Hard ceiling | Approx. tool turns |
|-----------------|---------------|--------------|---------------------|
| Single simple question | 2-4 hours | 8 hours | ~15 turns |
| Standard feasibility question | 1 day | 2 days | ~30 turns |
| Complex multi-library comparison | 2-3 days | 4 days | ~60 turns |

If the budget expires and the question is still open: **stop**, write a PARTIAL verdict with what you learned, and propose a narrower follow-up spike. Do not extend silently. If the user explicitly extends, record the new deadline in the README.

<!-- why: '1 sprint' is undefined for an agent with no calendar; hard ceilings in days and turn counts are the only agent-operable signals -->

If you've exceeded ~30 tool turns on a single spike without a verdict, treat it as overrun and stop.

## If the user has the full GSD system installed

If `skill_view(name='gsd-spike')` returns successfully, prefer **`gsd-spike`** for the full GSD workflow (persistent `.planning/spikes/` state, MANIFEST tracking, Given/When/Then verdict format). This skill is the standalone fallback when GSD is absent.

## Core method

<!-- why: every spike needs a loop not a checklist; the loop structure prevents skipping the verdict step when a result looks good enough at the build stage -->

Regardless of scale, every spike follows this loop:

```
decompose  →  research  →  build  →  verdict
   ↑__________________________________________↓
                  iterate on findings
```

### 1. Decompose

<!-- why: decomposing catches the failure mode of one giant spike that conflates multiple kill-criteria, making the verdict ambiguous -->

If the user's request contains **multiple independent kill-criteria**, break them into separate spikes. If the user asks one concrete feasibility question, take it as a single spike — do not invent a decomposition.

Present spikes as a table with Given/When/Then framing:

| # | Spike | Validates (Given/When/Then) | Risk |
|---|-------|----------------------------|------|
| 001 | websocket-streaming | Given a WS connection, when LLM streams tokens, then client receives chunks < 100ms | High |
| 002a | pdf-parse-pdfjs | Given a multi-page PDF, when parsed with pdfjs, then structured text is extractable | Medium |
| 002b | pdf-parse-camelot | Given a multi-page PDF, when parsed with camelot, then structured text is extractable | Medium |

**Spike types:**
- **standard** — one approach answering one question
- **comparison** — same question, two or more approaches (shared number, letter suffix `a`/`b`). Credible alternative libraries always become comparison spikes (separate dirs, separate verdicts, head-to-head at end) — not variants collapsed inside one spike dir.

**Good spike questions:** specific feasibility with observable output.
**Bad spike questions:** too broad, no observable output, or just "read the docs about X".

**Order by risk.** The spike most likely to kill the idea runs first. No point prototyping the easy parts if the hard part doesn't work.

<!-- why: risk-first ordering saves total time; if the highest-risk spike fails, later spikes are abandoned without cost -->

### 2. Align (for multi-spike ideas)

<!-- why: user may know which spike is highest risk; skipping align on multi-spike work wastes effort if the blocker spike fails; align must be a real turn-boundary to avoid same-turn consent traps -->

Present the spike table and **end the turn**. Ask: "Build all in this order, or adjust?" Proceed only after an explicit user reply (including "go ahead"). Do not interpret silence as consent.

### 3. Research (per spike, before building)

<!-- why: skipping research causes the agent to pick a library or approach it knows rather than the best available one; the research step is the minimum viable due diligence -->

Spikes are not research-free — you research enough to pick the right approach, then you build. Per spike:

1. **Brief it.** 2-3 sentences: what this spike is, why it matters, key risk.
2. **Surface competing approaches** if there's real choice:

   | Approach | Tool/Library | Pros | Cons | Status |
   |----------|-------------|------|------|--------|
   | ... | ... | ... | ... | maintained / abandoned / beta |

3. **Pick one.** State why. If two are credible, they become a comparison spike (separate dirs, head-to-head) — not variants inside one dir.
4. **Skip research** for pure logic with no external dependencies.

Use Hermes tools for the research step:

- `web_search("python websocket streaming libraries")` — undated; let recency signal come from results
- `web_extract(urls=["https://websockets.readthedocs.io/..."])` — read actual docs (returns markdown)
- `terminal("pip show websockets | grep Version")` — check what's installed in the project venv

For libraries without docs pages, read their `README.md` / `examples/` via `read_file`.

### 4. Build

<!-- why: one directory per spike prevents shared state from corrupting comparison results and makes it safe to delete a failed spike without touching others -->

One directory per spike. Keep it standalone.

```
spikes/
├── 001-websocket-streaming/
│   ├── README.md
│   └── main.py
├── 002a-pdf-parse-pdfjs/
│   ├── README.md
│   └── parse.js
└── 002b-pdf-parse-camelot/
    ├── README.md
    └── parse.py
```

**Bias toward something the user can interact with.** Spikes fail when the only output is a log line that says "it works." The user wants to *feel* the spike working. Default choices, in order of preference:

1. A runnable CLI that takes input and prints observable output
2. A minimal HTML page that demonstrates the behavior
3. A small web server with one endpoint
4. A unit test that exercises the question with recognizable assertions

**Depth over speed.** Never declare "it works" after one happy-path run. Test at least two edge cases. Follow surprising findings. The verdict is only trustworthy when the investigation was honest.

<!-- why: 'depth over speed' without a concrete floor leaves the agent to decide what counts as enough; two edge cases is the minimum observable bar -->

**Package installs are OK** when necessary to test the library — install the minimum package needed to answer the question. **Avoid** config layers, lockfiles, build tools, bundlers, Docker, and env files. Hardcode everything else — it's a spike.

**Comparison spikes: sequential, highest-risk first.** Run 002a to verdict before building 002b. Abandon 002b if 002a is already clearly better or already INVALIDATED.

<!-- why: parallel comparison creates race conditions on shared files and ignores risk-first ordering; sequential comparison preserves kill-criterion discipline -->

Delegation to a subagent is appropriate only when the comparison is purely independent (no shared state, neither is a kill-criterion for the other). If you delegate, pass the full spike protocol to each child in `context`:

```
delegate_task(tasks=[
    {
      "goal": "Build 002a-pdf-parse-pdfjs spike. Question: [...]. Write README.md with time-box, approach, two edge cases tested, verdict (VALIDATED/PARTIAL/INVALIDATED). Include a runnable command.",
      "context": "Verdict schema: VALIDATED=question answered with evidence. PARTIAL=works under constraints. INVALIDATED=approach dead. Record: time-box start, edge cases tried, recommendation."
    },
    ...
])
```

After children return: run each child's runnable command yourself to verify the verdict before writing the head-to-head.

### 5. Verdict

<!-- why: verdict in the README ensures the output survives the spike directory; the structured format forces the agent to be explicit about what worked and what didn't instead of leaving a vague 'seems fine' -->

Each spike's `README.md` closes with:

```markdown
## Verdict: VALIDATED | PARTIAL | INVALIDATED

### What worked
- ...

### What didn't
- ...

### Surprises
- ...

### Recommendation for the real build
- ...
```

**VALIDATED** = question answered with evidence (including a measured result or a confirmed winner — not just 'answered yes').
**PARTIAL** = works under constraints X, Y, Z — document them. Use this when evidence is incomplete, not when the evidence clearly says no.
**INVALIDATED** = approach is dead, for this reason. This is a successful spike.

**When the spike is INVALIDATED and there's no obvious alternative path:**

<!-- why: an invalidated spike with no pivot guidance leaves the user stuck; giving options prevents the session from ending without actionable next steps -->

Don't just write INVALIDATED and stop. Surface at least one of:
- A narrowed version of the same question that might still be answerable
- An alternative technical approach to the same goal
- A recommendation to drop the idea (with rationale)
- A question that needs answering before any path forward is clear

If no path forward is obvious, say so explicitly: "This spike invalidated the approach and I don't have a clear pivot. Recommend pausing and reassessing the goal."

## Comparison spikes

<!-- why: comparison spikes need a structured head-to-head or the comparison degrades into 'both seemed fine'; sequential build preserves risk-first discipline -->

When two approaches answer the same question (002a / 002b), build highest-risk first, then head-to-head:

```markdown
## Head-to-head: pdfjs vs camelot

| Dimension | pdfjs (002a) | camelot (002b) |
|-----------|--------------|----------------|
| Extraction quality | 9/10 structured | 7/10 table-only |
| Setup complexity | npm install, 1 line | pip + ghostscript |
| Perf on 100-page PDF | 3s | 18s |
| Handles rotated text | no | yes |

**Winner:** pdfjs for our use case. Camelot if we need table-first extraction later.
```

## Frontier mode (picking what to spike next)

<!-- why: without a structured scan of existing spikes, 'what next' devolves into the user's current curiosity rather than the highest-risk unknown remaining -->

If spikes already exist and the user says "what should I spike next?", walk the existing directories and look for:

- **Integration risks** — two validated spikes that touch the same resource but were tested independently
- **Data handoffs** — spike A's output was assumed compatible with spike B's input; never proven
- **Gaps in the vision** — capabilities assumed but unproven
- **Alternative approaches** — different angles for PARTIAL or INVALIDATED spikes

Propose 2-4 candidates as Given/When/Then. Let the user pick.

## Output

<!-- why: explicit output contract prevents the agent from doing spike work without writing the README verdict, which is the only durable artifact of a throwaway spike; gitignore prevents accidental production imports -->

- Create `spikes/` in the repo root; add it to `.gitignore` (or at minimum add `spikes/*/` to keep READMEs but exclude code). Do not import spike modules from production code.
- One dir per spike: `NNN-descriptive-name/`
- `README.md` per spike follows this skeleton (time-box at top, verdict at bottom):

```markdown
# NNN: spike-name

**Question (Given/When/Then):** Given X, when Y, then Z.
**Time-box:** 1 day (start: 2026-09-08T14:30)
**Approach:** chosen library / method and why

## How to run
```
python3 main.py
```

## Edge cases tested
1. ...
2. ...

## Verdict: VALIDATED | PARTIAL | INVALIDATED

### What worked
- ...

### What didn't
- ...

### Surprises
- ...

### Recommendation for the real build
- ...
```

- Keep the code throwaway — a spike that takes 2 days to "clean up for production" was a bad spike

## Attribution

Adapted from the GSD (Get Shit Done) project's `/gsd-spike` workflow — MIT © 2025 Lex Christopherson ([gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done)).
