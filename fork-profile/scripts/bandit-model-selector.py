#!/usr/bin/python3
"""Thompson Sampling model selector from routing-quality.jsonl.

For each (task_type, model) pair maintain Beta(alpha, beta) with
alpha = successes + 1, beta = failures + 1 (uniform Beta(1, 1) prior).
Success: outcome in {'completed', 'ok', 'pass'}; otherwise failure.
Each round samples theta ~ Beta(alpha, beta) per arm and picks argmax.

Reads ~/.hermes/logs/routing-quality.jsonl (missing file is empty).
Arm id is actual_route (schema), falling back to model.

Monitor-suite contract: emit exactly one ALARM line.
  ALARM: no -- insufficient data   (< 5 parsed entries; exit 0)
  ALARM: no                        (recommendation produced)

Requires chmod 755 to be executable:
    chmod 755 bandit-model-selector.py

Usage:
    /usr/bin/python3 bandit-model-selector.py
    /usr/bin/python3 bandit-model-selector.py --dry-run
    /usr/bin/python3 bandit-model-selector.py --query code_edit

Only stdlib + numpy. Shebang is /usr/bin/python3 (not the hermes-fork venv).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

LOG_PATH = Path.home() / ".hermes" / "logs" / "routing-quality.jsonl"
MIN_ENTRIES = 5
SUCCESS_OUTCOMES = frozenset({"completed", "ok", "pass"})
ALARM_INSUFFICIENT = "ALARM: no -- insufficient data"
ALARM_OK = "ALARM: no"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Thompson Sampling model selector per task_type"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output without writing cache files",
    )
    parser.add_argument(
        "--query",
        metavar="TASK_TYPE",
        default=None,
        help="Recommend for a single task_type",
    )
    parser.add_argument(
        "--log",
        default=str(LOG_PATH),
        help="Path to routing-quality.jsonl",
    )
    return parser.parse_args(argv)


def _is_success(record: dict) -> bool:
    """Bernoulli success from outcome (schema) with completed fallback."""
    outcome = record.get("outcome")
    if outcome is not None:
        return str(outcome).strip().lower() in SUCCESS_OUTCOMES
    completed = record.get("completed")
    if isinstance(completed, bool):
        return completed
    if isinstance(completed, str):
        return completed.strip().lower() in SUCCESS_OUTCOMES | {"true", "yes", "1"}
    return False


def _arm_id(record: dict) -> str | None:
    for key in ("actual_route", "model", "route"):
        val = record.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def load_entries(path: Path) -> list[dict]:
    """Load JSONL records. Missing file or bad lines are skipped."""
    if not path.exists():
        return []
    entries: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        task_type = rec.get("task_type")
        arm = _arm_id(rec)
        if not task_type or not arm:
            continue
        rec["_task_type"] = str(task_type).strip()
        rec["_arm"] = arm
        rec["_success"] = _is_success(rec)
        entries.append(rec)
    return entries


def posterior_counts(
    entries: list[dict],
) -> dict[str, dict[str, dict[str, int]]]:
    """Return {task_type: {model: {successes, failures, alpha, beta}}}."""
    stats: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"successes": 0, "failures": 0})
    )
    for rec in entries:
        cell = stats[rec["_task_type"]][rec["_arm"]]
        if rec["_success"]:
            cell["successes"] += 1
        else:
            cell["failures"] += 1
    out: dict[str, dict[str, dict[str, int]]] = {}
    for task_type, arms in stats.items():
        out[task_type] = {}
        for model, cell in arms.items():
            successes = cell["successes"]
            failures = cell["failures"]
            out[task_type][model] = {
                "successes": successes,
                "failures": failures,
                "alpha": successes + 1,
                "beta": failures + 1,
            }
    return out


def thompson_select(
    arms: dict[str, dict[str, int]],
    rng: np.random.Generator,
) -> tuple[str | None, dict[str, float]]:
    """Sample Beta(alpha, beta) per arm; return (argmax model, samples)."""
    if not arms:
        return None, {}
    samples: dict[str, float] = {}
    best_model: str | None = None
    best_theta = -1.0
    # Sorted keys: ties break lexicographically (stable, not insertion order).
    for model in sorted(arms):
        alpha = float(arms[model]["alpha"])
        beta = float(arms[model]["beta"])
        theta = float(rng.beta(alpha, beta))
        samples[model] = theta
        if theta > best_theta:
            best_theta = theta
            best_model = model
    return best_model, samples


def build_recommendations(
    counts: dict[str, dict[str, dict[str, int]]],
    query: str | None,
    rng: np.random.Generator,
) -> dict:
    task_types = sorted(counts)
    if query is not None:
        task_types = [query]

    recommendations: dict = {}
    for task_type in task_types:
        arms = counts.get(task_type, {})
        recommended, samples = thompson_select(arms, rng)
        arm_payload = {}
        for model in sorted(arms):
            cell = arms[model]
            arm_payload[model] = {
                "alpha": cell["alpha"],
                "beta": cell["beta"],
                "successes": cell["successes"],
                "failures": cell["failures"],
                "theta": samples.get(model),
            }
        rec_alpha = None
        rec_beta = None
        if recommended is not None and recommended in arms:
            rec_alpha = arms[recommended]["alpha"]
            rec_beta = arms[recommended]["beta"]
        recommendations[task_type] = {
            "recommended_model": recommended,
            "alpha": rec_alpha,
            "beta": rec_beta,
            "arms": arm_payload,
        }
    return recommendations


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # --dry-run accepted for suite compatibility; this script has no writes.
    _ = args.dry_run

    entries = load_entries(Path(args.log).expanduser())
    if len(entries) < MIN_ENTRIES:
        print(ALARM_INSUFFICIENT)
        return 0

    counts = posterior_counts(entries)
    rng = np.random.default_rng()
    recommendations = build_recommendations(counts, args.query, rng)

    payload = {
        "n_entries": len(entries),
        "log": str(Path(args.log).expanduser()),
        "recommendations": recommendations,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(ALARM_OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
