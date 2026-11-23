#!/usr/bin/python3
"""
route-preemption-scheduler.py

Dynamically preempts stale tool/memory queries in favour of fresher,
higher-value routing options when information gain from continuing
the current path drops below a threshold.

Math basis: Preemptive scheduling with information-gain priority
  At each step, compute marginal gain G_t of continuing current route.
  If G_t < PREEMPT_THRESHOLD, switch to the highest-gain available route.

Run on-demand: /usr/bin/python3 route-preemption-scheduler.py
"""
from __future__ import annotations
import math, sys

PREEMPT_THRESHOLD = 0.10  # nats; below = preempt

ROUTES = {
    "web_search":        {"base_gain": 0.8,  "decay": 0.3},
    "skill_view":        {"base_gain": 0.6,  "decay": 0.5},
    "session_search":    {"base_gain": 0.5,  "decay": 0.4},
    "direct_answer":     {"base_gain": 0.3,  "decay": 0.1},
    "delegate_subagent": {"base_gain": 1.0,  "decay": 0.2},
}

def marginal_gain(route: str, call_number: int) -> float:
    r = ROUTES.get(route, {"base_gain": 0.3, "decay": 0.3})
    return r["base_gain"] * math.exp(-r["decay"] * call_number)

def schedule(task: str, call_log: list[str]) -> None:
    print(f"\n=== Route Preemption Scheduler ===")
    print(f"Task: {task[:60]}")
    print(f"Call log: {call_log}\n")

    call_counts = {}
    for route in call_log:
        call_counts[route] = call_counts.get(route, 0) + 1

    print(f"  {'Route':<25} {'Count':>6} {'MargGain':>10}  Action")
    print("  " + "-"*55)
    gains = {}
    for route, cfg in ROUTES.items():
        n = call_counts.get(route, 0)
        g = marginal_gain(route, n)
        gains[route] = g
        current = " <CURRENT" if route == (call_log[-1] if call_log else "") else ""
        preempt = " PREEMPT" if g < PREEMPT_THRESHOLD else ""
        print(f"  {route:<25} {n:>6} {g:>10.4f}{preempt}{current}")

    current_route = call_log[-1] if call_log else list(ROUTES)[0]
    current_gain  = gains.get(current_route, 0)
    best_route    = max(gains.keys(), key=lambda k: gains[k])
    best_gain     = gains[best_route]

    print(f"\nCurrent route:  {current_route}  gain={current_gain:.4f}")
    if current_gain < PREEMPT_THRESHOLD and best_route != current_route:
        print(f"PREEMPT: switch to {best_route}  (gain={best_gain:.4f} >> {current_gain:.4f})")
    else:
        print(f"Continue: {current_route} still above preemption threshold")

if __name__ == "__main__":
    demo_log = ["web_search", "web_search", "web_search", "skill_view"]
    schedule("research and implement findings", demo_log)
