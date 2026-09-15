#!/usr/bin/env python3
"""KL-distance skill prior (heuristic, not Sanov's theorem).

Scores skills by KL divergence D(session || skill) between the query token
distribution and each skill's historical observation tokens.

Live skill-state schema (hermes-skill-state/v1):
  ~/.hermes/cache/skill-state/{session_id}__{skill_name}.json
  field `observations`: list of {step, obs, at}  (NOT `obs_ring_buffer`;
  that name is a config integer in skill-state.py, not a JSON key).

Low KL → past observations are closer to the current query → higher prior.
Skills with no usable observation tokens are omitted (they must not outrank
skills that have real but mismatched history).

Usage:
    python3 kl-skill-prior.py <query_tokens...>
    python3 kl-skill-prior.py --top 5 "compress context" "memory write"

Output: JSON list of {name, kl, score, n_obs} sorted by score descending.

This is epsilon-smoothed KL in bits (log2), used as a ranking distance.
It is not an I-projection and does not apply Sanov's theorem; n is tiny
and the "types" are bag-of-words, not empirical process types.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
SKILL_STATE_DIR = HERMES_HOME / "cache" / "skill-state"
_SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _tokenize(text: str) -> list[str]:
    """Lowercase-word tokenizer; ASCII letters+digits only, tokens longer than 2 chars."""
    return [w.lower() for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2]


def _freq_dist(tokens: list[str]) -> dict[str, float]:
    """Normalised frequency distribution over token types."""
    if not tokens:
        return {}
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = sum(counts.values())
    return {k: v / total for k, v in counts.items()}


def _kl(p: dict[str, float], q: dict[str, float], epsilon: float = 1e-8) -> float:
    """D(P||Q) in bits (log2). Smooths Q with epsilon; does not renormalise Q.

    Only sums over supp(P). Empty P is the caller's problem (return inf).

    Zero-observation fallback: skills with no usable tokens are omitted upstream
    (load_skill_distributions). If q is empty, the epsilon smoothing acts as a
    Laplace add-one prior: effectively 1/(vocab_size+1) per token.
    # Jaynes Ch18 rule of succession: P(next=1|k,n) = (k+1)/(n+2); here k=0, n=0 -> 1/2.
    # For vocab: 1/(V+1).
    """
    if not p:
        return float("inf")
    result = 0.0
    for k, pk in p.items():
        if pk <= 0.0:
            continue
        qk = q.get(k, 0.0) + epsilon
        result += pk * math.log2(pk / qk)
    # result is already in bits (log2)
    return result


def _obs_texts(data: object) -> list[str]:
    """Extract observation strings from v1 `observations` or legacy keys."""
    if not isinstance(data, dict):
        return []
    obs = data.get("observations")
    if obs is None:
        obs = data.get("obs_ring_buffer", [])
    if not isinstance(obs, list):
        return []
    texts: list[str] = []
    for entry in obs:
        if isinstance(entry, str):
            texts.append(entry)
        elif isinstance(entry, dict):
            for key in ("obs", "observation", "query", "text"):
                val = entry.get(key)
                if isinstance(val, str):
                    texts.append(val)
                    break
    return texts


def _safe_skill_name(name: str) -> str | None:
    if not name or not _SKILL_NAME_RE.fullmatch(name):
        return None
    return name


def load_skill_distributions() -> dict[str, tuple[dict[str, float], int]]:
    """Aggregate observation-token distributions per skill_name.

    Returns {skill_name: (dist, n_observation_strings)}.
    """
    out: dict[str, list[str]] = {}
    if not SKILL_STATE_DIR.is_dir():
        return {}
    try:
        state_root = SKILL_STATE_DIR.resolve()
    except OSError:
        return {}

    for state_file in SKILL_STATE_DIR.glob("*.json"):
        try:
            resolved = state_file.resolve()
            resolved.relative_to(state_root)
        except (ValueError, OSError):
            continue
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError):
            continue
        if isinstance(data, dict) and data.get("skill_name"):
            skill_name = str(data["skill_name"])
        else:
            stem = state_file.stem
            skill_name = stem.split("__", 1)[-1] if "__" in stem else stem
        skill_name = _safe_skill_name(skill_name)
        if not skill_name:
            continue
        texts = _obs_texts(data)
        if not texts:
            continue
        out.setdefault(skill_name, []).extend(texts)

    dists: dict[str, tuple[dict[str, float], int]] = {}
    for name, texts in out.items():
        tokens: list[str] = []
        for t in texts:
            tokens.extend(_tokenize(t))
        dist = _freq_dist(tokens)
        if dist:
            dists[name] = (dist, len(texts))
    return dists


def score_skills(query_tokens: list[str], top_k: int = 10) -> list[dict]:
    """Return top_k skills ranked by KL-based prior score. Empty history omitted."""
    if not SKILL_STATE_DIR.exists():
        print(f"[kl-skill-prior] skill-state dir not found: {SKILL_STATE_DIR}", file=sys.stderr)
        return []

    session_dist = _freq_dist(query_tokens)
    if not session_dist:
        return []

    results = []
    for skill_name, (skill_dist, n_obs) in load_skill_distributions().items():
        kl = _kl(session_dist, skill_dist)
        # kl_bits = kl (already in bits via log2); convert nats to bits if source were nats
        # Here _kl uses log2 directly, so kl_bits == kl.
        kl_bits = kl  # Shannon 1948: information in bits = entropy in log2 units
        score = math.exp2(-kl_bits)  # 2^{-D} in [0, 1]
        results.append({
            "name": skill_name,
            "kl": round(kl_bits, 4),
            "score": round(score, 4),
            "n_obs": n_obs,
        })

    results.sort(key=lambda x: (-x["score"], x["name"]))
    if top_k < 0:
        top_k = 0
    return results[:top_k]


def main() -> None:
    parser = argparse.ArgumentParser(description="KL-distance skill prior ranker (heuristic)")
    subparsers = parser.add_subparsers(dest="subcommand")

    # Default (no subcommand): rank by KL prior
    rank_parser = subparsers.add_parser("rank", help="Rank skills by KL prior (default)")
    rank_parser.add_argument("queries", nargs="+", help="Query text(s)")
    rank_parser.add_argument("--top", type=int, default=10)
    rank_parser.add_argument("--w2-bound", action="store_true", dest="w2_bound",
                             help="Append Talagrand W2 upper bound advisory (VIL-6)")
    rank_parser.add_argument("--lambda", dest="spectral_gap", type=float, default=1.0,
                             help="Spectral gap lambda for W2 bound (default 1.0)")

    # OT-6: JS divergence subcommand
    js_parser = subparsers.add_parser(
        "js-divergence",
        help="JS divergence between two token distributions (OT-6)",
    )
    js_parser.add_argument("--p", nargs="+", required=True,
                           help="Tokens for distribution P")
    js_parser.add_argument("--q", nargs="+", required=True,
                           help="Tokens for distribution Q")
    js_parser.add_argument("--w2-bound", action="store_true", dest="w2_bound",
                           help="Append Talagrand W2 upper bound advisory (VIL-6)")
    js_parser.add_argument("--lambda", dest="spectral_gap", type=float, default=1.0,
                           help="Spectral gap lambda for W2 bound (default 1.0)")

    # ROY-5: Radon-Nikodym likelihood ratio subcommand
    rn_parser = subparsers.add_parser(
        "radon-nikodym",
        help="Radon-Nikodym likelihood ratio dnu/dmu (ROY-5)",
    )
    rn_parser.add_argument("--session", nargs="+", required=True,
                           help="Session (observed) tokens (nu)")
    rn_parser.add_argument("--skill", nargs="+", required=True,
                           help="Skill (prior) tokens (mu)")
    rn_parser.add_argument("--epsilon", type=float, default=1e-8,
                           help="Smoothing for prior (default 1e-8)")

    # GS-3: Empirical frequency-estimate subcommand
    fe_parser = subparsers.add_parser(
        "frequency-estimate",
        help="Empirical skill frequency p_k from metacognitive.db (GS-3/LLN intuition)",
    )
    fe_parser.add_argument("--json", action="store_true", dest="json_out",
                           help="Output raw JSON instead of table")

    # Backwards-compat: bare queries without subcommand → rank
    # Pre-check: if first non-flag arg is not a known subcommand, use simple parser.
    _SUBCOMMANDS = {"rank", "js-divergence", "radon-nikodym", "frequency-estimate"}
    _first = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    if _first is not None and _first not in _SUBCOMMANDS:
        simple = argparse.ArgumentParser(description="KL-distance skill prior ranker (heuristic)")
        simple.add_argument("queries", nargs="+", help="Query text(s) to build session distribution")
        simple.add_argument("--top", type=int, default=10, help="Number of top skills to return")
        simple.add_argument("--w2-bound", action="store_true", dest="w2_bound",
                            help="Append Talagrand W2 upper bound advisory (VIL-6)")
        simple.add_argument("--lambda", dest="spectral_gap", type=float, default=1.0)
        sargs = simple.parse_args()
        tokens_bare: list[str] = []
        for q in sargs.queries:
            tokens_bare.extend(_tokenize(q))
        ranked_bare = score_skills(tokens_bare, top_k=sargs.top)
        if sargs.w2_bound:
            lam = sargs.spectral_gap  # --lambda arg
            for row in ranked_bare:
                kl = row.get("kl", float("inf"))
                if math.isfinite(kl) and kl >= 0.0 and lam > 0.0:
                    # VIL-6: Talagrand T2 inequality W2(session, skill) <= sqrt(2*KL/lambda)
                    # Villani Ch 22 (Optimal Transport: Old and New, 2009 Thm 22.17)
                    w2_ub = math.sqrt(2.0 * kl / lam)
                else:
                    w2_ub = None
                row["w2_upper"] = (
                    round(w2_ub, 6) if w2_ub is not None else None
                )
                row["w2_note"] = (
                    "Talagrand T2 inequality: W2(session, skill) <= W2_upper (Villani Ch 22). "
                    "W2_upper = sqrt(2*KL/lambda). ADVISORY; assumes log-Sobolev with gap lambda."
                )
            # Sort by W2_upper ascending (None/inf last) — VIL-6
            ranked_bare.sort(key=lambda r: (
                r["w2_upper"] if r["w2_upper"] is not None else float("inf")
            ))
        print(json.dumps(ranked_bare, indent=2))
        return

    args, remaining = parser.parse_known_args()

    if args.subcommand == "js-divergence":
        _cmd_js_divergence(args)
        return

    if args.subcommand == "radon-nikodym":
        _cmd_radon_nikodym(args)
        return

    if args.subcommand == "frequency-estimate":
        _cmd_frequency_estimate(args)
        return

    # Subcommand is "rank" or None (bare positional query mode)
    if args.subcommand == "rank":
        tokens: list[str] = []
        for q in args.queries:
            tokens.extend(_tokenize(q))
        top_k = args.top
        w2_bound = args.w2_bound
        spectral_gap = args.spectral_gap
    else:
        # Bare-mode: re-parse with simple parser for backwards compat
        simple = argparse.ArgumentParser(description="KL-distance skill prior ranker (heuristic)")
        simple.add_argument("queries", nargs="+", help="Query text(s) to build session distribution")
        simple.add_argument("--top", type=int, default=10, help="Number of top skills to return")
        simple.add_argument("--w2-bound", action="store_true", dest="w2_bound",
                            help="Append Talagrand W2 upper bound advisory (VIL-6)")
        simple.add_argument("--lambda", dest="spectral_gap", type=float, default=1.0)
        sargs = simple.parse_args()
        tokens = []
        for q in sargs.queries:
            tokens.extend(_tokenize(q))
        top_k = sargs.top
        w2_bound = sargs.w2_bound
        spectral_gap = sargs.spectral_gap

    ranked = score_skills(tokens, top_k=top_k)

    if w2_bound:
        lam = spectral_gap  # --lambda arg
        for row in ranked:
            kl = row.get("kl", float("inf"))
            if math.isfinite(kl) and kl >= 0.0 and lam > 0.0:
                # VIL-6: Talagrand T2 inequality W2(session, skill) <= sqrt(2*KL/lambda)
                # Villani Ch 22 (Optimal Transport: Old and New, 2009 Thm 22.17)
                w2_ub = math.sqrt(2.0 * kl / lam)
            else:
                w2_ub = None
            row["w2_upper"] = (
                round(w2_ub, 6) if w2_ub is not None else None
            )
            row["w2_note"] = (
                "Talagrand T2 inequality: W2(session, skill) <= W2_upper (Villani Ch 22). "
                "W2_upper = sqrt(2*KL/lambda). ADVISORY; assumes log-Sobolev with gap lambda."
            )
        # Sort by W2_upper ascending (None/inf last) — VIL-6
        ranked.sort(key=lambda r: (
            r["w2_upper"] if r["w2_upper"] is not None else float("inf")
        ))

    print(json.dumps(ranked, indent=2))


def _frequency_estimate_data() -> list[dict]:
    """Read skill invocation counts; return sorted empirical frequency table.

    Primary source: metacognitive.db skill_profiles (SUM(total) per skill).
    Fallback: lifecycle.db access_count as proxy.
    LLN intuition: p_k = count_k / N converges to true frequency as N -> inf.
    """
    counts: dict[str, int] = {}

    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    lifecycle_db = hermes_home / "memory-facts" / "lifecycle.db"

    # Try explicit MH_DB env var first, then standard locations
    _meta_candidates = [
        Path(os.environ["MH_DB"]) if "MH_DB" in os.environ else None,
        hermes_home / "memory-facts" / "metacognitive.db",
        Path.home() / ".hermes" / "memory-facts" / "metacognitive.db",
    ]
    meta_db = next((p for p in _meta_candidates if p is not None and p.is_file()), None)

    import sqlite3 as _sqlite3

    if meta_db is not None:
        try:
            conn = _sqlite3.connect(f"file:{meta_db}?mode=ro", uri=True)
            try:
                rows = conn.execute(
                    "SELECT skill, SUM(total) FROM skill_profiles GROUP BY skill"
                ).fetchall()
                for skill, total in rows:
                    if skill and total:
                        counts[str(skill)] = counts.get(str(skill), 0) + int(total)
            except _sqlite3.Error:
                pass
            finally:
                conn.close()
        except (OSError, _sqlite3.Error):
            pass

    # Lifecycle.db fallback: also try default path
    _lc_candidates = [
        lifecycle_db,
        Path.home() / ".hermes" / "memory-facts" / "lifecycle.db",
    ]
    lc_db = next((p for p in _lc_candidates if p.is_file()), None)
    if not counts and lc_db is not None:
        try:
            conn = _sqlite3.connect(f"file:{lc_db}?mode=ro", uri=True)
            try:
                rows = conn.execute(
                    "SELECT fact_text, access_count FROM fact_lifecycle"
                ).fetchall()
                for fact_text, ac in rows:
                    if fact_text and ac:
                        key = str(fact_text).split()[0][:80]
                        counts[key] = counts.get(key, 0) + int(ac or 0)
            except _sqlite3.Error:
                pass
            finally:
                conn.close()
        except (OSError, _sqlite3.Error):
            pass

    if not counts:
        return []
    total = sum(counts.values())
    if total <= 0:
        return []
    return sorted(
        [{"skill": s, "count": c, "p_k": round(c / total, 6)} for s, c in counts.items()],
        key=lambda x: (-x["p_k"], x["skill"]),
    )


def _cmd_frequency_estimate(args) -> None:
    """GS-3: Empirical frequency estimate (LLN intuition: converges as N->inf)."""
    table = _frequency_estimate_data()
    if not table:
        print("No skill invocation data found in metacognitive.db or lifecycle.db.",
              file=sys.stderr)
        return

    json_out = getattr(args, "json_out", False)
    if json_out:
        print(json.dumps({
            "method": "empirical_frequency_estimate",
            "note": "LLN intuition: p_k = count_k / N converges as N -> inf",
            "skills": table,
            "total_invocations": sum(r["count"] for r in table),
        }, indent=2))
    else:
        print("Empirical frequency estimate (LLN intuition: converges as N->inf)")
        print(f"{'rank':>4}  {'skill':<40}  {'count':>6}  {'p_k':>8}")
        print(f"{'----':>4}  {'-'*40}  {'------':>6}  {'--------':>8}")
        for rank, row in enumerate(table, 1):
            print(f"{rank:>4}  {row['skill']:<40}  {row['count']:>6}  {row['p_k']:>8.6f}")
        print(f"\nTotal: {sum(r['count'] for r in table)} invocations across {len(table)} skills")


def _cmd_js_divergence(args) -> None:
    """OT-6: JS divergence JS(P||Q) = 0.5*KL(P||M) + 0.5*KL(Q||M), M = 0.5*(P+Q).

    Output in bits (log2). Bounded [0, 1] bits. Symmetric.
    """
    p_tokens: list[str] = []
    for t in args.p:
        p_tokens.extend(_tokenize(t))
    q_tokens: list[str] = []
    for t in args.q:
        q_tokens.extend(_tokenize(t))

    p = _freq_dist(p_tokens)
    q = _freq_dist(q_tokens)

    if not p or not q:
        print(json.dumps({"error": "empty distribution — provide more tokens"}))
        return

    # Build mixture M over shared vocab (union)
    vocab = set(p) | set(q)
    m: dict[str, float] = {k: 0.5 * (p.get(k, 0.0) + q.get(k, 0.0)) for k in vocab}

    # KL(P||M) and KL(Q||M) — mixture M is never zero on supp(P) or supp(Q)
    def _kl_to_mixture(dist: dict[str, float], mix: dict[str, float]) -> float:
        result = 0.0
        for k, pk in dist.items():
            if pk <= 0.0:
                continue
            mk = mix.get(k, 0.0)
            if mk <= 0.0:
                continue  # should not happen since m covers both supports
            result += pk * math.log2(pk / mk)
        return result

    kl_pm = _kl_to_mixture(p, m)
    kl_qm = _kl_to_mixture(q, m)
    js = 0.5 * kl_pm + 0.5 * kl_qm
    # Clamp to [0, 1] for numerical safety
    js = max(0.0, min(1.0, js))

    result: dict = {
        "js_divergence_bits": round(js, 6),
        "kl_p_given_m_bits": round(kl_pm, 6),
        "kl_q_given_m_bits": round(kl_qm, 6),
        "symmetric": True,
        "bounded": "[0, 1] bits",
        "note": "JS(P,Q) = 0.5*KL(P||M) + 0.5*KL(Q||M), M = 0.5*(P+Q). OT-6.",
    }

    if hasattr(args, "w2_bound") and args.w2_bound:
        spectral_gap = getattr(args, "spectral_gap", 1.0)
        if spectral_gap > 0.0 and math.isfinite(js):
            w2_ub = math.sqrt(2.0 * js / spectral_gap)
            result["w2_upper_bound_advisory"] = round(w2_ub, 6)
            result["w2_note"] = (
                "ADVISORY ONLY: W2 <= sqrt(2*JS/lambda) via Talagrand T2 (using JS as proxy KL). "
                "Not a guarantee."
            )

    print(json.dumps(result, indent=2))


def _cmd_radon_nikodym(args) -> None:
    """ROY-5: Radon-Nikodym likelihood ratio dnu/dmu.

    nu = observed session distribution; mu = skill (prior) distribution.
    dnu/dmu(x) = nu(x) / mu(x) for each token x in vocab.
    L1 norm of (dnu/dmu - 1) * dmu = total variation distance TV(nu, mu).
    """
    session_tokens: list[str] = []
    for t in args.session:
        session_tokens.extend(_tokenize(t))
    skill_tokens: list[str] = []
    for t in args.skill:
        skill_tokens.extend(_tokenize(t))

    nu = _freq_dist(session_tokens)   # observed (session)
    mu = _freq_dist(skill_tokens)     # prior (skill)

    if not nu or not mu:
        print(json.dumps({"error": "empty distribution — provide more tokens"}))
        return

    epsilon = getattr(args, "epsilon", 1e-8)
    vocab = set(nu) | set(mu)
    ratios: dict[str, float] = {}
    for k in vocab:
        nu_k = nu.get(k, 0.0)
        mu_k = mu.get(k, 0.0) + epsilon   # smoothed prior
        ratios[k] = nu_k / mu_k

    # TV = 0.5 * sum_k |nu(k) - mu(k)| (standard definition)
    # L1 norm of update = sum_k |nu(k) - mu(k)|  (total absolute difference)
    tv = 0.5 * sum(abs(nu.get(k, 0.0) - mu.get(k, 0.0)) for k in vocab)

    # Sort by ratio descending (most enriched tokens first)
    sorted_ratios = sorted(ratios.items(), key=lambda x: -x[1])

    print(json.dumps({
        "radon_nikodym_ratios": {k: round(v, 6) for k, v in sorted_ratios},
        "total_variation_distance": round(tv, 6),
        "l1_norm_update": round(2.0 * tv, 6),
        "n_session_tokens": len(session_tokens),
        "n_skill_tokens": len(skill_tokens),
        "vocab_size": len(vocab),
        "epsilon_smoothing": epsilon,
        "note": (
            "dnu/dmu(x) = session_freq(x) / (skill_freq(x) + epsilon). "
            "TV = 0.5*L1. ROY-5 (Royden-Fitzpatrick discrete RN derivative)."
        ),
    }, indent=2))


if __name__ == "__main__":
    main()
