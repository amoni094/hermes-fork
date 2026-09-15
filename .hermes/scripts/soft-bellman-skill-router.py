#!/usr/bin/python3
"""
soft-bellman-skill-router.py

Soft Bellman skill routing: replaces the hard-argmax skill selection with a
softmax-tempered Bellman update, producing a probability distribution over
skills rather than a single winner.

Math basis (RL theory / soft Q-learning): the soft Bellman operator
  V*(s) = τ log Σ_a exp(Q*(s,a)/τ)
produces an entropy-regularized value function where temperature τ controls
exploration vs. exploitation. At τ→0, recovers hard argmax. At τ→∞, uniform.

For Hermes skill routing:
  s = query embedding (approximated by query keyword features)
  a = skill names
  Q(s,a) = historical success rate of skill a on queries similar to s
  V(s)   = soft max over skills (expected value with exploration)
  Policy π(a|s) = exp(Q(s,a)/τ) / Σ_a' exp(Q(s,a')/τ)

The router reads skill usage history from session logs, computes Q-values
per (query-feature, skill) pair, applies soft Bellman update, and outputs
a ranked probability distribution over skills for a given query.

Unlike the hard skill router, this detects when Q-values are flat (all
skills equally good → high routing entropy → system is uncertain → should
diversify or escalate) vs. sharply peaked (confident routing → low entropy).
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
SESSIONS  = HOME / ".hermes/sessions"
CACHE_DIR = HOME / ".hermes/cache/monitors"
OUT_FILE  = CACHE_DIR / "soft-bellman-routing.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TEMPERATURE = 0.5   # τ: routing temperature (0.1=sharp, 2.0=diffuse)
MIN_SESSIONS        = 3     # need at least this many sessions for meaningful Q


# --- feature extraction -------------------------------------------------------

SKILL_PATTERN = re.compile(r'"name"\s*:\s*"skill_view".*?"name"\s*:\s*"([^"]+)"', re.DOTALL)
TOOL_CALL_PAT = re.compile(r'"tool_calls"')


def _query_features(text: str) -> frozenset[str]:
    """
    Cheap bag-of-keywords feature from a session's first user message.
    Returns a frozenset of normalized keyword tokens.
    """
    # grab first user message content
    lines = text.split("\n")
    for line in lines:
        try:
            obj = json.loads(line)
            if obj.get("role") == "user":
                content = obj.get("content", "")
                if isinstance(content, list):
                    content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                words = re.findall(r"[a-z]{4,}", content.lower())
                return frozenset(words[:30])
        except Exception:
            pass
    return frozenset()


def _extract_skill_calls(text: str) -> list[str]:
    """Extract skill names from skill_view tool calls in a session."""
    skills: list[str] = []
    for line in text.split("\n"):
        try:
            obj = json.loads(line)
            if obj.get("role") == "assistant":
                for tc in obj.get("tool_calls", []):
                    if isinstance(tc, dict):
                        fn = tc.get("function", {})
                        if fn.get("name") == "skill_view":
                            args = fn.get("arguments", "{}")
                            if isinstance(args, str):
                                args = json.loads(args)
                            skill = args.get("name", "")
                            if skill:
                                skills.append(skill)
        except Exception:
            pass
    return skills


def _session_outcome(text: str) -> float:
    """Heuristic outcome score for a session (0.0–1.0)."""
    lines = text.split("\n")
    # positive signals
    pos = sum(1 for l in lines if '"finish_reason": "end_turn"' in l)
    # negative signals (errors, retries)
    neg = sum(1 for l in lines if '"finish_reason": "tool_use"' in l or "error" in l.lower())
    if pos + neg == 0:
        return 0.5
    return min(1.0, pos / (pos + neg + 1))


# --- Q-value computation ------------------------------------------------------

def build_q_table(sessions_dir: Path) -> tuple[dict[str, dict[str, tuple[float, int]]], int]:
    """
    Returns q_table[feature_token][skill] = (mean_outcome, count).
    Aggregated over all sessions: for each feature token in a session's query,
    credit each skill loaded in that session with the session's outcome score.
    """
    q_acc: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    session_files = sorted(sessions_dir.glob("*.jsonl"))
    loaded = 0
    for sf in session_files:
        try:
            text = sf.read_text()
        except Exception:
            continue
        features = _query_features(text)
        skills   = _extract_skill_calls(text)
        outcome  = _session_outcome(text)
        if not features or not skills:
            continue
        for feat in features:
            for skill in skills:
                q_acc[feat][skill].append(outcome)
        loaded += 1

    # Aggregate to mean
    q_table: dict[str, dict[str, tuple[float, int]]] = {}
    for feat, skill_map in q_acc.items():
        q_table[feat] = {
            skill: (sum(vs) / len(vs), len(vs))
            for skill, vs in skill_map.items()
        }
    return q_table, loaded


# --- soft Bellman routing -----------------------------------------------------

def soft_bellman_route(
    query: str,
    q_table: dict[str, dict[str, tuple[float, int]]],
    temperature: float = DEFAULT_TEMPERATURE,
    top_k: int = 10,
) -> list[dict]:
    """
    Compute softmax skill distribution for a query string.
    Returns ranked list of {skill, q_value, probability, count}.
    """
    query_feats = frozenset(re.findall(r"[a-z]{4,}", query.lower())[:30])

    # Accumulate Q-values across matching features
    skill_q: dict[str, list[float]] = defaultdict(list)
    skill_n: dict[str, int] = defaultdict(int)

    for feat in query_feats:
        if feat in q_table:
            for skill, (mean_q, count) in q_table[feat].items():
                skill_q[skill].append(mean_q)
                skill_n[skill] = max(skill_n[skill], count)

    if not skill_q:
        return []

    # Mean Q per skill
    q_vals = {skill: sum(qs) / len(qs) for skill, qs in skill_q.items()}

    # Softmax with temperature
    max_q = max(q_vals.values())
    exp_q = {s: math.exp((q - max_q) / max(temperature, 1e-6)) for s, q in q_vals.items()}
    z = sum(exp_q.values())

    result = sorted(
        [
            {
                "skill":       s,
                "q_value":     round(q_vals[s], 4),
                "probability": round(exp_q[s] / z, 4),
                "count":       skill_n[s],
            }
            for s in q_vals
        ],
        key=lambda x: -x["probability"],
    )
    return result[:top_k]


def routing_entropy(probs: list[float]) -> float:
    """Shannon entropy of routing distribution."""
    return -sum(p * math.log2(p) for p in probs if p > 0)


# --- main ---------------------------------------------------------------------

def run(
    query: str | None,
    temperature: float,
    dry_run: bool,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    q_table, n_sessions = build_q_table(SESSIONS)

    print(f"\n=== Soft-Bellman Skill Router — {now[:10]} ===")
    print(f"Sessions loaded: {n_sessions},  Feature tokens: {len(q_table)}")

    if n_sessions < MIN_SESSIONS:
        print(f"Too few sessions ({n_sessions} < {MIN_SESSIONS}). Baseline not established.")
        return

    if query:
        routing = soft_bellman_route(query, q_table, temperature)
        if not routing:
            print(f"\nNo Q-data for query: '{query}'")
        else:
            probs = [r["probability"] for r in routing]
            H = routing_entropy(probs)
            print(f"\nQuery: '{query}'")
            print(f"Temperature τ={temperature},  Routing entropy H={H:.3f} bits")
            print(f"\n{'Skill':<45} {'P':>6} {'Q':>6} {'N':>5}")
            print("-" * 65)
            for r in routing:
                print(f"  {r['skill']:<43} {r['probability']:>6.3f} {r['q_value']:>6.3f} {r['count']:>5}")
    else:
        # Summary mode: compute mean routing entropy across all feature tokens
        entropies: list[float] = []
        for feat, skill_map in q_table.items():
            if len(skill_map) < 2:
                continue
            q_vals = {s: mv[0] for s, mv in skill_map.items()}
            max_q  = max(q_vals.values())
            exp_q  = {s: math.exp((q - max_q) / temperature) for s, q in q_vals.items()}
            z      = sum(exp_q.values())
            probs  = [v / z for v in exp_q.values()]
            entropies.append(routing_entropy(probs))

        mean_H = sum(entropies) / max(len(entropies), 1)
        print(f"\nMean routing entropy: {mean_H:.3f} bits (τ={temperature})")
        print(f"Feature tokens with ≥2 skills: {len(entropies)}")
        if mean_H > 2.0:
            print("WARNING: high routing entropy — skill Q-values are flat (low confidence routing)")
        elif mean_H < 0.3:
            print("OK — routing entropy low (sharp skill preferences)")
        else:
            print("OK — routing entropy moderate")

        if not dry_run:
            out = {
                "ts": now, "sessions": n_sessions, "features": len(q_table),
                "mean_routing_entropy": round(mean_H, 4),
                "temperature": temperature,
            }
            OUT_FILE.write_text(json.dumps(out, indent=2))
            print(f"Written: {OUT_FILE}")
    if dry_run:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Soft-Bellman skill router")
    parser.add_argument("--query",       default=None,
                        help="Route a specific query string")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE,
                        help="Routing temperature τ (default 0.5)")
    parser.add_argument("--dry-run",     action="store_true")
    args = parser.parse_args()
    run(query=args.query, temperature=args.temperature, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
