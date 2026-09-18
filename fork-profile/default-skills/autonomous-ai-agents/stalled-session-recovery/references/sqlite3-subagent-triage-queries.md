# SQLite3 Subagent Triage Queries

Reusable queries for recovering orphaned subagent research data from `~/.hermes/state.db`.
Used when sessions expire mid-task and subagent outputs need to be reconstructed.

## Step 1: Find sessions created in a time window

```python
import sqlite3

db_path = "/var/home/rainbow/.hermes/state.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Schema: columns are id, session_id, role, content, tool_call_id, tool_calls,
# tool_name, timestamp, token_count, finish_reason, ...
# sessions table: id, title, ...

# Get recent sessions with message counts and timestamps
cur.execute("""
    SELECT s.id, s.title,
           min(m.timestamp) as first_ts,
           max(m.timestamp) as last_ts,
           count(m.id) as msg_count
    FROM sessions s
    JOIN messages m ON m.session_id = s.id
    GROUP BY s.id
    ORDER BY last_ts DESC
    LIMIT 20
""")
for row in cur.fetchall():
    sid, title, first_ts, last_ts, cnt = row
    print(f"  {sid} | msgs={cnt} | title={str(title)[:55]}")
```

## Step 2: Inspect message shape for each candidate session

```python
# Check what each session produced
cur.execute("""
    SELECT id, role, length(content), timestamp
    FROM messages WHERE session_id=? ORDER BY id
""", (session_id,))

for mid, role, content_len, ts in cur.fetchall():
    print(f"  id={mid} role={role} len={content_len}")

# Interpretation:
# - role=user with 600-800 chars = the initial goal prompt (confirms this is a subagent)
# - role=tool with >30K chars = web extract / research data collected
# - role=tool with ~53K chars = often a skills_list dump (skip this one)
# - role=assistant with <200 chars ending the session = "next I'll synthesize" (timed out)
# - no final role=assistant = timed out mid-tool-chain
```

## Step 3: Extract research data, skipping noise

```python
import os

output_dir = "/var/home/rainbow/.hermes/cache/recovered_research"
os.makedirs(output_dir, exist_ok=True)

STANDARD_SKILL_DUMP_SIZE = 53552  # skills_list tool result is consistently this size

def extract_cluster_data(session_id, cluster_name):
    cur.execute("""
        SELECT id, content FROM messages
        WHERE session_id=? AND role='tool'
        ORDER BY id
    """, (session_id,))

    blocks = []
    for mid, content in cur.fetchall():
        # Skip tiny ack messages and the standard skills_list dump
        if len(content) < 600 or len(content) == STANDARD_SKILL_DUMP_SIZE:
            continue
        blocks.append(f"=== Source block (msg {mid}, {len(content)} chars) ===\n{content[:12000]}\n")

    filepath = f"{output_dir}/{cluster_name}.txt"
    with open(filepath, 'w') as f:
        f.write(f"RESEARCH DATA: {cluster_name}\n")
        f.write("=" * 60 + "\n\n")
        f.write("\n".join(blocks))

    return filepath, len(blocks), os.path.getsize(filepath)
```

## Step 4: Verify before re-dispatching synthesis

```python
# Confirm all cluster files are non-trivially large before dispatching synthesis agents
for filepath in cluster_files:
    size = os.path.getsize(filepath)
    if size < 10000:
        print(f"WARNING: {filepath} only {size} bytes — gather may be incomplete")
    else:
        print(f"OK: {filepath} — {size:,} bytes")

conn.close()
```

## Typical multi-cluster signature (from 2026-08-30 academic.dt research recovery)

```
Session 20260830_160556_ed2eba: 10 messages
  user(717) → assistant(73) → tool×7 (large) → assistant(63)  # gathered + "next I'll..."

Session 20260830_160556_9293f4: 8 messages
  user(812) → assistant(169) → tool×6 (large)  # gathered, no final summary
```

The 8-10 message sessions with large tool results are goldmines — they did the hard
research work; they just ran out of context before writing synthesis. Extract their
tool results and re-dispatch synthesis-only agents with file paths.

## Dispatch re-synthesis agents with file paths (not inline data)

Do NOT pass inline research content in the context string:
```python
# WRONG — repeats the context-timeout failure
delegate_task(tasks=[{"context": raw_research_data_12000_chars, "goal": "synthesize"}])

# CORRECT — synthesis agent reads the file, has fresh context budget
delegate_task(tasks=[{"context": f"Read /path/to/{cluster}.txt — do NOT do web searches.", "goal": "synthesize"}])
```
