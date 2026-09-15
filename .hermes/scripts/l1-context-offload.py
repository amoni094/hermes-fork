#!/usr/bin/env python3
"""
l1-context-offload.py — LangChain-style 3-tier context offload for Hermes sessions.

Implements a three-tier offload pattern to prevent context blowout:
  Tier 1 — Hot (in-context): current turn content, recent tool outputs ≤ 4K chars
  Tier 2 — Warm (offload file): tool outputs 4K–20K chars; accessible by key reference
  Tier 3 — Cold (evicted): content > 20K chars; truncated summary written to warm tier

Writes offload chunks to ~/.hermes/offload/<session_id>/<label>.md
A reference token [OFFLOAD:<label>] replaces the full content in-context.

Usage:
  # Offload a large tool output (pipe or --text):
  echo "big content" | python3 l1-context-offload.py --session SESSION_ID --label "search:redis"
  python3 l1-context-offload.py --session SESSION_ID --label "search:redis" --text "big content"

  # Read a previously offloaded chunk:
  python3 l1-context-offload.py --session SESSION_ID --show search:redis

  # List all offloaded chunks for a session:
  python3 l1-context-offload.py --session SESSION_ID --list

  # Summarize all warm-tier chunks to one cold-tier summary (call at 85% context):
  python3 l1-context-offload.py --session SESSION_ID --evict

  # Show total offload size for a session:
  python3 l1-context-offload.py --session SESSION_ID --stats

Thresholds:
  HOT_LIMIT  = 4_000 chars  — content below this stays in-context
  WARM_LIMIT = 20_000 chars — content 4K–20K goes to warm offload file
  At 85% context capacity: call --evict to consolidate warm → cold summary

Reference: LangChain 3-tier memory management + TencentDB Agent Memory offload pattern.
See: ~/.hermes/skills/autonomous-ai-agents/llm-agent-memory-pipeline-research/
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
OFFLOAD_DIR = HERMES_HOME / "offload"
LLM_MODEL = os.environ.get("L1_OFFLOAD_MODEL", "claude-haiku-4-5")

HOT_LIMIT = 4_000       # chars: stay in context
WARM_LIMIT = 20_000     # chars: write to offload file; above this → cold eviction
CONTEXT_EVICT_PCT = 0.85  # evict warm → cold when context at this fraction

# ---------------------------------------------------------------------------
# Env loading
# ---------------------------------------------------------------------------

def _load_env():
    env_path = HERMES_HOME / ".env"
    if env_path.exists() and not os.environ.get("ANTHROPIC_API_KEY"):
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY=") and "=" in line:
                os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()
                break

_load_env()


# ---------------------------------------------------------------------------
# Anthropic API (haiku — cheap, fast; used only for --evict cold summarization)
# ---------------------------------------------------------------------------

def _haiku_summarize(content: str, label: str, intent: str = "") -> str:
    """Summarize content to a compact cold-tier entry (≤ 150 words).

    Paritok-lite (arXiv:2608.24188): when intent is provided, prefer extractive
    retention of identifiers/paths/numbers relevant to that intent over free rewrite.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    intent_line = (
        f"Current agent intent/goal: {intent.strip()}\n"
        "Select and keep spans that serve this intent; drop intent-irrelevant bulk.\n"
        if intent.strip()
        else ""
    )
    prompt = (
        f"Compress the following agent tool output (label: {label}) to ≤ 150 words.\n"
        f"{intent_line}"
        "Prefer EXTRACTIVE compression: keep verbatim paths, identifiers, error strings, "
        "numbers, and commands that already appear in the input. Do not paraphrase identifiers. "
        "Focus on key findings, data points, and conclusions. "
        "Omit boilerplate, headers, and repeated rows. "
        "Write in compact prose, no bullet nesting.\n\n"
        f"Content:\n{content[:8000]}"
    )
    payload = json.dumps({
        "model": LLM_MODEL,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data.get("content", [{}])[0].get("text", "").strip()


# ---------------------------------------------------------------------------
# Offload path helpers
# ---------------------------------------------------------------------------

def session_dir(session_id: str) -> Path:
    d = OFFLOAD_DIR / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def label_path(session_id: str, label: str) -> Path:
    safe = label.replace("/", "_").replace(":", "_").replace(" ", "_")
    return session_dir(session_id) / f"{safe}.md"


def index_path(session_id: str) -> Path:
    return session_dir(session_id) / "_index.json"


def load_index(session_id: str) -> dict:
    p = index_path(session_id)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def save_index(session_id: str, idx: dict):
    index_path(session_id).write_text(json.dumps(idx, indent=2))


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def cmd_offload(session_id: str, label: str, content: str, dry_run: bool = False, intent: str = ""):
    """Tier-route content: hot → pass-through, warm → file, large → cold summary."""
    size = len(content)
    ts = datetime.now(timezone.utc).isoformat()

    if size <= HOT_LIMIT:
        print(f"[offload] HOT ({size} chars) — content fits in context, no offload needed.")
        print(content)
        return

    if size > WARM_LIMIT:
        # Cold path: summarize then store summary as warm
        print(f"[offload] COLD ({size} chars > {WARM_LIMIT}) — summarizing to cold tier...",
              file=sys.stderr)
        if not dry_run:
            summary = _haiku_summarize(content, label, intent=intent)
            cold_content = (
                f"# COLD SUMMARY: {label}\n"
                f"_Original size: {size} chars. Summarized at {ts}_\n\n"
                f"{summary}\n\n"
                f"_Full content evicted — not recoverable from offload._\n"
            )
            p = label_path(session_id, label)
            p.write_text(cold_content)
            idx = load_index(session_id)
            idx[label] = {"tier": "cold", "size": size, "summary_size": len(cold_content),
                          "written_at": ts, "path": str(p), "intent": intent or None}
            save_index(session_id, idx)
            print(f"[offload] Wrote cold summary → {p}")
            print(f"[OFFLOAD:{label}]")
        else:
            print(f"[offload] DRY-RUN: would write cold summary for {label} ({size} chars)")
        return

    # Warm path: store full content
    if not dry_run:
        warm_content = (
            f"# OFFLOAD: {label}\n"
            f"_Size: {size} chars. Stored at {ts}_\n\n"
            f"{content}\n"
        )
        p = label_path(session_id, label)
        p.write_text(warm_content)
        idx = load_index(session_id)
        idx[label] = {"tier": "warm", "size": size, "written_at": ts, "path": str(p)}
        save_index(session_id, idx)
        print(f"[offload] WARM ({size} chars) → {p}", file=sys.stderr)
        print(f"[OFFLOAD:{label}]")
    else:
        print(f"[offload] DRY-RUN: would write warm offload for {label} ({size} chars)")


def cmd_show(session_id: str, label: str):
    """Retrieve a previously offloaded chunk by label."""
    p = label_path(session_id, label)
    if p.exists():
        print(p.read_text())
    else:
        idx = load_index(session_id)
        if idx:
            print(f"Label '{label}' not found. Available: {', '.join(idx.keys())}")
        else:
            print(f"No offloads found for session {session_id}")
        sys.exit(1)


def cmd_list(session_id: str):
    """List all offloaded chunks for a session."""
    idx = load_index(session_id)
    if not idx:
        print(f"No offloads for session {session_id}")
        return
    print(f"Offloads for session {session_id[:16]}:")
    for label, meta in sorted(idx.items()):
        tier = meta.get("tier", "?")
        size = meta.get("size", 0)
        written = meta.get("written_at", "?")[:19]
        print(f"  [{tier:4s}] {label:40s}  {size:>8,} chars  {written}")


def cmd_evict(session_id: str, dry_run: bool = False, intent: str = ""):
    """Evict all warm-tier chunks to cold (summarize). Call at 85% context capacity."""
    idx = load_index(session_id)
    warm = [(label, meta) for label, meta in idx.items() if meta.get("tier") == "warm"]
    if not warm:
        print(f"[offload] No warm-tier chunks to evict for session {session_id[:16]}")
        return
    print(f"[offload] Evicting {len(warm)} warm chunks to cold tier...", file=sys.stderr)
    ts = datetime.now(timezone.utc).isoformat()
    for label, meta in warm:
        p = Path(meta["path"])
        if not p.exists():
            continue
        content = p.read_text()
        if not dry_run:
            summary = _haiku_summarize(content, label, intent=intent or meta.get("intent") or "")
            cold_content = (
                f"# COLD SUMMARY (evicted): {label}\n"
                f"_Evicted at {ts}. Original size: {meta['size']} chars._\n\n"
                f"{summary}\n"
            )
            p.write_text(cold_content)
            idx[label]["tier"] = "cold"
            idx[label]["evicted_at"] = ts
            idx[label]["summary_size"] = len(cold_content)
            if intent:
                idx[label]["intent"] = intent
            print(f"  evicted: {label} ({meta['size']} → {len(cold_content)} chars)")
        else:
            print(f"  DRY-RUN evict: {label} ({meta['size']} chars)")
    if not dry_run:
        save_index(session_id, idx)
    print(f"[offload] Eviction complete.")


def cmd_stats(session_id: str):
    """Show total offload size for a session."""
    idx = load_index(session_id)
    if not idx:
        print(f"No offloads for session {session_id}")
        return
    warm_size = sum(m.get("size", 0) for m in idx.values() if m.get("tier") == "warm")
    cold_size = sum(m.get("summary_size", 0) for m in idx.values() if m.get("tier") == "cold")
    orig_cold = sum(m.get("size", 0) for m in idx.values() if m.get("tier") == "cold")
    print(f"Session {session_id[:16]} offload stats:")
    print(f"  Warm: {len([m for m in idx.values() if m.get('tier')=='warm'])} chunks, "
          f"{warm_size:,} chars in files")
    print(f"  Cold: {len([m for m in idx.values() if m.get('tier')=='cold'])} chunks, "
          f"{orig_cold:,} chars original → {cold_size:,} chars summarized")
    print(f"  Total offloaded (not in context): {warm_size + orig_cold:,} chars")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="3-tier context offload for Hermes sessions")
    p.add_argument("--session", "-s", required=True, help="Session ID")
    p.add_argument("--label", "-l", default=None,
                   help="Chunk label (required for offload/show)")
    p.add_argument("--text", default=None,
                   help="Content to offload (alternative to stdin)")
    p.add_argument("--show", metavar="LABEL", default=None,
                   help="Retrieve offloaded chunk by label")
    p.add_argument("--list", action="store_true",
                   help="List all offloads for session")
    p.add_argument("--evict", action="store_true",
                   help="Evict warm tier to cold (call at 85%% context)")
    p.add_argument("--stats", action="store_true",
                   help="Show offload stats for session")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would happen without writing")
    p.add_argument("--intent", default="",
                   help="Current task goal for Paritok-lite intent-conditioned cold summarize")
    args = p.parse_args()

    if args.show:
        cmd_show(args.session, args.show)
    elif args.list:
        cmd_list(args.session)
    elif args.evict:
        cmd_evict(args.session, dry_run=args.dry_run, intent=args.intent)
    elif args.stats:
        cmd_stats(args.session)
    else:
        # Default: offload content from --text or stdin
        if not args.label:
            p.error("--label is required for offload")
        if args.text:
            content = args.text
        elif not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            p.error("Provide content via --text or stdin pipe")
        cmd_offload(args.session, args.label, content, dry_run=args.dry_run, intent=args.intent)


if __name__ == "__main__":
    main()
