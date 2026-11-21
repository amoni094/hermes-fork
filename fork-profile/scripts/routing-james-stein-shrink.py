#!/usr/bin/env python3
"""routing-james-stein-shrink.py — James-Stein shrinkage of routing weights.

Theory: for p>=3, theta_JS = mu_0 + max(0, 1-(p-2)/S) * (X - mu_0)
where S = sum((X_i - mu_0_i)^2). Dominates coordinatewise MLE in MSE.
mu_0 is the grand mean broadcast. Alarm when top-3 skills reorder.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

home = os.environ.get("HERMES_HOME", "")
home = home.removesuffix("/profiles/fork")
if not home:
    home = os.path.expanduser("~/.hermes")
profile_dir = home + "/profiles/fork"
CACHE = os.path.join(profile_dir, "cache")
WEIGHTS_PATH = os.path.join(CACHE, "routing-exp3-skill-weights.json")
WEIGHTS_FALLBACK = os.path.join(CACHE, "routing-weights.json")
OUT_PATH = os.path.join(CACHE, "routing-js-state.json")


def _atomic_write(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _as_float(v: Any) -> Optional[float]:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            x = float(v)
        except (TypeError, ValueError):
            return None
        if x != x or x in (float("inf"), float("-inf")):
            return None
        return x
    return None


def extract_weights(raw: Any) -> dict[str, float]:
    """Accept skill->float or skill->{weight: float} (and similar wrappers)."""
    out: dict[str, float] = {}
    if not isinstance(raw, dict):
        return out
    # unwrap common envelope
    if "weights" in raw and isinstance(raw["weights"], dict):
        raw = raw["weights"]
    for k, v in raw.items():
        if k in ("generated_at", "ts", "updated_at", "meta"):
            continue
        fv = _as_float(v)
        if fv is None and isinstance(v, dict):
            fv = _as_float(v.get("weight", v.get("w", v.get("score"))))
        if fv is None:
            continue
        out[str(k)] = fv
    return out


def james_stein(xs: Sequence[float]) -> tuple[list[float], float, bool]:
    """Return (js_weights, shrinkage_factor, skipped).

    skipped=True when p<3 (JS undefined) or S==0 (no variation).
    """
    p = len(xs)
    if p < 3:
        return list(xs), 1.0, True
    mu = sum(xs) / p
    s = sum((x - mu) ** 2 for x in xs)
    if s <= 0.0:
        return list(xs), 1.0, True
    factor = max(0.0, 1.0 - (p - 2) / s)
    js = [max(0.0, mu + factor * (x - mu)) for x in xs]
    return js, factor, False


def top_k_names(pairs: Sequence[tuple[str, float]], k: int = 3) -> list[str]:
    ranked = sorted(pairs, key=lambda t: (-t[1], t[0]))
    return [n for n, _ in ranked[:k]]


def run(weights: Optional[dict[str, float]] = None) -> dict[str, Any]:
    if weights is None:
        weights = {}
        for _wpath in (WEIGHTS_PATH, WEIGHTS_FALLBACK):
            try:
                with open(_wpath, encoding="utf-8") as f:
                    raw = json.loads(f.read())
                weights = extract_weights(raw)
                if len(weights) >= 3:
                    break
            except FileNotFoundError:
                continue
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue

    names = list(weights.keys())
    xs = [weights[n] for n in names]
    p = len(xs)
    if p == 0:
        result = {
            "shrinkage_factor": 1.0,
            "top3_raw": [],
            "top3_js": [],
            "alarm": False,
            "switched_skills": [],
            "skipped": True,
            "reason": "no_data",
            "p": 0,
        }
        return result

    js, factor, skipped = james_stein(xs)
    raw_pairs = list(zip(names, xs))
    js_pairs = list(zip(names, js))
    k = min(3, p)
    top3_raw = top_k_names(raw_pairs, k)
    top3_js = top_k_names(js_pairs, k)
    switched = sorted(set(top3_raw) ^ set(top3_js))
    alarm = (not skipped) and top3_raw != top3_js
    result = {
        "shrinkage_factor": factor,
        "top3_raw": top3_raw,
        "top3_js": top3_js,
        "alarm": alarm,
        "switched_skills": switched,
        "skipped": skipped,
        "p": p,
        "js_weights": {n: w for n, w in js_pairs},
    }
    return result


def self_test() -> None:
    # p=5, one dominant outlier
    names = ["a", "b", "c", "d", "e"]
    X = [10.0, 1.0, 1.0, 1.0, 1.0]
    js, factor, skipped = james_stein(X)
    assert not skipped, "p=5 must apply JS"
    assert 0.0 < factor < 1.0, f"shrinkage_factor not in (0,1): {factor}"
    assert js[0] < X[0], f"JS outlier {js[0]} not < raw {X[0]}"
    assert all(w >= 0.0 for w in js), f"negative JS weights: {js}"

    # p=2 must skip, no crash
    js2, factor2, skipped2 = james_stein([10.0, 1.0])
    assert skipped2, "p=2 must skip shrinkage"
    assert js2 == [10.0, 1.0]
    assert factor2 == 1.0

    # p=1 skip
    james_stein([4.0])

    # S=0 skip
    js0, _, skipped0 = james_stein([2.0, 2.0, 2.0])
    assert skipped0
    assert js0 == [2.0, 2.0, 2.0]

    # clipping keeps non-negative
    js_neg, _, _ = james_stein([-10.0, 0.0, 0.0, 0.0, 0.0])
    assert all(w >= 0.0 for w in js_neg)

    # end-to-end run() with in-memory weights
    w = {n: x for n, x in zip(names, X)}
    r = run(w)
    assert 0.0 < r["shrinkage_factor"] < 1.0
    assert r["top3_raw"][0] == "a"
    assert all(v >= 0.0 for v in r["js_weights"].values())

    # missing file path: extract_weights on empty
    assert extract_weights(None) == {}
    assert extract_weights({"skill": {"weight": 3.5}}) == {"skill": 3.5}

    print("self-test: PASS")


def main() -> int:
    if "--self-test" in sys.argv:
        self_test()
        return 0
    result = run()
    try:
        _atomic_write(OUT_PATH, result)
    except OSError:
        pass
    print(json.dumps({k: result[k] for k in (
        "shrinkage_factor", "top3_raw", "top3_js", "alarm", "switched_skills"
    ) if k in result}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # H-I7: shadow path never raises
        sys.exit(0)
