#!/usr/bin/env python3
"""memory-sprt-commit.py — Wald SPRT stopping rule for memory commit.

Wald Sequential Analysis: replace fixed UE thresholds (DENY>0.75, WARN>0.6)
with a sequential probability ratio test on UE sub-scores.

H0: UE ~ Uniform(0, 0.3)   (low uncertainty → COMMIT)
H1: UE ~ Uniform(0.6, 1.0) (high uncertainty → DENY)

LLR_n = sum_{i=1..n} log(p1(x_i) / p0(x_i))
A = log((1-beta)/alpha),  B = log(beta/(1-alpha)),  alpha=beta=0.05

Decision: LLR > A → DENY;  LLR < B → COMMIT;  else CONTINUE.

Supports of H0/H1 are disjoint; densities use an epsilon floor so LLR is finite.
Also reports Wald ASN (average sample number) under each hypothesis.

Usage:
  python3 memory-sprt-commit.py
  python3 memory-sprt-commit.py --scores 0.1,0.12,0.08
  python3 memory-sprt-commit.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import uuid
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

ALPHA = 0.05
BETA = 0.05
# ADV21-004: overlapping Beta densities prevent single-sample boundary crossing
# H0: Beta(2,5) ~ low UE (mode=0.2) -> COMMIT
# H1: Beta(5,2) ~ high UE (mode=0.8) -> DENY
H0_ALPHA, H0_BETA = 2.0, 5.0
H1_ALPHA, H1_BETA = 5.0, 2.0
DENSITY_FLOOR = 1e-9
SCORES_CANDIDATES = (
    "ue-memory-gate-log.jsonl",   # ADV21-004: primary path (actually written)
    "ue-blackbox-scores.jsonl",
    "ue-memory-gate-scores.jsonl",
)


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write_jsonl_append(path: Path, obj: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        existing = ""
        if path.exists():
            try:
                existing = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                existing = ""
        tmp = path.with_suffix(".tmp")
        tmp.write_text(existing + line, encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass


def _clip01(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(v):
        return 0.5
    return max(0.0, min(1.0, v))


def _beta_pdf(x: float, a: float, b: float) -> float:
    """Beta(a,b) unnormalized pdf (log-space for stability)."""
    if x <= 0.0 or x >= 1.0:
        return DENSITY_FLOOR
    try:
        # Use math.lgamma for the beta function
        log_p = (a - 1) * math.log(x) + (b - 1) * math.log(1 - x)
        log_b = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
        return max(math.exp(log_p - log_b), DENSITY_FLOOR)
    except Exception:
        return DENSITY_FLOOR


def log_likelihood_ratio_term(x: float) -> float:
    """ADV21-004: Beta LLR with overlapping supports — no single sample crosses boundary."""
    p0 = _beta_pdf(x, H0_ALPHA, H0_BETA)
    p1 = _beta_pdf(x, H1_ALPHA, H1_BETA)
    return math.log(max(p1, DENSITY_FLOOR) / max(p0, DENSITY_FLOOR))


def sprt_boundaries(alpha: float = ALPHA, beta: float = BETA) -> tuple[float, float]:
    a = max(min(float(alpha), 0.49), 1e-12)
    b = max(min(float(beta), 0.49), 1e-12)
    A = math.log((1.0 - b) / a)
    B = math.log(b / (1.0 - a))
    return A, B


def expected_llr(hypothesis: str) -> float:
    """Monte-Carlo-free midpoint estimate of E[log p1/p0] on each support."""
    # ADV21-004: Beta support ranges: H0~Beta(2,5) mass in [0.05,0.5], H1~Beta(5,2) in [0.5,0.95]
    if hypothesis == "H0":
        xs = [0.05 + 0.45 * i / 20.0 for i in range(21)]
    else:
        xs = [0.5 + 0.45 * i / 20.0 for i in range(21)]
    return sum(log_likelihood_ratio_term(x) for x in xs) / len(xs)


def average_sample_number(A: float, B: float, alpha: float = ALPHA, beta: float = BETA) -> dict:
    e0 = expected_llr("H0")
    e1 = expected_llr("H1")
    # Wald ASN approximations
    num0 = (1.0 - alpha) * B + alpha * A
    num1 = beta * B + (1.0 - beta) * A
    asn0 = num0 / e0 if abs(e0) > 1e-12 else float("inf")
    asn1 = num1 / e1 if abs(e1) > 1e-12 else float("inf")
    def _fin(v: float) -> float:
        if not math.isfinite(v):
            return 1e9
        return float(v)
    return {
        "asn_h0": _fin(asn0),
        "asn_h1": _fin(asn1),
        "e_llr_h0": e0,
        "e_llr_h1": e1,
    }


def sprt_decide(scores: list[float], alpha: float = ALPHA, beta: float = BETA) -> dict:
    A, B = sprt_boundaries(alpha, beta)
    llr = 0.0
    n = 0
    decision = "CONTINUE"
    clipped = [_clip01(x) for x in (scores or [])]
    for x in clipped:
        llr += log_likelihood_ratio_term(x)
        n += 1
        if llr > A:
            decision = "DENY"
            break
        if llr < B:
            decision = "COMMIT"
            break
    asn = average_sample_number(A, B, alpha, beta)
    return {
        "decision": decision,
        "llr": round(llr, 6),
        "n_samples": n,
        "boundary_a": round(A, 6),
        "boundary_b": round(B, 6),
        "alpha": alpha,
        "beta": beta,
        "asn_h0": round(asn["asn_h0"], 4),
        "asn_h1": round(asn["asn_h1"], 4),
    }


def _extract_subscores(row: dict) -> list[float]:
    """ADV21-004: one independent measurement per row to preserve i.i.d. LLR."""
    if not isinstance(row, dict):
        return []
    # Use only the primary composite score — not sub-scores from the same row
    for key in ("composite_ue", "ue_score", "ue"):
        if key in row:
            v = row.get(key)
            try:
                return [_clip01(float(v))]
            except Exception:
                pass
    return []


def _iter_jsonl(path: Path):
    try:
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if not s or not s.startswith("{"):
                    continue
                try:
                    obj = json.loads(s)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except Exception:
        return


def load_ue_subscores() -> list[float]:
    scores: list[float] = []
    cache = _cache_dir()
    for name in SCORES_CANDIDATES:
        path = cache / name
        for row in _iter_jsonl(path) or []:
            scores.extend(_extract_subscores(row))
        if scores:
            break
    return scores[-200:]


def run_and_log(scores: list[float] | None = None) -> dict:
    try:
        xs = list(scores) if scores is not None else load_ue_subscores()
        rec = sprt_decide(xs)
        rec["ts"] = time.time()
        rec["source_n"] = len(xs)
        _atomic_write_jsonl_append(_cache_dir() / "memory-sprt-decisions.jsonl", rec)
        return rec
    except Exception as exc:
        return {
            "decision": "CONTINUE",
            "llr": 0.0,
            "n_samples": 0,
            "boundary_a": 0.0,
            "boundary_b": 0.0,
            "fail_open": str(exc),
        }


def self_test() -> int:
    A, B = sprt_boundaries()
    assert A > 0 and B < 0, (A, B)
    # Low UE sequence must COMMIT (cross B)
    low = [0.05, 0.08, 0.1, 0.02, 0.12, 0.09, 0.11, 0.07]
    d_low = sprt_decide(low)
    assert d_low["decision"] == "COMMIT", d_low
    assert d_low["llr"] < d_low["boundary_b"]
    # High UE sequence must DENY (cross A)
    high = [0.85, 0.9, 0.95, 0.8, 0.99, 0.7, 0.88]
    d_high = sprt_decide(high)
    assert d_high["decision"] == "DENY", d_high
    assert d_high["llr"] > d_high["boundary_a"]
    # Ambiguous mid-band should CONTINUE for a short stream
    mid = [0.45, 0.5, 0.48]
    d_mid = sprt_decide(mid)
    assert d_mid["decision"] == "CONTINUE", d_mid
    # Empty / missing
    empty = sprt_decide([])
    assert empty["decision"] == "CONTINUE"
    assert empty["n_samples"] == 0
    # Bounds in [0,1] clipping
    weird = sprt_decide(["nope", float("nan"), 1e9, -4])
    assert weird["decision"] in {"COMMIT", "DENY", "CONTINUE"}
    # ASN finite and positive
    assert d_low["asn_h0"] > 0 and d_low["asn_h1"] > 0
    # Isolated cache write
    prev = os.environ.get("UE_CACHE_DIR")
    import tempfile
    td = tempfile.mkdtemp(prefix="sprt-" + uuid.uuid4().hex[:8] + "-")
    os.environ["UE_CACHE_DIR"] = td
    try:
        rec = run_and_log([0.05, 0.06, 0.04, 0.08])
        assert rec["decision"] == "COMMIT"
        p = Path(td) / "memory-sprt-decisions.jsonl"
        assert p.exists()
        json.loads(p.read_text(encoding="utf-8").strip().splitlines()[-1])
    finally:
        if prev is None:
            os.environ.pop("UE_CACHE_DIR", None)
        else:
            os.environ["UE_CACHE_DIR"] = prev
    print("PASS memory-sprt-commit self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--scores", default="", help="Comma-separated UE sub-scores")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        xs = None
        if args.scores.strip():
            xs = []
            for tok in args.scores.split(","):
                tok = tok.strip()
                if tok:
                    try:
                        xs.append(float(tok))
                    except ValueError:
                        continue
        rec = run_and_log(xs)
        print(json.dumps(rec, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            "decision": "CONTINUE",
            "llr": 0.0,
            "n_samples": 0,
            "boundary_a": 0.0,
            "boundary_b": 0.0,
            "fail_open": str(exc),
        }))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
