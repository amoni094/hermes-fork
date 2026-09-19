"""
MDP-based retention policy for Hermes jev-compaction.

Grounded in Puterman (1994) 'Markov Decision Processes':
- 2-state, 2-action finite MDP
- Value iteration to compute V*(s) and optimal policy pi*(s)

States:
    LOW_PRESSURE  – context_tokens well within budget
    HIGH_PRESSURE – context_tokens near/over budget

Actions:
    RETAIN – keep message in context
    DEMOTE – move message to compressed store

Rewards:
    r(s=HIGH, a=RETAIN) = -1          (fills context, costly)
    r(s=LOW,  a=RETAIN) = 0.1         (small positive: preserves quality)
    r(s=*,    a=DEMOTE) = 0 - quality_penalty
        quality_penalty = rr_score * 0.5  (risk of losing useful content)

Transitions (abbreviated – complement fills remaining probability):
    T(HIGH→HIGH | RETAIN) = 0.7   T(HIGH→LOW  | RETAIN) = 0.3
    T(HIGH→HIGH | DEMOTE) = 0.2   T(HIGH→LOW  | DEMOTE) = 0.8
    T(LOW→LOW   | RETAIN) = 0.9   T(LOW→HIGH  | RETAIN) = 0.1
    T(LOW→LOW   | DEMOTE) = 0.6   T(LOW→HIGH  | DEMOTE) = 0.4

Discount: gamma = 0.9
"""

from __future__ import annotations

import math
import sys

# ---------------------------------------------------------------------------
# State / action constants
# ---------------------------------------------------------------------------
LOW_PRESSURE = "LOW_PRESSURE"
HIGH_PRESSURE = "HIGH_PRESSURE"
RETAIN = "RETAIN"
DEMOTE = "DEMOTE"

STATES = [LOW_PRESSURE, HIGH_PRESSURE]
ACTIONS = [RETAIN, DEMOTE]

# ---------------------------------------------------------------------------
# MDP parameters
# ---------------------------------------------------------------------------
GAMMA = 0.9

# Transition matrix T[s][a][s'] = P(s' | s, a)
TRANSITIONS: dict[str, dict[str, dict[str, float]]] = {
    HIGH_PRESSURE: {
        RETAIN: {HIGH_PRESSURE: 0.7, LOW_PRESSURE: 0.3},
        DEMOTE: {HIGH_PRESSURE: 0.2, LOW_PRESSURE: 0.8},
    },
    LOW_PRESSURE: {
        RETAIN: {LOW_PRESSURE: 0.9, HIGH_PRESSURE: 0.1},
        DEMOTE: {LOW_PRESSURE: 0.6, HIGH_PRESSURE: 0.4},
    },
}


def _base_reward(state: str, action: str) -> float:
    """Deterministic part of the reward (without rr_score quality penalty)."""
    if action == RETAIN:
        return -1.0 if state == HIGH_PRESSURE else 0.1
    else:  # DEMOTE: base reward 0; caller subtracts quality penalty
        return 0.0


def _reward(state: str, action: str, rr_score: float = 0.5) -> float:
    """Full reward including rr_score-based quality penalty for DEMOTE."""
    base = _base_reward(state, action)
    quality_penalty = rr_score * 0.5 if action == DEMOTE else 0.0
    return base - quality_penalty


# ---------------------------------------------------------------------------
# Value iteration
# ---------------------------------------------------------------------------

def value_iteration(
    rr_score: float = 0.5,
    gamma: float = GAMMA,
    n_iter: int = 20,
    tol: float = 1e-8,
) -> tuple[dict[str, float], dict[str, str]]:
    """
    Run value iteration and return (V*, pi*).

    Parameters
    ----------
    rr_score : float
        The quality score of the message being evaluated (0–1).
        Used to compute the DEMOTE quality penalty.
    gamma    : float  Discount factor.
    n_iter   : int    Max iterations (converges well before 20 steps).
    tol      : float  Convergence threshold for max |V_{k+1} - V_k|.

    Returns
    -------
    V  : dict[state -> value]
    pi : dict[state -> action]
    """
    V: dict[str, float] = {s: 0.0 for s in STATES}
    # P5B-10 fix: n_iter=0 silently returns a myopic policy with no Bellman backups.
    n_iter = max(n_iter, 1)

    for _ in range(n_iter):
        V_new: dict[str, float] = {}
        for s in STATES:
            q_values: dict[str, float] = {}
            for a in ACTIONS:
                r = _reward(s, a, rr_score)
                future = sum(
                    TRANSITIONS[s][a][s_prime] * V[s_prime]
                    for s_prime in STATES
                )
                q_values[a] = r + gamma * future
            V_new[s] = max(q_values.values())

        delta = max(abs(V_new[s] - V[s]) for s in STATES)
        V = V_new
        if delta < tol:
            break

    # Extract greedy policy
    pi: dict[str, str] = {}
    for s in STATES:
        best_a = max(
            ACTIONS,
            key=lambda a: _reward(s, a, rr_score)
            + gamma * sum(TRANSITIONS[s][a][sp] * V[sp] for sp in STATES),
        )
        pi[s] = best_a

    return V, pi


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def optimal_action(state: str, rr_score: float) -> str:
    """
    Return the MDP-optimal action for a given pressure state and rr_score.

    Parameters
    ----------
    state    : str    'LOW_PRESSURE' or 'HIGH_PRESSURE'
    rr_score : float  Relevance/retention score for the message (0–1).

    Returns
    -------
    'RETAIN' or 'DEMOTE'

    P4B-04 fix: memoize by (state, round(rr_score, 2)) — value_iteration is
    deterministic for a given rr_score (TRANSITIONS is static at module level),
    so re-running 20 Bellman passes on every call for repeated scores is pure waste.
    """
    if state not in STATES:
        raise ValueError(f"Unknown state: {state!r}. Must be one of {STATES}")
    _, pi = _cached_value_iteration(round(rr_score, 2))
    return pi[state]


import functools as _functools  # noqa: E402 — placed here to keep module-level imports minimal
import types as _types

@_functools.lru_cache(maxsize=128)
def _cached_value_iteration(rr_score_rounded: float) -> tuple:
    """Cached wrapper: key on rr_score rounded to 2dp (100 distinct values max).

    P5B-03 fix: return MappingProxyType views of v and pi so that any external
    caller cannot mutate the cached dicts (lru_cache stores by reference; a mutation
    would corrupt every subsequent call at this rr_score bucket).
    """
    v, pi = value_iteration(rr_score=rr_score_rounded)
    return _types.MappingProxyType(v), _types.MappingProxyType(pi)


def pressure_from_tokens(context_tokens: int, budget: int) -> str:
    """
    Helper: derive the MDP state from token counts.

    HIGH_PRESSURE when context_tokens > 80 % of budget.
    """
    ratio = context_tokens / max(budget, 1)
    return HIGH_PRESSURE if ratio > 0.80 else LOW_PRESSURE


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== MDP Retention Policy Demo (Puterman) ===\n")

    for rr in [0.1, 0.5, 0.9]:
        V, pi = value_iteration(rr_score=rr)
        print(f"rr_score={rr:.1f}")
        for s in STATES:
            print(f"  V*({s}) = {V[s]:+.4f}   pi*({s}) = {pi[s]}")
        print()

    # Spot-check: HIGH_PRESSURE should DEMOTE for moderate rr_score
    action_hp = optimal_action(HIGH_PRESSURE, rr_score=0.5)
    action_lp = optimal_action(LOW_PRESSURE, rr_score=0.5)
    print(f"Sanity: HIGH_PRESSURE → {action_hp}  (expect DEMOTE)")
    print(f"Sanity: LOW_PRESSURE  → {action_lp}  (expect RETAIN)")

    assert action_hp == DEMOTE, f"Expected DEMOTE in HIGH_PRESSURE, got {action_hp}"
    assert action_lp == RETAIN, f"Expected RETAIN in LOW_PRESSURE, got {action_lp}"

    print("\nAll assertions passed. Exit 0.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
        sys.exit(0)
    print("Usage: python mdp_retention_policy.py --demo")
    sys.exit(1)
