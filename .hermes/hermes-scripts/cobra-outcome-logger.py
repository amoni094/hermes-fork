#!/usr/bin/env python3
"""cobra-outcome-logger.py — CoBRA prospective outcome logging for tool-use usefulness signals.

arXiv:2609.00967 (CoBRA: Learning Tool-Use Boundaries via Counterfactual Margins)

The current cobra-skip-guard.py uses synthetic training data. Full CoBRA requires real
(query_context, tool_name, outcome=useful/wasteful) triples. This script provides a CLI
for manually recording and querying tool-use outcome signals for future training.

NOTE: This CLI is also invoked automatically by the cobra-guard plugin's
post_tool_call hook. HERMES_COBRA_GUARD=0 disables that plugin.

Two modes:
    record   — append a post_tool_call event to the outcome log (called from post_tool_call hook)
    report   -- print a summary of the logged outcomes (for review/training data QA)
    export   -- export a training-ready JSONL file for cobra probe retraining

Log format (JSONL at ~/.hermes/logs/cobra-outcomes.jsonl):
    {
        "ts": "2026-09-08T...",
        "tool_name": "web_search",
        "query_tokens": 12,
        "context_chars": 8400,
        "context_tools_prior": ["hindsight_recall"],
        "result_len": 2400,
        "result_used": null,   # null = unknown; true/false = confirmed by follow-up analysis
        "session_id": "...",
        "turn_id": "..."
    }

result_used is set to null at record time and can be updated by a follow-up heuristic:
  - true if the tool result string appears verbatim in the next LLM assistant turn
  - false if the next assistant turn ignores it entirely
This heuristic is weak but good enough for initial training corpus bootstrap.

Usage:
    python3 cobra-outcome-logger.py record --tool web_search --result-len 2400 ...
    python3 cobra-outcome-logger.py report
    python3 cobra-outcome-logger.py export --output /tmp/cobra-train.jsonl
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

def _hermes_dir() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def _log_path() -> Path:
    return _hermes_dir() / "logs" / "cobra-outcomes.jsonl"


# Back-compat alias; prefer _log_path() so profile HERMES_HOME is honored at write time.
LOG_PATH = Path.home() / ".hermes" / "logs" / "cobra-outcomes.jsonl"


def _append(record: dict[str, Any]) -> None:
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")


def _load_records() -> list[dict[str, Any]]:
    path = _log_path()
    if not path.exists():
        return []
    records = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def cmd_record(args) -> int:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool_name": args.tool,
        "query_tokens": args.query_tokens or 0,
        "context_chars": args.context_chars or 0,
        "context_tools_prior": (args.context_tools_prior or "").split(",") if args.context_tools_prior else [],
        "result_len": args.result_len or 0,
        "result_used": None,  # updated by follow-up analysis
        "session_id": args.session_id or "",
        "turn_id": args.turn_id or "",
    }
    _append(record)
    print(json.dumps({"status": "recorded", "tool": args.tool}))
    return 0


def cmd_report(args) -> int:
    records = _load_records()
    if not records:
        print(json.dumps({"status": "empty", "log": str(_log_path())}))
        return 0

    from collections import Counter
    tool_counts = Counter(r["tool_name"] for r in records)
    used_counts = Counter(
        (r["tool_name"], r.get("result_used"))
        for r in records
    )
    unknown = sum(1 for r in records if r.get("result_used") is None)

    report = {
        "total_records": len(records),
        "unknown_outcome": unknown,
        "labeled": len(records) - unknown,
        "by_tool": dict(tool_counts.most_common()),
        "usefulness_rate": {
            tool: round(
                sum(1 for r in records if r["tool_name"] == tool and r.get("result_used") is True)
                / max(1, sum(1 for r in records if r["tool_name"] == tool and r.get("result_used") is not None)),
                3
            )
            for tool in tool_counts
        },
        "log_path": str(_log_path()),
        "training_ready": (len(records) - unknown) >= 200,
        "note": "result_used=null means outcome not yet labeled. Label manually via the record subcommand with --used true/false.",
    }
    print(json.dumps(report, indent=2))
    return 0


def cmd_export(args) -> int:
    records = _load_records()
    labeled = [r for r in records if r.get("result_used") is not None]
    if not labeled:
        print(json.dumps({"error": "No labeled records to export. Run outcome labeling first."}))
        return 1

    out_path = Path(args.output).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Export as training-ready feature rows
    with out_path.open("w") as f:
        for r in labeled:
            feature_row = {
                "tool_name": r["tool_name"],
                "query_tokens": r.get("query_tokens", 0),
                "context_chars": r.get("context_chars", 0),
                "n_prior_tools": len(r.get("context_tools_prior") or []),
                "result_len": r.get("result_len", 0),
                "label": 1 if r["result_used"] else 0,
            }
            f.write(json.dumps(feature_row) + "\n")

    print(json.dumps({"exported": len(labeled), "path": str(out_path)}))
    return 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="CoBRA outcome logger")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_record = sub.add_parser("record", help="Append a tool outcome record")
    p_record.add_argument("--tool", required=True)
    p_record.add_argument("--query-tokens", type=int, default=0)
    p_record.add_argument("--context-chars", type=int, default=0)
    p_record.add_argument("--context-tools-prior", default="")
    p_record.add_argument("--result-len", type=int, default=0)
    p_record.add_argument("--session-id", default="")
    p_record.add_argument("--turn-id", default="")

    sub.add_parser("report", help="Print outcome log summary")

    p_export = sub.add_parser("export", help="Export labeled records as training JSONL")
    p_export.add_argument("--output", required=True)

    args = parser.parse_args()
    if args.cmd == "record":
        return cmd_record(args)
    elif args.cmd == "report":
        return cmd_report(args)
    elif args.cmd == "export":
        return cmd_export(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
