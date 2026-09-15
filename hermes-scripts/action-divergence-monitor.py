#!/usr/bin/python3
"""
action-divergence-monitor.py

Detects when Hermes tool-call patterns are diverging faster than an
information-theoretic stability bound allows — a signal that the agent
is entering an unstable exploration regime or chasing a spurious goal.

Math basis: KL divergence rate between consecutive tool-distribution windows.
  A stable agent has KL(P_t || P_{t-1}) < ε for small ε.
  When the divergence rate exceeds a Lyapunov-like stability bound
  (derived from entropy production rates in non-equilibrium systems),
  the agent's policy is drifting — not converging.

  Alarm when: mean KL over last WINDOW consecutive pairs > KL_THRESHOLD
  AND the trend is increasing (slope > 0).

  Distinct from performative-stability-monitor (which tracks JSD between
  full windows) — this tracks consecutive-pair KL rate trend.
"""
from __future__ import annotations

import json, math, sys
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

HOME          = Path.home()
SESSIONS_DIR  = HOME / ".hermes/sessions"
FORK_SESSIONS = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR     = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE      = CACHE_DIR / "action-divergence.json"

WINDOW        = 6
MIN_TOOLS     = 6
KL_THRESHOLD  = 0.80   # nats; consecutive-pair KL above = drifting
MIN_SESSIONS  = 4


def _tool_dist(path: Path) -> Counter:
    try:
        lines = path.read_text().strip().splitlines()
        msgs = [json.loads(l) for l in lines if l.strip()] if lines and lines[0].startswith("{") \
               else (json.loads(path.read_text()) if path.stat().st_size else [])
        msgs = msgs if isinstance(msgs, list) else msgs.get("messages", [])
    except Exception:
        return Counter()
    c: Counter = Counter()
    for msg in msgs:
        for b in (msg.get("content", []) if isinstance(msg.get("content"), list) else []):
            if isinstance(b, dict) and b.get("type") == "tool_use":
                c[b.get("name", "unknown")] += 1
    return c


def _kl(p: Counter, q: Counter) -> float:
    vocab = set(p) | set(q)
    n_p, n_q = sum(p.values()), sum(q.values())
    if not n_p or not n_q:
        return 0.0
    eps = 1e-9
    kl = 0.0
    for t in vocab:
        pp = p.get(t, 0) / n_p + eps
        qq = q.get(t, 0) / n_q + eps
        kl += pp * math.log(pp / qq)
    return max(kl, 0.0)


def run() -> int:
    now = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Action Divergence Monitor — {now[:10]} ===\n")

    files = sorted(
        [f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")],
        key=lambda p: p.stat().st_mtime
    )[-WINDOW:]

    dists = [(f.stem[:30], _tool_dist(f)) for f in files]
    dists = [(s, d) for s, d in dists if sum(d.values()) >= MIN_TOOLS]

    if len(dists) < MIN_SESSIONS:
        print(f"Analysable sessions: {len(dists)} (need {MIN_SESSIONS})")
        print("ALARM: no — insufficient data")
        return 0

    kls = []
    print(f"  {'Pair':<50} {'KL (nats)':>10}")
    print("  " + "-"*63)
    for i in range(1, len(dists)):
        kl = _kl(dists[i][1], dists[i-1][1])
        label = f"{dists[i-1][0][:22]}→{dists[i][0][:22]}"
        flag = "  ↑ HIGH" if kl > KL_THRESHOLD else ""
        print(f"  {label:<50} {kl:>10.4f}{flag}")
        kls.append(kl)

    mean_kl = sum(kls) / len(kls)
    # Trend: simple slope via least-squares
    n = len(kls)
    xs = list(range(n))
    slope = (n*sum(x*y for x,y in zip(xs,kls)) - sum(xs)*sum(kls)) / \
            max(n*sum(x**2 for x in xs) - sum(xs)**2, 1e-9)

    print(f"\nPairs analysed: {n}")
    print(f"Mean KL:        {mean_kl:.4f} nats  (threshold={KL_THRESHOLD})")
    print(f"Trend slope:    {slope:+.4f} (positive = diverging)")

    alarm = mean_kl > KL_THRESHOLD and slope > 0
    if alarm:
        print(f"\nALARM: yes — tool-call distribution diverging: mean KL={mean_kl:.4f} nats, slope={slope:+.4f}")
    else:
        print(f"\nALARM: no — action distribution stable (mean KL={mean_kl:.4f})")

    OUT_FILE.write_text(json.dumps({
        "ts": now, "pairs": n, "mean_kl": round(mean_kl, 6),
        "slope": round(slope, 6), "threshold": KL_THRESHOLD,
        "alarm": alarm, "kl_series": [round(k, 4) for k in kls],
    }, indent=2))
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(run())
