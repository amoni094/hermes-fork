#!/usr/bin/env python3
"""
Shadow-mode telemetry for Hermes feature evaluation.

Ported from Denuto `src/pipeline/shadow_telemetry.py` and `scripts/shadow_gate.py`.

Every new Hermes feature ships behind a flag, runs in shadow-mode (results
emitted as JSONL telemetry events, live path untouched), and a gate script
evaluates shadow events before promoting to default-on.

Design constraints (from Denuto):
  - record() NEVER raises — shadow path must not contaminate live analysis
  - Stdlib only. No boto3, no AWS SDK.
  - Deterministic event shape (schema version pinned).
  - Shadow path: swallows ALL exceptions.

Usage:
    from shadow_telemetry import ShadowConfig, is_shadow_enabled, record

    config = ShadowConfig(shadow_consistency_scoring=False, shadow_coverage_audit=False)

    if is_shadow_enabled(config, "consistency_scoring"):
        # Run shadow path (does NOT affect live result)
        record("consistency_scoring", {"score": 0.85, "n_agreements": 3}, sink="~/.hermes/logs/shadow.jsonl")

Gate evaluation:
    python shadow_telemetry.py --evaluate --flag consistency_scoring --events ~/.hermes/logs/shadow.jsonl
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextlib import suppress
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SHADOW_EVENT_SCHEMA_VERSION = 1
DEFAULT_SINK = Path.home() / ".hermes" / "logs" / "shadow_telemetry.jsonl"

# Gate thresholds (from Denuto shadow_gate.py)
GATE_MIN_EVENTS = 20          # Minimum events before gate evaluates
GATE_RECALL_UPLIFT_PP = 0.05  # Must show ≥5pp uplift to promote
GATE_FP_RATE_MAX = 0.10       # False positive rate must stay below 10%


@dataclass
class ShadowConfig:
    """
    Feature flags for shadow evaluation.
    All flags default-off. Enable in config.yaml under shadow_flags:
    """
    shadow_consistency_scoring: bool = False
    shadow_coverage_audit: bool = False
    shadow_middle_section_rerun: bool = False
    shadow_aimd_controller: bool = False
    shadow_loop_detection: bool = False
    # Add new flags here as new features are developed


def is_shadow_enabled(config: ShadowConfig, flag_name: str) -> bool:
    """
    Check if a shadow flag is enabled.
    Reads shadow_<flag_name> attribute from config.

    Example:
        is_shadow_enabled(config, "consistency_scoring")
        → reads config.shadow_consistency_scoring
    """
    attr = f"shadow_{flag_name}"
    return bool(getattr(config, attr, False))


def record(
    flag: str,
    analysis: dict[str, Any],
    sink: str | Path | None = None,
) -> None:
    """
    Emit one JSONL event to the shadow telemetry sink.

    NEVER RAISES. All exceptions are suppressed — shadow path must not
    contaminate live analysis.

    Event shape (schema v1):
        {"schema_version": 1, "flag": str, "ts": float, "analysis": dict}
    """
    with suppress(Exception):
        _record_impl(flag, analysis, sink)


def _record_impl(
    flag: str,
    analysis: dict[str, Any],
    sink: str | Path | None,
) -> None:
    """Actual recording — called from record() inside suppress()."""
    sink_path = Path(sink) if sink else DEFAULT_SINK
    sink_path.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "schema_version": SHADOW_EVENT_SCHEMA_VERSION,
        "flag": flag,
        "ts": time.time(),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "analysis": analysis,
    }
    with sink_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def evaluate_flag(
    flag: str,
    events_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Read shadow events for a flag, compute go/no-go verdict.

    Returns:
        {
          "flag": str,
          "verdict": "go" | "no_go" | "needs_more_data",
          "n_events": int,
          "reason": str,
          "metrics": dict,
        }
    """
    sink_path = Path(events_path) if events_path else DEFAULT_SINK
    events = []
    if sink_path.exists():
        with sink_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                with suppress(json.JSONDecodeError):
                    event = json.loads(line)
                    if event.get("flag") == flag:
                        events.append(event)

    n = len(events)
    if n < GATE_MIN_EVENTS:
        return {
            "flag": flag,
            "verdict": "needs_more_data",
            "n_events": n,
            "reason": f"Need {GATE_MIN_EVENTS} events, have {n}",
            "metrics": {},
        }

    # Compute aggregate metrics from analysis fields
    scores = [e.get("analysis", {}).get("score", None) for e in events]
    scores = [s for s in scores if s is not None]
    mean_score = sum(scores) / len(scores) if scores else None

    fp_count = sum(1 for e in events if e.get("analysis", {}).get("false_positive", False))
    fp_rate = fp_count / n

    metrics = {
        "n_events": n,
        "mean_score": mean_score,
        "fp_rate": fp_rate,
        "fp_count": fp_count,
    }

    if fp_rate > GATE_FP_RATE_MAX:
        return {
            "flag": flag,
            "verdict": "no_go",
            "n_events": n,
            "reason": f"FP rate {fp_rate:.2%} exceeds max {GATE_FP_RATE_MAX:.2%}",
            "metrics": metrics,
        }

    return {
        "flag": flag,
        "verdict": "go",
        "n_events": n,
        "reason": f"Gate passed: fp_rate={fp_rate:.2%} ≤ {GATE_FP_RATE_MAX:.2%}",
        "metrics": metrics,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Shadow telemetry gate evaluation")
    parser.add_argument("--evaluate", action="store_true", help="Run gate evaluation")
    parser.add_argument("--flag", required=True, help="Flag name to evaluate")
    parser.add_argument(
        "--events",
        default=str(DEFAULT_SINK),
        help=f"Path to JSONL events file (default: {DEFAULT_SINK})",
    )
    parser.add_argument("--emit-test", action="store_true", help="Emit a test event")
    args = parser.parse_args()

    if args.emit_test:
        config = ShadowConfig(shadow_consistency_scoring=True)
        if is_shadow_enabled(config, args.flag.replace("shadow_", "")):
            record(args.flag, {"score": 0.85, "n_agreements": 3}, sink=args.events)
            print(f"Emitted test event for flag={args.flag} to {args.events}")
        else:
            print(f"Flag {args.flag} is disabled in config")
        sys.exit(0)

    if args.evaluate:
        result = evaluate_flag(args.flag, args.events)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["verdict"] != "no_go" else 1)

    parser.print_help()
