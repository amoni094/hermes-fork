#!/usr/bin/env python3
"""Inter-rater reliability audit for Hermes swarm consensus.

Shapley + RRF merge can look unanimous when subagents are model-correlated.
This script scores whether rater (subagent) labels are genuinely reliable.

Citations:
  - Krippendorff, K. (2004). Content Analysis: An Introduction to Its
    Methodology, ch. 11 (reliability, coincidence matrices, alpha).
  - Gwet, K. L. (2008). Computing inter-rater reliability and its variance
    in the presence of high agreement. Journal of the Royal Statistical
    Society (AC2 statistic).
  - Barber, D. Bayesian Reasoning and Machine Learning, section 28.4.

Usage:
  python3 inter-rater-swarm-audit.py --json-file PATH
  python3 inter-rater-swarm-audit.py --self-test
  python3 inter-rater-swarm-audit.py --demo
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)


def _delta_nominal(a, b):
    return 0.0 if a == b else 1.0


def _item_columns(ratings_matrix):
    """Transpose raters x items into per-item non-missing values."""
    if not ratings_matrix:
        return []
    n_items = max((len(row) for row in ratings_matrix), default=0)
    columns = []
    for j in range(n_items):
        vals = []
        for row in ratings_matrix:
            if j < len(row) and row[j] is not None:
                vals.append(row[j])
        columns.append(vals)
    return columns


def krippendorff_alpha(ratings_matrix, metric="nominal"):
    """Nominal Krippendorff alpha (2004, ch. 11).

    ratings_matrix: list of lists, raters x items (None = missing).
    delta(a, b) = 0 if a == b else 1 (nominal).
    alpha = 1 - D_o / D_e.

    Coincidence-weighted D_o / D_e so missing values and unequal m_i are
    handled as in Krippendorff. When every unit has the same m, this is
    pairwise disagreement averaged over pairable values.

    D_e uses n_u = total pairable values and n_c = coincidence count of
    category c: expected *disagreement* = 1 - sum_c n_c(n_c-1) / (n_u(n_u-1)).

    No-variation (D_e == 0): returns 0.0 (chance / undefined), not 1.0.
    """
    if metric != "nominal":
        raise ValueError("only metric='nominal' is implemented")
    coincidences = {}
    n_u = 0.0
    for unit in _item_columns(ratings_matrix):
        m = len(unit)
        if m < 2:
            continue
        n_u += m
        weight = 1.0 / (m - 1)
        for i, left in enumerate(unit):
            for k, right in enumerate(unit):
                if i == k:
                    continue
                key = (left, right)
                coincidences[key] = coincidences.get(key, 0.0) + weight
    if n_u < 2:
        return 0.0
    categories = sorted({cat for pair in coincidences for cat in pair}, key=lambda x: (str(type(x)), str(x)))
    n_c = {
        cat: sum(coincidences.get((cat, other), 0.0) for other in categories)
        for cat in categories
    }
    d_o_num = 0.0
    for (a, b), mass in coincidences.items():
        d_o_num += mass * _delta_nominal(a, b)
    d_o = d_o_num / n_u
    agree_e = sum(n_c[c] * (n_c[c] - 1.0) for c in categories) / (n_u * (n_u - 1.0))
    d_e = 1.0 - agree_e
    if d_e == 0.0:
        # Perfect agreement (D_o=0) or no category variation: both indicate alpha=1.0
        return 1.0 if d_o == 0.0 else 0.0
    return 1.0 - (d_o / d_e)


def gwet_ac2(ratings_matrix):
    """Gwet AC2 for (typically binary 0/1) ratings.

    p_a = (1/(n*q)) * sum_i sum_{k<l} I(r_ik == r_il)
    p_e = sum_c pi_c^2
    AC2 = (p_a - p_e) / (1 - p_e)

    n = items with at least two non-missing ratings; q varies per item
    when some ratings are missing (use total valid pairs).
    Degenerate p_e == 1 (no category variation): returns 0.0.
    """
    columns = _item_columns(ratings_matrix)
    agree = 0
    pairs = 0
    cat_counts = Counter()
    n_rated = 0
    for unit in columns:
        m = len(unit)
        if m < 2:
            continue
        for i in range(m):
            cat_counts[unit[i]] += 1
            n_rated += 1
            for k in range(i + 1, m):
                pairs += 1
                if unit[i] == unit[k]:
                    agree += 1
    if pairs == 0 or n_rated == 0:
        return 0.0
    p_a = agree / float(pairs)
    # Gwet AC1/AC2 chance agreement: p_e = (1/(K-1)) * sum_c pi_c*(1-pi_c)
    # This is robust to prevalence imbalance (Scott/Fleiss p_e = sum pi_c^2 is biased).
    k = len(cat_counts)
    if k <= 1:
        return 1.0 if p_a == 1.0 else 0.0
    p_e = sum((cnt / float(n_rated)) * (1.0 - cnt / float(n_rated))
              for cnt in cat_counts.values()) / (k - 1)
    denom = 1.0 - p_e
    if denom == 0.0:
        return 1.0 if p_a == 1.0 else 0.0
    return (p_a - p_e) / denom


def cohen_kappa(r1, r2):
    """Cohen (1960) kappa for two raters (equal-length sequences).

    kappa = (p_o - p_e) / (1 - p_e)
    p_e uses each rater's own marginals. Pairs with None are skipped.
    Degenerate p_e == 1: returns 0.0.
    """
    if r1 is None or r2 is None:
        return 0.0
    pairs = [(a, b) for a, b in zip(r1, r2) if a is not None and b is not None]
    n = len(pairs)
    if n == 0:
        return 0.0
    p_o = sum(1 for a, b in pairs if a == b) / float(n)
    counts_a = Counter(a for a, _ in pairs)
    counts_b = Counter(b for _, b in pairs)
    cats = set(counts_a) | set(counts_b)
    p_e = sum((counts_a[c] / float(n)) * (counts_b[c] / float(n)) for c in cats)
    denom = 1.0 - p_e
    if denom == 0.0:
        return 0.0
    return (p_o - p_e) / denom


def interpret_alpha(alpha):
    """Landis-style bins on Krippendorff alpha."""
    if alpha is None or (isinstance(alpha, float) and math.isnan(alpha)):
        return "poor"
    if alpha < 0.2:
        return "poor"
    if alpha < 0.4:
        return "fair"
    if alpha < 0.6:
        return "moderate"
    if alpha <= 0.8:
        return "substantial"
    return "excellent"


def audit(ratings_matrix):
    alpha = krippendorff_alpha(ratings_matrix, metric="nominal")
    ac2 = gwet_ac2(ratings_matrix)
    return {
        "krippendorff_alpha": float(alpha),
        "gwet_ac2": float(ac2),
        "interpretation": interpret_alpha(alpha),
    }


def load_ratings_json(path):
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict) or "ratings" not in data:
        raise ValueError('JSON must be {"ratings": [[...], ...]}')
    ratings = data["ratings"]
    if not isinstance(ratings, list) or not all(isinstance(r, list) for r in ratings):
        raise ValueError("ratings must be a list of lists (raters x items)")
    return ratings


def _approx(got, expected, tol=1e-9):
    return abs(float(got) - float(expected)) <= tol


def run_self_test():
    failures = []

    def check(name, cond, detail=""):
        if cond:
            print("PASS " + name)
        else:
            failures.append(name)
            print("FAIL " + name + ((": " + detail) if detail else ""))

    perfect = [[1, 0, 1, 0, 1], [1, 0, 1, 0, 1], [1, 0, 1, 0, 1]]
    a_alpha = krippendorff_alpha(perfect)
    a_ac2 = gwet_ac2(perfect)
    check(
        "a: perfect agreement",
        _approx(a_alpha, 1.0) and _approx(a_ac2, 1.0),
        "alpha=%s ac2=%s" % (a_alpha, a_ac2),
    )

    no_var = [[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]]
    b_alpha = krippendorff_alpha(no_var)
    b_ac2 = gwet_ac2(no_var)
    check(
        "b: chance agreement (no variation)",
        abs(b_alpha) < 1e-9 and (b_ac2 == 0.0 or b_ac2 is None),
        "alpha=%s ac2=%s" % (b_alpha, b_ac2),
    )

    mixed = [[1, 0, 1, 0], [1, 1, 1, 0], [0, 0, 1, 0]]
    c_alpha = krippendorff_alpha(mixed)
    check(
        "c: 3 raters x 4 items alpha > 0",
        c_alpha > 0.0,
        "alpha=%s" % c_alpha,
    )

    r1 = [1, 0, 1, 1]
    r2 = [1, 0, 0, 1]
    kappa = cohen_kappa(r1, r2)
    check(
        "d: cohen kappa = 0.5",
        _approx(kappa, 0.5),
        "kappa=%s" % kappa,
    )

    if failures:
        print("self-test: %d failed" % len(failures))
        return 1
    print("self-test: 4 passed")
    return 0


def run_demo():
    ratings = [
        [1, 0, 1, 1, 0],
        [1, 0, 1, 0, 0],
        [1, 1, 1, 1, 0],
    ]
    result = audit(ratings)
    result["demo_ratings"] = ratings
    result["n_raters"] = 3
    result["n_items"] = 5
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Krippendorff alpha / Gwet AC2 audit for swarm rater agreement"
    )
    parser.add_argument("--json-file", dest="json_file", help="JSON file of ratings")
    parser.add_argument("--self-test", action="store_true", help="run unit tests")
    parser.add_argument("--demo", action="store_true", help="print 3-rater 5-item demo")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()
    if args.demo:
        return run_demo()
    if args.json_file:
        try:
            ratings = load_ratings_json(args.json_file)
        except FileNotFoundError:
            print(json.dumps({"error": "file not found", "path": args.json_file}))
            return 1
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            print(json.dumps({"error": str(exc)}))
            return 1
        print(json.dumps(audit(ratings), indent=2, sort_keys=True))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
