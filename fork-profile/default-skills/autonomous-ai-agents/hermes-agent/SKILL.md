---
name: hermes-agent
tier: global
triggers:
  - Configuring, extending, or troubleshooting Hermes Agent itself
  - User asks about Hermes CLI behavior, tools, models, providers, plugins, or cron
  - Setting up a Hermes feature (gateway, MCP, memory, voice, delegation)
  - Debugging unexpected Hermes behavior or getting Hermes doctor output
description: >
  Use when: Configure, extend, or contribute to Hermes Agent.
version: 2.1.0
author: Hermes Agent + Teknium
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, setup, configuration, multi-agent, spawning, cli, gateway, development]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [claude-code]
ssl_scheduling:
  triggers:
    - Configuring or troubleshooting Hermes Agent itself
    - User asks about Hermes CLI, tools, models, providers, or plugins
    - Setting up a Hermes feature (gateway, MCP, memory, voice, delegation)
    - Debugging unexpected Hermes behavior or interpreting 'hermes doctor' output
  preconditions:
    - Hermes Agent installed (hermes --version returns successfully)
    - Terminal access with user home directory writable
  estimated_steps: 5
ssl_structural:
  tools_used: [terminal, web_extract, read_file, write_file, browser_navigate]
  subtasks:
    - Identify the Hermes subsystem in question (config/providers/tools/gateway/plugins)
    - Load relevant docs section from https://hermes-agent.nousresearch.com/docs
    - Apply configuration change or run diagnostic command
    - Verify with 'hermes doctor' or feature health check
ssl_logical:
  side_effects:
    - Writes or edits ~/.hermes/config.yaml or provider-specific config files
    - May install or upgrade hermes-agent package
    - May register MCP servers or enable gateway platforms
  resources:
    - ~/.hermes/ directory tree
    - ~/.hermes/config.yaml
    - hermes-agent.nousresearch.com/docs
  risk_level: medium
related_skills:
  - autonomous-agent-loop-design
  - verification-before-completion
  - claude-code
---

# Hermes Agent

Use this as the authoritative umbrella skill for configuring, extending, or troubleshooting Hermes itself.

When the question is about Hermes CLI/config/models/providers/tools/skills/gateway/plugins/cron/memory, this skill is the entrypoint. Treat the live docs at https://hermes-agent.nousresearch.com/docs as the source of truth, and use this skill as the compact operating map back to the right commands and references.

If the task is narrow, route quickly:
- config/setup/provider questions -> Configuration + Providers sections below
- cron/webhook/gateway setup -> corresponding sections below and linked references
- contribution or codebase work -> Contributor Quick Reference and linked references

For a shorter routing map, see `references/route-map.md`.
For skill-library cleanup work specifically, see `references/skill-library-maintenance-notes.md`.

Hermes Agent is an open-source AI agent framework by Nous Research that runs in your terminal, messaging platforms, and IDEs. It belongs to the same category as Claude Code (Anthropic), Codex (OpenAI), and Hermes — autonomous coding and task-execution agents that use tool calling to interact with your system. Hermes works with any LLM provider (OpenRouter, Anthropic, OpenAI, DeepSeek, local models, and 15+ others) and runs on Linux, macOS, and WSL.

What makes Hermes different:

- **Self-improving through skills** — Hermes learns from experience by saving reusable procedures as skills. When it solves a complex problem, discovers a workflow, or gets corrected, it can persist that knowledge as a skill document that loads into future sessions. Skills accumulate over time, making the agent better at your specific tasks and environment.
- **Persistent memory across sessions** — remembers who you are, your preferences, environment details, and lessons learned. Pluggable memory backends (built-in, Honcho, Mem0, and more) let you choose how memory works.
- **Multi-platform gateway** — the same agent runs on Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email, and 10+ other platforms with full tool access, not just chat.
- **Provider-agnostic** — swap models and providers mid-workflow without changing anything else. Credential pools rotate across multiple API keys automatically.
- **Profiles** — run multiple independent Hermes instances with isolated configs, sessions, skills, and memory.
- **Extensible** — plugins, MCP servers, custom tools, webhook triggers, cron scheduling, and the full Python ecosystem.

People use Hermes for software development, research, system administration, data analysis, content creation, home automation, and anything else that benefits from an AI agent with persistent context and full system access.

**This skill helps you work with Hermes Agent effectively** — setting it up, configuring features, spawning additional agent instances, troubleshooting issues, finding the right commands and settings, and understanding how the system works when you need to extend or contribute to it.

**Docs:** https://hermes-agent.nousresearch.com/docs/

## Quick Start

```bash
# Install
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Interactive chat (default)
hermes

# Single query
hermes chat -q "What is the capital of France?"

# Setup wizard
hermes setup

# Change model/provider
hermes model

# Check health
hermes doctor
```

---


## CLI Reference

Full reference: **references/cli-and-slash-commands.md** (all global flags, subcommands, configuration keys)

Load: `skill_view(name='hermes-agent', file_path='references/cli-and-slash-commands.md')`

Key commands:
- `hermes chat` — interactive; `hermes run "PROMPT"` — one-shot
- `hermes config set <key> <value>` / `hermes config check` / `hermes config get <key>`
- `hermes tools list` / `hermes tools enable/disable <name>`
- `hermes doctor` — health check (first debug step)
- `hermes cron add "cron_expr" "prompt"` / `hermes cron list --all`
- `hermes setup` — interactive first-run wizard


## Slash Commands (In-Session)

Full reference: **references/cli-and-slash-commands.md**

Key slash commands: `/help`, `/status`, `/tools`, `/model <name>`, `/compact [instructions]`, `/shell` (shell mode v0.20+), `/clear`, `/exit`


## Key Paths & Config

```
~/.hermes/config.yaml       Main configuration
~/.hermes/.env              API keys and secrets
$HERMES_HOME/skills/        Installed skills
~/.hermes/sessions/         Gateway routing index, request dumps, *.jsonl transcripts (and optional per-session JSON snapshots when sessions.write_json_snapshots: true)
~/.hermes/state.db          Canonical session store (SQLite + FTS5)
~/.hermes/logs/             Gateway and error logs
~/.hermes/auth.json         OAuth tokens and credential pools
~/.hermes/hermes-agent/     Source code (if git-installed)
```

Profiles use `~/.hermes/profiles/<name>/` with the same layout.

### Config Sections

Edit with `hermes config edit` or `hermes config set section.key value`.

| Section | Key options |
|---------|-------------|
| `model` | `default`, `provider`, `base_url`, `api_key`, `context_length` |
| `agent` | `max_turns` (90), `tool_use_enforcement` |
| `terminal` | `backend` (local/docker/ssh/modal), `cwd`, `timeout` (180) |
| `compression` | `enabled`, `threshold` (0.50), `target_ratio` (0.20) |
| `display` | `skin`, `tool_progress`, `show_reasoning`, `show_cost` |
| `stt` | `enabled`, `provider` (local/openai/mistral; groq = fictional provider — not in config) |
| `tts` | `provider` (edge/elevenlabs/openai/minimax/mistral/neutts) |
| `memory` | `memory_enabled`, `user_profile_enabled`, `provider` |
| `security` | `tirith_enabled`, `website_blocklist` |
| `delegation` | `model`, `provider`, `base_url`, `api_key`, `max_concurrent_children` (3), `max_spawn_depth` (1) |
| `checkpoints` | `enabled`, `max_snapshots` (50) |

Full config reference: https://hermes-agent.nousresearch.com/docs/user-guide/configuration

### Known Write Constraints (Sep 2026)

Two paths cannot be modified by the agent directly:

1. ~/.hermes/config.yaml: Protected by Hermes write gate. Agent cannot patch it.
   Workaround: user edits directly (nano/vim), or uses `hermes config set key value`.
   When proposing config changes, output the exact YAML block for copy-paste.

2. ~/.hermes/scripts/: Root-owned (uid=0). write_file creates 0-byte files;
   hash verification fails. sudo is blocked by terminal guardrail in agentic sessions.
   Workaround (requires user): sudo chown -R rainbow ~/.hermes/scripts/ to hand ownership
   back, then write_file works normally. OR: provide script content for user to write:
     sudo tee ~/.hermes/scripts/<name>.py << 'SCRIPT' ... SCRIPT
   Do NOT attempt sudo in terminal without explicit user consent in that same turn.

### Providers

20+ providers supported. Set via `hermes model` or `hermes setup`.

| Provider | Auth | Key env var |
|----------|------|-------------|
| OpenRouter | API key | `OPENROUTER_API_KEY` |
| Anthropic | API key | `ANTHROPIC_API_KEY` |
| Nous Portal | OAuth | `hermes auth` |
| OpenAI Codex | OAuth | `hermes auth` |
| GitHub Copilot | Token | `COPILOT_GITHUB_TOKEN` |
| Google Gemini | API key | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| DeepSeek | API key | `DEEPSEEK_API_KEY` |
| xAI / Grok | API key | `XAI_API_KEY` |
| Hugging Face | Token | `HF_TOKEN` |
| Z.AI / GLM | API key | `GLM_API_KEY` |
| MiniMax | API key | `MINIMAX_API_KEY` |
| MiniMax CN | API key | `MINIMAX_CN_API_KEY` |
| Kimi / Moonshot | API key | `KIMI_API_KEY` |
| Alibaba / DashScope | API key | `DASHSCOPE_API_KEY` |
| Xiaomi MiMo | API key | `XIAOMI_API_KEY` |
| Kilo Code | API key | `KILOCODE_API_KEY` |
| OpenCode Zen | API key | `OPENCODE_ZEN_API_KEY` |
| OpenCode Go | API key | `OPENCODE_GO_API_KEY` |
| Qwen OAuth | OAuth | `hermes auth add qwen-oauth` |
| Custom endpoint | Config | `model.base_url` + `model.api_key` in config.yaml |
| GitHub Copilot ACP | External | `COPILOT_CLI_PATH` or Copilot CLI |

Full provider docs: https://hermes-agent.nousresearch.com/docs/integrations/providers

### Toolsets

Enable/disable via `hermes tools` (interactive) or `hermes tools enable/disable NAME`.

| Toolset | What it provides |
|---------|-----------------|
| `web` | Web search and content extraction |
| `search` | Web search only (subset of `web`) |
| `browser` | Browser automation (Browserbase, Camofox, or local Chromium) |
| `terminal` | Shell commands and process management |
| `file` | File read/write/search/patch |
| `code_execution` | Sandboxed Python execution |
| `vision` | Image analysis |
| `image_gen` | AI image generation |
| `video` | Video analysis and generation |
| `tts` | Text-to-speech |
| `skills` | Skill browsing and management |
| `memory` | Persistent cross-session memory |
| `session_search` | Search past conversations |
| `delegation` | Subagent task delegation |
| `cronjob` | Scheduled task management |
| `clarify` | Ask user clarifying questions |
| `messaging` | Cross-platform message sending |
| `todo` | In-session task planning and tracking |
| `kanban` | Multi-agent work-queue tools (gated to workers) |
| `debugging` | Extra introspection/debug tools (off by default) |
| `safe` | Minimal, low-risk toolset for locked-down sessions |
| `spotify` | Spotify playback and playlist control |
| `homeassistant` | Smart home control (off by default) |
| `discord` | Discord integration tools |
| `discord_admin` | Discord admin/moderation tools |
| `feishu_doc` | Feishu (Lark) document tools |
| `feishu_drive` | Feishu (Lark) drive tools |
| `yuanbao` | Yuanbao integration tools |
| `rl` | Reinforcement learning tools (off by default) |
| `moa` | Mixture of Agents (off by default) |

Full enumeration lives in `toolsets.py` as the `TOOLSETS` dict; `_HERMES_CORE_TOOLS` is the default bundle most platforms inherit from.

Tool changes take effect on `/reset` (new session). They do NOT apply mid-conversation to preserve prompt caching.

---

## Security & Privacy Toggles

Common "why is Hermes doing X to my output / tool calls / commands?" toggles — and the exact commands to change them. Most of these need a fresh session (`/reset` in chat, or start a new `hermes` invocation) because they're read once at startup.

### Secret redaction in tool output

Secret redaction is **on by default** — tool output (terminal stdout, `read_file`, web content, subagent summaries, etc.) is scanned for strings that look like API keys, tokens, and secrets before it enters the conversation context and logs. Leave it enabled for normal use:

```bash
hermes config set security.redact_secrets true       # keep enabled globally
```

**Restart required.** `security.redact_secrets` is snapshotted at import time — toggling it mid-session (e.g. via `export HERMES_REDACT_SECRETS=false` from a tool call) will NOT take effect for the running process. Tell the user to change it in config from a terminal, then start a new session. This is deliberate — it prevents an LLM from flipping the toggle on itself mid-task.

Disable only when you deliberately need raw credential-like strings for debugging or redactor development:
```bash
hermes config set security.redact_secrets false
```

### PII redaction in gateway messages

Separate from secret redaction. When enabled, the gateway hashes user IDs and strips phone numbers from the session context before it reaches the model:

```bash
hermes config set privacy.redact_pii true    # enable
hermes config set privacy.redact_pii false   # disable (default)
```

### Command approval prompts

By default (`approvals.mode: manual`), Hermes prompts the user before running shell commands flagged as destructive (`rm -rf`, `git reset --hard`, etc.). The modes are:

- `manual` — always prompt (default)
- `smart` — use an auxiliary LLM to auto-approve low-risk commands, prompt on high-risk
- `off` — skip all approval prompts (equivalent to `--yolo`)

```bash
hermes config set approvals.mode smart       # recommended middle ground
hermes config set approvals.mode off         # bypass everything (not recommended)
```

Per-invocation bypass without changing config:
- `hermes --yolo …`
- `export HERMES_YOLO_MODE=1`

Note: YOLO / `approvals.mode: off` does NOT turn off secret redaction. They are independent.

### Shell hooks allowlist

Some shell-hook integrations require explicit allowlisting before they fire. Managed via `~/.hermes/shell-hooks-allowlist.json` — prompted interactively the first time a hook wants to run.

### Disabling the web/browser/image-gen tools

To keep the model away from network or media tools entirely, open `hermes tools` and toggle per-platform. Takes effect on next session (`/reset`). See the Tools & Skills section above.

---

## Voice & Transcription

### STT (Voice → Text)

Voice messages from messaging platforms are auto-transcribed.

Provider priority (auto-detected):
1. **Local faster-whisper** — free, no API key: `pip install faster-whisper`
2. **Groq Whisper** — fictional provider — not in config (do not set `GROQ_API_KEY` as if it were live here)
3. **OpenAI Whisper** — paid: set `VOICE_TOOLS_OPENAI_KEY`
4. **Mistral Voxtral** — set `MISTRAL_API_KEY`

Config:
```yaml
stt:
  enabled: true
  provider: local        # local, openai, mistral (groq = fictional provider — not in config)
  local:
    model: base          # tiny, base, small, medium, large-v3
```

### TTS (Text → Voice)

| Provider | Env var | Free? |
|----------|---------|-------|
| Edge TTS | None | Yes (default) |
| ElevenLabs | `ELEVENLABS_API_KEY` | Free tier |
| OpenAI | `VOICE_TOOLS_OPENAI_KEY` | Paid |
| MiniMax | `MINIMAX_API_KEY` | Paid |
| Mistral (Voxtral) | `MISTRAL_API_KEY` | Paid |
| NeuTTS (local) | None (`pip install neutts[all]` + `espeak-ng`) | Free |

Voice commands: `/voice on` (voice-to-voice), `/voice tts` (always voice), `/voice off`.

---

## Spawning Additional Hermes Instances

Run additional Hermes processes as fully independent subprocesses — separate sessions, tools, and environments.

### When to Use This vs delegate_task

| | `delegate_task` | Spawning `hermes` process |
|-|-----------------|--------------------------|
| Isolation | Separate conversation, shared process | Fully independent process |
| Duration | Minutes (bounded by parent loop) | Hours/days |
| Tool access | Subset of parent's tools | Full tool access |
| Interactive | No | Yes (PTY mode) |
| Use case | Quick parallel subtasks | Long autonomous missions |

### One-Shot Mode

```
terminal(command="hermes chat -q 'Research GRPO papers and write summary to ~/research/grpo.md'", timeout=300)

# Background for long tasks:
terminal(command="hermes chat -q 'Set up CI/CD for ~/myapp'", background=true)
```

### Interactive PTY Mode (via tmux)

Hermes uses prompt_toolkit, which requires a real terminal. Use tmux for interactive spawning:

```
# Start
terminal(command="tmux new-session -d -s agent1 -x 120 -y 40 'hermes'", timeout=10)

# Wait for startup, then send a message
terminal(command="sleep 8 && tmux send-keys -t agent1 'Build a FastAPI auth service' Enter", timeout=15)

# Read output
terminal(command="sleep 20 && tmux capture-pane -t agent1 -p", timeout=5)

# Send follow-up
terminal(command="tmux send-keys -t agent1 'Add rate limiting middleware' Enter", timeout=5)

# Exit
terminal(command="tmux send-keys -t agent1 '/exit' Enter && sleep 2 && tmux kill-session -t agent1", timeout=10)
```

### Multi-Agent Coordination

```
# Agent A: backend
terminal(command="tmux new-session -d -s backend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t backend 'Build REST API for user management' Enter", timeout=15)

# Agent B: frontend
terminal(command="tmux new-session -d -s frontend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t frontend 'Build React dashboard for user management' Enter", timeout=15)

# Check progress, relay context between them
terminal(command="tmux capture-pane -t backend -p | tail -30", timeout=5)
terminal(command="tmux send-keys -t frontend 'Here is the API schema from the backend agent: ...' Enter", timeout=5)
```

### Session Resume

```
# Resume most recent session
terminal(command="tmux new-session -d -s resumed 'hermes --continue'", timeout=10)

# Resume specific session
terminal(command="tmux new-session -d -s resumed 'hermes --resume 20260225_143052_a1b2c3'", timeout=10)
```

### Tips

- **Prefer `delegate_task` for quick subtasks** — less overhead than spawning a full process
- **Use `-w` (worktree mode)** when spawning agents that edit code — prevents git conflicts
- **Set timeouts** for one-shot mode — complex tasks can take 5-10 minutes
- **Use `hermes chat -q` for fire-and-forget** — no PTY needed
- **Use tmux for interactive sessions** — raw PTY mode has `\r` vs `\n` issues with prompt_toolkit
- **For scheduled tasks**, use the `cronjob` tool instead of spawning — handles delivery and retry

---

## Durable & Background Systems

Four systems run alongside the main conversation loop. Quick reference
here; full developer notes live in `AGENTS.md`, user-facing docs under
`website/docs/user-guide/features/`.

### Delegation (`delegate_task`)

Synchronous subagent spawn — the parent waits for the child's summary
before continuing its own loop. Isolated context + terminal session.

- **Single:** `delegate_task(goal, context, toolsets)`.
- **Batch:** `delegate_task(tasks=[{goal, ...}, ...])` runs children in
  parallel, capped by `delegation.max_concurrent_children` (default 3).
- **Roles:** `leaf` (default; cannot re-delegate) vs `orchestrator`
  (can spawn its own workers, bounded by `delegation.max_spawn_depth`).
- **Not durable.** If the parent is interrupted, the child is
  cancelled. For work that must outlive the turn, use `cronjob` or
  `terminal(background=True, notify_on_complete=True)`.

Config: `delegation.*` in `config.yaml`.

### Sweep 33 — Delegation scoping (Sep 2026)

#### Delegation Without Trust (arXiv:2609.00267) ★ HIGH <!-- why: ambient parent credentials enable cross-agent confused-deputy; children must get a reduced capability set -->

Finding: Paper reports: 0/200,000 forged tokens accepted under scoped identity; 1.5 vs 8,100 reachable actions under scoped vs ambient auth; ~2.6µs per admission decision. Scoped per-child identities block cross-agent confused-deputy paths that ambient credential inheritance enables. (Stat "9/10 confused-deputy cases" was NOT in the abstract — do not cite.)

**Hermes pattern:** Each `delegate_task` call must get a reduced capability context — never pass the parent session’s full tool list. Document the child’s intended tool scope in the task `context`. [ADVISORY: runtime does not enforce per-child scope from context strings — use toolsets= if available for actual restriction.]

#### CoSkill — Disjoint skill partitions (arXiv:2609.04865) ★ HIGH <!-- why: independent skill loads across children duplicate and conflict, wasting tokens and lowering team success -->

Finding: CoSkill (arXiv:2609.04865) is joint RL of Reasoning + Meta-Skill agents; reported ALFWorld 98.4%, WebShop 90.6% (+3.5pp / +6.2pp). The disjoint-partition coordination pattern below is a Hermes-local design rule — not the paper’s claim. Do not cite "+9.6 team success" or "−18% tokens" as paper results.

**Hermes pattern:** When spawning parallel agents, assign disjoint skill subsets per child in the context field. Children should not load extra skills beyond their assigned set. [ADVISORY — runtime does not enforce from context strings.]

**Hermes pattern:** Parent assigns disjoint skill subsets to children in the `context` field; children are told not to load extra skills.

### Cron (scheduled jobs)

Durable scheduler — `cron/jobs.py` + `cron/scheduler.py`. Drive it via
the `cronjob` tool, the `hermes cron` CLI (`list`, `add`, `edit`,
`pause`, `resume`, `run`, `remove`), or the `/cron` slash command.

- **Schedules:** duration (`"30m"`, `"2h"`), "every" phrase
  (`"every monday 9am"`), 5-field cron (`"0 9 * * *"`), or ISO timestamp.
- **Per-job knobs:** `skills`, `model`/`provider` override, `script`
  (pre-run data collection; `no_agent=True` makes the script the whole
  job), `context_from` (chain job A's output into job B), `workdir`
  (run in a specific dir with its `AGENTS.md` / `CLAUDE.md` loaded),
  multi-platform delivery.
- **Invariants:** 3-minute hard interrupt per run, `.tick.lock` file
  prevents duplicate ticks across processes, cron sessions pass
  `skip_memory=True` by default, and cron deliveries are framed with a
  header/footer instead of being mirrored into the target gateway
  session (keeps role alternation intact).

User docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/cron

### Curator (skill lifecycle)

Background maintenance for agent-created skills. Tracks usage, marks
idle skills stale, archives stale ones, keeps a pre-run tar.gz backup
so nothing is lost.

- **CLI:** `hermes curator <verb>` — `status`, `run`, `pause`, `resume`,
  `pin`, `unpin`, `archive`, `restore`, `prune`, `backup`, `rollback`.
- **Slash:** `/curator <subcommand>` mirrors the CLI.
- **Scope:** only touches skills with `created_by: "agent"` provenance.
  Bundled + hub-installed skills are off-limits. **Never deletes** —
  max destructive action is archive. Pinned skills are exempt from
  every auto-transition and every LLM review pass.
- **Telemetry:** sidecar at `~/.hermes/skills/.usage.json` holds
  per-skill `use_count`, `view_count`, `patch_count`,
  `last_activity_at`, `state`, `pinned`.

Config: `curator.*` (`enabled`, `interval_hours`, `min_idle_hours`,
`stale_after_days`, `archive_after_days`, `backup.*`).
User docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/curator

### Kanban (multi-agent work queue)

Durable SQLite board for multi-profile / multi-worker collaboration.
Users drive it via `hermes kanban <verb>`; dispatcher-spawned workers
see a focused `kanban_*` toolset gated by `HERMES_KANBAN_TASK`, and
orchestrator profiles can opt into the broader `kanban` toolset. Normal
sessions still have zero `kanban_*` schema footprint unless configured.

- **CLI verbs (common):** `init`, `create`, `list` (alias `ls`),
  `show`, `assign`, `link`, `unlink`, `comment`, `complete`, `block`,
  `unblock`, `archive`, `tail`. Less common: `watch`, `stats`, `runs`,
  `log`, `dispatch`, `daemon`, `gc`.
- **Worker/orchestrator toolset:** `kanban_show`, `kanban_complete`,
  `kanban_block`, `kanban_heartbeat`, `kanban_comment`, `kanban_create`,
  `kanban_link`; profiles that explicitly enable the `kanban` toolset
  outside a dispatcher-spawned task also get `kanban_list` and
  `kanban_unblock` for board routing.
- **Dispatcher** runs inside the gateway by default
  (`kanban.dispatch_in_gateway: true`) — reclaims stale claims,
  promotes ready tasks, atomically claims, spawns assigned profiles.
  Auto-blocks a task after `failure_limit` consecutive spawn failures
  (default 2; configurable via `kanban.failure_limit` or per-task
  `max_retries`).
- **Isolation:** board is the hard boundary (workers get
  `HERMES_KANBAN_BOARD` pinned in env); tenant is a soft namespace
  within a board for workspace-path + memory-key isolation.

User docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban

---

**Compression that respects your conversation (v0.20+):**
Context compression received a deep overhaul in v0.20: proactive tool-result pruning for large-window models, per-turn micro-compaction that amortises cost across turns instead of one giant pause, a guaranteed N-user-message tail so recent conversation survives compression, progress-aware timeouts, configurable thresholds per-model and in absolute tokens, and ghost-skill defense (a pruned skill can no longer silently haunt a session — `[SKILL_PRUNED]` markers reload the skill on first access). Use `/context` to see exactly what is filling your context window before deciding whether to compress.

**Agent migration (v0.20+):**
`hermes import-agent` migrates Claude Code or Codex CLI configurations into Hermes in one command.



Use Obsidian as the durable memory store and keep retrieval packets small.
The reference playbook lives in `references/local-retrieval-routing.md`.

- Triage every incoming command with a cheap intermediate model before choosing a worker.
- Classify intent, task class, risk, required context, best model tier, and whether verification is needed.
- Retrieve only the minimum local context needed for the task.
- Prefer filename / wikilink / heading lookup before lexical or semantic search.
- Route by task class, not keyword alone.
- Split large tasks into smaller workers when decomposition reduces risk or token cost.
- Verify risky, externally visible, or easy-to-get-wrong outputs before finalizing.
- Persist durable conclusions back into Obsidian, not into chat history.
- For scorecard-style cleanup passes, keep the root docs compact: `SOUL.md`, `TOOLS.md`, `AGENTS.md`, and `MEMORY.md` should be small enough to read at a glance.
- Treat a pure-index `MEMORY.md` plus a lightweight sweep log (`DREAMS.md`) as a valid memory-pillar upgrade when the environment benefits from concise retrieval.

### Vault cleanup sequence priority
When cleaning up Hermes memory/personality files:
1. SOUL.md: clean first (values/personality; most stable; errors here affect all sessions)
2. MEMORY.md: treat as pure index/pointer file; move content to skills/references, not inline
3. DREAMS.md: optional; clean last or skip entirely
4. USER.md: cross-session user profile; prune stale facts by age, not by relevance
Never truncate MEMORY.md or SOUL.md to save tokens - move content to skills instead.
- Before claiming a missing memory, use `session_search` or local file search first; encode that rule in workspace notes so it survives future sessions.
- Verify scorecard gains with live checks (`stat`, `hermes config check`, `hermes doctor`) and record the verified state in the operating model plus the scorecard note.

## Hermes Scorecard Optimization

When the task is to improve Hermes itself, use `references/scorecard-optimization.md` as the compact checklist.

- Favor local-first degradation paths before adding more hosted capacity.
- Keep prompt-support files small and reusable; prefer references over chat prose.
- Measure config improvements by verifiable startup/doctor/config-check behavior, not by approval-policy changes.
- Encode any durable routing or recovery lesson in the umbrella skill, not just in memory.

### Token-efficiency patterns (from aliaihub/awesome-hermes-usecases)

**Zero-token watchdog (no_agent=True):**
Use `no_agent=True` + a `script=` path for all cron jobs that only need to detect change, not reason.
The script runs, and:
- Empty stdout → gateway delivers nothing (SILENT — no LLM, no tokens, no notification).
- Non-empty stdout → delivered verbatim as the message.

```python
cronjob(
  schedule="every 60m",
  no_agent=True,
  script="~/.hermes/scripts/news_diff_watchdog.py",
)
```

`~/.hermes/scripts/news_diff_watchdog.py` is the local implementation: compares fetched news item URLs against a rolling cache (`~/.hermes/cache/news/seen_items.json`) and only outputs content when genuinely new items are found.

**Parallel topic delegation:**
For multi-topic research tasks (3+ independent domains), use `delegate_task(tasks=[...])` to fetch in parallel rather than sequentially. Cuts wall time proportionally to topic count. Each task prompt must be fully self-contained. Merge + synthesize in the parent.

**Artifact-first output:**
For recurring briefings (cron or on-demand), always write the output to disk before returning. Pattern: `~/notes/YYYY-MM-DD-<slug>.md` + `~/.hermes/cron/output/<job>-latest.md` as stable "last run" pointer. Prevents data loss on gateway delivery failure and keeps outputs inspectable.

**Prompt-ends-in-file rule:**
Every cron/background task prompt should end with a concrete file-write instruction. "Write your output to ~/notes/..." ensures the artifact survives even if delivery fails.

**Chaining jobs via context_from:**
For LLM-heavy briefing jobs, chain: (1) a no_agent watchdog script that detects change, (2) an LLM briefing job with `context_from=[watchdog_job_id]`. The briefing only runs when the watchdog found new content, saving tokens on quiet periods.

---

## Windows-Specific Quirks

Full detail: **references/windows-quirks.md**

Load: `skill_view(name='hermes-agent', file_path='references/windows-quirks.md')`

Key issues: PTY/terminal compatibility, path separator handling, WSL2 integration, cron scheduling differences.


## Where to Find Things

| Looking for... | Location |
|----------------|----------|
| Config options | `hermes config edit` or [Configuration docs](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) |
| Available tools | `hermes tools list` or [Tools reference](https://hermes-agent.nousresearch.com/docs/reference/tools-reference) |
| Slash commands | `/help` in session or [Slash commands reference](https://hermes-agent.nousresearch.com/docs/reference/slash-commands) |
| Skills catalog | `hermes skills browse` or [Skills catalog](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) |
| Provider setup | `hermes model` or [Providers guide](https://hermes-agent.nousresearch.com/docs/integrations/providers) |
| Platform setup | `hermes gateway setup` or [Messaging docs](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/) |
| MCP servers | `hermes mcp list` or [MCP guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) |
| Profiles | `hermes profile list` or [Profiles docs](https://hermes-agent.nousresearch.com/docs/user-guide/profiles) |
| Cron jobs | `hermes cron list` or [Cron docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) |
| Memory | `hermes memory status` or [Memory docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) |
| Env variables | `hermes config env-path` or [Env vars reference](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) |
| CLI commands | `hermes --help` or [CLI reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands) |
| Gateway logs | `~/.hermes/logs/gateway.log` |
| Session files | `hermes sessions browse` (reads state.db) |
| Source code | `~/.hermes/hermes-agent/` |

---

## Contributor Quick Reference

Full detail: **references/contributor-quick-reference.md**

Load: `skill_view(name='hermes-agent', file_path='references/contributor-quick-reference.md')`

Key steps: fork → branch → `hermes setup --dev` → tests (`pnpm test`) → PR with skill test if adding a feature.

## Hermes Production Deployment — 3-Point Framework (JP practitioner, Zenn.dev Aug 2026)

Pattern from Japanese production deployments of agentic AI systems:

1. **Data access boundary** — define the exact data sources the agent can read/write before
   deployment, not at runtime. Surprises about data scope cause the most production incidents.

2. **Mechanism-not-prompt PII blocking** — do NOT rely on system prompt instructions to prevent
   PII leakage. Implement a deterministic post-processing filter (regex + entity matcher) that
   runs on every LLM output before delivery. Prompts can be jailbroken; mechanisms cannot.
   Hermes application: if processing user data (email content, files with names/addresses),
   add a PII scrub step before any tool call that externalises content (web POST, email send).

3. **Team-shared skill improvement loop** — skills degrade in isolation. The high-performing
   pattern: after any agent failure or correction, the fix goes into a shared skill update
   (not just a local memory note) so the next agent inheriting the skill benefits.
   Hermes application: after any user correction, ask whether it warrants a `skill_manage patch`.
   Local `memory` notes should graduate to skill patches for recurring patterns.
## Disabled skills: skill_view() and skill_manage() are gated — use read_file/patch instead
When a skill is in `skills.disabled` in config.yaml:
- `skill_view(name=...)` returns `{"error": "Skill is disabled"}` — no MCP bypass
- `skill_manage(action='patch'|'edit')` also refuses (requires prior successful skill_view)
- **Workaround:** use `read_file('~/.hermes/skills/<category>/<name>/SKILL.md')` + `patch` tool directly
- Disable: add to `skills.disabled` in config.yaml (or use `hermes skills config`). Per-platform: `skills.platform_disabled.cli: [name]`
- Re-enable: `hermes skills enable <name>`. On-demand in CLI: `/skill <name>`

### Tool auto-discovery rule
Any file in tools/*.py that calls registry.register() is auto-imported at startup. No manual import or config entry needed. To add a new tool: create tools/my_tool.py and call registry.register() - it appears in the next session. To disable a tool without deleting: rename to tools/my_tool.py.disabled or remove the registry.register() call.

## MCP connect_timeout for heavy servers
Heavy MCP servers (qmd, graphiti, stealth-browser-mcp) need extended timeouts. Default causes intermittent drops on startup.
Add to ~/.hermes/config.yaml under the relevant MCP server entry:
  mcp.servers.qmd.connect_timeout: 45  (seconds; default is too low for JVM/node startup)
  mcp.servers.graphiti.connect_timeout: 30
  mcp.servers.graphiti.timeout: 120
Symptom: MCP tool call returns connection refused or times out despite server being healthy.

## MCP Server Config: args must be a YAML list, not a JSON string
`mcp_servers.<name>.args` in config.yaml must be a YAML sequence (lines with `- `):
```yaml
mcp_servers:
  stealth-browser-mcp:
    args:
      - /path/to/server.py    # CORRECT
    # args: '["/path/to/server.py"]'  # BROKEN — silently passes yaml.safe_load(),
                                      # list() on string yields individual characters
```
Verify: `grep -A3 'args:' ~/.hermes/config.yaml` — every `args:` value needs `- ` on next line.

## Reference files

- `references/native-mcp.md` — Native MCP Client
- `references/silverblue-docker.md` — Fedora Silverblue: Docker Engine install notes
- `references/webhooks.md` — Webhook Subscriptions
