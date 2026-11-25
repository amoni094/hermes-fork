#!/usr/bin/env python3
"""Corpus-mined signals for 6-tier model routing (stdlib only).

Theory sources
--------------
- Shalev / Hoeffding: PAC confidence bound 1 - sqrt(log(1/delta)/(2n))
- Lattimore EXP4 / LinUCB: contextual arm weights over TIERS (not skills)
- Cover-Thomas Fano: error floor from I(X;Y) on the 6-tier audit
- Manning BM25 / McDiarmid: leave-one-out retrieval hint vs labelled queries
- Precup IPS: off-policy estimate of rule-set accuracy
- Hamming: week-over-week classifier drift
- Harchol-Balter M/G/1: load-aware shed of borderline reason → fast
- Dean-Boddy / Zilberstein: anytime routing stub (default off)

Fail-closed: never downgrade reason/elite to fast. Missing files/DB → no-op.
Does NOT touch DEFAULT_TIER_MODELS / reason-tier model assignment.
"""
from __future__ import annotations

import os
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    cur = p
    for _ in range(4):
        if (cur / "hermes-scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return p


_hermes_base = _hermes_home()
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

import json
import math
import re
import sys
from collections import Counter
from typing import Any

TIERS = ("fast", "math", "longctx", "tooluse", "reason", "elite")
_TIER_STRICTNESS = {
    "fast": 0,
    "math": 1,
    "longctx": 2,
    "tooluse": 3,
    "reason": 4,
    "elite": 5,
}
# Conservative Fano floor: only catch near-zero confidence, not PAC 0.84
# (applying 0.84 live would force almost all fast/math into reason).
FANO_CONFIDENCE_FLOOR = 0.10
PAC_DEFAULT_N = 60
PAC_DEFAULT_DELTA = 0.05
BM25_K1 = 1.2
BM25_B = 0.75
BM25_SIM_THRESH = 0.6
ONLINE_WEIGHT_MULT = 2.0
QUEUE_SHED_THRESHOLD = 8
TOKEN_RE = re.compile(r"[a-z0-9]+")


def _cache_dir() -> Path:
    override = os.environ.get("HERMES_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, FileNotFoundError, json.JSONDecodeError, TypeError):
        return default


def _atomic_write_json(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(path))
    except Exception:
        try:
            tmp = path.with_suffix(path.suffix + ".tmp")
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def pac_confidence_bound(n: int, delta: float = PAC_DEFAULT_DELTA) -> float:
    """Hoeffding lower bound on accuracy when empirical error is 0.

    threshold = 1 - sqrt(log(1/delta) / (2n)). n=60, delta=0.05 → ~0.842.
    This is a *classifier-level* bound, not a per-rule confidence rewrite:
    individual rules fire on << n samples, so live constants stay empirical.
    """
    try:
        nn = int(n)
        dd = float(delta)
    except (TypeError, ValueError):
        return 0.65
    if nn <= 0 or dd <= 0.0 or dd >= 1.0:
        return 0.65
    return max(0.0, min(1.0, 1.0 - math.sqrt(math.log(1.0 / dd) / (2.0 * nn))))


# Empirically assigned rule confidences (must stay in sync with classifier).
RULE_CONFIDENCES = {
    "adversarial_critical_skill": 0.98,
    "critical_skill_name": 0.98,
    "security_query": 0.90,
    "architecture_query": 0.85,
    "adversarial_audit_query": 0.95,
    "adversarial_skill": 0.95,
    "adversarial_skill_name": 0.95,
    "tool_format_error": 0.90,
    "reason_escalation": 0.95,
    "prev_error_recovery": 0.90,
    "very_large_context": 0.90,
    "longctx_skill": 0.85,
    "large_file_read": 0.80,
    "tool_schema_query": 0.80,
    "tooluse_skill": 0.85,
    "math_query": 0.85,
    "math_skill": 0.90,
    "large_context": 0.85,
    "reasoning_query": 0.85,
    "complex_question": 0.70,
    "comparison_query": 0.80,
    "hedge_query": 0.80,
    "implicit_question": 0.75,
    "research_recall": 0.80,
    "implicit_continuation": 0.75,
    "syntactic_complexity": 0.75,
    "named_entity_density": 0.75,
    "fast_whitelist": 0.90,
    "procedure_skill": 0.80,
    "mechanical_continuation": 0.75,
    "homelab_mechanical": 0.78,
    "short_correction": 0.78,
    "fast_thread_imperative": 0.72,
    "continuation_bias": 0.65,
    "short_simple_query": 0.70,
    "default_safe": 0.60,
}


def calibration_check(n: int = PAC_DEFAULT_N, delta: float = PAC_DEFAULT_DELTA) -> dict:
    """Report which rule confidences sit below the PAC bound for audit size n."""
    bound = pac_confidence_bound(n, delta)
    below = sorted(
        k for k, v in RULE_CONFIDENCES.items() if float(v) + 1e-12 < bound
    )
    return {
        "n": int(n),
        "delta": float(delta),
        "pac_bound": bound,
        "n_rules": len(RULE_CONFIDENCES),
        "n_below_bound": len(below),
        "below_bound": below,
        "note": (
            "PAC bound is classifier-level (n=audit). Do not rewrite live "
            "rule constants to the bound — that would collapse fast routing."
        ),
    }


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


def bm25_scores(query: str, docs: list[str]) -> list[float]:
    """BM25 scores of query against docs. Empty query → all zeros."""
    q_toks = _tokenize(query)
    if not q_toks or not docs:
        return [0.0] * len(docs)
    tokenized = [_tokenize(d) for d in docs]
    n_docs = len(tokenized)
    avgdl = sum(len(t) for t in tokenized) / max(1, n_docs)
    df: Counter[str] = Counter()
    for toks in tokenized:
        df.update(set(toks))
    q_tf = Counter(q_toks)
    idf = {}
    for term in q_tf:
        n_t = df.get(term, 0)
        idf[term] = math.log(1.0 + (n_docs - n_t + 0.5) / (n_t + 0.5))
    scores = []
    for toks in tokenized:
        tf = Counter(toks)
        dl = len(toks) or 1
        s = 0.0
        for term, qf in q_tf.items():
            f = tf.get(term, 0)
            if f <= 0:
                continue
            denom = f + BM25_K1 * (1.0 - BM25_B + BM25_B * dl / max(avgdl, 1e-9))
            s += idf[term] * (f * (BM25_K1 + 1.0) / denom) * qf
        scores.append(s)
    return scores


def _normalize_bm25(scores: list[float]) -> list[float]:
    mx = max(scores) if scores else 0.0
    if mx <= 0.0:
        return [0.0] * len(scores)
    return [s / mx for s in scores]


def retrieval_hint(
    query: str,
    labelled: list[tuple[str, str]],
    k: int = 3,
    sim_thresh: float = BM25_SIM_THRESH,
) -> dict:
    """Leave-one-out BM25: if top-k labelled neighbours agree, return that tier.

    labelled: list of (query, gold_tier). Exact query string is excluded.
    """
    empty = {
        "tier": None,
        "agree": False,
        "n_neighbors": 0,
        "mean_sim": 0.0,
        "neighbors": [],
    }
    q = (query or "").strip()
    if not q or not labelled:
        return empty
    docs = []
    labels = []
    for rec in labelled:
        if not rec:
            continue
        dq = str(rec[0] or "")
        lab = str(rec[1] or "").strip().lower()
        if not dq or lab not in _TIER_STRICTNESS:
            continue
        if dq.strip() == q:
            continue
        docs.append(dq)
        labels.append(lab)
    if not docs:
        return empty
    raw = bm25_scores(q, docs)
    norm = _normalize_bm25(raw)
    ranked = sorted(range(len(docs)), key=lambda i: norm[i], reverse=True)
    top = ranked[: max(1, int(k))]
    picked = [(labels[i], norm[i], docs[i][:80]) for i in top if norm[i] > 0]
    if len(picked) < k:
        return {**empty, "n_neighbors": len(picked), "neighbors": picked}
    if any(s < sim_thresh for _lab, s, _d in picked):
        return {
            "tier": None,
            "agree": False,
            "n_neighbors": len(picked),
            "mean_sim": sum(s for _l, s, _d in picked) / len(picked),
            "neighbors": picked,
        }
    tiers = [lab for lab, _s, _d in picked]
    agree = len(set(tiers)) == 1
    return {
        "tier": tiers[0] if agree else None,
        "agree": agree,
        "n_neighbors": len(picked),
        "mean_sim": sum(s for _l, s, _d in picked) / len(picked),
        "neighbors": picked,
    }


def query_feature_vector(payload: dict | None) -> list[float]:
    """7-d vector matching the task spec (clipped to [0, 1] extras allowed)."""
    data = payload or {}
    q = str(data.get("query") or "")
    words = q.split()
    n_words = len(words)
    has_question = 1.0 if ("?" in q or bool(re.search(r"^(who|what|why|how|when|where|is|are|do|does|did)\b", q.strip(), re.IGNORECASE))) else 0.0
    has_code = 1.0 if ("```" in q or bool(re.search(r"^\s*(def |class |import |from )", q))) else 0.0
    try:
        turn = max(0, int(data.get("turn_index") or 0))
    except (TypeError, ValueError):
        turn = 0
    prior = str(data.get("prior_tier") or data.get("prev_tier") or "").strip().lower()
    prior_fast = 1.0 if prior == "fast" else 0.0
    prior_reason = 1.0 if prior == "reason" else 0.0
    # cheap complexity: clauses + questions + length
    complexity = min(5.0, (q.count(",") + q.count(";") + q.count("?") + n_words / 8.0))
    return [
        min(1.0, n_words / 50.0),
        has_question,
        has_code,
        min(1.0, turn / 10.0),
        prior_fast,
        prior_reason,
        min(1.0, complexity / 5.0),
    ]


def online_tier_hint(payload: dict | None) -> dict:
    """Look up EXP4/LinUCB-style tier weights. Cold start → no hint.

    Existing routing-exp4-state.json is *skill* weights; this reads
    cache/routing-tier-online.json which maps tier -> weight. Absent file
    is a no-op (expected until the online learner is trained on tiers).
    """
    empty = {"tier": None, "weight": 0.0, "uniform": 1.0 / len(TIERS), "strong": False}
    path = _cache_dir() / "routing-tier-online.json"
    state = _load_json(path, None)
    if not isinstance(state, dict):
        return empty
    raw_w = state.get("weights")
    weights: dict[str, Any] = raw_w if isinstance(raw_w, dict) else state
    w = []
    for t in TIERS:
        try:
            w.append(max(0.0, float(weights.get(t, 0.0) or 0.0)))
        except (TypeError, ValueError):
            w.append(0.0)
    total = sum(w)
    if total <= 0.0:
        return empty
    uniform = 1.0 / len(TIERS)
    best_i = max(range(len(TIERS)), key=lambda i: w[i])
    p = w[best_i] / total
    return {
        "tier": TIERS[best_i],
        "weight": p,
        "uniform": uniform,
        "strong": p > ONLINE_WEIGHT_MULT * uniform,
        "features": query_feature_vector(payload),
    }


def fano_error_floor(n_classes: int = 6, mi_bits: float | None = None) -> float:
    """Fano: H(Y|X) <= h(Pe) + Pe log(|Y|-1). Lower-bound Pe given I(X;Y).

    Without a fitted MI we use a conservative floor (FANO_CONFIDENCE_FLOOR)
    so under-confident decisions escalate, not the PAC 0.84 rewrite.
    """
    cached = _load_json(_cache_dir() / "routing-tier-fano.json", None)
    if isinstance(cached, dict):
        try:
            v = float(cached.get("fano_floor") or cached.get("pe_bound") or 0.0)
            if 0.0 < v < 0.5:
                return v
        except (TypeError, ValueError):
            pass
    if mi_bits is None:
        return FANO_CONFIDENCE_FLOOR
    # |Y|=n_classes, H(Y) <= log2(n). H(Y|X)=H(Y)-I. Invert Fano loosely:
    # Pe >= (H(Y|X) - 1) / log(|Y|-1)  (Cover-Thomas).
    hy = math.log2(max(2, n_classes))
    hyx = max(0.0, hy - float(mi_bits))
    denom = math.log2(max(2, n_classes - 1))
    pe = max(0.0, (hyx - 1.0) / denom) if denom else 0.0
    return max(FANO_CONFIDENCE_FLOOR, min(0.49, pe))


def ips_accuracy(golds: list[str], preds: list[str], log_probs: list[float] | None = None) -> dict:
    """IPS off-policy accuracy. Deterministic logging policy → p_log=1 for pred.

    For a deterministic classifier IPS collapses to ordinary accuracy; still
    useful as the OPE hook when a new labelled example is appended.
    """
    n = min(len(golds), len(preds))
    if n <= 0:
        return {"n": 0, "ips_hat": 0.0, "n_clipped": 0}
    clipped = 0
    acc = 0.0
    for i in range(n):
        p = 1.0
        if log_probs is not None and i < len(log_probs):
            try:
                p = float(log_probs[i])
            except (TypeError, ValueError):
                p = 1.0
        if p <= 1e-6:
            clipped += 1
            p = 1e-6
        reward = 1.0 if str(golds[i]).lower() == str(preds[i]).lower() else 0.0
        acc += reward / p
    return {"n": n, "ips_hat": acc / n, "n_clipped": clipped}


def hamming_drift(prev: dict[str, str], curr: dict[str, str]) -> dict:
    """Fraction of shared queries whose predicted tier changed."""
    keys = sorted(set(prev) & set(curr))
    if not keys:
        return {"n_shared": 0, "n_changed": 0, "frac": 0.0, "alarm": False, "changed": []}
    changed = [k for k in keys if str(prev[k]).lower() != str(curr[k]).lower()]
    frac = len(changed) / len(keys)
    return {
        "n_shared": len(keys),
        "n_changed": len(changed),
        "frac": frac,
        "alarm": frac > 0.10,
        "changed": changed[:20],
    }


def mg1_wait(lambda_rate: float, mu_rate: float, cv2: float = 1.0) -> float:
    """M/G/1 mean wait (Pollaczek-Khinchine). rho=lambda/mu. cv2=Var(S)/E[S]^2."""
    if mu_rate <= 0 or lambda_rate < 0:
        return 0.0
    rho = lambda_rate / mu_rate
    if rho >= 1.0:
        return float("inf")
    if rho <= 0.0:
        return 0.0
    return (lambda_rate * (1.0 + cv2)) / (2.0 * mu_rate * mu_rate * (1.0 - rho))


def queue_depth_estimate(n_reason_inflight: int | None = None) -> dict:
    """Lightweight reason-tier load estimate. Missing DB → zeros, no throw."""
    cached = _load_json(_cache_dir() / "routing-queue-depth.json", {})
    if not isinstance(cached, dict):
        cached = {}
    if n_reason_inflight is not None:
        try:
            depth = max(0, int(n_reason_inflight))
        except (TypeError, ValueError):
            depth = 0
        cached["depth"] = depth
        _atomic_write_json(_cache_dir() / "routing-queue-depth.json", cached)
    try:
        depth = int(cached.get("depth") or 0)
    except (TypeError, ValueError):
        depth = 0
    try:
        lam = float(cached.get("lambda") or 0.0)
        mu = float(cached.get("mu") or 0.2)  # ~5s reason calls
    except (TypeError, ValueError):
        lam, mu = 0.0, 0.2
    wait = mg1_wait(lam, mu, cv2=1.0)
    return {
        "depth": depth,
        "lambda": lam,
        "mu": mu,
        "wait_s": wait if wait != float("inf") else 1e9,
        "shed": depth > QUEUE_SHED_THRESHOLD,
    }


def maybe_shed_reason_load(classification: dict, queue: dict | None = None) -> dict:
    """If reason-tier queue is deep, send borderline reason → fast with orch armed.

    Gated by HERMES_ROUTING_LOAD_AWARE=1 (default off so tests stay stable).
    Only conf in [0.60, 0.70] and reason not in {prev_error, elite, security}.
    Auto-escalation: caller should keep should_orchestrate True (conf < 0.7).
    """
    if os.environ.get("HERMES_ROUTING_LOAD_AWARE", "").strip() != "1":
        return classification
    if not isinstance(classification, dict):
        return classification
    tier = str(classification.get("tier") or "").strip().lower()
    reason = str(classification.get("reason") or "")
    try:
        conf = float(classification.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    if tier != "reason":
        return classification
    if reason in {"prev_error_recovery", "reason_escalation", "adversarial_skill",
                  "adversarial_skill_name", "adversarial_critical_skill"}:
        return classification
    if not (0.60 <= conf <= 0.70):
        return classification
    q = queue if isinstance(queue, dict) else queue_depth_estimate()
    if not q.get("shed"):
        return classification
    out = dict(classification)
    out["tier"] = "fast"
    out["reason"] = "load_shed_borderline"
    out["shed_from"] = "reason"
    # keep confidence so orchestrator still verifies (conf < 0.7)
    return out


def anytime_enabled(payload: dict | None = None) -> bool:
    """Dean-Boddy/Zilberstein stub. Default off.

    TODO: when routing_mode=anytime, start fast immediately and cancel if a
    reason signal fires within 2s. Not wired live — would need async cancel
    of in-flight provider calls (high complexity).
    """
    if os.environ.get("HERMES_ROUTING_MODE", "").strip().lower() == "anytime":
        return True
    data = payload or {}
    return str(data.get("routing_mode") or "").strip().lower() == "anytime"


def apply_signals(decision: dict, payload: dict | None = None, labelled: list | None = None) -> dict:
    """Fail-closed post-process. Never demotes reason/elite → fast/math."""
    if not isinstance(decision, dict):
        return decision
    out = dict(decision)
    try:
        tier = str(out.get("tier") or "reason").strip().lower()
        if tier == "slow":
            tier = "reason"
        try:
            conf = float(out.get("confidence") or 0.0)
        except (TypeError, ValueError):
            conf = 0.0
        reason = str(out.get("reason") or "")
        q = str((payload or {}).get("query") or "")

        floor = fano_error_floor()
        if conf < floor and tier not in {"reason", "elite"}:
            out["tier"] = "reason"
            out["reason"] = "fano_floor"
            out["original_tier"] = tier
            out["confidence"] = conf
            tier = "reason"

        hint = retrieval_hint(q, labelled or [])
        if hint.get("agree") and hint.get("tier"):
            ht = hint["tier"]
            if ht == tier:
                out["confidence"] = min(0.99, conf + 0.05)
                out["bm25_boost"] = True
            elif _TIER_STRICTNESS.get(ht, 0) > _TIER_STRICTNESS.get(tier, 0) and conf < 0.70:
                # escalate-only, never demote
                if tier not in {"reason", "elite"} or ht == "elite":
                    out["tier"] = ht
                    out["reason"] = "bm25_escalate"
                    out["original_tier"] = tier

        online = online_tier_hint(payload)
        if online.get("strong") and online.get("tier"):
            ot = online["tier"]
            if ot == out.get("tier"):
                try:
                    c2 = float(out.get("confidence") or 0.0)
                except (TypeError, ValueError):
                    c2 = conf
                out["confidence"] = min(0.99, c2 + 0.10)
                out["online_boost"] = True
            # different arm: ignore unless we would escalate, never demote
            elif (
                _TIER_STRICTNESS.get(ot, 0) > _TIER_STRICTNESS.get(str(out.get("tier")), 0)
                and str(out.get("tier")) not in {"reason", "elite"}
            ):
                out["online_hint"] = ot

        if anytime_enabled(payload):
            out["routing_mode"] = "anytime"

        # empty-query calibration pin: never let boosts move P6
        if not q.strip() and reason == "default_safe":
            out["tier"] = "reason"
            out["reason"] = "default_safe"
            out["confidence"] = 0.60
        return out
    except Exception:
        return decision


def write_queue_metric(depth: int) -> None:
    est = queue_depth_estimate(n_reason_inflight=depth)
    try:
        spec_path = _hermes_base / "hermes-scripts" / "routing-metrics-db.py"
        if not spec_path.is_file():
            return
        import importlib.util

        spec = importlib.util.spec_from_file_location("routing_metrics_db", spec_path)
        if spec is None or spec.loader is None:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.write_metric("queue_depth", est, source="routing-tier-signals")
    except Exception:
        return


def self_test() -> int:
    failures: list[str] = []

    def _check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    bound = pac_confidence_bound(60, 0.05)
    _check(0.83 < bound < 0.86, f"PAC n=60 bound ~0.84 got {bound}")
    _check(pac_confidence_bound(0) == 0.65, "PAC n=0 fallback")
    cal = calibration_check(60, 0.05)
    _check(cal["n_below_bound"] >= 1, "some rules below PAC bound")
    _check("default_safe" in cal["below_bound"], "default_safe below PAC")

    docs = ["fix cron sandbox error", "recursive adversarial pass", "sum of squares"]
    sc = bm25_scores("fix cron sandbox", docs)
    _check(sc[0] > sc[1] and sc[0] > sc[2], "BM25 ranks cron above adversarial")

    labelled = [
        ("fix all crons with sandbox errors", "fast"),
        ("did all cron jobs run overnight", "fast"),
        ("fix the acp retreive tool error", "fast"),
        ("do a recursive adversarial pass and wiring audit", "elite"),
        ("fix all gaps and then do a recursive adversarial pass and wiring audit", "elite"),
        ("wire relay_compaction and activate the HHR branch", "reason"),
    ]
    h = retrieval_hint("fix crons with sandbox errors tonight", labelled, k=3, sim_thresh=0.3)
    _check(h["n_neighbors"] == 3, "retrieval returns 3 neighbors")

    fv = query_feature_vector({"query": "hello?", "turn_index": 5, "prior_tier": "reason"})
    _check(len(fv) == 7, "feature vector dim 7")
    _check(fv[1] == 1.0, "has_question")
    _check(fv[5] == 1.0, "prior_reason")

    online = online_tier_hint({"query": "x"})
    _check(online["tier"] is None or online["tier"] in TIERS, "online cold-start ok")

    floor = fano_error_floor()
    _check(0.0 < floor < 0.5, f"fano floor in (0,0.5) got {floor}")

    ips = ips_accuracy(["fast", "reason"], ["fast", "elite"])
    _check(abs(ips["ips_hat"] - 0.5) < 1e-9, "IPS deterministic = accuracy")

    hd = hamming_drift({"a": "fast", "b": "reason"}, {"a": "reason", "b": "reason"})
    _check(hd["n_changed"] == 1 and hd["frac"] == 0.5 and hd["alarm"] is True, "hamming 50%")
    hd2 = hamming_drift({"a": "fast"}, {"a": "fast"})
    _check(hd2["alarm"] is False, "hamming 0% no alarm")

    _check(mg1_wait(0.1, 0.2) > 0, "M/G/1 wait positive")
    _check(mg1_wait(0.3, 0.2) == float("inf"), "rho>1 infinite wait")

    qe = queue_depth_estimate(n_reason_inflight=0)
    _check(qe["depth"] == 0, "queue depth 0")
    qe = queue_depth_estimate(n_reason_inflight=9)
    _check(qe["shed"] is True, "depth 9 sheds")

    d = {"tier": "reason", "reason": "default_safe", "confidence": 0.65}
    os.environ.pop("HERMES_ROUTING_LOAD_AWARE", None)
    _check(maybe_shed_reason_load(d, {"shed": True})["tier"] == "reason", "shed gated off")
    os.environ["HERMES_ROUTING_LOAD_AWARE"] = "1"
    shed = maybe_shed_reason_load(d, {"shed": True})
    _check(shed["tier"] == "fast" and shed["reason"] == "load_shed_borderline", "shed on")
    os.environ.pop("HERMES_ROUTING_LOAD_AWARE", None)
    blocked = maybe_shed_reason_load(
        {"tier": "reason", "reason": "prev_error_recovery", "confidence": 0.65},
        {"shed": True},
    )
    _check(blocked["tier"] == "reason", "error recovery never shed")

    applied = apply_signals(
        {"tier": "fast", "reason": "short_simple_query", "confidence": 0.70},
        {"query": "hello"},
        labelled=[],
    )
    _check(applied["tier"] == "fast", "apply_signals preserves fast")
    empty = apply_signals(
        {"tier": "reason", "reason": "default_safe", "confidence": 0.60},
        {"query": ""},
        labelled=labelled,
    )
    _check(empty["confidence"] == 0.60 and empty["reason"] == "default_safe", "P6 pin")

    # fail-closed: BM25 must not demote elite
    elite = apply_signals(
        {"tier": "elite", "reason": "security_query", "confidence": 0.90},
        {"query": "fix all crons with sandbox errors"},
        labelled=labelled,
    )
    _check(elite["tier"] == "elite", "never demote elite")

    _check(anytime_enabled({}) is False, "anytime default off")
    _check(anytime_enabled({"routing_mode": "anytime"}) is True, "anytime payload")

    if failures:
        print("SELF-TEST FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    print("SELF-TEST PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--self-test" in args:
        return self_test()
    if "--calibration-check" in args:
        print(json.dumps(calibration_check(), indent=2))
        return 0
    if "--queue-update" in args:
        depth = 0
        for i, a in enumerate(args):
            if a == "--depth" and i + 1 < len(args):
                try:
                    depth = int(args[i + 1])
                except ValueError:
                    depth = 0
        write_queue_metric(depth)
        print(json.dumps(queue_depth_estimate(), indent=2))
        return 0
    print("Usage: routing-tier-signals.py --self-test|--calibration-check|--queue-update [--depth N]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
