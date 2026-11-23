#!/usr/bin/env python3
"""
retrieval-saturation-monitor.py

Detects when Hermes recall/retrieval is pulling diminishing-value documents,
wasting context budget on low-marginal-value results.

Math basis (random_graphs / information_retrieval ideas queue):
  A retrieval-relevance ranking operator maintains a bounded information gap
  between query and retrieved set. When marginal relevance of the k-th document
  drops below a threshold (saturation), further retrieval adds noise, not signal.

  Implemented as: monitor the empirical relevance decay curve across retrieval
  calls in session logs. If the decay slope flattens (d(relevance)/d(k) < eps)
  before the context budget is exhausted, the retrieval is saturated.

  Relevance proxy: cosine similarity between query embedding (TF-IDF over query
  terms) and result embedding (TF-IDF over result content), measured from the
  arguments passed to recall/search tool calls in session JSONL.

Usage:
    python3 retrieval-saturation-monitor.py [--dry-run] [--threshold F] [--report]

Output:
    ~/.hermes/cache/retrieval-saturation.json  — saturation events
    ~/.hermes/cache/retrieval-saturation-alarm.json  — if alarm triggered
"""

import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np
import os

HOME = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = HOME / ".hermes/sessions"
FORK_SESSIONS = _RT / "sessions"  # fork-profile sessions

OUTPUT = HOME / ".hermes/cache/retrieval-saturation.json"
ALARM = HOME / ".hermes/cache/retrieval-saturation-alarm.json"

RETRIEVAL_TOOLS = {
    "web_search", "web_extract", "search_files", "unified_recall",
    "hindsight_recall", "skill_view", "read_file",
}


# ── TF-IDF cosine similarity (no external deps beyond numpy) ──────────────────

def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def tfidf_vector(tokens: list[str], vocab: list[str]) -> np.ndarray:
    count = {}
    for t in tokens:
        count[t] = count.get(t, 0) + 1
    total = len(tokens) or 1
    vec = np.array([count.get(v, 0) / total for v in vocab])
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


# ── Session parsing ────────────────────────────────────────────────────────────

def extract_retrieval_events(session_file: Path) -> list[dict]:
    """Extract retrieval tool calls with query and result content."""
    events = []
    try:
        lines = [l.strip() for l in session_file.read_text().splitlines() if l.strip()]
    except Exception:
        return events

    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    for i, rec in enumerate(records):
        if rec.get("role") != "assistant":
            continue
        for tc in (rec.get("tool_calls") or []):
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function", {})
            tool = fn.get("name", "").lower()
            if tool not in RETRIEVAL_TOOLS:
                continue
            # Extract query from arguments
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                args = {}
            query = args.get("query") or args.get("pattern") or args.get("path") or ""
            # Result: look for tool-result record after this
            result_content = ""
            for j in range(i + 1, min(i + 3, len(records))):
                nxt = records[j]
                if nxt.get("role") in ("tool", "user"):
                    content = nxt.get("content", "")
                    if isinstance(content, str):
                        result_content = content
                    break
            events.append({
                "tool": tool,
                "query": str(query)[:300],
                "result_len": len(result_content),
                "result_preview": result_content[:200],
                "session": session_file.stem,
            })
    return events


# ── Saturation detection ───────────────────────────────────────────────────────

def compute_saturation(events: list[dict], threshold: float) -> list[dict]:
    """Group events by session+tool, compute marginal relevance decay."""
    groups = defaultdict(list)
    for ev in events:
        key = f"{ev['session']}:{ev['tool']}"
        groups[key].append(ev)

    saturated = []
    for key, group in groups.items():
        if len(group) < 3:
            continue  # need at least 3 retrievals to detect decay

        # Build shared vocab
        all_tokens = []
        for ev in group:
            all_tokens.extend(tokenize(ev["query"]))
            all_tokens.extend(tokenize(ev["result_preview"]))
        vocab = sorted(set(all_tokens))
        if not vocab:
            continue

        # Query vector (first event's query as reference)
        q_vec = tfidf_vector(tokenize(group[0]["query"]), vocab)

        # Relevance of each result to query
        relevances = []
        for ev in group:
            r_vec = tfidf_vector(tokenize(ev["result_preview"]), vocab)
            relevances.append(cosine_sim(q_vec, r_vec))

        # Marginal decay: differences between successive relevances
        if len(relevances) < 2:
            continue
        deltas = [relevances[i] - relevances[i - 1] for i in range(1, len(relevances))]
        mean_delta = float(np.mean(deltas))

        # Saturation: mean delta is near-zero or negative (flat/declining curve)
        session_id, tool = key.split(":", 1)
        if mean_delta < threshold:
            saturated.append({
                "session": session_id,
                "tool": tool,
                "n_retrievals": len(group),
                "mean_relevance": round(float(np.mean(relevances)), 4),
                "mean_marginal_delta": round(mean_delta, 4),
                "relevances": [round(r, 4) for r in relevances],
                "saturated": True,
            })
    return saturated


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Retrieval saturation monitor")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--threshold", type=float, default=-0.01,
                        help="Mean marginal relevance delta below which saturation fires (default -0.01)")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    files = sorted([f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")])[-50:]
    all_events = []
    for f in files:
        all_events.extend(extract_retrieval_events(f))

    print(f"[retrieval-sat] {len(files)} sessions, {len(all_events)} retrieval events", file=sys.stderr)

    saturated = compute_saturation(all_events, args.threshold)

    now = datetime.now(timezone.utc).isoformat()
    result = {
        "analysed_at": now,
        "sessions": len(files),
        "retrieval_events": len(all_events),
        "saturated_chains": len(saturated),
        "chains": saturated,
    }

    if not args.dry_run:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        _tmp = OUTPUT.with_suffix('.tmp'); _tmp.write_text(json.dumps(result, indent=2)); _tmp.replace(OUTPUT)
        if saturated:
            _alarm_payload = json.dumps({"alarm": True, "saturated_chains": len(saturated), "details": saturated[:5], "ts": now}, indent=2)
            _tmp = ALARM.with_suffix('.tmp'); _tmp.write_text(_alarm_payload); _tmp.replace(ALARM)
            print(f"[retrieval-sat] ALARM: {len(saturated)} saturated chains — {ALARM}", file=sys.stderr)

    print(f"\n=== Retrieval Saturation Monitor — {now[:10]} ===")
    print(f"Sessions: {len(files)}, Events: {len(all_events)}, Saturated chains: {len(saturated)}")
    if saturated:
        print()
        for s in saturated[:10]:
            print(f"  [{s['tool']}] session={s['session'][:20]} "
                  f"n={s['n_retrievals']} mean_rel={s['mean_relevance']:.3f} "
                  f"delta={s['mean_marginal_delta']:.4f} SATURATED")
    else:
        print("  No saturation detected.")
    if args.dry_run:
        print("  (dry-run)")


if __name__ == "__main__":
    main()
