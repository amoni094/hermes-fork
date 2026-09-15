#!/usr/bin/env python3
"""
trace2skill.py — Trace2Skill pattern: session trajectory → candidate SKILL.md draft.

Usage:
  python3 trace2skill.py SESSION_ID [--dry-run] [--model MODEL]
  python3 trace2skill.py --merge FILE1 FILE2   (intersection merge of two candidates)

Based on: Trace2Skill (arXiv:2603.25158) — Sweep 21 implementation.
Repeated-edit merge: retain only steps present in BOTH candidates (regularization
against trajectory overfitting). Small-model experience can strengthen large models.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".hermes" / "state.db"
PENDING_DIR = Path.home() / ".hermes" / "cache" / "pending-improvements"
ENV_PATH = Path.home() / ".hermes" / ".env"

SKILL_DRAFT_PROMPT = """\
You are analyzing a Hermes Agent session trajectory to extract a reusable skill.

The trajectory below shows a complete task execution: user requests, assistant reasoning,
tool calls, and tool results. Your job is to distill this into a reusable SKILL.md.

TRAJECTORY:
{trajectory}

---

Produce a Hermes SKILL.md with this EXACT format (including the --- delimiters):

---
name: skill-name-lowercase-hyphens
description: >
  Use when: [concise trigger condition, max 57 chars before the colon].
  [One sentence describing what the skill does.]
version: 1.0.0
triggers:
  - "[trigger phrase 1]"
  - "[trigger phrase 2]"
  - "[trigger phrase 3]"
---

# [Skill Title]

## Steps

1. [First concrete step with exact commands/tool calls where visible in the trajectory]
2. [Second step]
3. [Continue for all key steps observed]

## Pitfalls

- [Error or retry pattern observed in trajectory, and how it was resolved]
- [Edge case or assumption that caused a detour]

## Verification

- [How to confirm the task succeeded based on what the trajectory showed]
- [Output or state to check]

---

Rules:
- Extract ONLY what is visible in the trajectory. Do not invent steps.
- Pitfalls come from actual errors/retries in the trace — if none, write "None observed."
- Steps must be specific enough that a fresh session can reproduce the task from this skill alone.
- Name must be lowercase with hyphens only (no underscores).
- Description must start exactly with "Use when:".
- Output ONLY the SKILL.md content, nothing else.
"""


def load_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def get_trajectory(session_id: str) -> list[dict]:
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
    if not cur.fetchone():
        print(f"ERROR: Session '{session_id}' not found in DB.", file=sys.stderr)
        sys.exit(1)
    cur.execute(
        "SELECT id, role, content, tool_calls, tool_name, timestamp FROM messages "
        "WHERE session_id = ? AND active = 1 ORDER BY id",
        (session_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows if r["role"] in ("user", "assistant", "tool")]


def format_trajectory(messages: list[dict], max_content=400) -> str:
    parts = []
    for i, msg in enumerate(messages):
        role = msg["role"].upper()
        content = (msg["content"] or "").strip()[:max_content]
        tool_calls = msg.get("tool_calls") or ""
        tool_name = msg.get("tool_name") or ""

        if tool_calls:
            try:
                calls = json.loads(tool_calls)
                tool_summary = ", ".join(
                    c.get("function", {}).get("name", c.get("name", "?"))
                    for c in (calls if isinstance(calls, list) else [calls])
                )
                content = f"[TOOL CALLS: {tool_summary}] {content}"
            except Exception:
                pass
        if tool_name:
            content = f"[TOOL RESULT: {tool_name}] {content}"

        if content:
            parts.append(f"[{i+1}] {role}: {content}")

    return "\n".join(parts)


def call_api(prompt: str, model: str, api_key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    for block in msg.content:
        if hasattr(block, "text"):
            return block.text
    return ""


def extract_steps(skill_md: str) -> list[str]:
    """Extract numbered steps from a SKILL.md for merge mode."""
    steps = []
    in_steps = False
    for line in skill_md.splitlines():
        if re.match(r"^##\s+Steps", line):
            in_steps = True
            continue
        if re.match(r"^##\s+", line) and in_steps:
            break
        if in_steps and re.match(r"^\d+\.\s+", line):
            steps.append(re.sub(r"^\d+\.\s+", "", line).strip())
    return steps


def merge_candidates(file1: str, file2: str):
    """Intersection merge: keep only steps present in both candidates."""
    md1 = Path(file1).read_text()
    md2 = Path(file2).read_text()
    steps1 = extract_steps(md1)
    steps2 = extract_steps(md2)

    def normalize(s):
        return re.sub(r"\W+", " ", s.lower()).strip()

    norm2 = [normalize(s) for s in steps2]
    shared = []
    for s in steps1:
        if normalize(s) in norm2:
            shared.append(s)

    print(f"Steps in file1: {len(steps1)}")
    print(f"Steps in file2: {len(steps2)}")
    print(f"Shared (intersection): {len(shared)}")
    print()
    if not shared:
        print("WARNING: No shared steps found — candidates are too dissimilar to merge.")
        return

    print("## Merged Steps (intersection, Trace2Skill repeated-edit gate)\n")
    for i, s in enumerate(shared, 1):
        print(f"{i}. {s}")


def main():
    parser = argparse.ArgumentParser(description="Trace2Skill: trajectory → SKILL.md candidate")
    parser.add_argument("session_id", nargs="?", help="Session ID to distill")
    parser.add_argument("--dry-run", action="store_true", help="Print trajectory only, no API call")
    parser.add_argument("--model", default="claude-haiku-4-5", help="Anthropic model to use")
    parser.add_argument("--merge", nargs=2, metavar=("FILE1", "FILE2"), help="Merge two candidates (intersection)")
    args = parser.parse_args()

    if args.merge:
        merge_candidates(*args.merge)
        return

    if not args.session_id:
        parser.print_help()
        sys.exit(1)

    messages = get_trajectory(args.session_id)

    if len(messages) < 5:
        print(f"WARNING: Trajectory has only {len(messages)} messages — too short for reliable distillation.", file=sys.stderr)

    print(f"Trajectory: {len(messages)} messages in session {args.session_id}")
    if messages:
        first = messages[0]
        last = messages[-1]
        first_content = (first.get("content") or "")[:120].replace("\n", " ")
        last_content = (last.get("content") or "")[:120].replace("\n", " ")
        print(f"  First [{first['role']}]: {first_content}")
        print(f"  Last  [{last['role']}]: {last_content}")

    if args.dry_run:
        print("\n--- TRAJECTORY EXTRACT ---")
        print(format_trajectory(messages))
        return

    api_key = load_api_key()
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in env or ~/.hermes/.env", file=sys.stderr)
        sys.exit(1)

    trajectory_text = format_trajectory(messages)
    prompt = SKILL_DRAFT_PROMPT.format(trajectory=trajectory_text)

    print(f"Calling {args.model} to draft skill...")
    try:
        skill_md = call_api(prompt, args.model, api_key)
    except Exception as e:
        print(f"ERROR: API call failed: {e}", file=sys.stderr)
        sys.exit(1)

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    sid8 = args.session_id[:8]
    out_path = PENDING_DIR / f"skill-candidate-{sid8}-{ts}.md"
    out_path.write_text(skill_md)

    print(f"\nCandidate written to: {out_path}")
    print("\n--- CANDIDATE PREVIEW (first 40 lines) ---")
    for line in skill_md.splitlines()[:40]:
        print(line)


if __name__ == "__main__":
    main()
