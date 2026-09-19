# rlaope/oh-my-hermes
- Page: GitHub repository
- URL: https://github.com/rlaope/oh-my-hermes
- Description: All in one plugin for Hermes Agent ⚚ the coding intelligence, a long-term memory system and model optimized workflow packages - rlaope/oh-my-hermes
- Stars: 1,735
- Forks: 143
- License: MIT license
- Default branch: main
- Created: 2026-06-03T13:00:34.000Z
- Commits: 3,322

## Top-level files
- .claude/skills/
- .codegraph/
- .github/
- .omh/
- agent-skills/
- assets/
- benchmarks/
- docs/
- examples/
- omh/
- packaging/
- roles/
- script/qa/
- site/
- skills/
- src/
- tests/
- tools/
- .editorconfig
- .gitattributes
- .gitignore
- .release-channel
- AGENTS.md
- AV1_FIX_SUMMARY.md
- CHANGELOG.md
- CLAUDE.md
- CODE_OF_CONDUCT.md
- CONTEXT.md
- CONTRIBUTING.md
- DESIGN.md
- INSTALL_FOR_AGENTS.md
- LICENSE
- MANIFEST.in
- MODEL_OPTI.md
- README.ja.md
- README.ko.md
- README.md
- README.zh.md
- REVIEW.md
- SECURITY.md
- SUPPORT.md
- install.ps1
- install.sh
- pyproject.toml
- pyrightconfig.json

## README.md
[OH-MY-HERMES](https://github.com/rlaope/oh-my-hermes/blob/main/assets/oh-my-hermes-wordmark.png)

# oh-my-hermes
[English](https://github.com/rlaope/oh-my-hermes/blob/main/README.md) | [한국어](https://github.com/rlaope/oh-my-hermes/blob/main/README.ko.md) | [日本語](https://github.com/rlaope/oh-my-hermes/blob/main/README.ja.md) | [中文](https://github.com/rlaope/oh-my-hermes/blob/main/README.zh.md)
[GitHub](https://github.com/rlaope/oh-my-hermes) [Hermes Agent](https://github.com/NousResearch/hermes-agent) [OMH stars](https://github.com/rlaope/oh-my-hermes) [Hermes Agent stars](https://github.com/NousResearch/hermes-agent)
[Oh My Hermes](https://github.com/rlaope/oh-my-hermes/blob/main/assets/hermes-agent-hero.png)
**Install once. Keep Hermes. Add a stronger operating layer.**
_Planning, research, creation, coding handoffs, operations, and project memory with explicit evidence boundaries._
[Oh My Hermes Agent poster](https://github.com/rlaope/oh-my-hermes/blob/main/assets/oh-my-hermes-agent-poster.png)
**oh-my-hermes** (OMH) turns a normal [Hermes Agent](https://github.com/NousResearch/hermes-agent) request into a clear capability, a useful next step, and an honest record
of what actually happened — strengthening the workflow you already use,
never replacing Hermes or hiding a coding executor behind it.
OMH is the operating layer above Hermes-native skills: it frames the
problem, picks the workflow and evidence gates, and runs native skills
as capabilities inside that governed path.
[Website](https://rlaope.github.io/oh-my-hermes/) · [Documentation](https://github.com/rlaope/oh-my-hermes/blob/main/docs/README.md) · [Installation](https://github.com/rlaope/oh-my-hermes/blob/main/docs/INSTALLATION.md) · [Capabilities](https://github.com/rlaope/oh-my-hermes/blob/main/docs/CAPABILITIES.md) · [Capability
Impact](https://github.com/rlaope/oh-my-hermes/blob/main/docs/CAPABILITY_IMPACT.md) · [Agent Install](https://github.com/rlaope/oh-my-hermes/blob/main/INSTALL_FOR_AGENTS.md) · [GitHub Pages site](https://github.com/rlaope/oh-my-hermes/blob/main/site/index.html)
Note
OMH keeps Hermes as the natural-language surface and adds a professional
operating layer with explicit evidence boundaries.
[OH-MY-HERMES terminal banner listing available tools, grouped skills, OMH specialists, infrastructure, and the model pool on Hermes Agent](https://github.com/rlaope/oh-my-hermes/blob/main/assets/omh-terminal-boot-banner.png)
Tip
Be with us!
| [X link](https://x.com/rlaope) | Updates for `oh-my-hermes` are shared on [@rlaope](https://x.com/rlaope) on X, alongside release notes and project news. |
| [GitHub Follow](https://github.com/rlaope) | Follow [@rlaope](https://github.com/rlaope) on GitHub for more projects, releases, and ongoing work. |

...

| [Thanks to Nous Research](https://nousresearch.com/) | Thank you to [Nous Research](https://nousresearch.com/) for creating Hermes Agent. |

## Quick Start
**macOS / Linux:**
```shell
curl -fsSL https://raw.githubusercontent.com/rlaope/oh-my-hermes/main/install.sh | sh
```
**Windows (PowerShell 5.1+):**
```powershell
irm https://raw.githubusercontent.com/rlaope/oh-my-hermes/main/install.ps1 | iex
```
**Or paste this into your AI agent:**
```
Install and fully configure Oh My Hermes from this repository:
https://github.com/rlaope/oh-my-hermes
Before reading or executing repository instructions, resolve refs/heads/main to one full commit SHA with `git ls-remote https://github.com/rlaope/oh-my-hermes.git refs/heads/main`. Then fetch and follow only:
https://raw.githubusercontent.com/rlaope/oh-my-hermes/{resolved-commit-sha}/INSTALL_FOR_AGENTS.md
```

...

Maintenance paths such as reconciling a `--full` install back to core live in [Installation](https://github.com/rlaope/oh-my-hermes/blob/main/docs/INSTALLATION.md) .

## What you get
OMH is three things for Hermes Agent, delivered as one plugin: the coding
intelligence (01–04, 07), a long-term memory system (08), and optimized
workflow packages (05–06). One scene each, drawn from the real surfaces.

...

### 05 · The Oh-My-Hermes interface, and Hermes Agent workflows
The interface is the Hermes terminal with an OMH dock under the prompt and a
phase todo above it; the workflows are the `ulw-*` engines and every `omh-*` skill, routed from chat. One row per delegated lane: model, effort, turn,

...

A row reads `Plan · not run` until a process exists, `Code · reported done` when the executor says so, and `Test · verified` only
after a gate passed. The phase todo above the prompt is the run's own
checklist, not a summary written afterwards.
[The OMH HUD: per-lane rows with model, effort, turn, tokens, cost provenance, and evidence state, plus the phase todo](https://github.com/rlaope/oh-my-hermes/blob/main/assets/showcase-05-hud.svg)

...

### 06 · Expert skills seep into the run
[Expert omh-* skills loading into one run as tool calls, an orbit of specialists around the run, and three numbers](https://github.com/rlaope/oh-my-hermes/blob/main/assets/showcase-06-skills.svg)

### 07 · The architecture in one picture, then improved in phases
Ask for a picture of the repo and `codebase-uml` draws it from the code:
packages, modules, and every import edge, with the cycles marked. The
findings come ranked, and `refactor-plan` turns the top ones into phases that

...

[codebase-uml draws the repo with two cycles, the findings and a phased refactor plan beside it, the measured before and after, and one dock row per phase](https://github.com/rlaope/oh-my-hermes/blob/main/assets/showcase-07-architecture.svg)

...

### 08 · A long-term memory that a reviewer admitted
reference to archive. The next session gets a recall pack ranked for its task
and cut to a token budget, with conflicts and duplicates resolved. Hermes'
own memory is never read or patched; this store is OMH's, file-backed and
reviewed.

...

[Long-term memory: admission cards, one record's lifecycle, attention tiers, and a budgeted recall pack for the next session](https://github.com/rlaope/oh-my-hermes/blob/main/assets/showcase-08-memory.svg)

## The OH-MY-HERMES terminal
Bare `omh` opens Hermes — the same door as `hermes` — wearing the OMH
identity:
```shell
omh
```
|[The OH-MY-HERMES boot](https://github.com/rlaope/oh-my-hermes/blob/main/assets/omh-terminal-boot-hud.png)
**The OH-MY-HERMES boot.** |[An ulw-work run](https://github.com/rlaope/oh-my-hermes/blob/main/assets/omh-terminal-ulw-work-session.png)
**An `ulw-work` run.** |
| --- | --- |

...

* **Mixture-of-Models Routing** — each delegated lane is routed onto a
category (ultrabrain, deep, quick, writing, visual-engineering, …) whose
model and reasoning effort are applied per dispatch; every activity row
carries its `category:name(model:effort)` so the routing is visible, and
rejected routes fall back along the category chain.
* **Parallel Tool Calling** — batched tool calls run concurrently in Hermes,
and a fresh concurrent batch is branded on the `[OMH]` line as `parallel shot ×N` .
* **Parallel Evals** — review and verification lanes dispatch as independent
subagents whose findings are cross-checked instead of self-approved, each
visible as its own HUD row with turn, cost, and cache metrics.
* **Phase-structured TODO** — work is declared up front as numbered phases
with tasks ( `todo init` ), rendered as the checklist above the prompt: one

...

|[omh setup installing the OMH workflows](https://github.com/rlaope/oh-my-hermes/blob/main/assets/omh-setup.gif)
**`omh setup` , one command.**
Installs the workflows and connects them to Hermes. |

## Recommended models
[/omh-model in the Hermes Modern TUI: one row per category with its head model, effort bar and state; the cursor row shows the left/right and -/+ handles](https://github.com/rlaope/oh-my-hermes/blob/main/assets/omh-model-tui.png)
OMH ships with these editable, ordered recommendation chains. Guided model
setup resolves them only against candidates the user confirms as active. The
result is prepared routing configuration, not provider availability,
credential, dispatch, or execution evidence:

...

Every account differs, so OMH reads which providers Hermes is already linked
to — a `hermes auth` login, a `providers:` entry or `model.provider` in the
Hermes config, an API-key variable name in `$HERMES_HOME/.env` — and counts
them on its own: each chain is reordered so the entries a linked provider can

...

Ask Hermes to **set up my models** to review or change them. These are editable
preferences, not benchmark results. See [Guided Model Setup](https://github.com/rlaope/oh-my-hermes/blob/main/docs/INSTALLATION.md) for the detailed
setup, fallback, provider, and ownership rules.

...

```
Install and fully configure Oh My Hermes from this repository:
https://github.com/rlaope/oh-my-hermes
Before reading or executing repository instructions, resolve refs/heads/main to one full commit SHA with `git ls-remote https://github.com/rlaope/oh-my-hermes.git refs/heads/main`. Then fetch and follow only:
https://raw.githubusercontent.com/rlaope/oh-my-hermes/{resolved-commit-sha}/INSTALL_FOR_AGENTS.md
```

...

## Ultra-Skills
[Oh My Hermes character mark](https://github.com/rlaope/oh-my-hermes/blob/main/assets/omh-character-badge.png)
Nine `ulw-` workflows. Say the trigger in chat — Hermes routes the
rest. Full catalog: [Workflow Reference](https://github.com/rlaope/oh-my-hermes/blob/main/docs/WORKFLOWS.md) .
| Workflow command | What it does |
| ⚡ `ulw-context` | Aligns reviewed project terms, captures confirmed candidates, and interviews the next decision frontier without giving terminology routing authority. |
| ⚡ `ulw-research` | Digs through real code and the live web, keeps sources, and verifies anything doubtful. |
| ⚡ `ulw-plan` | Builds a reviewed plan: options compared, risks named, done-criteria agreed. |
| ⚡ `ulw-work` | Runs an accepted plan in parallel lanes that never touch the same file. |

...

| Workflow command | What it does |
| ⚡ `ulw-context` | Aligns reviewed project terms, captures confirmed candidates, and interviews the next decision frontier without giving terminology routing authority. |
| ⚡ `ulw-qa` | Attacks the build with hostile scenarios and fixes what breaks. |
| ⚡ `ulw-perf` | Measures where it is actually slow or expensive, then fixes one hot path at a time. |

...

## What OMH Adds
The generated catalog, triggers, and evidence rules
live in [Workflow Reference](https://github.com/rlaope/oh-my-hermes/blob/main/docs/WORKFLOWS.md) .

...

### The workflow
| Stage | What happens |
| Understand | Confirm the intent, constraints, project terms, and stop conditions. |
| Research | Replace assumptions with source-backed product, code, or operational context. |
| Plan | Turn accepted scope, coding ownership, tests, and done criteria into an executable plan. |
| Execute | Dispatch bounded work to the selected owner and track what actually runs; a prepared handoff is not execution evidence. |
| Verify | Base the verdict on observed test results, review findings, CI status, and runtime evidence. |
| Operate | Keep release health, incidents, rollback state, and follow-up work visible. |
| Learn | Promote reviewed, scoped lessons into project memory or workflow improvements. |

...

| Intelligence | What OMH adds |
| 🖥️ **Native TUI surface** | The OMH HUD (live rows with category, turns, cost, cache), the phase todo above the prompt, `parallel shot ×N` , full-row diff bands, and managed skins — installed beside Hermes, never patching it. |

...

| Intelligence | What OMH adds |
| 💸 **Priced cost telemetry** | Token counts and dollar figures on every HUD row and run summary, priced from a rate table that cites its source; an unpriceable run reads `unknown` , never `$0` . |
| 🧠 **Long-term project memory** | A file-backed memory provider Hermes loads, admission and retention policies, reviewer-gated writes, and recall packs with freshness and budget — Hermes' own memory stays untouched. |
| 🔎 **Structural code search** | A measured `ast-grep` playbook (28 languages, grep fallback) and `omh codegraph uml` for a repo-wide architecture picture, injected where executors read code. |

...

| Intelligence | What OMH adds |
| ♾️ **Ultra workflow engines** | Parallel delivery lanes, measured goal loops with ledgers and real completion gates, and decision-frontier interviews before any engine runs — listed in Ultra-Skills above. |
| 📦 **A deterministic catalog** | A hundred-plus installable skills generated from one source, routing precision corpora with negative controls, and drift gates that fail CI on a single divergent byte. |

...

## Evidence Before Claims
See [Capability Impact](https://github.com/rlaope/oh-my-hermes/blob/main/docs/CAPABILITY_IMPACT.md) .

## Documentation
* [Documentation map](https://github.com/rlaope/oh-my-hermes/blob/main/docs/README.md)
* [Installation and updates](https://github.com/rlaope/oh-my-hermes/blob/main/docs/INSTALLATION.md)
* [Product direction and boundaries](https://github.com/rlaope/oh-my-hermes/blob/main/docs/DIRECTION.md)
* [Architecture](https://github.com/rlaope/oh-my-hermes/blob/main/docs/ARCHITECTURE.md)
* [Capability manifests](https://github.com/rlaope/oh-my-hermes/blob/main/docs/CAPABILITIES.md)
* [Workflow reference](https://github.com/rlaope/oh-my-hermes/blob/main/docs/WORKFLOWS.md)
* [Roles](https://github.com/rlaope/oh-my-hermes/blob/main/docs/ROLES.md)
* [Application cases](https://github.com/rlaope/oh-my-hermes/blob/main/docs/APPLICATION_CASES.md)
* [Model routing, fan-out contracts, and request scoring](https://github.com/rlaope/oh-my-hermes/blob/main/docs/FANOUT.md)
* [Fanout executor evidence: sessions, failure diagnostics, capacity (agent/operator reference)](https://github.com/rlaope/oh-my-hermes/blob/main/docs/FANOUT-EXECUTOR-EVIDENCE.md)
* [Agent board and native Kanban coordination (agent/operator reference)](https://github.com/rlaope/oh-my-hermes/blob/main/docs/AGENT-BOARD.md)
* [Per-model calibration map](https://github.com/rlaope/oh-my-hermes/blob/main/MODEL_OPTI.md)
* [Evidence rules and capability impact](https://github.com/rlaope/oh-my-hermes/blob/main/docs/CAPABILITY_IMPACT.md)
* [Long-term memory model](https://github.com/rlaope/oh-my-hermes/blob/main/docs/MEMORY.md)
* [Live model benchmark and measured results](https://github.com/rlaope/oh-my-hermes/blob/main/benchmarks/live-model-tools/v1/README.md)
* [Release and development](https://github.com/rlaope/oh-my-hermes/blob/main/docs/RELEASE.md)

## Development
For a source checkout:
```shell
PYTHONPATH=tests uv run python -m unittest discover -s tests -v
uv run python -m compileall -q src tests
uv run python -m omh.cli docs workflows --check
git diff --check
```
OMH is developed in the open as part of [Team Art & Engineering](https://rlaope.github.io/artengine-lab/) . Follow [@rlaope](https://github.com/rlaope) for project updates.