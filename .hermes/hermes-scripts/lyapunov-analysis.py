#!/usr/bin/env python3
"""
KHALIL-3: Lyapunov stability analysis for Hermes agent loops.
Implements phase portrait, Lyapunov-check, and bifurcation analysis
based on Khalil 'Nonlinear Systems' 3rd ed, Chapter 4.
"""

import argparse
import json
import sys
import numpy as np
from scipy.integrate import odeint


# ---------------------------------------------------------------------------
# ODE System definitions
# ---------------------------------------------------------------------------

def system_pid(state, t, mu=0.5):
    """Damped oscillator: dx/dt = y, dy/dt = -x - mu*y"""
    x, y = state
    return [y, -x - mu * y]


def system_retry(state, t, mu=None):
    """Retry state flow: dx/dt = -x*(x-1)*(x-2), dy/dt = -y"""
    x, y = state
    return [-x * (x - 1) * (x - 2), -y]


def system_memory(state, t, mu=None):
    """Memory attractor: dx/dt = -x + tanh(x+y), dy/dt = -y"""
    x, y = state
    return [-x + np.tanh(x + y), -y]


SYSTEMS = {
    "pid": system_pid,
    "retry": system_retry,
    "memory": system_memory,
}


def get_system(name):
    if name not in SYSTEMS:
        print(json.dumps({"error": f"Unknown system '{name}'. Choose from: {list(SYSTEMS.keys())}"}))
        sys.exit(1)
    return SYSTEMS[name]


# ---------------------------------------------------------------------------
# Subcommand: phase-portrait
# ---------------------------------------------------------------------------

def cmd_phase_portrait(args):
    system = args.system
    fn = get_system(system)

    # 4 initial conditions spread around the state space
    initial_conditions = [
        [1.0, 0.0],
        [-1.0, 0.5],
        [0.5, -1.0],
        [-0.5, -0.5],
    ]

    t = np.linspace(0, 10, 200)
    trajectories = []

    for x0 in initial_conditions:
        sol = odeint(fn, x0, t, args=(), tfirst=False)
        # Downsample to 50 points for compact JSON
        indices = np.linspace(0, len(sol) - 1, 50, dtype=int)
        path = [[float(sol[i, 0]), float(sol[i, 1])] for i in indices]
        trajectories.append({"x0": x0, "path": path})

    result = {"system": system, "trajectories": trajectories}
    print(json.dumps(result))


# ---------------------------------------------------------------------------
# Subcommand: lyapunov-check
# ---------------------------------------------------------------------------

def lyapunov_derivative_quadratic(state, fn):
    """V(x,y) = x^2 + y^2; dV/dt = grad(V) · f = 2x*fx + 2y*fy"""
    x, y = state
    f = fn([x, y], 0)
    fx, fy = f
    return 2 * x * fx + 2 * y * fy


def lyapunov_derivative_norm(state, fn):
    """V(x,y) = ||(x,y)||; dV/dt = (x*fx + y*fy) / ||(x,y)||"""
    x, y = state
    r = np.sqrt(x**2 + y**2)
    if r < 1e-10:
        return 0.0
    f = fn([x, y], 0)
    fx, fy = f
    return (x * fx + y * fy) / r


CANDIDATES = {
    "quadratic": lyapunov_derivative_quadratic,
    "norm": lyapunov_derivative_norm,
}


def cmd_lyapunov_check(args):
    system = args.system
    candidate = args.candidate

    if candidate not in CANDIDATES:
        print(json.dumps({"error": f"Unknown candidate '{candidate}'. Choose from: {list(CANDIDATES.keys())}"}))
        sys.exit(1)

    fn = get_system(system)
    dV_fn = CANDIDATES[candidate]

    np.random.seed(42)
    points = np.random.uniform(-2, 2, size=(50, 2))

    negative_count = 0
    for pt in points:
        # Skip origin to avoid degeneracy in norm candidate
        if np.linalg.norm(pt) < 1e-8:
            negative_count += 1  # dV/dt = 0 at origin, treat as non-positive
            continue
        dv = dV_fn(pt, fn)
        if dv < 0:
            negative_count += 1

    fraction = negative_count / 50.0
    verdict = "stable" if fraction > 0.8 else "inconclusive"

    result = {
        "system": system,
        "candidate": candidate,
        "points_checked": 50,
        "negative_definite_fraction": round(fraction, 4),
        "verdict": verdict,
    }
    print(json.dumps(result))


# ---------------------------------------------------------------------------
# Subcommand: bifurcation
# ---------------------------------------------------------------------------

def parse_param_range(s):
    """Parse 'start:stop:steps' string into a numpy linspace array."""
    parts = s.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid param-range '{s}'. Expected 'start:stop:steps'.")
    start, stop, steps = float(parts[0]), float(parts[1]), int(parts[2])
    return np.linspace(start, stop, steps)


def cmd_bifurcation(args):
    system = args.system

    try:
        mu_values = parse_param_range(args.param_range)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    t = np.linspace(0, 20, 500)
    x0 = [1.0, 0.0]
    bifurcation_points = []

    for mu in mu_values:
        if system == "pid":
            sol = odeint(system_pid, x0, t, args=(mu,))
        else:
            # For retry and memory, mu parameter is not used in their ODEs
            fn = get_system(system)
            sol = odeint(fn, x0, t)

        steady_state = float(sol[-1, 0])
        bifurcation_points.append({"mu": round(float(mu), 6), "steady_state": round(steady_state, 6)})

    result = {"param": "mu", "bifurcation_points": bifurcation_points}
    print(json.dumps(result))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="KHALIL-3: Lyapunov stability analysis for Hermes agent loops."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # phase-portrait
    pp = subparsers.add_parser("phase-portrait", help="Generate phase portrait trajectories.")
    pp.add_argument("--system", required=True, choices=list(SYSTEMS.keys()),
                    help="ODE system to analyse.")
    pp.set_defaults(func=cmd_phase_portrait)

    # lyapunov-check
    lc = subparsers.add_parser("lyapunov-check", help="Check Lyapunov stability candidate.")
    lc.add_argument("--system", required=True, choices=list(SYSTEMS.keys()),
                    help="ODE system to analyse.")
    lc.add_argument("--candidate", required=True, choices=list(CANDIDATES.keys()),
                    help="Lyapunov candidate function.")
    lc.set_defaults(func=cmd_lyapunov_check)

    # bifurcation
    bf = subparsers.add_parser("bifurcation", help="Run bifurcation analysis over parameter range.")
    bf.add_argument("--system", required=True, choices=list(SYSTEMS.keys()),
                    help="ODE system to analyse.")
    bf.add_argument("--param-range", default="0:2:20",
                    help="Parameter range as 'start:stop:steps' (default: '0:2:20').")
    bf.set_defaults(func=cmd_bifurcation)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
