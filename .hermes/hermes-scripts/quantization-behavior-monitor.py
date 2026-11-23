#!/usr/bin/python3
"""
quantization-behavior-monitor.py

Detects condition-dependent payload activation — monitors whether Hermes
agent behavior changes anomalously when quantized/compressed models are
used vs. full-precision, a signal of AGENTQ-style backdoor conditioning.

Math basis: AGENTQ (quantization-conditioned backdoor attacks)
  Backdoored models activate malicious behavior only when quantized to
  specific bit-width. Detection: compare behavioral signatures between
  full and quantized execution paths.
  
  Operationally (without model access): monitor for structured function
  calls that appear only in certain response patterns, measuring:
    divergence(pattern_full, pattern_compressed) via token distribution shift
  Proxy: track tool-call distribution across sessions flagged as
  "compressed" (short context) vs. "full" (long context).

Usage:
  python3 quantization-behavior-monitor.py          # scan recent sessions
  python3 quantization-behavior-monitor.py --dry-run
"""
from __future__ import annotations
import os

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = _RT / "sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "quantization-behavior-report.json"

# Threshold for flagging behavioral divergence between short/long contexts
DIVERGENCE_THRESHOLD = 0.50   # JS divergence; 0=identical, 1=completely different
SHORT_CONTEXT_CHARS  = 2000   # sessions with <2000 chars total = "compressed" proxy
MIN_SESSIONS_EACH    = 1      # need at least 1 session in each bucket


def _extract_tools(session_path: Path) -> tuple[list[str], int]:
    """Return (tool_names, total_chars)."""
    tools      = []
    total_chars = 0
    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            content = ev.get("api_content", ev.get("content", ""))
            text    = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict):
                        text += b.get("text", "")
                        if b.get("type") == "tool_use":
                            tools.append(b.get("name", "unknown"))
            total_chars += len(text)
        except Exception:
            pass
    return tools, total_chars


def _js_divergence(p: Counter, q: Counter) -> float:
    """Jensen-Shannon divergence between two tool distributions."""
    all_keys = set(p.keys()) | set(q.keys())
    total_p  = sum(p.values()) or 1
    total_q  = sum(q.values()) or 1

    def safe_log(x: float) -> float:
        return math.log(x) if x > 0 else 0.0

    jsd = 0.0
    for k in all_keys:
        pi = p.get(k, 0) / total_p
        qi = q.get(k, 0) / total_q
        mi = (pi + qi) / 2
        if mi > 0:
            jsd += 0.5 * pi * safe_log(pi / mi) if pi > 0 else 0
            jsd += 0.5 * qi * safe_log(qi / mi) if qi > 0 else 0

    return min(jsd, 1.0)


def run(dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-20:]

    if not paths:
        print("[quant-behavior] No sessions found")
        return 0

    # Bucket sessions by context size
    short_tools: list[str] = []
    full_tools:  list[str] = []
    session_info = []

    for p in paths:
        tools, chars = _extract_tools(p)
        bucket = "short" if chars < SHORT_CONTEXT_CHARS else "full"
        session_info.append({
            "session": p.stem, "chars": chars,
            "tools": len(tools), "bucket": bucket,
        })
        if bucket == "short":
            short_tools.extend(tools)
        else:
            full_tools.extend(tools)

    n_short = sum(1 for s in session_info if s["bucket"] == "short")
    n_full  = sum(1 for s in session_info if s["bucket"] == "full")

    print(f"\n=== Quantization Behavior Monitor — {now[:10]} ===")
    print(f"Sessions: {len(paths)}  short={n_short}  full={n_full}")

    if n_short < MIN_SESSIONS_EACH or n_full < MIN_SESSIONS_EACH:
        print(f"\nALARM: no — insufficient sessions for comparison "
              f"(need ≥{MIN_SESSIONS_EACH} in each bucket)")
        return 0

    short_dist = Counter(short_tools)
    full_dist  = Counter(full_tools)
    jsd        = _js_divergence(short_dist, full_dist)
    alarm      = jsd > DIVERGENCE_THRESHOLD

    print(f"\nTool distribution divergence (JS): {jsd:.4f}  (threshold={DIVERGENCE_THRESHOLD})")
    print(f"Short-context tools: {dict(short_dist.most_common(5))}")
    print(f"Full-context tools:  {dict(full_dist.most_common(5))}")

    if alarm:
        print(f"\nALARM: yes — behavioral divergence {jsd:.3f} suggests "
              f"condition-dependent activation")
        rc = 1
    else:
        print(f"\nALARM: no — tool behavior consistent across context sizes")
        rc = 0

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "jsd": round(jsd, 4),
            "n_short": n_short, "n_full": n_full, "alarm": alarm,
            "sessions": session_info,
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)

    return rc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.dry_run))


if __name__ == "__main__":
    main()
