#!/usr/bin/env python3
"""
se-gos-graphiti-bridge.py — SE-GoS skill graph evolution via Graphiti edge weights.

Implements arXiv:2609.08228 (SE-GoS): evolve the skill retrieval graph from
execution traces. Reads yield metrics from skill-yield-tracker.py's SQLite DB,
translates them into Graphiti episodes that encode skill edge weights, then
writes those episodes via l1-graphiti-write.py's MCP transport.

One evolution round improves reward: 52.4% -> 59.4%, 1/3 fewer input tokens.
Round-over-round overfitting warning: reward drops 59.4% -> 54.0% at round 3.
Run weekly, not daily. Stop if 3-week moving average drops below baseline.

Usage:
  python3 se-gos-graphiti-bridge.py [--dry-run] [--min-invocations N]
  --dry-run:          print episodes without writing to Graphiti
  --min-invocations:  minimum invocations before a skill's edge is updated (default: 3)

Cron: weekly Sunday 03:00 (configured separately via cronjob_manage)
"""
import sys
import json
import sqlite3
import datetime
import importlib.util
import pathlib
import urllib.request
import time

SCRIPTS_DIR = pathlib.Path(__file__).parent.parent.parent.parent.parent / ".hermes" / "scripts"
# Fallback: resolve relative to home
if not SCRIPTS_DIR.exists():
    SCRIPTS_DIR = pathlib.Path.home() / ".hermes" / "scripts"

DB_PATH = pathlib.Path.home() / ".hermes/state.db"
GRAPHITI_BASE = "http://127.0.0.1:8765/mcp"
GROUP_ID = "hermes-skill-graph"
TIMEOUT = 60
MIN_INVOCATIONS_DEFAULT = 3

# SE-GoS edge weight bands (arXiv:2609.08228 Table 3)
# yield >= 0.7  -> reinforce  (increment edge weight: skill is reliably useful)
# yield 0.3-0.7 -> stable     (no change)
# yield < 0.3   -> decay      (decrement edge weight: skill loaded but rarely helps)
BAND_REINFORCE = 0.7
BAND_DECAY = 0.3

# Overfitting guard: stop if 3-week moving average of total reinforced skills drops
# This mirrors the paper's round-3 performance drop (59.4% -> 54.0%)
EVOLUTION_LOG = pathlib.Path.home() / ".hermes/cache/se-gos-evolution-log.jsonl"


def load_yield_data(min_invocations: int) -> list[dict]:
    """Read skill yield metrics from SQLite. Returns rows with enough data."""
    if not DB_PATH.exists():
        print(f"[se-gos] state.db not found at {DB_PATH} — nothing to evolve")
        return []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT skill_name, success_count, failure_count, invocation_count,
                   yield, normalized_yield, last_invoked_at
            FROM skill_yield_metrics
            WHERE invocation_count >= ? AND deprecated = 0
            ORDER BY normalized_yield DESC
            """,
            (min_invocations,)
        )
        return [dict(r) for r in cur.fetchall()]


def classify_band(yield_val: float) -> str:
    if yield_val >= BAND_REINFORCE:
        return "reinforce"
    elif yield_val >= BAND_DECAY:
        return "stable"
    else:
        return "decay"


def build_episodes(rows: list[dict]) -> list[dict]:
    """
    Convert yield rows into Graphiti episode dicts.

    Each episode encodes a skill's current edge weight signal:
      [se-gos] skill=<name> band=reinforce|stable|decay yield=0.82 invocations=14

    Graphiti's LLM extractor will see these as facts about the skill graph.
    Retrieval consumers (skill-graph-walk.py, skill-router-index.py) can
    query Graphiti for [se-gos] episodes to get the current edge weight band.
    """
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    episodes = []
    for row in rows:
        band = classify_band(row["yield"])
        if band == "stable":
            continue  # stable skills: no edge update needed, skip
        text = (
            f"[se-gos] skill={row['skill_name']} band={band} "
            f"yield={row['yield']:.3f} norm_yield={row['normalized_yield']:.3f} "
            f"invocations={row['invocation_count']} "
            f"success={row['success_count']} failure={row['failure_count']} "
            f"as_of={now}"
        )
        episodes.append({
            "name": f"se-gos-{row['skill_name']}-{now[:10]}",
            "body": (
                f"[source_type=cron] [as_of={now}] [vc=volatile] [ns=record] "
                f"[entities: Skill:{row['skill_name']}] {text}"
            ),
            "skill": row["skill_name"],
            "band": band,
            "yield": row["yield"],
        })
    return episodes


def mcp_initialize() -> str:
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "se-gos-bridge", "version": "1.0"},
        },
    }).encode()
    req = urllib.request.Request(
        GRAPHITI_BASE, data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        sid = resp.headers.get("mcp-session-id", "")
        if not sid:
            raise RuntimeError("No mcp-session-id from Graphiti initialize")
        resp.read()
    return sid


def mcp_write_episode(session_id: str, name: str, body: str) -> bool:
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "add_memory", "arguments": {
            "episode_body": body,
            "group_id": GROUP_ID,
            "name": name,
        }},
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "mcp-session-id": session_id,
    }
    req = urllib.request.Request(GRAPHITI_BASE, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode()
            for line in raw.splitlines():
                if line.startswith("data: "):
                    result = json.loads(line[6:])
                    text = str(result)
                    return "queued" in text.lower() or "success" in text.lower()
            return True  # assume ok if no error
    except Exception as e:
        print(f"  [se-gos] write failed for '{name}': {e}", file=sys.stderr)
        return False


def check_overfitting_guard() -> bool:
    """
    SE-GoS overfitting guard (paper: round 3 drops 59.4%->54.0%).
    Returns True (safe to proceed) if we have < 3 rounds or moving average
    of reinforced_count is not declining over last 3 weeks.
    """
    if not EVOLUTION_LOG.exists():
        return True
    rounds = []
    for line in EVOLUTION_LOG.read_text().splitlines():
        try:
            rounds.append(json.loads(line))
        except Exception:
            continue
    if len(rounds) < 3:
        return True
    last3 = [r["reinforced"] for r in rounds[-3:]]
    # Declining for 2 consecutive rounds = stop
    if last3[0] > last3[1] > last3[2]:
        print(
            f"[se-gos] OVERFITTING GUARD: reinforced skills declining "
            f"{last3[0]}->{last3[1]}->{last3[2]} over 3 weeks. Skipping evolution."
        )
        return False
    return True


def log_evolution_round(reinforced: int, decayed: int, skipped: int) -> None:
    EVOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reinforced": reinforced,
        "decayed": decayed,
        "skipped": skipped,
    }
    with open(EVOLUTION_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    dry_run = "--dry-run" in sys.argv
    min_inv = MIN_INVOCATIONS_DEFAULT
    if "--min-invocations" in sys.argv:
        idx = sys.argv.index("--min-invocations")
        try:
            min_inv = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("ERROR: --min-invocations requires an integer argument"); sys.exit(1)

    print(f"[se-gos] SE-GoS Graphiti bridge starting (dry_run={dry_run}, min_inv={min_inv})")

    if not dry_run and not check_overfitting_guard():
        sys.exit(0)  # guard triggered, exit cleanly

    rows = load_yield_data(min_inv)
    if not rows:
        print("[se-gos] No skill yield data with enough invocations — nothing to write")
        sys.exit(0)

    episodes = build_episodes(rows)
    reinforced = sum(1 for e in episodes if e["band"] == "reinforce")
    decayed = sum(1 for e in episodes if e["band"] == "decay")
    skipped = len(rows) - len(episodes)  # stable skills

    print(f"[se-gos] {len(rows)} skills evaluated: {reinforced} reinforce, {decayed} decay, {skipped} stable (skipped)")

    if not episodes:
        print("[se-gos] All skills stable — no edge updates needed")
        if not dry_run:
            log_evolution_round(0, 0, skipped)
        sys.exit(0)

    if dry_run:
        print("[se-gos] DRY RUN — episodes that would be written:")
        for ep in episodes:
            print(f"  [{ep['band']:9}] {ep['skill']:40} yield={ep['yield']:.3f}")
        sys.exit(0)

    # Connect to Graphiti
    try:
        session_id = mcp_initialize()
        print(f"[se-gos] Graphiti session established")
    except Exception as e:
        print(f"[se-gos] ERROR: Cannot connect to Graphiti at {GRAPHITI_BASE}: {e}", file=sys.stderr)
        sys.exit(1)

    written = 0
    failed = 0
    for ep in episodes:
        ok = mcp_write_episode(session_id, ep["name"], ep["body"])
        if ok:
            written += 1
            print(f"  queued: [{ep['band']:9}] {ep['skill']}  yield={ep['yield']:.3f}")
        else:
            failed += 1
        time.sleep(0.3)  # rate-limit Graphiti

    log_evolution_round(reinforced, decayed, skipped)
    print(f"[se-gos] Done: {written} written, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
