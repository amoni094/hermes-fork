#!/usr/bin/env python3
"""
pre-compact-annotate.py — Pre-compaction signal annotation for Hermes sessions.

Runs as a cron job (no_agent=True). Watches state.db for sessions approaching
the compaction threshold and outputs a /compact instruction with a focus string
derived from high-signal content in recent messages.

Signal detection (what to protect):
  - Explicit user decisions ("use X", "prefer Y", "don't do Z")
  - Confirmed fixes (error + patch pairs)
  - File paths, URLs, session IDs, commit SHAs that appeared in tool results
  - Anything the user explicitly said to remember

Output contract (no_agent=True):
  - Empty stdout  -> silent (no compaction needed or already triggered)
  - Non-empty     -> delivered as message; agent reads it and can act

Usage:
  python3 pre-compact-annotate.py [--threshold 0.75] [--session SESSION_ID]

Config:
  THRESHOLD: fraction of input_tokens / context_limit at which to fire
  Context limit is read from the session's model config or falls back to 120000.
"""
from __future__ import annotations
import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import os as _os
_hermes_base = Path(_os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = _os.environ.get("HERMES_PROFILE", "")
_hermes_root = (_hermes_base / "profiles" / _hermes_profile) if _hermes_profile and "profiles" not in str(_hermes_base) else _hermes_base
DB_PATH       = _hermes_root / "state.db"
CONTEXT_LIMIT = 120_000       # fallback if model config missing
THRESHOLD     = 0.75          # fire at 75% of context limit
MAX_DECISIONS = 8             # cap focus string length
MAX_VERBATIM  = 10

# Patterns for high-signal content
_DECISION_RE = re.compile(
    r"(?:use\s+|prefer\s+|don'?t\s+|always\s+|never\s+|remember\s+|keep\s+|set\s+)"
    r"[^\n]{8,80}",
    re.I,
)
_VERBATIM_RE = re.compile(
    r"(?:"
    r"(?:/[\w./-]{4,60})"              # file paths
    r"|(?:https?://\S{8,80})"          # URLs
    r"|(?:[0-9a-f]{7,40}\b)"           # commit SHAs
    r"|(?::\d{4,5}\b)"                 # ports
    r"|(?:error[:\s][^\n]{8,60})"      # error messages
    r"|(?:FAILED[:\s][^\n]{8,60})"     # failures
    r")",
    re.I,
)


def _context_limit(model_config_json: str | None) -> int:
    if not model_config_json:
        return CONTEXT_LIMIT
    try:
        cfg = json.loads(model_config_json)
        return int(cfg.get("context_length") or cfg.get("max_tokens") or CONTEXT_LIMIT)
    except Exception:
        return CONTEXT_LIMIT


def _session_fill(session: tuple) -> float:
    """Return context fill ratio [0..1] for a session row."""
    sid, inp, cache, model_config = session
    tokens = (inp or 0) + (cache or 0)
    limit  = _context_limit(model_config)
    return tokens / limit if limit > 0 else 0.0


def _extract_signals(text: str) -> tuple[list[str], list[str]]:
    """Return (decisions, verbatim_refs) from a message body."""
    decisions = _DECISION_RE.findall(text)[:MAX_DECISIONS]
    verbatim  = list({m.group() for m in _VERBATIM_RE.finditer(text)})[:MAX_VERBATIM]
    return decisions, verbatim


def _recent_messages(con: sqlite3.Connection, session_id: str, limit: int = 30) -> list[tuple]:
    cur = con.cursor()
    cur.execute(
        """
        SELECT role, content, tool_name
        FROM messages
        WHERE session_id = ? AND active = 1
        ORDER BY display_order DESC
        LIMIT ?
        """,
        (session_id, limit),
    )
    return cur.fetchall()


def _build_focus(messages: list[tuple]) -> str:
    """Derive a focus string from recent high-signal messages."""
    decisions: list[str] = []
    verbatim:  list[str] = []

    for role, content, tool_name in messages:
        if not content:
            continue
        # User messages carry decisions; tool results carry verbatim refs
        if role == "user":
            d, v = _extract_signals(content)
            decisions.extend(d)
        elif role == "tool" or tool_name:
            _, v = _extract_signals(content)
            verbatim.extend(v)
        elif role == "assistant":
            d, v = _extract_signals(content)
            decisions.extend(d[:2])   # assistant summaries of decisions

    # Deduplicate preserving order
    seen: set[str] = set()
    decisions = [x for x in decisions if not (x in seen or seen.add(x))][:MAX_DECISIONS]
    seen.clear()
    verbatim  = [x for x in verbatim  if not (x in seen or seen.add(x))][:MAX_VERBATIM]

    parts: list[str] = []
    if decisions:
        parts.append("Recent decisions: " + "; ".join(decisions))
    if verbatim:
        parts.append("Key refs: " + ", ".join(verbatim))

    return " | ".join(parts) if parts else "recent work and decisions"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=THRESHOLD,
                        help="Fill ratio at which to fire (default 0.75)")
    parser.add_argument("--session",   help="Specific session ID (default: most recent active)")
    parser.add_argument("--dry-run",   action="store_true", help="Print focus string, don't output compact cmd")
    args = parser.parse_args()

    if not DB_PATH.exists():
        sys.exit(0)   # silent — no DB yet

    try:
        con = sqlite3.connect(str(DB_PATH))
        try:
            cur = con.cursor()

            if args.session:
                cur.execute(
                    "SELECT id, input_tokens, cache_read_tokens, model_config "
                    "FROM sessions WHERE id LIKE ? ORDER BY started_at DESC LIMIT 1",
                    (f"{args.session}%",),
                )
            else:
                cur.execute(
                    """
                    SELECT id, input_tokens, cache_read_tokens, model_config
                    FROM sessions
                    WHERE ended_at IS NULL AND archived = 0
                    ORDER BY last_activity_at DESC LIMIT 1
                    """,
                )

            row = cur.fetchone()
            if not row:
                sys.exit(0)

            session_id = row[0]
            fill = _session_fill(row)

            if fill < args.threshold and not args.dry_run:
                sys.exit(0)   # below threshold — silent

            messages = _recent_messages(con, session_id)
        finally:
            con.close()

        focus = _build_focus(messages)

        if args.dry_run:
            print(f"session={session_id}  fill={fill:.1%}  threshold={args.threshold:.0%}")
            print(f"focus: {focus}")
            sys.exit(0)

        # Output the compact instruction — delivered as a message by cron no_agent=True
        now = datetime.now(timezone.utc).strftime("%H:%M UTC")
        annotation = (
            f"[pre-compact-annotate @ {now}] Context at {fill:.0%}. "
            f"Suggested: /compact {focus}"
        )

        # Append rd-compaction-advisor advisory
        try:
            import subprocess as _sp
            import sys as _sys
            # Use input_tokens + cache tokens as best estimate; fall back to 80000
            _sid, _inp, _cache, _mcfg = row
            _current_tokens = max((_inp or 0) + (_cache or 0), 80000)
            _adv_result = _sp.run(
                [_sys.executable, str(Path(__file__).parent / "rd-compaction-advisor.py"),
                 "--current-tokens", str(_current_tokens)],
                capture_output=True, text=True, timeout=10,
            )
            if _adv_result.returncode == 0 and _adv_result.stdout.strip():
                _adv = json.loads(_adv_result.stdout)
                _agg = _adv.get("aggressiveness", 0.0)
                _focus = _adv.get("focus_topic_prefix", "")
                annotation += (
                    f"\nCompaction advisory: aggressiveness={_agg:.2f}, "
                    f"focus={_focus} (rd-compaction-advisor)"
                )
        except Exception:
            pass  # advisory is best-effort; never block annotation output

        # Append alarm-aggregator summary
        try:
            import subprocess as _sp  # noqa: F811 (re-import for standalone block)
            import sys as _sys         # noqa: F811
            _alarm_result = _sp.run(
                [_sys.executable, str(Path(__file__).parent / "alarm-aggregator.py")],
                capture_output=True, text=True, timeout=10,
            )
            if _alarm_result.stdout.strip():
                _alarm_data = json.loads(_alarm_result.stdout)
                _active = _alarm_data.get("active_alarms", [])
                _count = _alarm_data.get("count", 0)
                if _count > 0:
                    _alarm_lines = "; ".join(
                        f"{a['source']}[{a['severity']}]: {a['msg']}"
                        for a in _active
                    )
                    annotation += (
                        f"\nActive alarms ({_count}): {_alarm_lines}"
                    )
        except Exception:
            pass  # alarm aggregation is best-effort; never block annotation output

        # Append Focus Agent reminder (wires focus_compress.py as a live annotation)
        try:
            import subprocess as _sp  # noqa: F811
            import sys as _sys         # noqa: F811
            _fc_result = _sp.run(
                [_sys.executable, str(Path(__file__).parent / "focus_compress.py"),
                 "--mode", "reminder"],
                capture_output=True, text=True, timeout=10,
            )
            if _fc_result.returncode == 0 and _fc_result.stdout.strip():
                annotation += "\n\n## Focus Agent Reminder\n" + _fc_result.stdout.rstrip()
        except Exception:
            pass  # focus reminder is best-effort; never block annotation output

        print(annotation)

    except Exception as e:
        # Silent failure — never interrupt a session with a script error
        if args.dry_run:
            print(f"error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
