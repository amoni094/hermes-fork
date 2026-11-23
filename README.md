<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

# hermes-fork ☤

> **This is a personal fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).** It tracks upstream and layers a dense set of research-driven extensions on top. Not an official Nous Research product — one person's daily driver. For the supported version use the upstream repo.

<p align="center">
  <a href="https://hermes-agent.nousresearch.com/docs/"><img src="https://img.shields.io/badge/Docs-hermes--agent.nousresearch.com-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/NousResearch/hermes-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://nousresearch.com"><img src="https://img.shields.io/badge/Built%20by-Nous%20Research-blueviolet?style=for-the-badge" alt="Built by Nous Research"></a>
</p>

**396 commits ahead of upstream. 24 active plugins. 162 enabled scheduled jobs. 6 new agent modules.**

---

## What this fork adds over upstream

Additions are organised into five tiers by where they run:

1. **During every turn** — changes to the agent's core logic that fire on each message
2. **At compress time** — plugins that modify or observe every context compression event
3. **Background jobs** — scheduled scripts that maintain indexes, scores, and stores
4. **Memory** — a multi-tier memory system extending upstream's defaults
5. **Infrastructure** — sandbox hardening, scheduling, system maintenance

The core conversation loop — how the agent iterates, calls tools, and decides when to stop — is not replaced. All changes to the agent's core are listed precisely in the section below.

---

## Agent core changes

This is the most important section for accuracy. The fork adds six new modules to the agent and makes targeted changes to several existing ones. None of them rewrite the conversation loop.

### New agent modules

**Session classifier** — identifies what kind of session is underway (research, coding, mixed, or high-volume) based on the content of messages. Used by the lambda-tuner plugin to choose how aggressively to compress context. Also emits hints about how much reasoning effort is appropriate for the current work.

**Routing harmonizer** — a small stability layer that re-exports everything from the session classifier under a fixed name. Plugins import from this stable name so they don't break when the classifier evolves underneath.

**Reasoning verbosity** — adds three verbosity modes to the agent: full (default), compact (strips completed internal thinking from history on low-effort turns), and suppress (turns off thinking output entirely). Available for plugins to invoke; not called automatically from the conversation loop.

**Retrieval heuristics library** — a set of relevance checks for deciding when to retrieve skills, run a web search, or discard a web passage. For example: skip skill retrieval if the query is very short and the best match is weak; force skill retrieval if the query matches a known hard domain. Also flags tool results that are degenerate (empty, error-only, or repeated). Used by the skill utilities module; not called directly from the conversation loop.

**SSL guard** — ensures the agent never makes HTTP requests with certificate verification disabled. Also provides a linter for skill files that reference SSL settings.

**Memory partition pruner** — when the agent uses a tree-structured memory layout, this module handles weighted pruning before summarisation: tool results are pruned most aggressively, internal reasoning moderately, user messages never.

### Changes to existing agent modules

**Conversation loop** (two changes):
- When a session starts, the live agent object is now passed to plugins. Previously plugins received only the session ID.
- On the Bot Chat capability-refresh path, tool definitions are now persisted. Upstream did not persist them here.

**Tool executor** (three changes):
- Before each tool call, a lightweight governance check runs in the background. It does not block execution or change the result — it just logs a proposal if the call touches a sensitive path.
- After a successful auto-compress, a compress event is fired so compress-time plugins receive it.
- A deadline-clamping mechanism that limited tool timeouts based on remaining session time was removed. Tool timeouts now rely on the timeout argument alone.

**Tool guardrails** (two changes):
- Added a background governance check for writes to sensitive paths: when a file write or terminal command targets the agent's core code, config, or plugins, a background process is launched to log a proposal. It has a 5-second timeout and does not block execution.
- Removed a blocklist of jailbreak-style phrases (e.g. "ignore previous instructions"). The fork replaces blocking with logging-only: matching patterns are noted but the call is not blocked.

**Context compressor** (additions, no removal of core logic):
- Compression can now be blocked from firing when context is growing too slowly. This avoids compressing prematurely.
- Plugins can set a compression profile by name (research, code, or mixed). Each profile controls how aggressively context is trimmed and how many recent turns are protected.
- Before the summarisation step, a fact ledger is prepended to the summary: paths, paper IDs, model names, and numbered facts extracted from the conversation, to reduce information loss.
- A message-folding pass runs before the language model summarisation step to reduce token cost.

**Prompt builder** (two changes):
- Textbook-category skills collapse to name-only listings when the agent is in coding mode, reducing noise.
- A new skill flag allows skills to be hidden from the agent's available-skills list while remaining accessible via direct lookup.

**Subagent lifecycle** — when a subagent times out, the fork now records a clean failed state with a diagnostic message instead of letting the timeout propagate as an exception.

**Agent init** — the agent's memory emit method is now bound at startup as a fail-open wrapper. Memory write failures no longer crash the turn.

---

## Memory

The fork runs four distinct memory stores. They are not unified — each has its own write path and its own retrieval mechanism.

### The four stores

**1. Hindsight (live, per-turn)**

The primary long-term memory backend. Runs every turn.

- Connects to a local Hindsight server.
- Retains every turn asynchronously. A deduplication cache prevents double-commits on the last 20 writes.
- Before each turn, relevant past observations are recalled automatically.
- The agent can also recall and reflect on memory on demand via dedicated tools.
- Distinct from the knowledge graph — Hindsight writes happen during turns; graph writes happen in background jobs.

**2. Standing facts (always-injected)**

Facts injected into every system prompt. 2200 character budget. Managed manually or by background scripts — not a retrieval store.

**3. Extracted facts (batch, not per-turn)**

A pipeline that extracts important facts from session history into dated markdown files.

- Runs daily: extracts bullet-point facts from recent sessions, then promotes high-confidence ones to a query tier.
- Every ~4 hours: writes promoted facts to the knowledge graph.
- Retries failed graph writes using a local state tracker.
- A graph consolidation job promotes facts from session-tier to query-tier when they appear at least twice, and to insight-tier when they appear at least three times.

**4. Knowledge graph (entity/relation graph)**

A knowledge graph fed by the extraction pipeline, not directly by conversation turns. The agent can query it on demand via search and add tools.

### Recall tools (not in the agent loop)

Several recall tools exist for offline or on-demand use — they are not called automatically during turns. These include a unified recall tool that queries both the Hindsight server and knowledge graph and merges the results, a dual-backend fuser for relevance-minus-redundancy merging, and a query router that picks the right backend by query type (semantic, temporal, relational, or exact).

### Background memory maintenance

Around 50 scheduled scripts maintain the health of the memory stores — detecting when to evict old entries, whether the embedding space has drifted, whether duplicate facts should be merged. None of these run during a conversation turn.

---

## Cognitive science foundations

Several parts of the fork's memory and scheduling behaviour are grounded in specific cognitive science models. These are not theoretical decoration — each model is actively wired into how the agent stores, retrieves, and schedules work.

### How memories compete and fade

The fork models memory retrieval using two interlocking ideas from cognitive science.

The first is that memories have **strength** that decays over time and is restored when a memory is used. A fact that hasn't been retrieved in weeks is weaker than one retrieved yesterday. When two memories are relevant to the same question, the stronger one wins — but its win also slightly suppresses the weaker one. This is not just passive competition: the suppression is active, meaning the stronger memory actively reduces the other's chances of being recalled next time.

The second is about what this means for the memory stores. If the agent always retrieves the same recent facts, the older ones it never retrieves get progressively harder to reach — not because they're gone, but because they've been repeatedly passed over in favour of stronger competitors. The background maintenance jobs partially counteract this by periodically touching under-accessed memories to prevent them from fading entirely.

In practice: the memory stores track a strength score per fact. A background job applies exponential decay to all facts on a schedule, and resets the score upward whenever a fact is retrieved. A second background job tracks pairs of facts that compete on the same topic and applies a small suppression penalty to the loser each time the winner is recalled.

### Reminders are protected from pruning

The fork makes a special exception for one category of memory: intended actions. When a fact contains a reminder or a pending task — something the agent is supposed to do in the future — it is protected from being pruned or down-ranked by the suppression mechanism above.

This matters because the normal rules (decay, competition, recency bias) would otherwise make it possible for a reminder to get quietly crowded out by more recently active memories. The fork explicitly checks for reminder-style facts before applying suppression and pruning, and injects them before other retrieved facts regardless of their retrieval score.

### Memory that matters for decisions

When the agent has to decide what to keep under a memory budget, it prioritises facts that would change what action it takes next — not facts that are merely interesting or well-summarised. Two histories that would lead to the same next action can safely share the same compressed memory state. Two histories that would lead to different actions cannot.

This principle — called decision-centric compression — guides what the memory pruner keeps when it has to discard something. Description is the first to go. Tool outputs, identifiers, paths, constraints, and outcomes that split possible actions are the last.

### Scheduling that knows when to stop

Background jobs don't all need to run to completion to be useful. The fork models each scheduled job as producing increasing quality over time, with diminishing returns: running for twice as long yields less than twice the improvement. Each job tracks a quality score that reflects how fresh and complete its last output was.

The scheduler uses this score to decide whether to re-run a job or use its cached output. If the quality score is high enough and the job ran recently enough, it skips re-running. Under load, it prioritises jobs with the lowest quality scores — the ones that have degraded the most since they last ran.

Each job also follows a checkpoint pattern: it writes partial results before doing expensive work, so that if it's interrupted it has already produced something useful rather than nothing.

---

## Skill routing

There are two completely separate routing layers: one that fires every turn (the nudge plugin), and a large set of background scripts that maintain an offline model.

### What runs during turns: skill-routing-nudge plugin

The only live routing change in the turn is the skill-routing-nudge plugin. It:

1. Scores the user message against a text-matching skill index.
2. If the message is long enough and the top match is strong enough, injects a skill suggestion into the message naming the top candidates.
3. Safety-related skills are suggested at a lower threshold.
4. Fail-open: any failure is swallowed and the message is sent unmodified.

The index is rebuilt weekly. The nudge does not select the skill — it hints the model, which still makes the final call.

A companion plugin appends every skill-view call to a log for offline analysis.

### What runs in background: the routing model infrastructure

About 60 scheduled scripts maintain an offline routing model whose weights are stored on disk. These weights are **not currently wired** into the live turn routing — the nudge plugin uses a plain text-matching index, not the model weights. The model infrastructure is research/forward-looking and tracks routing quality offline.

Background jobs include weekly and Sunday index rebuilds, a daily semantic fallback index rebuild, and a daily offline model weight update.

Around 30 other routing scripts write alarm logs and metrics — they are observability infrastructure, not the live routing path.

---

## Compression

The fork modifies what happens at compress time and measures quality in background jobs. These are two separate things.

### What runs at compress time (every compression)

**Context compressor** — the core compress logic is upstream's. The fork adds: a fact ledger prepended to summaries, a message-folding pass before the language model summarisation step, and growth-gating (defer compression until context is actually growing fast enough).

**jev-compaction plugin** — the most significant compaction modification. Replaces the tool-result pruning step with a scored version: tool results are ranked by recency and relevance density, divided into tiers, and the middle tier is scored for informativeness using up to 8 secondary model calls per compaction. Fail-open.

**compaction-gate plugin** — compression gate using Wald SPRT on head-hit-rate. Fires before compression: scores MDL facts, injects a hindsight context block, and can defer or suppress compression when the SPRT signal says the compressor is healthy. Also writes quality metrics per compression.

**context-pressure-guard plugin** — computes a compression signal based on how much pressure the context is under and writes it to a cache file for use by other components.

**billion-context plugin** — the most aggressive live modification. Folds tool results to compact JSON before the language model summarisation step. Applies growth gating to defer auto-compress when context isn't growing fast enough. Offloads oversized tool results to disk and inserts a retrieval placeholder.

**lambda-tuner plugin** — classifies the session type (research, coding, or mixed) from your messages and applies the matching compression profile. Research sessions compress earlier and protect more recent turns. Coding sessions keep more context per turn. Mixed is the balanced default. Also scores each message for complexity to suggest reasoning depth, and pre-compresses large tool outputs before they enter context. See the [lambda-tuner section](#lambda-tuner) below.

### Offline quality measurement (not at compress time)

A separate evaluation tool compresses a saved transcript under different policies, asks recall questions about the dropped content, and uses a language model to judge the answers. This is a manual tool for evaluating compression quality — not a scheduled job.

Scheduled quality metrics that run on a cron schedule (not modifying the compressor):
- Nightly compression quality score — precision and recall between pre/post compression. Alarms if precision drops below 0.3 (fabrication risk) or recall below 0.2 (too much lost).
- Hourly typical-set coverage score
- Every 30 minutes: a compression quality monitor and an rd-compaction advisor
- Every 2 hours: a compression signal fuser

---

## Lambda-tuner

Lambda-tuner is the plugin that connects session classification to compression behaviour. It was available in the codebase but not enabled in the fork profile until now.

### What it does

The agent often switches between very different kinds of work — a research session looks nothing like a coding session. Lambda-tuner watches your messages and classifies the session type. Once it has enough signal (usually after the first message), it applies a compression profile matched to that type:

- **Research sessions** — compress earlier, protect more recent turns, prune older context more aggressively. Keeps the working context tight so recent findings are always available.
- **Coding sessions** — keep more context per turn, protect more turns from pruning, compress less aggressively. Code needs more surrounding context to be useful.
- **Mixed sessions** — the balanced default. Neither aggressive nor conservative.

The classification is based on the content of your messages: research-heavy vocabulary (citing papers, asking about studies, information retrieval) pulls toward research; code-heavy vocabulary (debugging, function names, stack traces) pulls toward code.

### What else it does

Beyond compression, lambda-tuner also:
- **Scores message complexity** — each message is scored for how hard it is. This score is available to plugins for adjusting reasoning depth or model tier.
- **Pre-compresses large tool outputs** — before large tool results enter context, lambda-tuner strips boilerplate and compresses them. This runs before compression, not at it.
- **Writes a session type hint** — the classification is written to a cache file so other plugins can read the session type without re-classifying.
- **Warm-starts on session resume** — if a previous session was classified, the classification carries over at the start of the new session instead of starting from scratch.

### Why it wasn't enabled before

Lambda-tuner existed in the codebase as a shipped-but-not-deployed plugin. The fork profile's plugin directory didn't include it, so it never loaded. The context-pressure-guard plugin was writing a compression signal that lambda-tuner was designed to consume, but nothing was consuming it. This change copies lambda-tuner into the active plugin directory and adds it to the enabled list.

### What changed to enable it

- Copied the plugin into the active plugin directory.
- Added it to the enabled plugins list in config.
- Verified all hooks register correctly and relative imports work under the fork's plugin loader.
- Confirmed that the compression profiles lambda-tuner sets match the profiles the compressor knows about (research, code, mixed).

---

## Plugin inventory

24 plugins are enabled. All are fail-open except where noted.

| Plugin | When it runs | What it does |
|---|---|---|
| `hindsight` | Every turn | The primary long-term memory backend. Retains every turn asynchronously. Recalls relevant past observations before each turn. |
| `jev-compaction` | At compress time | Replaces the tool-result pruning step with a scored version. Up to 8 secondary model calls per compression to judge informativeness. |
| `compaction-gate` | At compress time | Compression gate with Wald SPRT on head-hit-rate. Fires before compression: scores MDL facts, injects a hindsight context block, and can defer or suppress compression via the SPRT signal. Also logs quality metrics per compression. |
| `context-pressure-guard` | At compress time | Computes a compression pressure signal and writes it to a cache file. |
| `billion-context` | At compress time, on tool results | Growth-gated compression. Folds tool results to compact JSON before summarisation. Offloads oversized tool results to disk. |
| `lambda-tuner` | On each message, at compress time, on session start/end, on tool results | Classifies the session as research, coding, or mixed. Applies the matching compression profile. Scores message complexity. Pre-compresses large tool outputs. |
| `jev-turn-evaluator` | After each model response | Scores each model response via a secondary model. Gates policy updates until enough turns are scored with a satisfactory average. |
| `governance-hard-block` | On load only | **Currently disabled.** Logs that it is disabled; does not block tool calls. |
| `cobra-guard` | After each tool call | Tracks decision outcomes. Blocks repeated failures on the same decision type until manually reviewed. |
| `tool-auth-gate` | After each tool call | Spot-checks auth tokens on a sample of external service calls. |
| `tool-result-audit` | After each tool call | Scans external tool results for injection attempts before they enter context. |
| `memory-ransac-gate` | After each tool call | Checks new facts against existing memories before commit; rejects statistical outliers. |
| `decision-audit` | After each tool call | Accumulates tool outcome stats per session; writes to a database periodically. |
| `delegation-audit-hook` | After each tool call | Records subagent delegation outcomes (success/failure, duration). |
| `deductive-verifier` | After each model response | Checks that the agent's stated conclusions follow from its stated premises. |
| `formal-verify-plugin` | After each tool call | Enforces proof-state integrity on tool calls that claim to verify formal properties. |
| `compliance-score-hook` | After each tool call | Scores tool outputs for compliance concerns and excessive length; logs results. |
| `post-tool-compliance` | After each tool call | Independent compliance scorer; observation-only, never blocks. |
| `turn-behavior-logger` | After each model response | Logs per-turn metrics: response length, tool count, model used, compression events. |
| `skill-routing-nudge` | Before each model call | Scores the user message against the skill index; injects a skill suggestion if the match is strong enough. The only live routing change. |
| `skill-access-logger` | After each tool call | Appends skill-view calls to a log for offline analysis. |
| `skill-latency-logger` | After each tool call | Records how long skill loads and uses take. |
| `orca-status` | Lifecycle events | Reports lifecycle events to an external monitoring service. |
| `camofox` | Browser tool calls | Stealth browser backend with fingerprint evasion. |

**In-repo plugins** (tracked in git, not in the active plugin directory):
- `hindsight` — the full memory provider implementation. Registers via the memory provider interface.

---

## Safety and approval changes

**Approval pattern list** — the set of patterns that trigger an approval prompt was updated. Some patterns that caused false positives on legitimate operations were removed; patterns more specific to actual injection vectors were added.

**Session-scoped approval tracking** — approval and pattern tracking are now keyed to the current session. The core approval interaction flow is unchanged.

**Governance pre-check** — a background governance check fires on writes to sensitive paths (agent core, config, plugins). It launches a background process with a 5-second timeout, does not block execution, and is fail-open.

**Skills guard change** — upstream blocked tool calls matching jailbreak-style phrases. The fork replaces blocking with logging-only. Matching patterns are noted but the call proceeds.

---

## Infrastructure and scheduling

**Scheduled jobs**: 209 total, 162 enabled. The majority are research or alarm scripts that write to cache and are not in any critical path. The ones that matter for agent operation:

| Job | Schedule | Role |
|---|---|---|
| Fact extraction | Daily 01:00 | Extract facts from recent sessions to markdown |
| Fact promotion | Daily 01:30 | Promote high-confidence extracted facts |
| Graph write | Every ~4 hours | Write promoted facts to the knowledge graph |
| Graph retain | Daily 09:00 | Agent job: retain staged facts via the memory tool |
| Skill index rebuild | Saturday 05:00 | Rebuild the text-matching skill index the nudge plugin reads |
| Skill index rebuild (unconditional) | Sunday 03:00 | Full skill index rebuild |
| Semantic fallback index | Daily 02:00 | Rebuild the semantic fallback index |
| Compression quality score | Daily 04:50 | Precision and recall score on recent compressions |
| Compression coverage | Hourly | Typical-set coverage score |
| System update | Daily | OS, packages, and firmware updates with per-step timeouts |
| Graph health check | Every 6h | Knowledge graph health |
| Routing model update | Daily 09:10 | Offline routing model state update |

**Sandbox**: every scheduled script runs inside a landlock sandbox. Read-only access to system binaries and the scripts themselves. Read-write access to temp, cache, memory-facts, and logs. Sandbox bypass is blocked in the wrapper. A load-aware admission controller drops low-priority jobs under system load.

**System updates**: per-step timeouts (package manager 20 min, firmware 5 min, each git repo 1 min). Non-fatal on metadata errors. A login-trigger variant handles steps that need a graphical session.

**Data versioning**: three-way merge for concurrent writes to the job list (field-level conflict detection, never silent last-write-wins). Append-only change history on the lifecycle database with time-travel and blame.

**Compression quality scorer**: computes two scores between pre/post compression snapshots — a precision score (did anything fabricated appear?) and a recall score (how much was lost?). Alarms if precision drops below 0.3 or recall below 0.2. Uses sampling for large inputs.

---

## What is not changed from upstream

- Core conversation loop iteration, tool dispatch flow, and stop conditions
- Installation procedure, model provider support, MCP server integration, messaging gateway, TUI/CLI interface
- The approval interaction flow (session scoping was added; prompting behaviour is unchanged)

For anything not covered here: **[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)**

---

## Upstream merge policy

This fork rebases or merges from upstream main periodically. Conflicts on core agent loop files resolve in favour of upstream; fork additions win on scripts, plugins, and config.

**Current base:** See `git log --oneline upstream/main..HEAD` for fork-only commits.

---

## Running this fork

```bash
hermes-fork          # start CLI on the fork profile
hermes-fork doctor   # health check
hermes-fork -z       # fork profile with zero context (fresh session)
```

The fork profile lives at `~/.hermes/profiles/fork/`. The binary at `~/.local/bin/hermes-fork` pins to the correct Python interpreter — do not use the venv binary directly.

---

## Original upstream README

---


Everything below is the original Hermes Agent README.

---

<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

# Hermes Agent ☤
<p align="center">
  <a href="https://hermes-agent.nousresearch.com/">Hermes Agent</a> | <a href="https://hermes-agent.nousresearch.com/">Hermes Desktop</a>
</p>
<p align="center">
  <a href="https://hermes-agent.nousresearch.com/docs/"><img src="https://img.shields.io/badge/Docs-hermes--agent.nousresearch.com-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/NousResearch/hermes-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://nousresearch.com"><img src="https://img.shields.io/badge/Built%20by-Nous%20Research-blueviolet?style=for-the-badge" alt="Built by Nous Research"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/Lang-中文-red?style=for-the-badge" alt="中文"></a>
  <a href="README.ur-pk.md"><img src="https://img.shields.io/badge/Lang-اردو-green?style=for-the-badge" alt="اردو"></a>
  <a href="README.es.md"><img src="https://img.shields.io/badge/Lang-Español-orange?style=for-the-badge" alt="Español"></a>
</p>

**The self-improving AI agent built by [Nous Research](https://nousresearch.com).** It's the only agent with a built-in learning loop — it creates skills from experience, improves them during use, nudges itself to persist knowledge, searches its own past conversations, and builds a deepening model of who you are across sessions. Run it on a $5 VPS, a GPU cluster, or serverless infrastructure that costs nearly nothing when idle. It's not tied to your laptop — talk to it from Telegram while it works on a cloud VM.

Use any model you want — [Nous Portal](https://portal.nousresearch.com), OpenRouter, OpenAI, your own endpoint, and [many others](https://hermes-agent.nousresearch.com/docs/integrations/providers). Switch with `hermes model` — no code changes, no lock-in.

<table>
<tr><td><b>A real terminal interface</b></td><td>Full TUI with multiline editing, slash-command autocomplete, conversation history, interrupt-and-redirect, and streaming tool output.</td></tr>
<tr><td><b>Lives where you do</b></td><td>Telegram, Discord, Slack, WhatsApp, Signal, and CLI — all from a single gateway process. Voice memo transcription, cross-platform conversation continuity.</td></tr>
<tr><td><b>A closed learning loop</b></td><td>Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks. Skills self-improve during use. Full-text session search with LLM summarization for cross-session recall. <a href="https://github.com/plastic-labs/honcho">Honcho</a> dialectic user modeling. Compatible with the <a href="https://agentskills.io">agentskills.io</a> open standard.</td></tr>
<tr><td><b>Scheduled automations</b></td><td>Built-in cron scheduler with delivery to any platform. Daily reports, nightly backups, weekly audits — all in natural language, running unattended.</td></tr>
<tr><td><b>Delegates and parallelizes</b></td><td>Spawn isolated subagents for parallel workstreams. In Desktop, choose their provider, model, and limits under Settings → Model → Subagents, then Apply the complete route. Write Python scripts that call tools via RPC, collapsing multi-step pipelines into zero-context-cost turns.</td></tr>
<tr><td><b>Runs anywhere, not just your laptop</b></td><td>Six built-in terminal backends — local, Docker, SSH, Modal, Daytona, and Vercel Sandbox — plus plugin backends such as Singularity/Apptainer. Daytona and Modal offer serverless persistence — your agent's environment hibernates when idle and wakes on demand, costing nearly nothing between sessions. Run it on a $5 VPS or a GPU cluster.</td></tr>
<tr><td><b>Research-ready</b></td><td>Batch trajectory generation, trajectory compression for training the next generation of tool-calling models.</td></tr>
</table>

---

## Quick Install

### Linux, macOS, WSL2

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

### Windows (native, PowerShell)

> **Heads up:** Native Windows runs Hermes without WSL — CLI, gateway, TUI, and tools all work natively. If you'd rather use WSL2, the Linux/macOS one-liner above works there too. Found a bug? Please [file issues](https://github.com/NousResearch/hermes-agent/issues).

Run this in PowerShell:

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

The source installer delegates Python 3.14, Node.js, npm, pnpm, ripgrep, FFmpeg,
and Python dependencies to PM. If Git is absent, it stages the verified Git
for Windows archive in Hermes' tool store. It does not replace your system Git.
See [installation methods](https://hermes-agent.nousresearch.com/docs/getting-started/installation)
for the separate MSIX/App Installer package and its update ownership.

> **Android / Termux:** A signed APT repository is available for aarch64 devices, with a `stable` channel (tagged releases) and a prerelease `canary` channel. The package includes Python, Node.js, and the TUI. Use the [Termux guide](https://hermes-agent.nousresearch.com/docs/getting-started/termux), not the desktop/server installer script.
>
> **Windows:** Native Windows is fully supported — the PowerShell one-liner above installs everything. If you'd rather use WSL2, the Linux command works there too. Native Windows install lives under `%LOCALAPPDATA%\hermes`; WSL2 installs under `~/.hermes` as on Linux.

After installation:

```bash
source ~/.bashrc    # reload shell (or: source ~/.zshrc)
hermes              # start chatting!
```

### Troubleshooting

#### Windows Defender or antivirus flags `uv.exe` as malware

If your antivirus (Bitdefender, Windows Defender, etc.) quarantines `uv.exe` from the Hermes `bin` folder (`%LOCALAPPDATA%\hermes\bin\uv.exe`), this is a **false positive**. The file is Astral's `uv` — the Rust Python package manager Hermes bundles to manage its Python environment. ML-based antivirus engines commonly flag unsigned Rust binaries that download and install packages.

**To verify your copy is authentic:**

```powershell
# Install GitHub CLI if needed
winget install --id GitHub.cli

# Login to GitHub
gh auth login

# Run verification
$uv = "$env:LOCALAPPDATA\hermes\bin\uv.exe"
$ver = (& $uv --version).Split(' ')[1]
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$zip = "$env:TEMP\uv.zip"
Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/$ver/uv-x86_64-pc-windows-msvc.zip" -OutFile $zip -UseBasicParsing
gh attestation verify $zip --repo astral-sh/uv
Expand-Archive $zip "$env:TEMP\uv_x" -Force
(Get-FileHash "$env:TEMP\uv_x\uv.exe").Hash -eq (Get-FileHash $uv).Hash
```

If attestation says "Verification succeeded" and the last line prints `True`, you're good.

**To whitelist Hermes:**
- **Windows Defender:** Run PowerShell as Admin → `Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\hermes\bin"`
- **Bitdefender:** Add an exception in the Bitdefender console (Protection > Antivirus > Settings > Manage Exceptions)
- Whitelist the **folder**, not the file hash — Hermes updates `uv` and the hash changes every version

For more context, see the upstream Astral reports: [astral-sh/uv#13553](https://github.com/astral-sh/uv/issues/13553), [astral-sh/uv#15011](https://github.com/astral-sh/uv/issues/15011), [astral-sh/uv#10079](https://github.com/astral-sh/uv/issues/10079).

---

## Getting Started

```bash
hermes              # Interactive CLI — start a conversation
hermes model        # Choose your LLM provider and model
hermes tools        # Configure which tools are enabled
hermes config set   # Set individual config values
hermes config get   # Print individual config values
hermes gateway      # Start the messaging gateway (Telegram, Discord, etc.)
hermes setup        # Run the full setup wizard (configures everything at once)
hermes update       # Update to the latest version
hermes doctor       # Diagnose any issues
```

📖 **[Full documentation →](https://hermes-agent.nousresearch.com/docs/)**

---

## Skip the API-key collection — Nous Portal

Hermes works with whatever provider you want — that's not changing. But if you'd rather not collect five separate API keys for the model, web search, image generation, TTS, and a cloud browser, **[Nous Portal](https://portal.nousresearch.com)** covers all of them under one subscription:

- **300+ models** — pick any of them with `/model <name>`
- **Tool Gateway** — web search, image generation (FAL), text-to-speech (OpenAI), cloud browser (Browser Use), all routed through your sub. No extra accounts.

One command from a fresh install:

```bash
hermes setup --portal
```

That logs you in via OAuth, sets Nous as your provider, and turns on the Tool Gateway. Check what's wired up any time with `hermes portal info`. Full details on the [Tool Gateway docs page](https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway).

You can still bring your own keys per-tool whenever you want — the gateway is per-backend, not all-or-nothing.

---

## CLI vs Messaging Quick Reference

Hermes has two entry points: start the terminal UI with `hermes`, or run the gateway and talk to it from Telegram, Discord, Slack, WhatsApp, Signal, or Email. Once you're in a conversation, many slash commands are shared across both interfaces.

| Action                         | CLI                                           | Messaging platforms                                                              |
| ------------------------------ | --------------------------------------------- | -------------------------------------------------------------------------------- |
| Start chatting                 | `hermes`                                      | Run `hermes gateway setup` + `hermes gateway start`, then send the bot a message |
| Start fresh conversation       | `/new` or `/reset`                            | `/new` or `/reset`                                                               |
| Change model                   | `/model [provider:model]`                     | `/model [provider:model]`                                                        |
| Set a personality              | `/personality [name]`                         | `/personality [name]`                                                            |
| Retry or undo the last turn    | `/retry`, `/undo`                             | `/retry`, `/undo`                                                                |
| Compress context / check usage | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]`                                        |
| Browse skills                  | `/skills` or `/<skill-name>`                  | `/<skill-name>`                                                                  |
| Interrupt current work         | `Ctrl+C` or send a new message                | `/stop` or send a new message                                                    |
| Platform-specific status       | `/platforms`                                  | `/status`, `/sethome`                                                            |

For the full command lists, see the [CLI guide](https://hermes-agent.nousresearch.com/docs/user-guide/cli) and the [Messaging Gateway guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging).

---

## Documentation

All documentation lives at **[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)**:

| Section                                                                                             | What's Covered                                             |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)                 | Install → setup → first conversation in 2 minutes          |
| [CLI Usage](https://hermes-agent.nousresearch.com/docs/user-guide/cli)                             | Commands, keybindings, personalities, sessions             |
| [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)               | Config file, providers, models, all options                |
| [Messaging Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)               | Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant |
| [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security)                         | Command approval, DM pairing, container isolation          |
| [Tools & Toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)           | 40+ tools, toolset system, terminal backends               |
| [Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)             | Procedural memory, Skills Hub, creating skills             |
| [Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)                    | Persistent memory, user profiles, best practices           |
| [MCP Integration](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)              | Connect any MCP server for extended capabilities           |
| [Cron Scheduling](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)             | Scheduled tasks with platform delivery                     |
| [Context Files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)      | Project context that shapes every conversation             |
| [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)            | Project structure, agent loop, key classes                 |
| [Contributing](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing)            | Development setup, PR process, code style                  |
| [CLI Reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)                 | All commands and flags                                     |
| [Environment Variables](https://hermes-agent.nousresearch.com/docs/reference/environment-variables)| Complete env var reference                                 |

---

## Migrating from OpenClaw or another agent

If you're coming from OpenClaw, Claude Code, Codex CLI or Cursor, Hermes can import your settings, memories and skills (and, for OpenClaw, API keys when you ask for them).

**During setup:** `hermes setup` asks whether to import from another agent, pre-selects the ones it finds (`~/.openclaw`, `~/.claude`, `~/.codex`, `~/.cursor`), installs the official `agent-importers` plugin and runs the import with a preview first.

**Anytime after install:**

```bash
hermes plugins install agent-importers          # once per profile
hermes import-agent openclaw                    # interactive migration (full preset)
hermes import-agent openclaw --dry-run          # preview what would be migrated
hermes import-agent openclaw --migrate-secrets  # also bring allowlisted API keys
hermes import-agent claude-code                 # or codex / cursor
```

What gets imported from OpenClaw:

- **SOUL.md** — persona file
- **Memories** — MEMORY.md and USER.md entries
- **Skills** — user-created skills → `~/.hermes/skills/openclaw-imports/`
- **Command allowlist** — approval patterns
- **Messaging settings** — platform configs, allowed users, working directory
- **API keys** — allowlisted secrets (Telegram, OpenRouter, OpenAI, Anthropic, ElevenLabs), only with `--migrate-secrets`
- **TTS assets** — workspace audio files
- **Workspace instructions** — AGENTS.md (with `--workspace-target`)

`hermes claw migrate` still works as the older spelling. See the [OpenClaw migration guide](https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw) and [Import from Other Agents](https://hermes-agent.nousresearch.com/docs/user-guide/import-from-other-agents).

---

## Contributing

We welcome contributions! See the [Contributing Guide](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing) for development setup, code style, and PR process.

Start with the [PM developer workflow](website/docs/reference/package-management.md#developer-workflow)
for activation, daily use, dependency changes, and leaving the environment.
[Development Setup](CONTRIBUTING.md#development-setup) covers the separate test environment and verification commands.

---

## Community

- 💬 [Discord](https://discord.gg/NousResearch)
- 📚 [Skills Hub](https://agentskills.io)
- 🐛 [Issues](https://github.com/NousResearch/hermes-agent/issues)
- 🔌 [computer-use-linux](https://github.com/avifenesh/computer-use-linux) — Linux desktop-control MCP server for Hermes and other MCP hosts, with AT-SPI accessibility trees, Wayland/X11 input, screenshots, and compositor window targeting.
- 🔌 [HermesClaw](https://github.com/AaronWong1999/hermesclaw) — Community WeChat bridge: Run Hermes Agent and OpenClaw on the same WeChat account.

---

## License

MIT — see [LICENSE](LICENSE).

Built by [Nous Research](https://nousresearch.com).
