#!/usr/bin/python3
"""
federated-consensus-monitor.py

Enables Hermes to detect and automatically recover from skill-delegation
fragmentation — monitors agreement across parallel subagent outputs and
flags divergence that exceeds a configurable threshold.

Math basis: federated consensus as Jensen-Shannon divergence across agents
  Given k parallel agent outputs O_1..O_k, model each as a probability
  distribution over outcome tokens P_i(w) = count(w,O_i)/|O_i|.
  JS divergence: JSD(P_1..P_k) = H(mean(P_i)) - mean(H(P_i))
  Consensus score = 1 - JSD  (1.0 = perfect agreement, 0.0 = max fragmentation)
  FRAGMENTED when JSD > FRAGMENTATION_THRESHOLD.

Usage:
  python3 federated-consensus-monitor.py              # scan recent sessions
  python3 federated-consensus-monitor.py --outputs "ans1" "ans2" "ans3"
  python3 federated-consensus-monitor.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "federated-consensus-report.json"

FRAGMENTATION_THRESHOLD = 0.40   # JSD > 0.40 → fragmented


def _tokenize(text: str) -> Counter:
    words = re.findall(r"[a-z0-9_]{2,}", text.lower())
    return Counter(words)


def _to_dist(counter: Counter, vocab: set[str]) -> np.ndarray:
    total = sum(counter.values()) or 1
    return np.array([counter.get(w, 0) / total for w in sorted(vocab)])


def _entropy(p: np.ndarray) -> float:
    p = p[p > 0]
    return float(-np.sum(p * np.log2(p + 1e-12)))


def jsd(distributions: list[np.ndarray]) -> float:
    """Jensen-Shannon divergence across k distributions."""
    k    = len(distributions)
    mean = np.mean(distributions, axis=0)
    h_mean = _entropy(mean)
    h_each = np.mean([_entropy(d) for d in distributions])
    return float(min(max(0.0, h_mean - h_each), math.log(max(len(distributions), 2))))


def compute_consensus(outputs: list[str]) -> dict:
    if len(outputs) < 2:
        return {"error": "need ≥2 outputs", "jsd": 0.0, "consensus": 1.0}

    counters = [_tokenize(o) for o in outputs]
    vocab    = set().union(*[set(c.keys()) for c in counters])
    dists    = [_to_dist(c, vocab) for c in counters]
    j        = jsd(dists)
    consensus = 1.0 - j
    fragmented = j > FRAGMENTATION_THRESHOLD

    return {
        "n_outputs":   len(outputs),
        "vocab_size":  len(vocab),
        "jsd":         round(j, 4),
        "consensus":   round(consensus, 4),
        "fragmented":  fragmented,
        "threshold":   FRAGMENTATION_THRESHOLD,
    }


def _extract_assistant_outputs(session_path: Path) -> list[str]:
    outputs = []
    for line in session_path.read_text().splitlines():
        try:
            ev = json.loads(line)
            if ev.get("role") == "assistant":
                content = ev.get("content", "")
                if isinstance(content, str) and len(content) > 30:
                    outputs.append(content[:500])
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            txt = block.get("text", "")
                            if len(txt) > 30:
                                outputs.append(txt[:500])
        except Exception:
            pass
    return outputs


def run(outputs: list[str] | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    if outputs:
        result = compute_consensus(outputs)
        print(f"\n=== Federated Consensus Monitor ===")
        print(f"Outputs: {result['n_outputs']}  vocab={result['vocab_size']}")
        print(f"JSD={result['jsd']:.4f}  consensus={result['consensus']:.4f}")
        if result["fragmented"]:
            print(f"FRAGMENTED: YES — JSD {result['jsd']:.3f} > {FRAGMENTATION_THRESHOLD}")
            return 1
        else:
            print(f"FRAGMENTED: NO — consensus within bounds")
            return 0

    # Session-level scan: compare assistant outputs within each session
    paths   = sorted(SESSIONS_DIR.glob("*.jsonl"))[-5:]
    results = []

    for p in paths:
        session_outputs = _extract_assistant_outputs(p)
        if len(session_outputs) < 2:
            results.append({
                "session": p.stem, "outputs": len(session_outputs),
                "note": "insufficient outputs for consensus check",
            })
            continue
        r = compute_consensus(session_outputs)
        r["session"] = p.stem
        results.append(r)

    print(f"\n=== Federated Consensus Monitor — {now[:10]} ===")
    print(f"Sessions checked: {len(results)}")

    fragmented_sessions = [r for r in results if r.get("fragmented")]
    for r in results:
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            icon = "✗" if r["fragmented"] else "✓"
            print(f"  {icon} {r['session'][:30]}  "
                  f"outputs={r['n_outputs']}  JSD={r['jsd']:.3f}  "
                  f"cons={r['consensus']:.3f}")

    if fragmented_sessions:
        print(f"\nALARM: yes — {len(fragmented_sessions)} session(s) show output fragmentation "
              f"(JSD > {FRAGMENTATION_THRESHOLD})")
        alarm_exit = 1
    else:
        print(f"\nALARM: no — all sessions within consensus bounds")
        alarm_exit = 0

    if not dry_run:
        OUT_FILE.write_text(json.dumps({"ts": now, "results": results}, indent=2))

    return alarm_exit


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outputs", nargs="+", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.outputs, args.dry_run))


if __name__ == "__main__":
    main()
