# Local Inference Patterns for Multi-Agent Nightshift (Aug 2026)

Source: r/LocalLLaMA, Aug 14 2026 — community-discovered patterns for local LLM nightshift agents.
**Note for maintainer:** These patterns should be promoted into SKILL.md body. File created because
the read-before-write guard prevented same-turn SKILL.md patches after context dedup.

---

## KV Cache RAM-Swap for Sequential Multi-Agent GPU Sharing

**Pattern** (llama.cpp build 10423+, confirmed working):
- llama.cpp auto-saves KV cache to RAM when a slot goes idle (built-in behavior)
- Main agent KV cache saved → subagent gets fresh GPU KV cache
- Subagent only pays prefill on its own system prompt delta
- On subagent completion + idle, main session RAM cache swaps back — near-instant (no prefill)
- Net effect: multiple sequential Hermes subagents (research → code → review) share one GPU

**Implementation:** `--parallel 2` (or N) creates multiple slots; llama.cpp handles serialization.
Available RAM is the ceiling: `RAM_GB × 1024 × 1024 × 1024 ÷ (bytes_per_token × max_context)`.

**Integration with Hermes nightshift:**
```bash
# Start llama-server with slot parallelism for multi-agent caching
./llama-server \
  --model /path/to/model.gguf \
  --ctx-size 131072 \
  --parallel 3 \
  --cache-reuse 256
# Hermes subagents use different slot IDs via the API
```

**Pitfall:** RAM-to-GPU swap takes seconds for large contexts (not instant for 128K+).
Plan for 2–10s swap latency in tight timing loops.

---

## llama.cpp --tools-runtime: Rootless Container Sandboxing for Tools

**New flag** (llama-server build 10423+):
```bash
./llama-server \
  --model /path/to/model.gguf \
  --tools \
  --tools-runtime podman:alpine   # or docker:alpine
```

**Behavior:**
- Each tool shell command runs inside a fresh rootless podman/docker container
- Alpine image auto-pulled on first use
- Container is ephemeral: no persistent state between tool calls
- Rootless: container process has no host root capabilities

**Security properties:**
- Filesystem: host not visible unless explicitly mounted
- Network: inherits host network by default (add `--network=none` if desired)
- Process: isolated PID namespace
- Blast radius: one tool call, one container, torn down immediately

**Hermes setup:**
```bash
# Ensure podman is installed (on Fedora Silverblue: already available)
podman --version  # should be 4.x+
# No additional config needed; llama-server pulls the image automatically
```

**Pitfall:** 100–500ms container startup latency per tool call. Not suitable for rapid-fire
lightweight tool calls (status checks, string ops). Best for: bash commands, Python execution,
file operations, code compilation.

**Connection to OpenART finding (arXiv:2608.00677):** Runtime implementation drives safety
variation more than model choice. This flag provides the harness-layer sandboxing primitive
that OpenART's research identifies as critical for reducing attack surface.

---

## Quota-Aware Auto-Wake Pattern (loopx, GitHub, Aug 2026)

Source: huangruiteng/loopx (Python, 4,664 ⭐, 1,967 stars/week, Chinese author)
GitHub: https://github.com/huangruiteng/loopx

**Core idea:** agent detects quota exhaustion → checkpoints state → exits cleanly →
systemd timer resumes at quota-reset time. No human intervention required.

**Hermes adaptation:**
```python
# In a long-running Hermes cron agent script
import json, sys, pathlib, datetime

CHECKPOINT_PATH = pathlib.Path("~/.hermes/agent-outputs/nightshift/quota-checkpoint.json").expanduser()

def run_with_quota_awareness():
    # Resume from checkpoint if exists
    if CHECKPOINT_PATH.exists():
        state = json.loads(CHECKPOINT_PATH.read_text())
        print(f"Resuming from checkpoint: {state['phase']}")
    else:
        state = {"phase": "start", "completed": []}
    
    while not is_complete(state):
        try:
            state = run_next_phase(state)
            CHECKPOINT_PATH.write_text(json.dumps(state))  # checkpoint after each phase
        except QuotaExhausted:
            CHECKPOINT_PATH.write_text(json.dumps({**state, "quota_exhausted_at": str(datetime.datetime.utcnow())}))
            print("Quota exhausted. Checkpoint saved. Wakeup timer will resume.")
            sys.exit(0)  # clean exit; systemd timer handles wakeup
    
    CHECKPOINT_PATH.unlink(missing_ok=True)  # clean up on success
```

**systemd wakeup timer:**
```ini
# ~/.config/systemd/user/hermes-nightshift-resume.timer
[Unit]
Description=Resume Hermes nightshift agent after quota reset

[Timer]
OnCalendar=*-*-* 01:05:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Distinction from crash recovery:**
- Crash recovery: unexpected failure → retry from last checkpoint
- Quota-wake: planned exit → scheduled resume at known reset time
- Both use the same checkpoint file format — combine for full resilience

**Three-pattern combination (best practice for overnight agents):**
1. **Checkpoint on milestone success** (durable pattern) → survives crashes
2. **Quota-wake on limit exhaustion** (loopx pattern) → survives quota hits
3. **HITL deny on timeout** (existing nightshift pattern) → survives unclear situations
