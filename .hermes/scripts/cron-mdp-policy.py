#!/usr/bin/env python3
"""cron-mdp-policy.py — tabular discounted MDP for cron dispatch (Puterman).

States s = (backlog_bin, hour, last_error)
  backlog_bin in {0,1,2,3,4}
  hour in {0..23}
  last_error in {0=ok, 1=transient, 2=hard}
  nS = 5 * 24 * 3 = 360
Actions a in {run_now, delay_1m, delay_5m, delay_30m}

Bellman optimality operator (gamma-discounted):
  (T V)(s) = max_a [ R(s,a) + gamma * sum_{s'} P(s'|s,a) V(s') ]

Hard core: T is a contraction on (R^{nS}, ||.||_inf) with modulus gamma < 1:
  ||T V - T W||_inf <= gamma ||V - W||_inf
This FAILS if gamma >= 1 (no Banach fixed-point guarantee).

Requires /usr/bin/python3 (numpy). Stdlib+numpy only.

Usage:
  /usr/bin/python3 cron-mdp-policy.py --self-test
  /usr/bin/python3 cron-mdp-policy.py --plan
  /usr/bin/python3 cron-mdp-policy.py --recommend --backlog 2 --hour 14 --last-error 0
"""
from __future__ import annotations

# numpy-reexec-guard: re-exec under /usr/bin/python3 if numpy unavailable (ADV-006 fix)
import sys as _sys
try:
    import numpy as _np_test  # noqa: F401
    del _np_test
except ImportError:
    import os as _os
    _os.execv('/usr/bin/python3', ['/usr/bin/python3'] + _sys.argv)







import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

N_BACKLOG = 5
N_HOUR = 24
N_ERR = 3
N_S = N_BACKLOG * N_HOUR * N_ERR  # 360
ACTIONS = ("run_now", "delay_1m", "delay_5m", "delay_30m")
N_A = len(ACTIONS)
GAMMA_DEFAULT = 0.95

_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_profile = os.environ.get("HERMES_PROFILE", "")
_root = (_base / "profiles" / _profile) if _profile and "profiles" not in str(_base) else _base
OUT_PATH = _root / "cache" / "cron-mdp-policy.json"


def _sid(b: int, h: int, e: int) -> int:
    return int(b) * (N_HOUR * N_ERR) + int(h) * N_ERR + int(e)


def _decode(s: int) -> tuple[int, int, int]:
    e = s % N_ERR
    h = (s // N_ERR) % N_HOUR
    b = s // (N_HOUR * N_ERR)
    return b, h, e


def build_model(arrival_p: float = 0.25, fail_p: float = 0.08) -> tuple[np.ndarray, np.ndarray]:
    """Construct P[s,a,s'] and R[s,a]. Stochastic, row-stochastic P."""
    P = np.zeros((N_S, N_A, N_S), dtype=np.float64)
    R = np.zeros((N_S, N_A), dtype=np.float64)
    delay_hours = (0, 0, 0, 1)  # run_now/1m/5m stay in hour; 30m may tick hour
    for s in range(N_S):
        b, h, e = _decode(s)
        for a, name in enumerate(ACTIONS):
            # Reward: clear backlog, penalize delay and last_error, extra penalty if idle with work.
            delay_cost = (0.0, 0.02, 0.08, 0.25)[a]
            R[s, a] = -0.4 * b - 0.3 * e - delay_cost
            if name == "run_now" and b > 0:
                R[s, a] += 1.0  # service reward
            if name != "run_now" and b >= 4:
                R[s, a] -= 0.5  # saturated backlog + delay

            # Transitions (sparse, two-point).
            if name == "run_now":
                b_ok = max(0, b - 1)
                b_fail = min(N_BACKLOG - 1, b)  # failed run does not clear
                h2 = (h + delay_hours[a]) % N_HOUR
                # success: error -> 0; fail: error -> min(2, e+1)
                s_ok = _sid(b_ok, h2, 0)
                s_fail = _sid(b_fail, h2, min(2, e + 1))
                p_fail = fail_p if e < 2 else min(0.4, fail_p * 2)
                P[s, a, s_ok] += 1.0 - p_fail
                P[s, a, s_fail] += p_fail
            else:
                # Delay: arrival may increase backlog; hour may advance for 30m.
                h2 = (h + (1 if name == "delay_30m" else 0)) % N_HOUR
                b_up = min(N_BACKLOG - 1, b + 1)
                s_arr = _sid(b_up, h2, e)
                s_stay = _sid(b, h2, e)
                P[s, a, s_arr] += arrival_p
                P[s, a, s_stay] += 1.0 - arrival_p
    # Numerical row-stochastic repair.
    row = P.sum(axis=2, keepdims=True)
    row[row == 0] = 1.0
    P /= row
    return P, R


def bellman_operator(V: np.ndarray, P: np.ndarray, R: np.ndarray, gamma: float) -> np.ndarray:
    """T V = max_a [ R + gamma P V ]. Vectorized."""
    if not (0.0 <= float(gamma) < 1.0):
        raise ValueError(f"gamma must satisfy 0 <= gamma < 1 (got {gamma}); otherwise T is not a contraction")
    q = R + gamma * (P @ V)
    return q.max(axis=1)


def greedy_policy(V: np.ndarray, P: np.ndarray, R: np.ndarray, gamma: float) -> np.ndarray:
    q = R + gamma * (P @ V)
    return q.argmax(axis=1)


def value_iteration(P: np.ndarray, R: np.ndarray, gamma: float = GAMMA_DEFAULT,
                    eps: float = 1e-6, max_iter: int = 500) -> tuple[np.ndarray, np.ndarray, int]:
    V = np.zeros(N_S, dtype=np.float64)
    for i in range(max_iter):
        Vn = bellman_operator(V, P, R, gamma)
        if float(np.max(np.abs(Vn - V))) < eps:
            V = Vn
            return V, greedy_policy(V, P, R, gamma), i + 1
        V = Vn
    return V, greedy_policy(V, P, R, gamma), max_iter


def contraction_gap(V: np.ndarray, W: np.ndarray, P: np.ndarray, R: np.ndarray, gamma: float) -> dict:
    tv = bellman_operator(V, P, R, gamma)
    tw = bellman_operator(W, P, R, gamma)
    lhs = float(np.max(np.abs(tv - tw)))
    rhs = float(gamma) * float(np.max(np.abs(V - W)))
    return {"lhs": lhs, "rhs": rhs, "holds": lhs <= rhs + 1e-9}


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def self_test() -> int:
    P, R = build_model()
    assert P.shape == (N_S, N_A, N_S)
    assert abs(P.sum(axis=2) - 1.0).max() < 1e-9
    rng = np.random.default_rng(0)
    gamma = GAMMA_DEFAULT
    holds = 0
    for _ in range(8):
        V = rng.normal(size=N_S)
        W = rng.normal(size=N_S)
        g = contraction_gap(V, W, P, R, gamma)
        if not g["holds"]:
            print(json.dumps({"property": "Bellman contraction", "passed": False, **g}))
            return 1
        holds += 1
    # gamma >= 1 must be rejected (no contraction certificate)
    threw = False
    try:
        bellman_operator(np.zeros(N_S), P, R, 1.0)
    except ValueError:
        threw = True
    if not threw:
        print(json.dumps({"property": "gamma<1 gate", "passed": False}))
        return 1
    V, pi, n_iter = value_iteration(P, R, gamma)
    print(json.dumps({
        "property": "Bellman contraction ||TV-TW||_inf <= gamma ||V-W||_inf",
        "passed": True,
        "gamma": gamma,
        "nS": N_S,
        "nA": N_A,
        "random_pairs_ok": holds,
        "gamma_ge_1_rejected": True,
        "vi_iters": n_iter,
        "V_min": float(V.min()),
        "V_max": float(V.max()),
        "policy_hist": {ACTIONS[i]: int((pi == i).sum()) for i in range(N_A)},
    }))
    return 0


def cmd_plan() -> int:
    P, R = build_model()
    V, pi, n_iter = value_iteration(P, R, GAMMA_DEFAULT)
    recs = []
    for hour in range(N_HOUR):
        recs.append({
            "hour": hour,
            "backlog2_ok": ACTIONS[int(pi[_sid(2, hour, 0)])],
            "backlog4_hard": ACTIONS[int(pi[_sid(4, hour, 2)])],
        })
    out = {
        "theorem": "Puterman discounted MDP / Bellman optimality",
        "gamma": GAMMA_DEFAULT,
        "nS": N_S,
        "nA": N_A,
        "vi_iters": n_iter,
        "policy_hist": {ACTIONS[i]: int((pi == i).sum()) for i in range(N_A)},
        "hourly_slice": recs,
        "note": "Policy is computed; it is NOT claimed optimal for the live arrival process.",
    }
    _atomic_write(OUT_PATH, out)
    print(json.dumps({"written": str(OUT_PATH), "vi_iters": n_iter, "policy_hist": out["policy_hist"]}))
    return 0


def cmd_recommend(backlog: int, hour: int, last_error: int) -> int:
    path = OUT_PATH
    if path.exists():
        data = json.loads(path.read_text())
    else:
        cmd_plan()
        data = json.loads(path.read_text())
    P, R = build_model()
    V, pi, _ = value_iteration(P, R, GAMMA_DEFAULT)
    s = _sid(max(0, min(4, backlog)), hour % 24, max(0, min(2, last_error)))
    a = int(pi[s])
    print(json.dumps({
        "state": {"backlog": backlog, "hour": hour, "last_error": last_error, "sid": s},
        "action": ACTIONS[a],
        "V": float(V[s]),
        "note": "Do not cite as live OPT; model is a bounded tabular approximation.",
    }))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--plan", action="store_true")
    p.add_argument("--recommend", action="store_true")
    p.add_argument("--backlog", type=int, default=1)
    p.add_argument("--hour", type=int, default=0)
    p.add_argument("--last-error", type=int, default=0, dest="last_error")
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.recommend:
        return cmd_recommend(args.backlog, args.hour, args.last_error)
    return cmd_plan()


if __name__ == "__main__":
    sys.exit(main())
