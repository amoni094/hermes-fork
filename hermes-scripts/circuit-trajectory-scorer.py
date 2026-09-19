#!/usr/bin/env python3
"""
circuit-trajectory-scorer.py

Mines Hermes session/lifecycle logs for recurring tool-call patterns (circuits)
that precede high-confidence, successful outcomes. Surfaces which skill chains
reliably work so the agent can preferentially reuse them.

Source idea: CircuitLens (CS ideas queue) — causal subgraph features that
correlate with reward signals in agent execution traces.

Algorithm:
  1. Load tool-call sequences from lifecycle.db (or session JSON logs)
  2. Extract n-grams (sequences of 2-4 consecutive tool calls) per session
  3. Score each n-gram by: frequency × mean_outcome_score
  4. Output ranked circuit table to ~/.hermes/cache/circuit-scores.json
  5. Optionally inject top circuits as a skill-routing hint

Usage:
    python3 circuit-trajectory-scorer.py [--min-freq N] [--top K] [--dry-run]

Output:
    ~/.hermes/cache/circuit-scores.json
"""

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

# ── Paths ──────────────────────────────────────────────────────────────────────

HOME = Path.home()
import os
_HH = Path(os.environ.get("HERMES_HOME", str(HOME / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
LIFECYCLE_DB = HOME / ".hermes/memory-facts/lifecycle.db"
SESSION_LOGS_DIR = HOME / ".hermes/sessions"
OUTPUT_PATH = HOME / ".hermes/cache/circuit-scores.json"
SKILL_HINT_PATH = HOME / ".hermes/cache/circuit-routing-hints.json"

# ── Outcome scoring ────────────────────────────────────────────────────────────

def outcome_score(record: dict) -> float:
    """Heuristic outcome score for a JSONL session record.

    Uses available signals: finish_reason, error presence, role.
    Returns float in [0, 1].
    """
    score = 0.5  # neutral baseline
    finish = record.get("finish_reason", "") or ""
    if finish == "end_turn":
        score += 0.2   # completed normally
    elif finish in ("error", "timeout", "max_tokens"):
        score -= 0.2
    if record.get("error") or record.get("is_error"):
        score -= 0.3
    # Explicit success/confidence fields (tracegrant or custom)
    if record.get("success") is True:
        score += 0.3
    elif record.get("success") is False:
        score -= 0.3
    conf = record.get("confidence", "")
    if conf == "high":
        score += 0.1
    elif conf == "low":
        score -= 0.1
    # Revoked grants = bad outcome
    if record.get("revoked"):
        score -= 0.2
    return max(0.0, min(1.0, score))


# ── Log loading ────────────────────────────────────────────────────────────────

def load_from_lifecycle_db() -> list[dict]:
    """Load tool-call records from lifecycle.db if it exists."""
    if not LIFECYCLE_DB.exists():
        return []
    records = []
    try:
        conn = sqlite3.connect(str(LIFECYCLE_DB))
        conn.row_factory = sqlite3.Row
        # tracegrant_grants has session_id + caller (tool name) — primary source
        try:
            rows = conn.execute(
                "SELECT session_id, caller as tool, source_type, granted_at as timestamp, "
                "revoked, decision_hash FROM tracegrant_grants ORDER BY granted_at"
            ).fetchall()
            if rows:
                records.extend([dict(r) for r in rows])
                print(f"  Loaded {len(rows)} rows from lifecycle.db:tracegrant_grants", file=sys.stderr)
        except sqlite3.OperationalError as e:
            print(f"  tracegrant_grants load error: {e}", file=sys.stderr)
        conn.close()
    except Exception as e:
        print(f"  lifecycle.db load error: {e}", file=sys.stderr)
    return records


def load_from_session_logs() -> list[dict]:
    """Load tool-call sequences from session JSONL logs."""
    records = []
    for logs_dir in [SESSION_LOGS_DIR,
                     _RT / "sessions",
                     HOME / ".hermes/logs"]:
        if not logs_dir.exists():
            continue
        for log_file in sorted(logs_dir.glob("*.jsonl"))[-100:]:
            session_id = log_file.stem
            try:
                lines = log_file.read_text().splitlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        entry.setdefault("session_id", session_id)
                        records.append(entry)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass
    print(f"  Loaded {len(records)} records from session JSONL logs", file=sys.stderr)
    return records


# ── Circuit extraction ─────────────────────────────────────────────────────────

def extract_tool_name(record: dict) -> str | None:
    """Extract a canonical tool/skill name from a JSONL record."""
    # JSONL format: tool_calls is a list of {function: {name: ...}}
    tool_calls = record.get("tool_calls")
    if tool_calls and isinstance(tool_calls, list):
        for tc in tool_calls:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function", {})
            name = fn.get("name", "")
            if name and isinstance(name, str):
                return name.lower().strip()
    # Flat fields (tracegrant, fallback)
    for field in ("tool", "tool_name", "skill", "action", "type", "event_type", "name"):
        val = record.get(field, "")
        if val and isinstance(val, str) and len(val) > 1:
            val = val.lower().replace("tool_call:", "").replace("skill:", "").strip()
            return val
    return None


def records_to_sequences(records: list[dict]) -> list[tuple[list[str], float]]:
    """Group records by session_id, return list of (tool_sequence, outcome_score)."""
    sessions: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        sid = r.get("session_id") or r.get("session") or r.get("run_id") or "default"
        sessions[str(sid)].append(r)

    sequences = []
    for sid, sess_records in sessions.items():
        # Sort by timestamp or index if available
        try:
            sess_records.sort(key=lambda r: r.get("timestamp") or r.get("ts") or r.get("inserted_at") or "")
        except Exception:
            pass
        tools = [extract_tool_name(r) for r in sess_records]
        tools = [t for t in tools if t]  # drop None
        if len(tools) < 2:
            continue
        # Session outcome = mean of individual record scores
        sess_score = sum(outcome_score(r) for r in sess_records) / len(sess_records)
        sequences.append((tools, sess_score))

    return sequences


def extract_ngrams(tools: list[str], n: int) -> list[tuple[str, ...]]:
    """Extract all n-grams from a tool sequence."""
    return [tuple(tools[i:i+n]) for i in range(len(tools) - n + 1)]


# ── Scoring ────────────────────────────────────────────────────────────────────

def score_circuits(sequences: list[tuple[list[str], float]],
                   min_freq: int = 2,
                   ngram_sizes: tuple = (2, 3, 4)) -> list[dict]:
    """Score all n-gram circuits by frequency × mean outcome score."""
    ngram_counts: Counter = Counter()
    ngram_scores: dict[tuple, list[float]] = defaultdict(list)

    for tools, sess_score in sequences:
        seen_in_session = set()
        for n in ngram_sizes:
            for ng in extract_ngrams(tools, n):
                ngram_counts[ng] += 1
                if ng not in seen_in_session:
                    ngram_scores[ng].append(sess_score)
                    seen_in_session.add(ng)

    circuits = []
    for ng, count in ngram_counts.items():
        if count < min_freq:
            continue
        scores = ngram_scores[ng]
        mean_score = sum(scores) / len(scores) if scores else 0.5
        circuit_score = count * mean_score  # frequency × quality
        circuits.append({
            "circuit": list(ng),
            "circuit_str": " → ".join(ng),
            "length": len(ng),
            "frequency": count,
            "mean_outcome": round(mean_score, 3),
            "circuit_score": round(circuit_score, 3),
            "sessions_seen": len(scores),
        })

    circuits.sort(key=lambda x: x["circuit_score"], reverse=True)
    return circuits


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Score Hermes tool-call circuit patterns")
    parser.add_argument("--min-freq", type=int, default=2, help="Minimum circuit frequency (default 2)")
    parser.add_argument("--top", type=int, default=30, help="Top N circuits to output (default 30)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output files")
    args = parser.parse_args()

    print(f"[circuit-scorer] Loading tool-call records...", file=sys.stderr)
    records = []
    records.extend(load_from_lifecycle_db())
    records.extend(load_from_session_logs())
    print(f"[circuit-scorer] Total records: {len(records)}", file=sys.stderr)

    if not records:
        print("[circuit-scorer] No records found — nothing to score. Run more sessions first.", file=sys.stderr)
        print(json.dumps({"status": "no_data", "message": "No session records found"}, indent=2))
        return

    sequences = records_to_sequences(records)
    print(f"[circuit-scorer] {len(sequences)} session sequences extracted", file=sys.stderr)

    if not sequences:
        print("[circuit-scorer] No sequences extracted — records may lack tool_name/session_id fields.", file=sys.stderr)
        return

    circuits = score_circuits(sequences, min_freq=args.min_freq)
    top_circuits = circuits[:args.top]

    output = {
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "total_sessions": len(sequences),
        "total_records": len(records),
        "total_circuits_found": len(circuits),
        "min_freq_filter": args.min_freq,
        "top_circuits": top_circuits,
    }

    if not args.dry_run:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _tmp_output_path = OUTPUT_PATH.with_suffix('.tmp')
        _tmp_output_path.write_text(json.dumps(output, indent=2))
        _tmp_output_path.replace(OUTPUT_PATH)
        print(f"[circuit-scorer] Written: {OUTPUT_PATH}", file=sys.stderr)

        # Routing hints: top-5 circuits as skill-routing suggestions
        hints = {
            "generated_at": output["scored_at"],
            "hint": "These tool-call sequences have the highest historical success rate. Prefer them when routing similar tasks.",
            "top_circuits": top_circuits[:5],
        }
        _tmp_skill_hint_path = SKILL_HINT_PATH.with_suffix('.tmp')
        _tmp_skill_hint_path.write_text(json.dumps(hints, indent=2))
        _tmp_skill_hint_path.replace(SKILL_HINT_PATH)
        print(f"[circuit-scorer] Routing hints: {SKILL_HINT_PATH}", file=sys.stderr)

    print(f"\n=== Circuit Trajectory Scores — {output['scored_at'][:10]} ===")
    print(f"Sessions: {len(sequences)}, Circuits found: {len(circuits)}")
    print()
    if top_circuits:
        print(f"Top {min(args.top, len(top_circuits))} circuits (freq × mean_outcome):")
        for c in top_circuits[:15]:
            print(f"  [{c['circuit_score']:.1f}] (freq={c['frequency']}, quality={c['mean_outcome']:.2f}) {c['circuit_str']}")
    else:
        print(f"No circuits met min-freq={args.min_freq}. Try --min-freq 1.")


if __name__ == "__main__":
    main()
