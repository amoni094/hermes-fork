#!/usr/bin/python3
"""MDP session planner (Puterman value iteration).

Finite decision horizon N=5; discounted VI (Ch 6.3) for 10 backups with
λ∈[0,1). Greedy rollout of the resulting stationary policy is the action
chain. Remaining time is not encoded in the state — the chain is a length-N
greedy trajectory, not backward induction.

States: (task_type, context_bucket, tool_call_count, error_count)
  context_bucket:    low (<30k), medium (30–100k), high (>100k)
  tool_call_count:   low (<10), medium (10–30), high (>30)
  error_count:       none (0), few (1–2), many (3+)
plus absorbing terminals COMPLETE (+1 on entry) and STALL_S1..S11 (−10).

Actions (capability class → live wiring):
  aux, parent, deepseek, grok_worker, magistral, adversarial

Rewards follow the S1–S11 stall taxonomy in claude-routing-hierarchy.

Usage:
  /usr/bin/python3 mdp-session-planner.py \\
      --task-type coding --context-size 12000 --tool-calls 4
"""
from __future__ import annotations

import argparse
import sys

LAMBDA = 0.9
VI_ITERS = 10
HORIZON = 5
REWARD_COMPLETE = 1.0
REWARD_STALL = -10.0

ACTIONS = (
    "aux",
    "parent",
    "deepseek",
    "grok_worker",
    "magistral",
    "adversarial",
)
ACTION_MODELS = {
    "aux": "mistral-small",
    "parent": "sonnet",
    "deepseek": "deepseek",
    "grok_worker": "grok-4.6",
    "magistral": "magistral",
    "adversarial": "sol",
}

CONTEXT_BUCKETS = ("low", "medium", "high")
TOOL_BUCKETS = ("low", "medium", "high")
ERROR_BUCKETS = ("none", "few", "many")
STALL_CLASSES = tuple(f"S{i}" for i in range(1, 12))

TASK_CANON = {
    "extract": "extract",
    "classify": "extract",
    "triage": "extract",
    "mechanical": "extract",
    "aux": "extract",
    "coding": "coding",
    "code": "coding",
    "agentic": "coding",
    "orchestration": "coding",
    "parent": "coding",
    "research": "research",
    "knowledge": "research",
    "synthesis": "research",
    "worker": "worker",
    "delegation": "worker",
    "parallel": "worker",
    "math": "math",
    "reasoning": "math",
    "critique": "critique",
    "review": "critique",
    "adversarial": "critique",
    "general": "coding",
}

PREFERRED = {
    "extract": "aux",
    "coding": "parent",
    "research": "deepseek",
    "worker": "grok_worker",
    "math": "magistral",
    "critique": "adversarial",
}

COMPLETE = ("COMPLETE", "-", "-", "-")


def stall_state(klass: str) -> tuple[str, str, str, str]:
    return ("STALL", klass, "-", "-")


def is_terminal(state: tuple[str, str, str, str]) -> bool:
    return state[0] in ("COMPLETE", "STALL")


def context_bucket(n: int) -> str:
    if n < 30_000:
        return "low"
    if n <= 100_000:
        return "medium"
    return "high"


def tool_bucket(n: int) -> str:
    if n < 10:
        return "low"
    if n <= 30:
        return "medium"
    return "high"


def error_bucket(n: int) -> str:
    if n <= 0:
        return "none"
    if n <= 2:
        return "few"
    return "many"


def canon_task(raw: str) -> str:
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    return TASK_CANON.get(key, "coding")


def _bump(value: str, ladder: tuple[str, ...]) -> str:
    i = ladder.index(value)
    return ladder[min(i + 1, len(ladder) - 1)]


def _drop(value: str, ladder: tuple[str, ...]) -> str:
    i = ladder.index(value)
    return ladder[max(i - 1, 0)]


def completion_prob(
    task: str, ctx: str, tools: str, err: str, action: str
) -> float:
    preferred = PREFERRED[task]
    if action == preferred:
        p = 0.48
    elif {action, preferred} <= {"parent", "grok_worker"}:
        p = 0.28
    elif action == "parent":
        p = 0.22
    else:
        p = 0.10

    if err == "many":
        p *= 0.45
    elif err == "few":
        p *= 0.75

    if ctx == "high":
        if action in ("aux", "magistral"):
            p *= 0.55
        elif action in ("deepseek", "parent"):
            p *= 1.10
        elif action == "grok_worker":
            p *= 1.05
    if tools == "high" and action == "aux":
        p *= 0.50
    if tools == "high" and action == "adversarial" and err in ("few", "many"):
        p *= 1.12
    if task == "research" and action == "deepseek" and tools != "high":
        p *= 1.08
    if task == "math" and action == "magistral" and ctx != "high":
        p *= 1.08
    return min(p, 0.85)


def stall_masses(
    task: str, ctx: str, tools: str, err: str, action: str
) -> dict[str, float]:
    """Unnormalized stall hazard by S1–S11 class for (s, a)."""
    m = {k: 0.0 for k in STALL_CLASSES}

    # S1 IAL / schema: high tool-call count, weak tool fidelity (aux).
    if tools == "high":
        if action == "aux":
            m["S1"] = 0.14
        elif action == "magistral":
            m["S1"] = 0.08
        elif action == "parent":
            m["S1"] = 0.02
        else:
            m["S1"] = 0.04
    elif tools == "medium":
        m["S1"] = 0.05 if action == "aux" else 0.015

    # S2 context rot: high context; knowledge→deepseek, throughput→grok.
    if ctx == "high":
        m["S2"] = {
            "aux": 0.18,
            "magistral": 0.16,
            "adversarial": 0.10,
            "parent": 0.06,
            "grok_worker": 0.05,
            "deepseek": 0.04,
        }[action]
    elif ctx == "medium":
        m["S2"] = 0.03 if action in ("aux", "magistral") else 0.01

    # S3 silent provider fallback (adversarial transport, deepseek 429).
    if action == "adversarial":
        m["S3"] = 0.04
    elif action == "deepseek":
        m["S3"] = 0.03
    else:
        m["S3"] = 0.01

    # S4 compression stall: high ctx + aux (mistral 422 extra_forbidden).
    if ctx == "high" and action == "aux":
        m["S4"] = 0.12
    elif ctx == "high":
        m["S4"] = 0.02

    # S5 async delegation stall: grok workers at high tool count.
    if action == "grok_worker":
        m["S5"] = 0.10 if tools == "high" else 0.03

    # S6 completion/coverage failure.
    if err == "many":
        m["S6"] = 0.08
    elif err == "few":
        m["S6"] = 0.03

    # S7 doomed early: errors; adversarial as JUDGE lowers hazard.
    if err == "many":
        if action == "adversarial":
            m["S7"] = 0.04
        elif action == "aux":
            m["S7"] = 0.14
        else:
            m["S7"] = 0.08
    elif err == "few":
        m["S7"] = 0.02 if action == "adversarial" else 0.05

    # S8 reasoning / no-progress loop; COTA judge (adversarial) helps.
    if tools == "high":
        if action == "adversarial":
            m["S8"] = 0.04
        elif action in ("aux", "magistral"):
            m["S8"] = 0.12
        else:
            m["S8"] = 0.06
    elif tools == "medium":
        m["S8"] = 0.03

    # S9 cron silent stall — not a session-route lever.
    m["S9"] = 0.005

    # S10 token amplification: high tools + high ctx; do not escalate.
    if tools == "high" and ctx == "high":
        m["S10"] = 0.14 if action in ("parent", "adversarial") else 0.08
    elif tools == "high":
        m["S10"] = 0.04

    # S11 control-primitive gap — harness, not model class.
    m["S11"] = 0.005

    # Task mismatch slightly raises S7/S8 (wrong class, doomed / no-progress).
    if action != PREFERRED[task]:
        m["S7"] += 0.02
        m["S8"] += 0.02
    return m


def continue_successors(
    task: str, ctx: str, tools: str, err: str, action: str
) -> list[tuple[tuple[str, str, str, str], float]]:
    """Mass-1 continue kernel (scaled later by p_continue)."""
    preferred = PREFERRED[task]
    next_tools = _bump(tools, TOOL_BUCKETS)
    next_ctx = ctx if ctx == "high" else (
        _bump(ctx, CONTEXT_BUCKETS) if tools == "high" else ctx
    )
    if action == preferred:
        next_err = _drop(err, ERROR_BUCKETS) if err != "none" else "none"
    elif err == "many":
        next_err = "many"
    else:
        next_err = _bump(err, ERROR_BUCKETS)

    progress = (task, next_ctx, next_tools, next_err)
    stay = (task, ctx, next_tools, err)
    rot = (task, _bump(ctx, CONTEXT_BUCKETS), next_tools, next_err)
    parts = [(progress, 0.55), (stay, 0.25), (rot, 0.20)]
    merged: dict[tuple[str, str, str, str], float] = {}
    for s, p in parts:
        merged[s] = merged.get(s, 0.0) + p
    return list(merged.items())


def transitions(
    state: tuple[str, str, str, str], action: str
) -> list[tuple[tuple[str, str, str, str], float, float]]:
    """Return [(next_state, probability, r(s,a,j)), ...] summing to 1."""
    if is_terminal(state):
        return [(state, 1.0, 0.0)]

    task, ctx, tools, err = state
    p_c = completion_prob(task, ctx, tools, err, action)
    masses = stall_masses(task, ctx, tools, err, action)
    stall_sum = sum(masses.values())
    raw = p_c + stall_sum
    if raw > 0.92:
        scale = 0.92 / raw
        p_c *= scale
        masses = {k: v * scale for k, v in masses.items()}
        stall_sum = sum(masses.values())
    p_cont = 1.0 - p_c - stall_sum

    out: list[tuple[tuple[str, str, str, str], float, float]] = [
        (COMPLETE, p_c, REWARD_COMPLETE)
    ]
    for klass, p in masses.items():
        if p > 0.0:
            out.append((stall_state(klass), p, REWARD_STALL))
    for nxt, w in continue_successors(task, ctx, tools, err, action):
        out.append((nxt, p_cont * w, 0.0))

    total = sum(p for _, p, _ in out)
    if total <= 0.0:
        return [(state, 1.0, 0.0)]
    return [(s, p / total, r) for s, p, r in out if p > 0.0]


def all_transient(task: str) -> list[tuple[str, str, str, str]]:
    return [
        (task, c, t, e)
        for c in CONTEXT_BUCKETS
        for t in TOOL_BUCKETS
        for e in ERROR_BUCKETS
    ]


def all_states(task: str) -> list[tuple[str, str, str, str]]:
    terminals = [COMPLETE] + [stall_state(k) for k in STALL_CLASSES]
    return all_transient(task) + terminals


def expected_r(
    trans: list[tuple[tuple[str, str, str, str], float, float]]
) -> float:
    return sum(p * r for _, p, r in trans)


def value_iteration(
    task: str, n_iter: int = VI_ITERS, lam: float = LAMBDA
) -> tuple[dict[tuple[str, str, str, str], float], dict[tuple[str, str, str, str], str], float]:
    """Puterman Ch 6.3: v^{n+1} = T v^n, n_iter backups, v^0 = 0.

    Returns (v, greedy policy, span seminorm of last residual).
    """
    states = all_states(task)
    v = {s: 0.0 for s in states}
    trans_cache = {
        s: {a: transitions(s, a) for a in ACTIONS} for s in states
    }

    span = 0.0
    for _ in range(n_iter):
        v_next = {}
        deltas = []
        for s in states:
            if is_terminal(s):
                v_next[s] = 0.0
                deltas.append(0.0)
                continue
            best = None
            for a in ACTIONS:
                tr = trans_cache[s][a]
                q = expected_r(tr) + lam * sum(p * v[j] for j, p, _ in tr)
                if best is None or q > best:
                    best = q
            v_next[s] = best if best is not None else 0.0
            deltas.append(v_next[s] - v[s])
        span = max(deltas) - min(deltas)
        v = v_next

    policy: dict[tuple[str, str, str, str], str] = {}
    for s in states:
        if is_terminal(s):
            policy[s] = "stop"
            continue
        preferred = PREFERRED[task]
        ranked: list[tuple[float, str]] = []
        for a in ACTIONS:
            tr = trans_cache[s][a]
            q = expected_r(tr) + lam * sum(p * v[j] for j, p, _ in tr)
            ranked.append((q, a))
        max_q = max(q for q, _ in ranked)
        tied = [a for q, a in ranked if abs(q - max_q) < 1e-12]
        policy[s] = preferred if preferred in tied else tied[0]
    return v, policy, span


def q_values(
    state: tuple[str, str, str, str],
    v: dict[tuple[str, str, str, str], float],
    lam: float = LAMBDA,
) -> dict[str, float]:
    out = {}
    for a in ACTIONS:
        tr = transitions(state, a)
        out[a] = expected_r(tr) + lam * sum(p * v[j] for j, p, _ in tr)
    return out


def modal_next(
    state: tuple[str, str, str, str], action: str
) -> tuple[tuple[str, str, str, str], float]:
    tr = transitions(state, action)
    s, p, _ = max(tr, key=lambda x: x[1])
    return s, p


def modal_continue(
    state: tuple[str, str, str, str], action: str
) -> tuple[tuple[str, str, str, str], float] | None:
    """Highest-probability non-absorbing successor (session continues)."""
    cont = [(s, p) for s, p, _ in transitions(state, action) if not is_terminal(s)]
    if not cont:
        return None
    s, p = max(cont, key=lambda x: x[1])
    return s, p


def outcome_probs(
    state: tuple[str, str, str, str], action: str
) -> tuple[float, float, float]:
    p_c = p_s = p_k = 0.0
    for s, p, _ in transitions(state, action):
        if s[0] == "COMPLETE":
            p_c += p
        elif s[0] == "STALL":
            p_s += p
        else:
            p_k += p
    return p_c, p_s, p_k


def action_chain(
    start: tuple[str, str, str, str],
    policy: dict[tuple[str, str, str, str], str],
    horizon: int = HORIZON,
) -> list[tuple[str, tuple[str, str, str, str], tuple[str, str, str, str]]]:
    """Length-horizon greedy routing plan, conditioned on continuation.

    Absorbing COMPLETE/STALL is the one-step outcome of each (s,a); the
    chain is the N-step session plan if the episode does not absorb.
    """
    path = []
    s = start
    for _ in range(horizon):
        if is_terminal(s):
            break
        a = policy[s]
        nxt = modal_continue(s, a)
        if nxt is None:
            term, _ = modal_next(s, a)
            path.append((a, s, term))
            break
        path.append((a, s, nxt[0]))
        s = nxt[0]
    return path


def fmt_state(s: tuple[str, str, str, str]) -> str:
    if s[0] == "COMPLETE":
        return "COMPLETE"
    if s[0] == "STALL":
        return f"STALL_{s[1]}"
    return f"({s[0]}, ctx={s[1]}, tools={s[2]}, err={s[3]})"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Puterman VI session planner (horizon 5, 10 backups)."
    )
    p.add_argument("--task-type", required=True, help="Task class (coding, research, math, …)")
    p.add_argument("--context-size", required=True, type=int, help="Context tokens")
    p.add_argument("--tool-calls", required=True, type=int, help="Tool-call count so far")
    p.add_argument(
        "--errors",
        type=int,
        default=0,
        help="Error count so far (0=none, 1–2=few, 3+=many)",
    )
    p.add_argument("--discount", type=float, default=LAMBDA, help="Puterman λ in [0,1)")
    p.add_argument("--iters", type=int, default=VI_ITERS)
    p.add_argument("--horizon", type=int, default=HORIZON)
    return p.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    if not (0.0 <= args.discount < 1.0):
        print("ERROR: --discount must be in [0, 1) (Puterman λ; VI needs contraction)", file=sys.stderr)
        return 2
    if args.context_size < 0 or args.tool_calls < 0 or args.errors < 0:
        print("ERROR: counts must be non-negative", file=sys.stderr)
        return 2

    task = canon_task(args.task_type)
    start = (
        task,
        context_bucket(args.context_size),
        tool_bucket(args.tool_calls),
        error_bucket(args.errors),
    )
    v, policy, span = value_iteration(task, n_iter=args.iters, lam=args.discount)
    qs = q_values(start, v, lam=args.discount)
    chain = action_chain(start, policy, horizon=args.horizon)
    greedy = policy[start]
    actions = [a for a, _, _ in chain]
    p_c, p_s, p_k = outcome_probs(start, greedy)

    print("=== MDP Session Planner (Puterman VI, Ch 6.3) ===")
    print(f"task_type_raw: {args.task_type}")
    print(f"task_type:     {task}  (preferred action: {PREFERRED[task]})")
    print(
        f"buckets:       context={start[1]} (<30k/30–100k/>100k from {args.context_size})"
        f"  tools={start[2]} (<10/10–30/>30 from {args.tool_calls})"
        f"  errors={start[3]} (from {args.errors})"
    )
    print(f"initial_state: {fmt_state(start)}")
    print(f"λ={args.discount}  VI_iters={args.iters}  horizon={args.horizon}  last_span={span:.6f}")
    print()
    print(f"V(initial_state) = {v[start]:.6f}")
    print("Q(initial_state, ·):")
    best_q = max(qs.values())
    for a in ACTIONS:
        mark = " *" if abs(qs[a] - best_q) < 1e-12 else "  "
        print(
            f"  {mark} {a:<14} {qs[a]:>10.6f}  ({ACTION_MODELS[a]})"
        )
    print()
    print(f"greedy_action: {greedy} ({ACTION_MODELS[greedy]})")
    print(
        f"P(complete|s0,a*)={p_c:.4f}  P(stall|s0,a*)={p_s:.4f}  "
        f"P(continue|s0,a*)={p_k:.4f}  "
        f"r∈{{+{REWARD_COMPLETE:.0f} complete, {REWARD_STALL:.0f} stall}}"
    )
    print("recommended_action_chain: " + (" -> ".join(actions) if actions else "(already terminal)"))
    print("rollout (conditioned on continuation):")
    for i, (a, s, nxt) in enumerate(chain, 1):
        print(f"  t={i}  {fmt_state(s)}  --{a}-->  {fmt_state(nxt)}")
    return 0


def main() -> None:
    sys.exit(run(parse_args()))


if __name__ == "__main__":
    main()
