#!/usr/bin/python3
"""
output-length-predictor.py

Enables Hermes agents to forecast decode workload before delegating to
sub-agents or choosing tool chains, preventing timeout/budget overruns
by routing heavy workloads to larger context windows or longer timeouts.

Research basis (output length prediction for LLM decode scheduling):
  Before dispatching a sub-agent task, predict the expected output token
  count from task features. Tasks with predicted length > threshold should:
    - Use longer timeouts (or background=true)
    - Use a larger context-window model
    - Be split into smaller subtasks

Math basis: linear regression on task features → log(output_tokens)
  Features:
    - n_clauses: number of task sub-goals (via conjunction counting)
    - has_code: boolean (code tasks → longer output)
    - has_research: boolean (research → long summaries)
    - has_implementation: boolean (implementation → long code)
    - n_files_mentioned: count of file paths in task
    - n_tools_mentioned: count of tool names mentioned

  Calibration: fitted on session data (token counts from past completed tasks)
  Falls back to feature-based heuristic when no calibration data exists.

Usage:
  python3 output-length-predictor.py "research arxiv papers on LLM agents"
  python3 output-length-predictor.py --calibrate  # fit from session history
  python3 output-length-predictor.py --dry-run
"""

from __future__ import annotations
import os

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_HH_OLP      = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP_OLP      = os.environ.get("HERMES_PROFILE", "fork")
_RT_OLP      = (_HH_OLP / "profiles" / _HP_OLP) if _HP_OLP else _HH_OLP
HOME         = Path.home()
SESSIONS_DIR = _RT_OLP / "sessions"
CACHE_DIR    = _HH_OLP / "cache" / "monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CALIB_FILE   = CACHE_DIR / "output-length-calibration.json"
OUT_FILE     = CACHE_DIR / "output-length-prediction.json"

# Default regression weights (log-scale; trained on internal heuristics)
# log(tokens) = w0 + w1*n_clauses + w2*has_code + w3*has_research + w4*has_impl + w5*n_files + w6*n_tools
DEFAULT_WEIGHTS = np.array([5.5, 0.3, 1.2, 0.8, 1.5, 0.2, 0.1])

# Thresholds for routing decisions
SHORT_THRESHOLD  = 500    # tokens — fast, no special handling
MEDIUM_THRESHOLD = 2000   # tokens — standard timeout
LONG_THRESHOLD   = 8000   # tokens — background=true, longer timeout
HUGE_THRESHOLD   = 20000  # tokens — split or use bigger model


def _extract_features(task: str) -> dict:
    task_l = task.lower()

    n_clauses = len(re.split(r"\band\b|\bthen\b|\balso\b|,|;", task, flags=re.IGNORECASE))

    has_code = int(bool(re.search(r"(?i)\b(code|implement|script|function|class|test|debug|refactor|fix bug)\b", task_l)))
    has_research = int(bool(re.search(r"(?i)\b(research|survey|paper|arxiv|literature|read|summarize|analyse)\b", task_l)))
    has_impl = int(bool(re.search(r"(?i)\b(implement|build|create|write|generate|develop|add feature)\b", task_l)))

    n_files = len(re.findall(r"[\~/][a-zA-Z0-9_./-]+\.[a-zA-Z]{1,5}", task))
    n_tools = len(re.findall(r"(?i)\b(terminal|web_search|execute_code|write_file|patch|browser|delegate|skill_view)\b", task_l))

    return {
        "n_clauses":  n_clauses,
        "has_code":   has_code,
        "has_research": has_research,
        "has_impl":   has_impl,
        "n_files":    min(n_files, 10),
        "n_tools":    min(n_tools, 10),
    }


def _feature_vector(f: dict) -> np.ndarray:
    return np.array([1.0, f["n_clauses"], f["has_code"],
                     f["has_research"], f["has_impl"],
                     f["n_files"], f["n_tools"]])


def _load_weights() -> np.ndarray:
    if CALIB_FILE.exists():
        try:
            d = json.loads(CALIB_FILE.read_text())
            w = np.array(d["weights"])
            if len(w) == len(DEFAULT_WEIGHTS):
                return w
        except Exception:
            pass
    return DEFAULT_WEIGHTS


def _predict_tokens(task: str, weights: np.ndarray) -> tuple[int, dict]:
    feats = _extract_features(task)
    fv    = _feature_vector(feats)
    log_tokens = float(np.dot(weights, fv))
    tokens = int(math.exp(log_tokens))
    return tokens, feats


def _routing_recommendation(tokens: int) -> dict:
    if tokens < SHORT_THRESHOLD:
        return {"tier": "SHORT", "timeout_s": 60, "background": False,
                "model_note": "any model", "split": False}
    elif tokens < MEDIUM_THRESHOLD:
        return {"tier": "MEDIUM", "timeout_s": 180, "background": False,
                "model_note": "standard context", "split": False}
    elif tokens < LONG_THRESHOLD:
        return {"tier": "LONG", "timeout_s": 600, "background": True,
                "model_note": "standard context, background=True", "split": False}
    elif tokens < HUGE_THRESHOLD:
        return {"tier": "HUGE", "timeout_s": 1800, "background": True,
                "model_note": "large context model preferred", "split": True}
    else:
        return {"tier": "OVERSIZED", "timeout_s": 1800, "background": True,
                "model_note": "split task first", "split": True}


def calibrate_from_sessions() -> None:
    """Fit weights from session JSONL data (assistant message lengths)."""
    xs, ys = [], []
    for p in sorted(SESSIONS_DIR.glob("*.jsonl"))[-50:]:
        lines = p.read_text().splitlines()
        total_tokens = 0
        task_line = ""
        for line in lines:
            try:
                ev = json.loads(line)
                if ev.get("role") == "user" and not task_line:
                    c = ev.get("content", "")
                    if isinstance(c, str) and len(c) > 10:
                        task_line = c[:500]
                if ev.get("role") == "assistant":
                    c = ev.get("content", ev.get("api_content", ""))
                    if isinstance(c, str):
                        total_tokens += len(c) // 4
                    elif isinstance(c, list):
                        for b in c:
                            if isinstance(b, dict):
                                total_tokens += len(str(b.get("text", ""))) // 4
            except Exception:
                pass
        if task_line and total_tokens > 0:
            feats = _extract_features(task_line)
            xs.append(_feature_vector(feats))
            ys.append(math.log(max(total_tokens, 1)))

    if len(xs) < 5:
        print(f"[output-predictor] Only {len(xs)} sessions — insufficient for calibration (need ≥5)")
        return

    X = np.array(xs)
    y = np.array(ys)
    # OLS: w = (X'X)^-1 X'y
    try:
        w = np.linalg.lstsq(X, y, rcond=None)[0]
        _tmp_olp = CALIB_FILE.with_suffix(".tmp")
        _tmp_olp.write_text(json.dumps({"weights": w.tolist(), "n_sessions": len(xs)}, indent=2))
        _tmp_olp.replace(CALIB_FILE)
        print(f"[output-predictor] Calibrated from {len(xs)} sessions. Weights: {w.round(3).tolist()}")
    except Exception as e:
        print(f"[output-predictor] Calibration failed: {e}")


def run(task: str, calibrate: bool, dry_run: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()

    if calibrate:
        calibrate_from_sessions()
        return

    weights = _load_weights()
    tokens, feats = _predict_tokens(task, weights)
    routing = _routing_recommendation(tokens)

    print(f"\n=== Output Length Predictor — {now[:10]} ===")
    print(f"Task: '{task[:80]}'")
    print(f"\n  Features: clauses={feats['n_clauses']} code={feats['has_code']} "
          f"research={feats['has_research']} impl={feats['has_impl']} "
          f"files={feats['n_files']} tools={feats['n_tools']}")
    print(f"\n  Predicted output: ~{tokens:,} tokens")
    print(f"  Tier: {routing['tier']}")
    print(f"  Recommended: timeout={routing['timeout_s']}s  background={routing['background']}")
    print(f"  Model note: {routing['model_note']}")
    if routing["split"]:
        print(f"  SPLIT RECOMMENDED: task likely exceeds single-turn budget")

    if not dry_run:
        _tmp_out = OUT_FILE.with_suffix(".tmp")
        _tmp_out.write_text(json.dumps({
            "ts": now, "task": task, "predicted_tokens": tokens,
            "routing": routing, "features": feats,
        }, indent=2))
        _tmp_out.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", nargs="?",
                        default="research arxiv papers on LLM agents and implement findings")
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(task=args.task, calibrate=args.calibrate, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
