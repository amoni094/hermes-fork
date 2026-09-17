#!/usr/bin/python3
"""
entropy-fidelity-stability-monitor.py

Detects memory degradation by tracking the entropy-fidelity bound across
memory consolidation events. When memory entropy increases faster than
fidelity can absorb, the memory layer is losing signal.

Math basis (information_theory / rate-distortion): the entropy-fidelity tradeoff
gives a lower bound on information loss under any compression. R(D) = min_{p(y|x):E[d]<=D} I(X;Y).
When monitored cumulatively over memory events, rising entropy with flat or falling
fidelity signals lossy-but-irreversible compression — the distortion D is exceeding
the acceptable fidelity constraint, and information cannot be recovered.

Concretely for Hermes:
  - Memory writes = compression events (x → y via LLM summarization)
  - Entropy H(Y) estimated from token-frequency distribution of memory surface content
  - Fidelity F = coverage of source facts (estimated from memory-facts/lifecycle.db
    entry survival rate: how many facts survive consolidation)
  - Alarm: ΔH > 0 (entropy rising) AND ΔF < 0 (fidelity falling) over sliding window
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
MEMORY_DIR = HOME / ".hermes/memories"
FACTS_DB   = HOME / ".hermes/memory-facts/lifecycle.db"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
ALARM_FILE = CACHE_DIR / "entropy-fidelity-alarm.json"
STATE_FILE = CACHE_DIR / "entropy-fidelity-state.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

# --- helpers ------------------------------------------------------------------

def _token_entropy(text: str) -> float:
    """Estimate token-level entropy from word frequency distribution."""
    words = text.lower().split()
    if not words:
        return 0.0
    counts = Counter(words)
    n = len(words)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _read_memory_entropy() -> float:
    """Estimate entropy of current memory surface (all .md files in memories dir)."""
    texts: list[str] = []
    for md in MEMORY_DIR.glob("*.md"):
        try:
            texts.append(md.read_text())
        except Exception:
            pass
    if not texts:
        return 0.0
    combined = " ".join(texts)
    return _token_entropy(combined)


def _read_fidelity() -> float:
    """
    Estimate memory fidelity from lifecycle.db survival rate.
    Fidelity = fraction of inserted facts that are still valid (valid_to IS NULL or future).
    """
    if not FACTS_DB.exists():
        return 1.0  # no DB = no consolidation loss yet
    try:
        con = sqlite3.connect(str(FACTS_DB))
        cur = con.cursor()
        # total facts ever inserted
        cur.execute("SELECT COUNT(*) FROM memory_facts")
        total = cur.fetchone()[0]
        if total == 0:
            con.close()
            return 1.0
        # still-valid facts (valid_to is NULL = no expiry, or valid_to in the future)
        now_ts = time.time()
        cur.execute(
            "SELECT COUNT(*) FROM memory_facts WHERE valid_to IS NULL OR valid_to > ?",
            (now_ts,),
        )
        alive = cur.fetchone()[0]
        con.close()
        return alive / total
    except Exception:
        return 1.0


def _read_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"snapshots": []}


def _write_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _append_alarm(alarm: dict) -> None:
    existing: list = []
    if ALARM_FILE.exists():
        try:
            existing = json.loads(ALARM_FILE.read_text())
        except Exception:
            pass
    existing.append(alarm)
    ALARM_FILE.write_text(json.dumps(existing[-50:], indent=2))  # keep last 50


# --- main logic ---------------------------------------------------------------

def run(dry_run: bool = False, window: int = 5) -> None:
    now = datetime.now(timezone.utc).isoformat()
    entropy  = _read_memory_entropy()
    fidelity = _read_fidelity()

    state = _read_state()
    snapshots: list[dict] = state.get("snapshots", [])

    # Add current snapshot
    snap = {"ts": now, "entropy": entropy, "fidelity": fidelity}
    snapshots.append(snap)
    # Keep last 20
    snapshots = snapshots[-20:]

    alarm = False
    alarm_reason = ""

    if len(snapshots) >= window:
        window_snaps = snapshots[-window:]
        h_first = window_snaps[0]["entropy"]
        h_last  = window_snaps[-1]["entropy"]
        f_first = window_snaps[0]["fidelity"]
        f_last  = window_snaps[-1]["fidelity"]

        delta_h = h_last - h_first
        delta_f = f_last - f_first

        # Alarm: entropy rising AND fidelity falling over window
        if delta_h > 0.05 and delta_f < -0.02:
            alarm = True
            alarm_reason = (
                f"ΔH={delta_h:+.3f} bits (entropy rising), "
                f"ΔF={delta_f:+.3f} (fidelity falling) over last {window} snapshots"
            )

    print(f"\n=== Entropy-Fidelity Stability Monitor — {now[:10]} ===")
    print(f"Memory entropy H:  {entropy:.4f} bits")
    print(f"Fact fidelity  F:  {fidelity:.4f}")
    print(f"Snapshots stored:  {len(snapshots)}")

    if alarm:
        print(f"\nALARM: yes — {alarm_reason}")
        alarm_rec = {
            "ts": now,
            "entropy": entropy,
            "fidelity": fidelity,
            "reason": alarm_reason,
        }
        if not dry_run:
            _append_alarm(alarm_rec)
        print(f"Written to: {ALARM_FILE}")
    else:
        print("\nALARM: no — entropy-fidelity within bounds")

    if not dry_run:
        state["snapshots"] = snapshots
        _write_state(state)
        print(f"State saved: {STATE_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Entropy-fidelity stability monitor")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--window", type=int, default=5,
                        help="Rolling window size for trend detection (default 5)")
    args = parser.parse_args()
    run(dry_run=args.dry_run, window=args.window)


if __name__ == "__main__":
    main()
