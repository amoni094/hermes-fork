#!/usr/bin/env python3
"""Occam-weighted skill ranker (MACKAY-1 coverage volume ratio).

Default evidence score (coverage Occam, not a length penalty):
  coverage(q, s) = |tokens(q) ∩ tokens(s)| / max(1, |tokens(s)|)
  occam = coverage(q, s)
  evidence = 0.5 * cosine(q, s) + 0.5 * ruzicka(q, s) * occam

coverage is the fraction of skill-scope tokens the query addresses
(posterior-constrained volume / prior volume). 1 = query saturates skill
scope (specialist match); 0 = query misses the skill entirely. occam=0
dampens the Ruzicka term; occam=1 keeps full Ruzicka weight.

--legacy-score restores the older heuristic:
  score = (sim − λ * min(length/1000, 1) * logN_factor) * specificity
That path is NOT MacKay Ch 28 Bayesian evidence and NOT BIC. length_tokens
remains a diagnostic on both paths.

Usage:
    python3 occam-skill-ranker.py <query>
    python3 occam-skill-ranker.py rank --query 'github pull request'
    python3 occam-skill-ranker.py rank --query 'github pull request' --hamming
    python3 occam-skill-ranker.py "compress context" --top 5 --lambda 0.25
    python3 occam-skill-ranker.py "compress context" --metric blend --coverage
    python3 occam-skill-ranker.py dp-route --query 'Q' [--k 4] [--n-limit 16]
    python3 occam-skill-ranker.py routing-nt --task-type TASK_TYPE [--policy-file PATH] [--set RANKER]
    python3 occam-skill-ranker.py "github" --uncovered --legacy-score

Output: JSON list of {name, cosine, l1_overlap, metric, occam_penalty, score,
length_tokens, occam_coverage, specificity, op_norm} sorted by score descending.
With --coverage, wraps as {results: [...], coverage_rank: [...]}.
With --uncovered, adds uncovered_tokens (query tokens in no skill token set).

Jaynes Ch.24 Occam (legacy path only): specific skills penalise broad priors.
Score is multiplied by specificity = 1 / max(1, n_task_types). n_task_types
comes from the skill_profiles DB when available; otherwise description-length
/ 10 is a breadth proxy.

Notes:
- Similarity is TF bag-of-words cosine (not TF-IDF, no embedding API).
- lambda=0 → pure cosine on --legacy-score; ignored on the default path.
- Not wired into Hermes skill routing; compose by replacing a sort key.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
import sqlite3
import numpy as np

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
SKILL_WIKI_DIR = HERMES_HOME / "cache" / "skill-wiki"
SKILLS_DIR = HERMES_HOME / "skills"
_SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2]


def _tf_vec(tokens: list[str]) -> dict[str, float]:
    """Normalised term frequency (not TF-IDF)."""
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = sum(counts.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in counts.items()}


_TF_CACHE: dict[tuple[str, str], dict[str, float]] = {}
_tf_cache_hits = 0
_tf_cache_misses = 0


def _tf_vec_cached(name: str, text: str) -> dict:
    global _tf_cache_hits, _tf_cache_misses
    key = (name, hashlib.md5(text.encode()).hexdigest()[:16])
    if key not in _TF_CACHE:
        _TF_CACHE[key] = _tf_vec(_tokenize(name + " " + text))
        _tf_cache_misses += 1
    else:
        _tf_cache_hits += 1
    return _TF_CACHE[key]


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(k, 0.0) * v for k, v in b.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (na * nb)


def _dot(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))


def _ruzicka_overlap(a: dict[str, float], b: dict[str, float]) -> float:
    """Ruzicka (generalized Jaccard) similarity on TF masses. Not the L1 norm."""
    keys = set(a) | set(b)
    num = sum(min(a.get(k, 0.0), b.get(k, 0.0)) for k in keys)
    den = sum(max(a.get(k, 0.0), b.get(k, 0.0)) for k in keys) or 1e-9
    return num / den


_l1_overlap = _ruzicka_overlap


def _occam_coverage(q_tokens: list[str], s_token_set: set[str]) -> float:
    """Fraction of skill-scope tokens the query addresses. Ranges [0, 1]."""
    if not s_token_set:
        return 0.0
    return len(set(q_tokens) & s_token_set) / max(1, len(s_token_set))


def _hamming_sim(q_token_set: set[str], s_token_set: set[str]) -> float:
    """Normalized set Hamming similarity in [0, 1]; 1=identical, 0=no overlap."""
    vocab = q_token_set | s_token_set
    hamming = len(q_token_set.symmetric_difference(s_token_set))
    hamming_norm = hamming / max(1, len(vocab))
    return 1.0 - hamming_norm


def _op_norm(x: dict[str, float], Tx: dict[str, float]) -> float:
    nx = math.sqrt(sum(v * v for v in x.values()))
    nTx = math.sqrt(sum(v * v for v in Tx.values()))
    return nTx / nx if nx > 0 else float("inf")


def _sinkhorn(C: "np.ndarray", reg: float = 0.05, max_iter: int = 100) -> "np.ndarray":
    """Sinkhorn-Knopp algorithm for regularised OT. Returns soft transport plan P.

    Args:
        C: cost matrix of shape (n, m), entries in [0, 1].
        reg: entropic regularisation strength (epsilon). Larger = more uniform plan.
        max_iter: maximum Sinkhorn iterations.

    Returns:
        P: (n, m) transport plan with uniform marginals 1/n (rows) and 1/m (cols).

    Reference: Cuturi 2013; Sinkhorn-Knopp matrix scaling.
    """
    n, m = C.shape
    # Log-domain Sinkhorn for numerical stability
    # K_ij = exp(-C_ij / reg)
    log_K = -C / reg
    # Uniform marginals
    log_a = np.full(n, -math.log(n))   # log(1/n)
    log_b = np.full(m, -math.log(m))   # log(1/m)
    # Dual variables (log-space)
    log_u = np.zeros(n)
    log_v = np.zeros(m)
    for _ in range(max_iter):
        # u_i = a_i / (K @ v)_i  → log_u = log_a - logsumexp(log_K + log_v, axis=1)
        log_u = log_a - np.array([
            np.logaddexp.reduce(log_K[i] + log_v) for i in range(n)
        ])
        # v_j = b_j / (K.T @ u)_j
        log_v = log_b - np.array([
            np.logaddexp.reduce(log_K[:, j] + log_u) for j in range(m)
        ])
    # P_ij = u_i * K_ij * v_j
    P = np.exp(log_u[:, None] + log_K + log_v[None, :])
    return P


def sinkhorn_similarity(
    a: dict[str, float],
    b: dict[str, float],
    reg: float = 0.05,
) -> float:
    """Soft OT similarity between two TF dicts (OT-1).

    Ground metric: 0 for same token, 1 for different (Hamming on vocabulary).
    Cost C_ij = 1 - int(vocab[i] == vocab[j]).
    Returns 1 - OT_cost, so 1.0 = identical distributions, 0.0 = disjoint.
    """
    if not a or not b:
        return 0.0
    vocab_a = list(a.keys())
    vocab_b = list(b.keys())
    n, m = len(vocab_a), len(vocab_b)
    va = np.array([a[k] for k in vocab_a], dtype=float)
    vb = np.array([b[k] for k in vocab_b], dtype=float)
    # Normalise (should already be TF-normalised, but guard against drift)
    va /= va.sum() if va.sum() > 0 else 1.0
    vb /= vb.sum() if vb.sum() > 0 else 1.0
    vocab_b_set = set(vocab_b)
    # C_ij = 0 if tokens match, 1 otherwise (discrete Hamming ground metric)
    C = np.ones((n, m), dtype=float)
    for i, tok in enumerate(vocab_a):
        if tok in vocab_b_set:
            j = vocab_b.index(tok)
            C[i, j] = 0.0
    P = _sinkhorn(C, reg=reg)
    ot_cost = float(np.sum(P * C))
    return max(0.0, 1.0 - ot_cost)


def _greedy_ls_coverage(
    q_vec: dict[str, float],
    named_vecs: list[tuple[str, dict[str, float]]],
    max_iter: int = 4,
    min_delta: float = 0.02,
) -> list[dict]:
    """Greedy least-squares coverage of the query residual (Luenberger)."""
    q_rem = dict(q_vec)
    coverage_order: list[dict] = []
    selected: set[str] = set()
    for _ in range(max_iter):
        best_name = None
        best_gain = float("-inf")
        best_svec: dict[str, float] | None = None
        for name, s_vec in named_vecs:
            if name in selected or not s_vec:
                continue
            ss = _dot(s_vec, s_vec)
            if ss <= 0:
                continue
            proj_gain = _dot(q_rem, s_vec) / math.sqrt(ss)
            if proj_gain > best_gain:
                best_gain = proj_gain
                best_name = name
                best_svec = s_vec
        if best_name is None or best_svec is None:
            break
        ss = _dot(best_svec, best_svec)
        if ss <= 0:
            break
        gain_scalar = _dot(q_rem, best_svec) / ss
        delta_residual = gain_scalar * math.sqrt(ss)
        if delta_residual < min_delta:
            break
        for k in set(q_rem) | set(best_svec):
            q_rem[k] = q_rem.get(k, 0.0) - gain_scalar * best_svec.get(k, 0.0)
        selected.add(best_name)
        coverage_order.append({
            "skill": best_name,
            "delta_residual": round(float(delta_residual), 4),
        })
    return coverage_order


def _is_under(base: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(base.resolve())
        return True
    except (ValueError, OSError):
        return False


def _index_skill_md() -> dict[str, Path]:
    index: dict[str, Path] = {}
    if not SKILLS_DIR.is_dir():
        return index
    for path in SKILLS_DIR.rglob("SKILL.md"):
        if not _is_under(SKILLS_DIR, path):
            continue
        index[path.parent.name] = path
    return index


def _skill_token_length(skill_name: str, md_index: dict[str, Path]) -> int | None:
    """Body token count from skill-wiki or SKILL.md. None if unknown (no penalty)."""
    if not _SKILL_NAME_RE.fullmatch(skill_name or ""):
        return None
    wiki_file = SKILL_WIKI_DIR / f"{skill_name}.json"
    if wiki_file.exists() and _is_under(SKILL_WIKI_DIR, wiki_file):
        try:
            data = json.loads(wiki_file.read_text(encoding="utf-8"))
            body = ""
            if isinstance(data, dict):
                body = data.get("body", "") or data.get("content", "") or ""
            if isinstance(body, str) and body.strip():
                return max(len(body.split()), 1)
        except (OSError, json.JSONDecodeError, UnicodeError, TypeError):
            pass
    candidate = md_index.get(skill_name)
    if candidate is not None:
        try:
            return max(len(candidate.read_text(encoding="utf-8").split()), 1)
        except (OSError, UnicodeError):
            pass
    return None


def _task_type_counts() -> dict[str, int]:
    """Distinct task_types per skill from metacognitive skill_profiles DB."""
    db = Path(os.environ.get(
        "MH_DB", str(HERMES_HOME / "memory-facts" / "metacognitive.db")
    ))
    if not db.is_file():
        return {}
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT skill, COUNT(DISTINCT task_type) FROM skill_profiles GROUP BY skill"
            ).fetchall()
        except sqlite3.Error:
            return {}
        finally:
            conn.close()
        return {str(k): int(v) for k, v in rows}
    except (OSError, sqlite3.Error, ValueError):
        return {}


def rank_skills_occam(
    query: str,
    skills: list[dict],
    *,
    top_k: int = 10,
    occam_lambda: float = 0.25,
    metric: str = "blend",
    coverage: bool = False,
    uncovered: bool = False,
    legacy_score: bool = False,
    hamming: bool = False,
):
    """Rank skills by TF similarity with a coverage Occam factor.

    Default (MACKAY-1): evidence = 0.5*cosine + 0.5*ruzicka*coverage(q,s).
    --legacy-score: TF similarity minus a body-length penalty, times specificity.
    --hamming: evidence = 0.5*hamming_sim + 0.5*coverage; ruzicka*occam is tiebreaker.

    Args:
        query: Natural language query string.
        skills: List of {"name": str, "description": str} dicts.
        top_k: Number of results to return.
        occam_lambda: Weight on the length penalty (legacy path; 0 = pure cosine).
        metric: Similarity metric on the legacy path: cosine, l1, or blend.
        coverage: If True, also return greedy LS coverage_rank.
        uncovered: If True, also return uncovered_tokens (informational).
        legacy_score: If True, use the length/1000 penalty formula.
        hamming: If True (and not legacy), replace cosine in the primary score.
    """
    q_tokens = _tokenize(query)
    q_vec = _tf_vec(q_tokens)
    if not q_vec:
        if coverage or uncovered:
            out: dict = {"results": []}
            if coverage:
                out["coverage_rank"] = []
            if uncovered:
                out["uncovered_tokens"] = []
            return out
        return []
    n_query_tokens = max(len(q_tokens), 1)
    min_length = 50
    # Floor at 1.0 so typical 2–8 token queries keep the length/1000 penalty.
    # log N / log 32 grows only for long queries; cap at 2.0.
    logn_factor = min(max(math.log(max(n_query_tokens, 2)) / math.log(32), 1.0), 2.0)

    md_index = _index_skill_md()
    task_counts = _task_type_counts()
    results = []
    named_vecs: list[tuple[str, dict[str, float]]] = []
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        name = str(skill.get("name", "") or "")
        desc = str(skill.get("description", "") or "")
        body_text = str(skill.get("body_text", "") or desc)
        s_vec = _tf_vec_cached(name, body_text)
        named_vecs.append((name, s_vec))
        cosine = _cosine(q_vec, s_vec)
        l1 = _ruzicka_overlap(q_vec, s_vec)
        occam = _occam_coverage(q_tokens, set(s_vec))
        body_tokens = set(_tokenize(body_text))
        hamming_sim = _hamming_sim(set(q_tokens), body_tokens)
        if metric == "cosine":
            sim = cosine
        elif metric == "l1":
            sim = l1
        else:
            sim = 0.5 * cosine + 0.5 * l1

        raw_length = _skill_token_length(name, md_index)
        if raw_length is None:
            length = None
            occam_penalty = 0.0
        else:
            length = max(raw_length, min_length)
            length_ratio = min(length / 1000.0, 1.0)
            occam_penalty = min(length_ratio * logn_factor, 1.0)

        if name in task_counts and task_counts[name] > 0:
            n_task_types = float(task_counts[name])
        else:
            n_task_types = len(desc.split()) / 10.0
        spec = 1.0 / max(1.0, n_task_types)
        opn = _op_norm(q_vec, s_vec)
        if legacy_score:
            # Jaynes Ch.24 Occam: specific skills penalise broad priors
            score = (sim - occam_lambda * occam_penalty) * spec
        elif hamming:
            # Hamming set-similarity replaces cosine; ruzicka*occam is the tiebreaker
            score = 0.5 * hamming_sim + 0.5 * occam
        else:
            # MACKAY-1: coverage volume ratio damps Ruzicka for catch-alls
            score = 0.5 * cosine + 0.5 * l1 * occam
        results.append({
            "name": name,
            "cosine": round(cosine, 4),
            "l1_overlap": round(l1, 4),
            "metric": metric,
            "length_tokens": length,
            "occam_coverage": round(occam, 4),
            "occam_penalty": round(occam_penalty, 4),
            "specificity": round(spec, 4),
            "op_norm": round(opn, 4) if math.isfinite(opn) else None,
            "hamming_sim": round(hamming_sim, 4),
            "score": round(score, 4),
            "_ruzicka_occam": l1 * occam,
        })

    if hamming and not legacy_score:
        results.sort(key=lambda x: (-x["score"], -x["_ruzicka_occam"], x["name"]))
    else:
        results.sort(key=lambda x: (-x["score"], x["name"]))
    for row in results:
        row.pop("_ruzicka_occam", None)
    if top_k < 0:
        top_k = 0
    ranked = results[:top_k]
    if coverage or uncovered:
        out: dict = {"results": ranked}
        if coverage:
            out["coverage_rank"] = _greedy_ls_coverage(q_vec, named_vecs)
        if uncovered:
            skill_tokens: set[str] = set()
            for _, s_vec in named_vecs:
                skill_tokens.update(s_vec)
            out["uncovered_tokens"] = sorted(set(q_tokens) - skill_tokens)
        return out
    return ranked


def _extract_description(content: str) -> str:
    m = re.search(r"^description:\s*[\"'](.+?)[\"']\s*$", content, re.M)
    if m:
        return m.group(1).strip()
    m = re.search(r"^description:\s+(.+)$", content, re.M)
    if m:
        return m.group(1).strip().strip("\"'")
    return ""


def _load_skill_records() -> list[dict]:
    skills: list[dict] = []
    # Fallback: if SKILLS_DIR (derived from HERMES_HOME env) yields no skills,
    # also try the canonical ~/.hermes/skills to survive fork-profile overlayfs issues.
    candidate_dirs = [SKILLS_DIR]
    canonical = Path.home() / ".hermes" / "skills"
    if canonical != SKILLS_DIR and canonical.is_dir():
        candidate_dirs.append(canonical)
    seen: set[str] = set()
    for skills_dir in candidate_dirs:
        if not skills_dir.is_dir():
            continue
        for skill_md in skills_dir.rglob("SKILL.md"):
            if not _is_under(skills_dir, skill_md):
                continue
            key = skill_md.parent.name
            if key in seen:
                continue
            seen.add(key)
            try:
                content = skill_md.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            desc = _extract_description(content)
            skills.append({
                "name": key,
                "description": desc,
                "body_text": desc,
            })
        if skills:
            break  # stop at first dir that yields results
    return skills


def _load_named_token_sets() -> dict[str, set[str]]:
    named: dict[str, set[str]] = {}
    candidate_dirs = [SKILLS_DIR]
    canonical = Path.home() / ".hermes" / "skills"
    if canonical != SKILLS_DIR and canonical.is_dir():
        candidate_dirs.append(canonical)
    for skills_dir in candidate_dirs:
        if not skills_dir.is_dir():
            continue
        for skill_md in skills_dir.rglob("SKILL.md"):
            if not _is_under(skills_dir, skill_md):
                continue
            key = skill_md.parent.name
            if key in named:
                continue
            try:
                content = skill_md.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            named[key] = set(_tokenize(content))
        if named:
            break
    return named


def _greedy_token_cover_seq(
    skills: dict[str, set[str]],
    universe: set[str],
    k: int,
) -> tuple[list[str], int]:
    u = set(universe)
    seq: list[str] = []
    gain = 0
    for _ in range(max(k, 0)):
        best_name, best_gain = None, 0
        for name, tok_set in skills.items():
            g = len(tok_set & u)
            if g > best_gain:
                best_gain, best_name = g, name
        if best_name is None or best_gain <= 0:
            break
        u -= skills[best_name]
        seq.append(best_name)
        gain += best_gain
    return seq, gain


def cmd_dp_route(argv: list[str]) -> None:
    """DIAGNOSTIC ONLY: do not auto-load skills from this result. suggested_sequence is a token-coverage subset, not an execution order."""
    parser = argparse.ArgumentParser(prog="occam-skill-ranker.py dp-route")
    parser.add_argument("--query", required=True)
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--n-limit", type=int, default=16, dest="n_limit")
    args = parser.parse_args(argv)

    skills = _load_named_token_sets()
    query_tokens = set(_tokenize(args.query))
    k = args.k
    n_limit = args.n_limit
    memo: dict[tuple[frozenset, int], tuple[int, list[str]]] = {}
    memo_hits = 0

    def dp(u_frozen: frozenset, remaining: int) -> tuple[int, list[str]]:
        nonlocal memo_hits
        key = (u_frozen, remaining)
        if key in memo:
            memo_hits += 1
            return memo[key]
        if remaining == 0 or not u_frozen:
            return (0, [])
        best_gain, best_seq = 0, []
        for name, tok_set in skills.items():
            cover = u_frozen & tok_set
            if not cover:
                continue
            g, seq = dp(u_frozen - cover, remaining - 1)
            if len(cover) + g > best_gain:
                best_gain = len(cover) + g
                best_seq = [name] + seq
        memo[key] = (best_gain, best_seq)
        return memo[key]

    reasons: list[str] = []
    if len(skills) > n_limit:
        reasons.append("n>n_limit")
    if k > 4:
        reasons.append("k>4")
    fallback = bool(reasons)
    if fallback:
        seq, gain = _greedy_token_cover_seq(skills, query_tokens, k)
    else:
        gain, seq = dp(frozenset(query_tokens), k)

    out: dict = {
        "suggested_sequence": seq,
        "gain": int(gain),
        "memo_hits": int(memo_hits),
        "fallback": bool(fallback),
        "diagnostic_only": True,
        "method": "greedy_fallback" if fallback else "exact_dp",
    }
    if fallback:
        out["fallback_reason"] = " or ".join(reasons)
    print(json.dumps(out, indent=2))


_VALID_RANKERS = ("occam", "legacy", "hamming")
_DEFAULT_POLICY_FILE = HERMES_HOME / "cache" / "ranker-policy.json"
_DEFAULT_POLICY = {
    "default": "occam",
    "policy": {},
    "note": (
        "Per-task-type ranker policy. Valid values: occam, legacy, hamming. "
        "Edit manually or update via routing-nt --set."
    ),
}


def _load_ranker_policy(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            if "default" not in data:
                data["default"] = _DEFAULT_POLICY["default"]
            if not isinstance(data.get("policy"), dict):
                data["policy"] = {}
            if "note" not in data:
                data["note"] = _DEFAULT_POLICY["note"]
            return data
        # non-dict: fall through — do not overwrite
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_DEFAULT_POLICY, indent=2) + "\n", encoding="utf-8")
        return dict(_DEFAULT_POLICY)
    except (json.JSONDecodeError, OSError, UnicodeError):
        pass
    # Corrupt / non-dict policy: return default in memory only — do NOT write
    return dict(_DEFAULT_POLICY)


def cmd_routing_nt(argv: list[str]) -> None:
    """Per-task-type ranker policy lookup / update (routing natural transformation)."""
    parser = argparse.ArgumentParser(prog="occam-skill-ranker.py routing-nt")
    parser.add_argument("--task-type", required=True, dest="task_type")
    parser.add_argument(
        "--policy-file",
        default=str(_DEFAULT_POLICY_FILE),
        help="Policy JSON path (default ~/.hermes/cache/ranker-policy.json)",
    )
    parser.add_argument(
        "--set",
        dest="set_ranker",
        default=None,
        choices=_VALID_RANKERS,
        help="Set ranker for this task type: occam, legacy, or hamming",
    )
    args = parser.parse_args(argv)

    path = Path(args.policy_file).expanduser()
    policy = _load_ranker_policy(path)
    task_type = args.task_type

    if args.set_ranker is not None:
        policy.setdefault("policy", {})[task_type] = args.set_ranker
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "task_type": task_type,
            "ranker": args.set_ranker,
            "updated": True,
        }))
        return

    mapping = policy.get("policy") or {}
    if task_type in mapping:
        ranker = mapping[task_type]
        source = "policy"
    else:
        ranker = policy.get("default", "occam")
        source = "default"
    print(json.dumps({
        "task_type": task_type,
        "ranker": ranker,
        "source": source,
        "policy_file": str(path),
    }))


def _lp_analysis_diagnostics(ranked) -> dict:
    """ROY-1: Lp-space diagnostics on the ranked score vector.

    (1) Normalise raw scores to L1 probability measure p_k = score_k / sum(scores).
    (2) L-inf deviation from uniform: max_k |p_k - 1/N|.
    (3) KL(p || uniform) = sum_k p_k * log(p_k * N)  (bits, log2).
    Returns diagnostic fields to append alongside scores.
    """
    results_list = ranked if isinstance(ranked, list) else ranked.get("results", [])
    if not results_list:
        return {"error": "no ranked results to analyse"}

    raw_scores = [float(r.get("score", 0.0)) for r in results_list]
    total = sum(raw_scores)
    N = len(raw_scores)

    if total <= 0 or N == 0:
        return {"error": "all scores are zero or no results"}

    # (1) L1-normalised probability measure
    p = [s / total for s in raw_scores]
    uniform = 1.0 / N

    # (2) L-inf deviation from uniform
    linf_dev = max(abs(pk - uniform) for pk in p)

    # (3) KL(p || uniform) in bits
    kl_bits = sum(pk * math.log2(pk * N) for pk in p if pk > 0.0)

    return {
        "method": "ROY-1_lp_analysis",
        "N": N,
        "l1_total_score": round(total, 6),
        "uniform_baseline": round(uniform, 6),
        "linf_deviation_from_uniform": round(linf_dev, 6),
        "kl_from_uniform_bits": round(kl_bits, 6),
        "note": (
            "p_k = score_k / sum(scores). "
            "L-inf = max_k|p_k - 1/N|. "
            "KL(p||uniform) = sum p_k * log2(p_k * N). "
            "ROY-1 Royden-Fitzpatrick Lp-space diagnostics."
        ),
        "skill_probs": [
            {"name": r.get("name", ""), "p_k": round(pk, 6)}
            for r, pk in zip(results_list, p)
        ],
    }


def cmd_score(argv: list[str]) -> None:
    """score subcommand: rank skills for a query, with optional --sinkhorn flag."""
    parser = argparse.ArgumentParser(prog="occam-skill-ranker.py score")
    parser.add_argument("query", help="Query text")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument(
        "--sinkhorn", action="store_true",
        help="Use Sinkhorn OT similarity (OT-1) instead of cosine",
    )
    parser.add_argument("--sinkhorn-reg", type=float, default=0.05, dest="sinkhorn_reg",
                        help="Sinkhorn regularisation (default 0.05)")
    parser.add_argument("--skills-json", help="Path to JSON file with skills list")
    parser.add_argument(
        "--lp-analysis", action="store_true", dest="lp_analysis",
        help=(
            "ROY-1: print Routing concentration block with L1=1.0, L2, L_inf, HHI, Entropy. "
            "Normalises score vector to L1=1 probability measure."
        ),
    )
    parser.add_argument(
        "--no-smooth", action="store_true", dest="no_smooth",
        # VIL-8: raw TF mode, no smoothness assumption
        help=(
            "VIL-8: raw TF mode. TF vectors already use raw counts/total with no "
            "add-1/Laplace smoothing. This flag is accepted and noted."
        ),
    )
    parser.add_argument(
        "--slw", action="store_true", dest="slw",
        help=(
            "OT-3: Sliced Wasserstein diagnostic mode. Projects query and skill TF "
            "vectors onto K=50 random unit vectors, computes sort-based 1D W1 for each, "
            "averages. Diagnostic comparison against cosine — not a replacement."
        ),
    )
    parser.add_argument(
        "--slw-projections", type=int, default=50, dest="slw_projections",
        help="Number of random projections for --slw (default 50)",
    )
    args = parser.parse_args(argv)

    if args.skills_json:
        path = Path(args.skills_json).expanduser()
        try:
            skills = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError) as e:
            print(json.dumps({"error": f"Could not read --skills-json: {e}"}))
            sys.exit(2)
        if not isinstance(skills, list):
            print(json.dumps({"error": "--skills-json must be a JSON array"}))
            sys.exit(2)
    else:
        skills = _load_skill_records()

    q_tokens = _tokenize(args.query)
    q_vec = _tf_vec(q_tokens)

    no_smooth = getattr(args, "no_smooth", False)
    if no_smooth:
        # VIL-8: raw TF mode, no smoothness assumption
        # _tf_vec already uses raw counts/total with no add-1/Laplace smoothing;
        # this flag is accepted and noted — no code path change required.
        print("# VIL-8: Raw TF mode already default (no smoothing active)", file=sys.stderr)

    if getattr(args, "slw", False):
        # OT-3: Sliced Wasserstein diagnostic mode.
        # Project sparse TF dicts onto K random unit vectors; compute sort-based 1D W1
        # for each projection and average. Diagnostic only — BOW vectors lack the geometric
        # structure that makes random projections meaningful (Peyre-Cuturi §5.5), but the
        # comparison against cosine can surface non-obvious token-space structure.
        import numpy as _np

        K = args.slw_projections  # default 50

        def _to_dense(vec: dict[str, float], vocab: list[str]) -> "_np.ndarray":
            a = _np.zeros(len(vocab), dtype=float)
            for i, t in enumerate(vocab):
                a[i] = vec.get(t, 0.0)
            return a

        def _sliced_w1(a: "_np.ndarray", b: "_np.ndarray", k: int, rng: "_np.random.Generator") -> float:
            """Monte-Carlo Sliced W1: average 1D W1 over k random projections."""
            d = len(a)
            if d == 0:
                return 0.0
            projs = rng.standard_normal((k, d))
            projs /= (_np.linalg.norm(projs, axis=1, keepdims=True) + 1e-12)
            pa = projs @ a  # (k,)
            pb = projs @ b  # (k,)
            # 1D W1 = |sort(pa) - sort(pb)|.mean()
            return float(_np.mean(_np.abs(_np.sort(pa) - _np.sort(pb))))

        # Build shared vocabulary from all skill TF vecs + query
        all_skills_vecs = []
        all_names = []
        for skill in skills:
            if not isinstance(skill, dict):
                continue
            name = str(skill.get("name", "") or "")
            desc = str(skill.get("description", "") or "")
            body_text = str(skill.get("body_text", "") or desc)
            s_vec = _tf_vec_cached(name, body_text)
            all_skills_vecs.append((name, s_vec))
            all_names.append(name)

        all_tokens: set[str] = set(q_vec.keys())
        for _, sv in all_skills_vecs:
            all_tokens.update(sv.keys())
        vocab = sorted(all_tokens)

        rng = _np.random.default_rng(42)
        q_dense = _to_dense(q_vec, vocab)
        cosine_cache: dict[str, float] = {}

        slw_results = []
        for name, s_vec in all_skills_vecs:
            s_dense = _to_dense(s_vec, vocab)
            slw_dist = _sliced_w1(q_dense, s_dense, K, rng)
            # Also compute cosine for comparison
            cos_sim = _cosine(q_vec, s_vec)
            slw_results.append({
                "name": name,
                "slw_distance": round(slw_dist, 6),
                "cosine_similarity": round(cos_sim, 4),
                "slw_vs_cosine_delta": round(slw_dist - (1.0 - cos_sim), 6),
            })
        slw_results.sort(key=lambda x: (x["slw_distance"], -x["cosine_similarity"]))
        top_k = max(args.top, 0)
        print(json.dumps({
            "method": "sliced_wasserstein",
            "note": "OT-3 diagnostic: SlW over random projections of BOW TF vectors. "
                    "BOW has no geometric structure that makes projections statistically meaningful "
                    "(Peyre-Cuturi §5.5); use as a cross-check against cosine, not a replacement.",
            "k_projections": K,
            "vocab_size": len(vocab),
            "results": slw_results[:top_k],
        }, indent=2))
    elif args.sinkhorn:
        results = []
        for skill in skills:
            if not isinstance(skill, dict):
                continue
            name = str(skill.get("name", "") or "")
            desc = str(skill.get("description", "") or "")
            body_text = str(skill.get("body_text", "") or desc)
            s_vec = _tf_vec_cached(name, body_text)
            sim = sinkhorn_similarity(q_vec, s_vec, reg=args.sinkhorn_reg)
            results.append({"name": name, "sinkhorn_similarity": round(sim, 4)})
        results.sort(key=lambda x: (-x["sinkhorn_similarity"], x["name"]))
        top_k = max(args.top, 0)
        print(json.dumps({
            "method": "sinkhorn_ot",
            "reg": args.sinkhorn_reg,
            "results": results[:top_k],
            "cache_hits": _tf_cache_hits,
            "cache_misses": _tf_cache_misses,
        }, indent=2))
    else:
        ranked = rank_skills_occam(args.query, skills, top_k=args.top)
        payload = _cache_payload(ranked)
        if args.lp_analysis:
            payload["lp_analysis"] = _lp_analysis_diagnostics(ranked)
            # ROY-1: print human-readable Routing concentration block
            results_list = ranked if isinstance(ranked, list) else ranked.get("results", [])
            raw_scores = [float(r.get("score", 0.0)) for r in results_list]
            total_s = sum(raw_scores)
            if total_s > 0 and len(raw_scores) > 0:
                p = [s / total_s for s in raw_scores]
                N = len(p)
                l2 = math.sqrt(sum(pk * pk for pk in p))
                linf = max(p)
                hhi = sum(pk * pk for pk in p)
                entropy = -sum(pk * math.log(pk + 1e-12) for pk in p)
                print("\nRouting concentration (Royden Lp norms):")
                print(f"  L1  = 1.0  (normalised)")
                print(f"  L2  = {l2:.6f}")
                print(f"  L∞  = {linf:.6f}")
                print(f"  HHI = {hhi:.6f}  (sum p_i^2; high → over-concentrated routing)")
                print(f"  H   = {entropy:.6f}  (entropy -sum p_i*log(p_i); low → concentrated)")
        print(json.dumps(payload, indent=2))


def _cache_payload(ranked) -> dict:
    if isinstance(ranked, list):
        payload: dict = {"results": ranked}
    else:
        payload = dict(ranked)
    payload["cache_hits"] = _tf_cache_hits
    payload["cache_misses"] = _tf_cache_misses
    return payload


def cmd_mdl_dedup(argv: list[str]) -> None:
    """Kolmogorov MDL skill deduplication via zlib compression lengths.

    Li and Vitanyi 2008 Ch 5, MDL principle:
      DL(A|B) ≈ len(compress(B+A)) - len(compress(B))
      Merge decision: compare DL(A) + DL(A|B) vs DL(B) + DL(B|A)
      If DL(A) + DL(A|B) < DL(B) + DL(B|A): A subsumes B (B redundant)
      If DL(B) + DL(B|A) < DL(A) + DL(A|B): B subsumes A (A redundant)
      Otherwise: INDEPENDENT
    """
    import zlib
    parser = argparse.ArgumentParser(prog="occam-skill-ranker.py mdl-dedup")
    parser.add_argument("--skill-a", required=True, dest="skill_a", help="Path to first skill file")
    parser.add_argument("--skill-b", required=True, dest="skill_b", help="Path to second skill file")
    args = parser.parse_args(argv)

    path_a = Path(args.skill_a).expanduser()
    path_b = Path(args.skill_b).expanduser()

    try:
        text_a = path_a.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        print(json.dumps({"error": f"Cannot read --skill-a: {e}"}))
        return
    try:
        text_b = path_b.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        print(json.dumps({"error": f"Cannot read --skill-b: {e}"}))
        return

    dl_a = len(zlib.compress(text_a.encode()))
    dl_b = len(zlib.compress(text_b.encode()))
    dl_a_given_b = len(zlib.compress((text_b + text_a).encode())) - dl_b
    dl_b_given_a = len(zlib.compress((text_a + text_b).encode())) - dl_a

    cost_a_subsumes = dl_a + dl_a_given_b   # cost to describe B via A
    cost_b_subsumes = dl_b + dl_b_given_a   # cost to describe A via B

    if cost_a_subsumes < cost_b_subsumes:
        recommendation = "MERGE: A subsumes B"
        verdict = "A_SUBSUMES_B"
    elif cost_b_subsumes < cost_a_subsumes:
        recommendation = "MERGE: B subsumes A"
        verdict = "B_SUBSUMES_A"
    else:
        recommendation = "INDEPENDENT: skills are complementary"
        verdict = "INDEPENDENT"

    print(json.dumps({
        "skill_a": str(path_a),
        "skill_b": str(path_b),
        "dl_a": dl_a,
        "dl_b": dl_b,
        "dl_a_given_b": dl_a_given_b,
        "dl_b_given_a": dl_b_given_a,
        "cost_a_subsumes_b": cost_a_subsumes,
        "cost_b_subsumes_a": cost_b_subsumes,
        "verdict": verdict,
        "recommendation": recommendation,
        "note": "Li and Vitanyi 2008 Ch 5, MDL principle — lower description length = better compression = subsumption",
    }, indent=2))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "dp-route":
        cmd_dp_route(sys.argv[2:])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "routing-nt":
        cmd_routing_nt(sys.argv[2:])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "mdl-dedup":
        cmd_mdl_dedup(sys.argv[2:])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "score":
        cmd_score(sys.argv[2:])
        return

    argv = sys.argv[1:]
    if argv and argv[0] == "rank":
        argv = argv[1:]

    parser = argparse.ArgumentParser(description="Occam-weighted skill ranker (coverage Occam)")
    parser.add_argument("query", nargs="?", default=None, help="Query text")
    parser.add_argument("--query", dest="query_flag", default=None, help="Query text (rank subcommand)")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--lambda", dest="lam", type=float, default=0.25,
                        help="Occam penalty weight (legacy path; default 0.25)")
    parser.add_argument(
        "--legacy-score", action="store_true",
        help="Use length/1000 penalty scoring instead of coverage Occam",
    )
    parser.add_argument(
        "--metric", choices=("cosine", "l1", "blend"), default="blend",
        help="Similarity metric (default blend = 0.5*cosine + 0.5*Ruzicka). l1 uses Ruzicka overlap, not L1 norm.",
    )
    parser.add_argument(
        "--coverage", action="store_true",
        help="Append greedy LS coverage_rank of the query residual",
    )
    parser.add_argument(
        "--uncovered", action="store_true",
        help="Emit uncovered_tokens: query tokens that appear in no skill token set",
    )
    parser.add_argument(
        "--hamming", action="store_true",
        help="Replace cosine in primary score with set Hamming similarity (diagnostic)",
    )
    parser.add_argument(
        "--ranker", choices=["occam", "legacy", "hamming"], default="occam",
        help="Ranker mode: occam (default), legacy (--legacy-score), hamming (--hamming)",
    )
    parser.add_argument(
        "--skill", default=None,
        help="Optional skill name (accepted for routing-nt passthrough; does not filter ranking)",
    )
    parser.add_argument("--skills-json", help="Path to JSON file with skills list")
    args = parser.parse_args(argv)
    if args.ranker == "legacy":
        args.legacy_score = True
    elif args.ranker == "hamming":
        args.hamming = True
    # 'occam' is default, no flag needed
    query = args.query_flag or args.query
    if not query:
        parser.error("query is required (positional or --query)")

    if args.skills_json:
        path = Path(args.skills_json)
        try:
            skills = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError) as e:
            print(json.dumps({"error": f"Could not read --skills-json: {e}"}))
            sys.exit(2)
        if not isinstance(skills, list):
            print(json.dumps({"error": "--skills-json must be a JSON array"}))
            sys.exit(2)
        for skill in skills:
            if isinstance(skill, dict):
                if "body_text" not in skill:
                    skill["body_text"] = str(skill.get("description", "") or "")
    else:
        skills = _load_skill_records()

    ranked = rank_skills_occam(
        query, skills, top_k=args.top, occam_lambda=args.lam,
        metric=args.metric, coverage=args.coverage, uncovered=args.uncovered,
        legacy_score=args.legacy_score, hamming=args.hamming,
    )
    print(json.dumps(_cache_payload(ranked), indent=2))


if __name__ == "__main__":
    main()
