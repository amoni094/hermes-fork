#!/usr/bin/env python3
"""Cost-aware evaluation: success rate minus alpha * normalized cost."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import sys
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "cost-aware-eval.json"
ALPHA = 0.3


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def evaluate(runs: list, alpha: float = ALPHA) -> dict:
    rows = []
    costs = []
    for run in runs or []:
        if not isinstance(run, dict):
            run = {}
        sr = run.get("success_rate", 1.0 if run.get("success") else 0.0)
        try:
            sr = float(sr)
        except (TypeError, ValueError):
            sr = 0.0
        sr = min(1.0, max(0.0, sr))
        tc = float(run.get("tool_call_count") or 0)
        lat = float(run.get("latency_ms") or 0)
        tok = float(run.get("token_estimate") or 0)
        cost = tc + lat / 1000.0 + tok / 1000.0
        costs.append(cost)
        rows.append({"success_rate": sr, "tool_call_count": tc, "latency_ms": lat, "token_estimate": tok, "raw_cost": cost})
    mx = max(costs) if costs else 1.0
    mx = mx if mx > 0 else 1.0
    for row in rows:
        nc = row["raw_cost"] / mx
        row["normalized_cost"] = round(nc, 6)
        row["score"] = round(row["success_rate"] - alpha * nc, 6)
    mean = sum(r["score"] for r in rows) / float(len(rows) or 1)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "alpha": alpha,
        "n": len(rows),
        "mean_score": round(mean, 6),
        "runs": rows,
    }


def self_test() -> dict:
    runs = [
        {"success_rate": 1.0, "tool_call_count": 1, "latency_ms": 100, "token_estimate": 200},
        {"success_rate": 1.0, "tool_call_count": 20, "latency_ms": 5000, "token_estimate": 8000},
        {"success": False, "tool_call_count": 2, "latency_ms": 50, "token_estimate": 10},
    ]
    r = evaluate(runs)
    assert r["runs"][0]["score"] > r["runs"][1]["score"], r
    assert evaluate([])["n"] == 0
    return {"self_test": "PASS", "sample": r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", default="")
    ap.add_argument("--alpha", type=float, default=ALPHA)
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    raw = args.json
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read()
    runs = []
    if raw:
        try:
            obj = json.loads(raw)
            runs = obj if isinstance(obj, list) else obj.get("runs") or []
        except json.JSONDecodeError:
            runs = []
    out = evaluate(runs, args.alpha)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
