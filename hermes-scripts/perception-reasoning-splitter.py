#!/usr/bin/env python3
"""Split agent errors into perception failures vs reasoning failures."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import re
import sys
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "perception-reasoning-split.json"
PERCEPT = re.compile(r"(misread|misparse|ocr|did not see|missed input|wrong file|wrong image|hallucinited input|input error|perception)", re.IGNORECASE)
REASON = re.compile(r"(logic|invalid|contradict|wrong conclusion|arithmetic|infer|because|therefore|reasoning)", re.IGNORECASE)


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def classify_step(step: dict) -> str:
    blob = json.dumps(step, default=str).lower()
    err = bool(step.get("error") or step.get("failed") or step.get("ok") is False)
    if not err and "error" not in blob and "fail" not in blob:
        return "ok"
    p = bool(PERCEPT.search(blob))
    r = bool(REASON.search(blob))
    if p and not r:
        return "perception"
    if r and not p:
        return "reasoning"
    if "tool" in blob and ("not found" in blob or "missing" in blob or "path" in blob):
        return "perception"
    return "reasoning"


def split_trace(trace: list) -> dict:
    rows = []
    for i, step in enumerate(trace or []):
        if not isinstance(step, dict):
            step = {"raw": step}
        label = classify_step(step)
        rows.append({"step": i, "label": label, "action": step.get("action") or step.get("tool")})
    n_p = sum(1 for r in rows if r["label"] == "perception")
    n_r = sum(1 for r in rows if r["label"] == "reasoning")
    n_ok = sum(1 for r in rows if r["label"] == "ok")
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "n": len(rows),
        "perception_errors": n_p,
        "reasoning_errors": n_r,
        "ok_steps": n_ok,
        "steps": rows,
    }


def self_test() -> dict:
    tr = [
        {"action": "read", "error": "misread the input file path"},
        {"action": "conclude", "failed": True, "detail": "logic contradiction therefore wrong conclusion"},
        {"action": "ok_step", "ok": True},
    ]
    r = split_trace(tr)
    assert r["perception_errors"] >= 1, r
    assert r["reasoning_errors"] >= 1, r
    assert split_trace([])["n"] == 0
    return {"self_test": "PASS", "sample": r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    raw = args.json
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read()
    trace = []
    if raw:
        try:
            obj = json.loads(raw)
            trace = obj if isinstance(obj, list) else obj.get("trace") or obj.get("steps") or []
        except json.JSONDecodeError:
            trace = []
    out = split_trace(trace)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
