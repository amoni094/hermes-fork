#!/usr/bin/env python3
"""MDP autonomy router: escalate to human-in-the-loop by confidence."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import sys
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "autonomy-routing-state.json"
STATES = ("routine", "ambiguous", "critical")


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def route(confidence: float, risk: float = 0.0) -> dict:
    c = min(1.0, max(0.0, float(confidence)))
    r = min(1.0, max(0.0, float(risk)))
    if r >= 0.8 or c < 0.35:
        state = "critical"
        action = "human_escalate"
    elif c < 0.7 or r >= 0.4:
        state = "ambiguous"
        action = "hybrid"
    else:
        state = "routine"
        action = "auto_resolve"
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "confidence": round(c, 6),
        "risk": round(r, 6),
        "state": state,
        "action": action,
        "states": list(STATES),
    }


def self_test() -> dict:
    a = route(0.95, 0.1)
    b = route(0.5, 0.2)
    c = route(0.2, 0.9)
    assert a["state"] == "routine", a
    assert b["state"] == "ambiguous", b
    assert c["state"] == "critical", c
    return {"self_test": "PASS", "routine": a, "ambiguous": b, "critical": c}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--confidence", type=float, default=0.8)
    ap.add_argument("--risk", type=float, default=0.1)
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    out = route(args.confidence, args.risk)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
