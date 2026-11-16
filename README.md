<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

# hermes-fork ☤

> **This is a personal fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).** It tracks upstream and adds a layer of research-driven extensions on top. It is not an official Nous Research product — it's one person's daily driver. If you want the supported version, use the upstream repo.

<p align="center">
  <a href="https://hermes-agent.nousresearch.com/docs/"><img src="https://img.shields.io/badge/Docs-hermes--agent.nousresearch.com-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/NousResearch/hermes-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://nousresearch.com"><img src="https://img.shields.io/badge/Built%20by-Nous%20Research-blueviolet?style=for-the-badge" alt="Built by Nous Research"></a>
</p>

---

## What this fork adds over upstream

Upstream Hermes is already a capable self-improving agent. This fork extends it with a dense layer of academic-theory-grounded additions — primarily around evaluation, cron automation, plugin hardening, compaction quality, and data versioning. All additions live in `hermes-scripts/`, `fork-profile/`, and the plugin system; the core agent loop is not modified.

### Evaluation pipeline

**Compaction quality scoring** — `score-compaction-rouge.py` adds stdlib-only ROUGE-1 and ROUGE-L scoring (no pip deps) on top of the existing Jaccard distortion gate. Runs nightly as a cron job. Outputs:
- `rouge1_recall` — coverage: fraction of source n-grams preserved in the compaction
- `rouge1_precision` — fabrication guard: fraction of compaction n-grams that actually appeared in source
- Alarms at fabrication < 0.3 or coverage < 0.2, appended to `cache/compaction-rouge-scores.jsonl`
- ROUGE-L via LCS with large-input sampling (inputs >10k tokens sampled from both ends, denominators adjusted to sampled lengths)

**Existing IT-based compaction metrics** — AEP typical-set coverage, chain-rule mutual information, rate-distortion advisor, distortion gate, all running on sub-hourly cron schedules.

**JEV shadow evaluator** — `jev-turn-evaluator` plugin scores every LLM turn asynchronously via a shadow model. Gate promotes policy arms only when `scored_turns >= 20`, `mean_score >= 3.5`, `error_rate < 10%`.

**CUSUM changepoint detection** — `loop-cusum-changepoint.py` with ADV-022 ring-full freeze fix: when `n_seen == len(xs)`, resets S+/S− and re-runs over the full ring rather than processing zero new samples.

**Anytime evaluation** — anytime-eval-feeder, NSPI evaluator, skill Neyman allocation, and campaign-scorer feed a multi-arm eval scorecard updated throughout the day.

### Data versioning (Dolt-inspired)

**PK three-way merge** — `dolt-merge.py` implements Dolt's data merge semantics without Dolt itself:
- Row-keyed by primary key; different PKs auto-merge; same PK different field → field-level merge; both sides changed same field from base → explicit conflict (not silent last-write-wins)
- Conflict record: `{pk_val, field, base_val, ours_val, theirs_val}`; resolve via `strategy='ours'|'theirs'`
- JSON/dict column values: one-level sub-key merge
- Delete+modify = conflict; delete+unmodified = drop
- CLI: `dolt-merge.py merge --base B.json --ours O.json --theirs T.json --pk job_id`

**Cell changelog / blame** — `lifecycle-changelog.py` adds `fact_commits` + `fact_changelog` tables to `lifecycle.db` (append-only, never touches existing tables):
- `new_commit()`, `log_change()`, `get_history()`, `time_travel()`, `blame()`
- Read operations use `uri=ro` connections — no WAL pragma on read path
- `time_travel(db, table, pk, as_of_commit)` replays I/U/D ops through commit ancestry
- `blame(db, table, pk, field)` returns last commit that changed that field
- Initialized against the canonical shared `~/.hermes/memory-facts/lifecycle.db`

### Plugin hardening

**openshell sandbox** — all cron scripts run inside an openshell policy sandbox. The policy file (`fork-profile/openshell-policy.yaml`) is maintained with clean RO/RW separation: `fork/logs` is write-only (RW), not duplicated in read-only. `HERMES_NO_SANDBOX=1` is explicitly blocked in the cron wrapper as a security boundary — bypass attempts are logged and ignored.

**Governance hard-block** — `governance-hard-block` plugin enforces adversarial policy rules. Settings declared in `config.yaml` under `plugins.entries.governance-hard-block`.

**compaction-gate** — `depth_threshold` and `mdl_min_saving` now explicitly declared in `plugins.entries.compaction-gate.settings` (were silently using hardcoded defaults).

**Plugin wiring audits** — periodic cold adversarial pass covers: py_compile + importlib load of all 23 enabled plugins, VALID_HOOKS alignment, shadow post_llm_call compliance, HERMES_HOME path-doubling, SQLite connect patterns.

### Cron infrastructure

Over 100 cron jobs organized into categories: compaction eval, memory maintenance, skill evaluation, security audits, system updates, and research pipelines. Key additions over upstream:

- **System update** (`daily-silverblue-update.sh`) — per-step timeouts: toolbox DNF (1200s), fwupdmgr (300s), git repos (60s each); flatpak appstream-only errors treated as non-fatal
- **Skill index rebuild** — weekly rebuild now correctly passes `--build` to `skill-router-index.py` (was silently a no-op)
- **ROUGE scorer** — nightly at 04:50, reads latest pre/post cache files, appends to `compaction-rouge-scores.jsonl`
- **lifecycle-db-migrate** — idempotent schema migration, exits 0 on already-populated DB

### Research scripts

`hermes-scripts/` contains ~40 research scripts implementing: anytime algorithms (Zilberstein/Dean-Boddy), CUSUM changepoint detection, conformal prediction, LLM autoscaling, skill routing bandit (wave routing + NSPI), encoding ranking, campaign scoring, two-timescale convergence checks, moment-edge sampling, and skill confidence calibration.

---

## Upstream merge policy

This fork rebases or merges from `NousResearch/hermes-agent` main periodically. Conflicts are resolved in favour of upstream on the core agent loop; fork additions win on scripts and plugins. Merge conflicts are recorded in git history.

**Current base:** See `git log --oneline upstream/main..HEAD` for fork-only commits.

---

## Running this fork

Same as upstream hermes, with the `fork` profile active:

```bash
hermes-fork          # start CLI on the fork profile
hermes-fork doctor   # health check
hermes-fork -z       # fork profile with zero context (fresh session)
```

The fork profile lives at `~/.hermes/profiles/fork/`. The binary at `~/.local/bin/hermes-fork` pins to the Py3.14 store interpreter (not the venv/bin/hermes 3.11 build — pydantic_core ABI mismatch).

---

## What is NOT different from upstream

- The core agent loop, tool dispatch, and plugin API are unmodified
- Installation procedure — same as upstream
- Model provider support — same as upstream
- MCP integration — same as upstream
- Messaging gateway — same as upstream

For anything not in this README, the upstream documentation applies: **[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)**

---

## Original upstream README

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
<tr><td><b>A closed learning loop</b></td><td>Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks. Skills self-improve during use. FTS5 session search with LLM summarization for cross-session recall. <a href="https://github.com/plastic-labs/honcho">Honcho</a> dialectic user modeling. Compatible with the <a href="https://agentskills.io">agentskills.io</a> open standard.</td></tr>
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
