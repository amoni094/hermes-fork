---
name: agent-mailbox-ipc
description: "Use when agents need durable file-based IPC between runs. Token-coherence aware versioned handoffs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - multiple agents or cron jobs need to pass data to each other
  - you need a durable inter-agent message queue that survives session restarts
  - a subagent needs to signal completion or an error to a parent/sibling agent
  - designing a multi-agent pipeline where agents can run independently and asynchronously
  - avoiding shared-state race conditions between parallel agents
tags: [multi-agent, ipc, coordination, mailbox, git, cron]
related_skills:
  - autonomous-agent-loop-design
  - hermes-cron-and-agents
  - async-agent-nightshift-patterns
  - mnemosyne-atp-safety
---

# Agent Mailbox IPC

File-based inter-agent message passing. Agents communicate via an inbox/outbox directory tree
rooted in a local git repo. No network dependency, no database, survives crashes, auditable.

Pattern distilled from: munder-difflin (chaitanyagiri/munder-difflin, MIT, ~1.7k stars),
adapted for Hermes cron/subagent workflows.

## Core Design Principles

1. Plain files as messages. Each message is a JSON file. No shared lock, no DB.
2. Single-committer git. Only one process (the router/harness) ever calls `git commit`.
   Agents never touch git directly. Eliminates `index.lock` corruption.
3. Atomic file delivery. Messages are written to `outbox/` by the sender, then moved
   (not copied) to `inbox/<recipient>/` by the router. `mv` on same filesystem is atomic.
4. Drain-on-wake model. Agents read and drain their `inbox/` at the start of each run.
   No polling loop needed — compatible with Hermes cron scheduling.

## Directory Layout

```
~/.hermes/hive/
  agents/
    agent-a/
      inbox/           # router writes here; agent-a reads and deletes
      outbox/          # agent-a writes here; router moves to recipients
      memory.md        # agent-a local memory (append-only)
    agent-b/
      inbox/
      outbox/
      memory.md
  blackboard/          # shared read/write key-value store (one file per key)
    task_ledger.json
    signals.json       # system-level signals: pause, drain, shutdown
  log/
    events.jsonl       # append-only event log
  .git/                # managed ONLY by the router
```

## Message Format

```json
{
  "id": "msg_<uuid4>",
  "from": "agent-a",
  "to": "agent-b",
  "ts": "2026-08-18T12:00:00Z",
  "type": "task | result | signal | error",
  "subject": "short label",
  "body": {},
  "ttl_turns": 5
}
```

`ttl_turns`: if not drained within N agent wakeups, router marks it expired and logs it.
`type=signal` reserved for control messages: pause, drain, stop, escalate.

## Router Script

The router runs as a cron job (every 2 minutes, `no_agent: true`).
Save to `~/.hermes/scripts/hive_router.py`:

```python
import os, shutil, json, glob, time, subprocess

HIVE = os.path.expanduser("~/.hermes/hive")

def route_once():
    for agent_dir in glob.glob(f"{HIVE}/agents/*/"):
        agent = os.path.basename(agent_dir.rstrip("/"))
        for msg_path in glob.glob(f"{agent_dir}outbox/*.json"):
            with open(msg_path) as f:
                msg = json.load(f)
            recipient = msg.get("to")
            if not recipient:
                continue
            dest_inbox = f"{HIVE}/agents/{recipient}/inbox"
            os.makedirs(dest_inbox, exist_ok=True)
            shutil.move(msg_path, f"{dest_inbox}/{os.path.basename(msg_path)}")
            _log("routed", agent, recipient, msg["id"])

def _log(etype, frm, to, mid):
    path = f"{HIVE}/log/events.jsonl"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps({"ts": time.time(), "type": etype,
                            "from": frm, "to": to, "msg_id": mid}) + "\n")

def git_commit():
    subprocess.run(["git", "add", "-A"], cwd=HIVE, check=True)
    r = subprocess.run(["git", "status", "--porcelain"], cwd=HIVE,
                       capture_output=True, text=True)
    if r.stdout.strip():
        subprocess.run(["git", "commit", "-m", "router: route batch"],
                       cwd=HIVE, check=True)

if __name__ == "__main__":
    route_once()
    git_commit()
```

Register as a cron job:
```yaml
schedule: "*/2 * * * *"
script: scripts/hive_router.py
no_agent: true
name: hive-router
```

Init the hive repo once:
```bash
mkdir -p ~/.hermes/hive/{blackboard,log}
cd ~/.hermes/hive && git init && git add -A && git commit -m "init hive"
```

## Agent Inbox Drain Preamble

Inject at the start of any cron agent prompt participating in the hive:

```
HIVE INBOX DRAIN:
1. Read all files in ~/.hermes/hive/agents/<my-name>/inbox/
2. Process each message, then DELETE the file.
3. Check ~/.hermes/hive/blackboard/signals.json for system signals before proceeding.
4. Write results to ~/.hermes/hive/agents/<my-name>/outbox/msg_<uuid>.json
   with "to" set to the recipient agent name.
```

## Blackboard (Shared Read/Write State)

One JSON file per key. Readers: any agent (safe, no lock needed).
Writers: ONE designated agent per key only. Never two agents writing the same key.

Always write atomically:
```python
import json, os

def write_blackboard(key, value, hive=os.path.expanduser("~/.hermes/hive")):
    path = f"{hive}/blackboard/{key}.json"
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(value, f, indent=2)
    os.replace(tmp, path)  # atomic rename on POSIX
```

## Cron Pipeline Example

```
hive-router (every 2m, no_agent): routes outbox->inbox for all agents

agent-researcher (every 15m):
  - drain inbox
  - run analysis
  - write result to outbox as msg_<uuid>.json with to="agent-synthesizer"

agent-synthesizer (every 30m):
  - drain inbox
  - synthesize messages from agent-researcher
  - update blackboard/task_ledger.json
```

## When to Use vs. delegate_task

Mailbox IPC:
  - agents on different schedules (cron)
  - durable, crash-safe message passing
  - full git audit trail
  - Agent A produces output Agent B reads later

delegate_task:
  - agents spawned synchronously in one session
  - result needed in the current turn
  - parallelism within a single parent task

The two compose: use delegate_task within a cron agent's run, use mailbox IPC
to pass results between separate cron agents across runs.

## Pitfalls

- Two agents writing the same blackboard key clobber each other. Assign key ownership
  upfront. Route contested writes through the router as a merge step.
- Large message bodies (>64KB): write payload to agents/<name>/data/<id>.json and put
  the path in the message body, not the body itself.
- Router crash mid-move: shutil.move is atomic on the same filesystem. On networked FS,
  use a .partial suffix to detect incomplete moves on restart.
- Inbox accumulation: if an agent cron is paused, inbox grows unbounded. Set ttl_turns;
  have the router expire and log stale messages rather than accumulating.
- Git repo size: rotate events.jsonl monthly. Rename to events-YYYY-MM.jsonl, start fresh.
  Git history preserves the full audit trail.
- Not for real-time coordination: drain-on-wake suits cron-scheduled agents. For
  sub-minute latency, use a different mechanism.

## Token Coherence for Mailbox Artifacts (arXiv:2603.15183)

When multiple agents share mailbox artifacts (inbox messages, blackboard keys, data files),
read-modify-write races can cause lost updates. The MESI-style versioning approach reduces
cross-agent sync cost by 84-95% over full rebroadcast:

  Modified  : one agent has the only valid copy; no broadcast needed on read
  Exclusive  : one agent has the copy, no other has it; safe to write without check
  Shared    : multiple agents have valid copies; on write, invalidate others’ copies
  Invalid   : cached copy is stale; agent must re-fetch before using

Hermes mailbox implementation:
  - Each inbox message gets a `version` field (integer, monotone incrementing)
  - Blackboard keys carry a `last_writer` + `version`
  - Before writing a shared key: check current version matches what you last read
    (optimistic lock: if version advanced, re-fetch and merge before writing)
  - On routing-agent crash: any key modified (M-state) and not flushed is suspect;
    recovery agent re-fetches from disk (canonical store) not from memory

Simple implementation: add `version` and `last_writer` to every blackboard write;
have the router reject writes whose `base_version` != current disk version.
