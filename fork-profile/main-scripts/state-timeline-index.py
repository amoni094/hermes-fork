#!/usr/bin/env python3
"""
state-timeline-index.py — RAFT stateful retrieval index for session recovery.

Based on: RAFT (arXiv:2609.20754) — Retrieval-Augmented Framework for Troubleshooting
Indexes session JSONL rows as (session_id, turn_idx, tool_name, state_summary).
On stall/debug, BM25-matches current tool-state to an intermediate entry, then injects
only the remainder of that parent trajectory (subsequent tools + outcomes).

Usage:
  python3 state-timeline-index.py --index          # Index all session JSONL files
  python3 state-timeline-index.py --query TEXT     # Find matching trajectory anchor
  python3 state-timeline-index.py --prune          # Remove entries older than 30 days
"""
import argparse, json, math, os, pathlib, re, sqlite3, sys, time
from collections import defaultdict

HERMES_HOME = pathlib.Path(os.environ.get("HERMES_HOME", str(pathlib.Path.home() / ".hermes")))
HERMES_PROFILE = os.environ.get("HERMES_PROFILE", "")
if HERMES_PROFILE and "profiles" not in str(HERMES_HOME):
    HERMES_ROOT = HERMES_HOME / "profiles" / HERMES_PROFILE
else:
    HERMES_ROOT = HERMES_HOME

SESSIONS_DIR = HERMES_ROOT / "cache" / "sessions"
INDEX_DB = HERMES_ROOT / "cache" / "raft-timeline-index.db"
RETENTION_DAYS = 30


def get_db(db_path: pathlib.Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS timeline_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_idx INTEGER NOT NULL,
            tool_name TEXT,
            state_summary TEXT,
            outcome TEXT,
            ts_epoch REAL,
            UNIQUE(session_id, turn_idx)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tool ON timeline_entries(tool_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON timeline_entries(ts_epoch)")
    conn.commit()
    return conn


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]{2,}", text.lower())


def bm25_score(query_tokens: list[str], doc_tokens: list[str],
               idf: dict[str, float], avgdl: float = 20.0,
               k1: float = 1.5, b: float = 0.75) -> float:
    tf: dict[str, int] = defaultdict(int)
    for t in doc_tokens:
        tf[t] += 1
    dl = len(doc_tokens)
    score = 0.0
    for t in query_tokens:
        if t not in tf:
            continue
        f = tf[t]
        score += idf.get(t, 0.0) * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / max(avgdl, 1)))
    return score


def index_session_file(conn: sqlite3.Connection, jsonl_path: pathlib.Path) -> int:
    """Parse one session JSONL and insert timeline entries. Returns rows inserted."""
    session_id = jsonl_path.stem
    inserted = 0
    try:
        lines = jsonl_path.read_text(errors="replace").splitlines()
    except OSError:
        return 0

    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue

        role = row.get("role", row.get("type", ""))
        if role not in ("tool", "tool_result", "assistant"):
            continue

        tool_name = row.get("name", row.get("tool_name", ""))
        content = row.get("content", "")
        if isinstance(content, list):
            # Anthropic message format: content is a list of blocks
            content = " ".join(
                b.get("text", b.get("input", {}).get("command", "")) if isinstance(b, dict) else str(b)
                for b in content
            )
        state_summary = str(content)[:512]
        outcome = "success" if row.get("exit_code", 0) == 0 else "error"
        ts = row.get("ts", row.get("timestamp", time.time()))

        try:
            conn.execute(
                "INSERT OR IGNORE INTO timeline_entries "
                "(session_id, turn_idx, tool_name, state_summary, outcome, ts_epoch) "
                "VALUES (?,?,?,?,?,?)",
                (session_id, idx, tool_name or None, state_summary, outcome, float(ts) if ts else None)
            )
            inserted += 1
        except sqlite3.Error:
            pass

    conn.commit()
    return inserted


def cmd_index() -> None:
    if not SESSIONS_DIR.is_dir():
        print(f"Sessions dir not found: {SESSIONS_DIR}", file=sys.stderr)
        sys.exit(2)

    conn = get_db(INDEX_DB)
    total = 0
    for p in sorted(SESSIONS_DIR.glob("*.jsonl")):
        n = index_session_file(conn, p)
        if n:
            total += n
            print(f"  indexed {p.name}: +{n} entries")
    conn.close()
    print(f"Total: {total} entries indexed to {INDEX_DB}")


def cmd_query(query_text: str, top: int = 3) -> None:
    if not INDEX_DB.exists():
        print("Index not built. Run --index first.", file=sys.stderr)
        sys.exit(2)

    conn = get_db(INDEX_DB)
    # Load all entries for BM25
    rows = conn.execute(
        "SELECT session_id, turn_idx, tool_name, state_summary, outcome FROM timeline_entries"
    ).fetchall()
    conn.close()

    if not rows:
        print("Index is empty.", file=sys.stderr)
        sys.exit(2)

    # Compute IDF
    q_tokens = tokenize(query_text)
    df: dict[str, int] = defaultdict(int)
    doc_tokens_all = []
    for row in rows:
        doc_text = f"{row[2] or ''} {row[3] or ''}"
        dt = tokenize(doc_text)
        doc_tokens_all.append(dt)
        for t in set(dt):
            df[t] += 1

    N = len(rows)
    idf = {t: math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1) for t in df}
    avgdl = sum(len(d) for d in doc_tokens_all) / max(N, 1)

    scored = [
        (bm25_score(q_tokens, doc_tokens_all[i], idf, avgdl), rows[i])
        for i in range(N)
    ]
    scored.sort(key=lambda x: -x[0])
    top_results = scored[:top]

    if not top_results or top_results[0][0] <= 0:
        print("No matching trajectory anchors found.")
        return

    print(f"Top {top} trajectory anchors for: {query_text!r}")
    for score, (session_id, turn_idx, tool_name, state_summary, outcome) in top_results:
        print(f"  score={score:.3f} session={session_id} turn={turn_idx} "
              f"tool={tool_name} outcome={outcome}")
        print(f"    summary: {(state_summary or '')[:120]}")

    # Output best match as JSON for programmatic consumption
    best_score, best_row = top_results[0]
    print(json.dumps({
        "session_id": best_row[0],
        "anchor_turn": best_row[1],
        "tool_name": best_row[2],
        "score": best_score,
        "state_summary": (best_row[3] or "")[:200],
    }))


def cmd_prune() -> None:
    if not INDEX_DB.exists():
        return
    conn = get_db(INDEX_DB)
    cutoff = time.time() - RETENTION_DAYS * 86400
    cur = conn.execute("DELETE FROM timeline_entries WHERE ts_epoch < ?", (cutoff,))
    deleted = cur.rowcount
    conn.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f"Pruned {deleted} entries older than {RETENTION_DAYS} days.")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAFT stateful trajectory index")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--index", action="store_true", help="Index session JSONL files")
    group.add_argument("--query", metavar="TEXT", help="Find matching trajectory anchor")
    group.add_argument("--prune", action="store_true", help="Remove old entries")
    parser.add_argument("--top", type=int, default=3, help="Top results to return (--query)")
    args = parser.parse_args()

    if args.index:
        cmd_index()
    elif args.query:
        cmd_query(args.query, top=args.top)
    elif args.prune:
        cmd_prune()


if __name__ == "__main__":
    main()
