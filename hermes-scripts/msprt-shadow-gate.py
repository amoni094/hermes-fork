#!/usr/bin/env python3
"""msprt-shadow-gate.py — Mixture SPRT wrapper for the nightly shadow gate.

Wald SPRT (shadow-gate-sprt.py) is not always-valid under peeking. Nightly
cron peeks every day; at AR(1) rho=0.6 the empirical Type I rate inflates
(loop eval: alpha_hat=0.243 vs nominal 0.05). Johari et al. arXiv:1512.04922
replace the point-alternative SPRT with a mixture prior, yielding an
always-valid p-value: P_H0(exists t: Lambda_t >= 1/alpha) <= alpha.

Mixture: pi = Beta(2,2) on Bernoulli pass-rate p.
H0: p = p0 (default 0.80, the keep-shadow floor).
Lambda_n = B(a+s, b+n-s)/B(a,b) / [p0^s (1-p0)^{n-s}]
Always-valid p-value = min(1, 1/Lambda_n).
PROMOTE only if: Lambda >= 1/alpha AND mean pass_rate > 0.9 AND n >= N_MIN_POWER
AND no zero-tolerance event AND error_rate < 0.10.

Usage:
  HERMES_HOME=~/.hermes HERMES_PROFILE=fork python3 msprt-shadow-gate.py
  python3 msprt-shadow-gate.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

OUT_PATH = _hermes_root / "cache" / "msprt-shadow-gate.json"
ALPHA = 0.05
P0 = 0.80
PRIOR_A = 2.0
PRIOR_B = 2.0
N_MIN_POWER = 50
PROMOTE_PASS = 0.90
ERROR_RATE_VETO = 0.10
ZERO_TOLERANCE = frozenset({"unauthorized_tool_call", "policy_violation", "tamper_detected"})


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def log_beta(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def mixture_lambda(successes: int, n: int, p0: float = P0, a: float = PRIOR_A, b: float = PRIOR_B) -> float:
    """Marginal likelihood ratio vs point null p=p0 under Beta(a,b) mixture."""
    if n <= 0:
        return 1.0
    s = max(0, min(int(successes), int(n)))
    p0 = min(1.0 - 1e-12, max(1e-12, float(p0)))
    log_num = log_beta(a + s, b + n - s) - log_beta(a, b)
    log_den = s * math.log(p0) + (n - s) * math.log(1.0 - p0)
    log_l = log_num - log_den
    log_l = max(-700.0, min(700.0, log_l))
    return math.exp(log_l)


def always_valid_p(lam: float) -> float:
    if lam <= 0:
        return 1.0
    return min(1.0, 1.0 / lam)


def wald_llr_normal(scores: list[float], mu0: float = 3.0, mu1: float = 4.0) -> float:
    """Peeked Wald LLR for comparison only (not always-valid)."""
    llr = 0.0
    for x in scores:
        llr += ((float(x) - mu0) ** 2 - (float(x) - mu1) ** 2) / 2.0
    return llr


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return rows
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def load_telemetry() -> list[dict]:
    rows: list[dict] = []
    try:
        shadow = _hermes_root / "cache" / "shadow-telemetry"
        if shadow.is_dir():
            for p in sorted(p for p in shadow.glob("*.jsonl") if not p.name.startswith("synthetic-")):  # exclude baseline test fixtures
                try:
                    rows.extend(_read_jsonl(p))
                except OSError:
                    continue
    except Exception:
        pass
    return rows


def extract_flag(rec: dict) -> str:
    for key in ("flag", "flag_name", "feature", "name"):
        v = rec.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "unknown"


def is_success(rec: dict) -> bool:
    if rec.get("event_type") in ZERO_TOLERANCE:
        return False
    pr = rec.get("pass_rate")
    if isinstance(pr, (int, float)) and not isinstance(pr, bool):
        return float(pr) > 0.8
    analysis = rec.get("analysis") if isinstance(rec.get("analysis"), dict) else {}
    if analysis.get("false_positive") is True:
        return False
    score = rec.get("score", rec.get("mean_score"))
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        return float(score) >= 4.0
    return False


def extract_score(rec: dict) -> float | None:
    for key in ("mean_score", "score"):
        v = rec.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return None


def evaluate_flag(flag: str, recs: list[dict]) -> dict:
    n = len(recs)
    successes = sum(1 for r in recs if is_success(r))
    zt = []
    err = 0
    scores = []
    pass_rates = []
    for r in recs:
        et = r.get("event_type", "")
        if et in ZERO_TOLERANCE:
            zt.append(et)
        analysis = r.get("analysis") if isinstance(r.get("analysis"), dict) else {}
        if analysis.get("false_positive") is True:
            err += 1
        s = extract_score(r)
        if s is not None:
            scores.append(s)
        pr = r.get("pass_rate")
        if isinstance(pr, (int, float)) and not isinstance(pr, bool):
            pass_rates.append(float(pr))
    lam = mixture_lambda(successes, n)
    pval = always_valid_p(lam)
    mean_pr = (sum(pass_rates) / len(pass_rates)) if pass_rates else None
    error_rate = (err / n) if n else None
    wald_llr = wald_llr_normal(scores) if scores else 0.0
    A = math.log(19.0)
    B = math.log(1.0 / 19.0)
    if wald_llr > A:
        wald = "PROMOTE"
    elif wald_llr < B:
        wald = "REJECT"
    else:
        wald = "CONTINUE"

    decision = "CONTINUE"
    veto = []
    if zt:
        decision = "REJECT"
        veto.append("zero_tolerance:" + ",".join(sorted(set(zt))))
    elif error_rate is not None and error_rate >= ERROR_RATE_VETO and lam >= (1.0 / ALPHA):
        decision = "CONTINUE"
        veto.append("error_rate_veto")
    elif n < N_MIN_POWER:
        decision = "CONTINUE"
        veto.append("underpowered_n<%d" % N_MIN_POWER)
    elif lam >= (1.0 / ALPHA) and mean_pr is not None and mean_pr > PROMOTE_PASS:
        decision = "PROMOTE"
    elif lam >= (1.0 / ALPHA) and mean_pr is not None and mean_pr < 0.40:
        decision = "REJECT"
    return {
        "flag": flag,
        "n": n,
        "successes": successes,
        "mean_pass_rate": mean_pr,
        "error_rate": error_rate,
        "lambda": lam,
        "always_valid_p": pval,
        "threshold_1_over_alpha": 1.0 / ALPHA,
        "decision": decision,
        "wald_llr": wald_llr,
        "wald_decision": wald,
        "veto": veto,
        "zero_tolerance": sorted(set(zt)),
        "n_min_power": N_MIN_POWER,
        "prior": "Beta(2,2)",
        "p0": P0,
        "citation": "Johari et al. arXiv:1512.04922",
    }


def run() -> dict:
    try:
        rows = load_telemetry()
    except Exception:
        rows = []
    groups: dict[str, list[dict]] = {}
    for rec in rows:
        groups.setdefault(extract_flag(rec), []).append(rec)
    decisions = [evaluate_flag(f, recs) for f, recs in sorted(groups.items())]
    summary = {
        "ts": datetime.now(UTC).isoformat(),
        "theorem": "mSPRT / always-valid inference; mixture prior Beta(2,2); Johari et al. arXiv:1512.04922",
        "alpha": ALPHA,
        "p0": P0,
        "n_records": len(rows),
        "n_flags": len(decisions),
        "n_promote": sum(1 for d in decisions if d["decision"] == "PROMOTE"),
        "n_reject": sum(1 for d in decisions if d["decision"] == "REJECT"),
        "n_continue": sum(1 for d in decisions if d["decision"] == "CONTINUE"),
        "note": (
            "Peeked Wald SPRT is not always-valid. At AR(1) rho=0.6 empirical "
            "alpha inflates (~0.243). mSPRT p-values remain valid under optional stopping. "
            "Residual within-day autocorrelation: prefer session-level block bootstrap."
        ),
        "decisions": decisions,
    }
    try:
        _atomic_write(OUT_PATH, summary)
        summary["output"] = str(OUT_PATH)
    except OSError as exc:
        summary["write_error"] = str(exc)
    return summary


def self_test() -> int:
    failures = []
    # Lambda(0,0) = 1
    if abs(mixture_lambda(0, 0) - 1.0) > 1e-12:
        failures.append("lambda(0,0)")
    # Under H0, Lambda should not explode for small n
    lam0 = mixture_lambda(8, 10, p0=0.80)
    if not (0.01 < lam0 < 100):
        failures.append(f"lam0={lam0}")
    # Strong evidence against p0=0.8: 95/100 successes
    lam1 = mixture_lambda(95, 100, p0=0.80)
    if lam1 < 20:
        failures.append(f"expected Lambda>=20 for 95/100, got {lam1}")
    pval = always_valid_p(lam1)
    if pval > 0.05:
        failures.append(f"pval={pval}")
    # ZT veto
    recs = [{"flag": "f", "pass_rate": 0.99, "event_type": "unauthorized_tool_call", "score": 5.0}] * 60
    d = evaluate_flag("f", recs)
    if d["decision"] != "REJECT":
        failures.append("ZT decision {}".format(d["decision"]))
    # underpowered
    recs2 = [{"flag": "g", "pass_rate": 0.95, "event_type": "shadow_eval", "score": 4.8}] * 10
    d2 = evaluate_flag("g", recs2)
    if d2["decision"] != "CONTINUE":
        failures.append("underpowered {}".format(d2["decision"]))
    # empty
    d3 = evaluate_flag("empty", [])
    if d3["decision"] != "CONTINUE":
        failures.append("empty {}".format(d3["decision"]))
    # malformed JSON load
    rows = _read_jsonl(Path("/nonexistent/nope.jsonl"))
    if rows != []:
        failures.append("missing file")
    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS", "lambda_95_100": lam1, "p": pval}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({
        "n_flags": out.get("n_flags"),
        "n_promote": out.get("n_promote"),
        "n_reject": out.get("n_reject"),
        "n_continue": out.get("n_continue"),
        "output": out.get("output"),
        "decisions": [
            {"flag": d["flag"], "decision": d["decision"], "n": d["n"],
             "lambda": d["lambda"], "p": d["always_valid_p"], "wald": d["wald_decision"]}
            for d in out.get("decisions", [])
        ],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
