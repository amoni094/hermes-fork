#!/usr/bin/env python3
"""ESL-4: .632 bootstrap skill test-error estimator (ESL §7.11).

Usage:
  python3 skill-bootstrap.py --skill github-operations --outcomes '[1,1,0,1,1,0,1]' [--B 200]
  python3 skill-bootstrap.py compare --outcomes-a '[1,1,0,1]' --outcomes-b '[1,0,1,1,1]'
"""
from __future__ import annotations

import argparse
import json
import random
import sys


def _arr(s):
    return [float(v) for v in json.loads(s)]


def estimate(y, B=200, rng=None):
    rng = rng or random.Random(632)
    n = len(y)
    if n == 0:
        raise SystemExit("empty outcomes")
    err = 1.0 - sum(y) / n
    oob_losses = []
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        seen = set(idx)
        oob = [i for i in range(n) if i not in seen]
        if not oob:
            continue
        _fit = sum(y[i] for i in idx) / n  # success rate on bootstrap sample
        oob_losses.append(1.0 - sum(y[i] for i in oob) / len(oob))
    Err1 = sum(oob_losses) / len(oob_losses) if oob_losses else err
    if err < 0.05:
        return err, Err1, Err1, "loo-only"
    return err, Err1, 0.368 * err + 0.632 * Err1, "632"


def result(skill, y, B, rng=None):
    err, Err1, hat, method = estimate(y, B, rng)
    return {
        "skill": skill, "n": len(y), "err": err, "Err1": Err1,
        "Err_hat": hat, "method": method, "B": B,
    }


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "compare":
        p = argparse.ArgumentParser(prog="skill-bootstrap.py compare")
        p.add_argument("--outcomes-a", required=True)
        p.add_argument("--outcomes-b", required=True)
        p.add_argument("--B", type=int, default=200)
        a = p.parse_args(argv[1:])
        rng = random.Random(632)
        ra = result("a", _arr(a.outcomes_a), a.B, rng)
        rb = result("b", _arr(a.outcomes_b), a.B, rng)
        winner = "a" if ra["Err_hat"] <= rb["Err_hat"] else "b"
        json.dump({"winner": winner, "a": ra, "b": rb}, sys.stdout)
        print()
        return
    p = argparse.ArgumentParser()
    p.add_argument("--skill", required=True)
    p.add_argument("--outcomes", required=True)
    p.add_argument("--B", type=int, default=200)
    a = p.parse_args(argv)
    json.dump(result(a.skill, _arr(a.outcomes), a.B), sys.stdout)
    print()


if __name__ == "__main__":
    main()
