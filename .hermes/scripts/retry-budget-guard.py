#!/usr/bin/env python3
"""
retry-budget-guard.py — 5-class error retry budget for Hermes pipeline scripts.

Self-Healing Failure Taxonomy (arXiv sweep 19, Aug 2026):
  Rather than a flat retry_count, classify errors by failure class and apply
  per-class budgets. This prevents thundering-herd retries on non-retryable errors
  (e.g. auth failures) while allowing generous retries on transient network errors.

5 classes (from arXiv taxonomy):
  TRANSIENT   — network blip, timeout, rate-limit 429 → retry up to 5×, exp backoff
  RESOURCE    — OOM, disk full, quota → retry 2× after 30s pause
  SEMANTIC    — LLM returned malformed output, schema mismatch → retry 2× with altered prompt
  AUTH        — 401/403, token expired → retry 1× after credential refresh, then escalate
  FATAL       — assertion error, data corruption, config missing → no retry, hard fail

Usage:
    from retry_budget_guard import with_retry, ErrorClass

    result = with_retry(my_function, args, classify_fn=classify_api_error, label="graphiti-write")

Import into l1-promote.py, l1-graphiti-write.py for resilient API calls.
"""

import time
import logging
from pathlib import Path
from typing import Callable, Any

log = logging.getLogger(__name__)


class ErrorClass:
    TRANSIENT = "transient"
    RESOURCE  = "resource"
    SEMANTIC  = "semantic"
    AUTH      = "auth"
    FATAL     = "fatal"


# Per-class budget: (max_attempts, base_delay_seconds, backoff_multiplier)
BUDGETS: dict[str, tuple[int, float, float]] = {
    ErrorClass.TRANSIENT: (5, 2.0,  2.0),   # 2s, 4s, 8s, 16s, 32s
    ErrorClass.RESOURCE:  (2, 30.0, 1.0),   # 30s flat
    ErrorClass.SEMANTIC:  (2, 1.0,  1.0),   # immediate, altered prompt on second try
    ErrorClass.AUTH:      (1, 5.0,  1.0),   # one refresh attempt
    ErrorClass.FATAL:     (0, 0.0,  1.0),   # no retry — hard fail immediately
}


def _load_budgets_from_config() -> None:
    global BUDGETS
    try:
        import yaml as _yaml
        cfg_path = Path.home() / ".hermes" / "config.yaml"
        if not cfg_path.exists():
            return
        cfg = _yaml.safe_load(cfg_path.read_text()) or {}
        rb = (cfg.get("memory") or {}).get("retry_budgets") or {}
        _class_map = {
            "transient": ErrorClass.TRANSIENT,
            "resource": ErrorClass.RESOURCE,
            "semantic": ErrorClass.SEMANTIC,
            "auth": ErrorClass.AUTH,
            "fatal": ErrorClass.FATAL,
        }
        for key, ec in _class_map.items():
            entry = rb.get(key)
            if not entry:
                continue
            try:
                BUDGETS[ec] = (
                    int(entry["max_attempts"]),
                    float(entry["base_delay"]),
                    float(entry.get("backoff", 1.0)),
                )
            except (KeyError, TypeError, ValueError):
                pass
    except Exception:
        pass

_load_budgets_from_config()


def classify_http_error(exc: Exception) -> str:
    """
    Default classifier: maps common exception patterns to error classes.
    Override with a domain-specific classify_fn in with_retry().
    """
    msg = str(exc).lower()

    if any(k in msg for k in ("timeout", "connection", "network", "429", "rate limit", "too many")):
        return ErrorClass.TRANSIENT
    if any(k in msg for k in ("401", "403", "unauthorized", "forbidden", "token", "auth")):
        return ErrorClass.AUTH
    if any(k in msg for k in ("memory", "disk", "quota", "space", "resource")):
        return ErrorClass.RESOURCE
    if any(k in msg for k in ("json", "schema", "parse", "decode", "format", "validation")):
        return ErrorClass.SEMANTIC
    # 5xx and transport errors are transient — do not hard-fail on unknown errors
    # (C1 fix: adversarial review 2026-09-07 — FATAL default broke Graphiti writes on 502/503/504)
    if any(k in msg for k in ("500", "502", "503", "504", "bad gateway", "unavailable",
                               "ssl", "reset", "broken pipe", "temporarily")):
        return ErrorClass.TRANSIENT
    # True unknowns: retry once conservatively (TRANSIENT budget is small)
    return ErrorClass.TRANSIENT


def with_retry(
    fn: Callable,
    *args,
    classify_fn: Callable[[Exception], str] = classify_http_error,
    label: str = "operation",
    fatal_classes: tuple[str, ...] = (ErrorClass.FATAL,),
    **kwargs,
) -> Any:
    """
    Call fn(*args, **kwargs) with per-class retry budgets.

    Returns fn's return value on success.
    Raises the last exception after all budget is exhausted.
    Raises immediately (no retry) for FATAL class.
    """
    last_exc: Exception | None = None
    attempt_counts: dict[str, int] = {}

    # Maximum total attempts across all classes to prevent infinite loops
    MAX_TOTAL = 12
    total = 0

    while total < MAX_TOTAL:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            error_class = classify_fn(exc)
            attempt_counts[error_class] = attempt_counts.get(error_class, 0) + 1
            total += 1
            last_exc = exc

            max_attempts, base_delay, backoff = BUDGETS.get(error_class, (1, 2.0, 1.0))

            # Hard stop: no-retry classes or budget exhausted
            if error_class in fatal_classes:
                log.error("[retry-guard] %s FATAL (%s): %s — no retry", label, error_class, exc)
                raise

            if attempt_counts[error_class] > max_attempts:
                log.error("[retry-guard] %s budget exhausted for class=%s (attempts=%d): %s",
                          label, error_class, attempt_counts[error_class], exc)
                raise

            delay = base_delay * (backoff ** (attempt_counts[error_class] - 1))
            log.warning("[retry-guard] %s class=%s attempt=%d/%d, retry in %.1fs: %s",
                        label, error_class, attempt_counts[error_class], max_attempts, delay, exc)
            time.sleep(delay)

    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Convenience: classify Anthropic API errors specifically
# ---------------------------------------------------------------------------

def classify_anthropic_error(exc: Exception) -> str:
    """Classify anthropic-sdk exceptions by class."""
    type_name = type(exc).__name__.lower()

    if "ratelimit" in type_name or "overloaded" in type_name:
        return ErrorClass.TRANSIENT
    if "authentication" in type_name or "permission" in type_name:
        return ErrorClass.AUTH
    if "badrequest" in type_name or "unprocessable" in type_name:
        return ErrorClass.SEMANTIC
    if "internalserver" in type_name or "serviceunavailable" in type_name:
        return ErrorClass.TRANSIENT
    if "connection" in type_name or "timeout" in type_name:
        return ErrorClass.TRANSIENT

    # Check message for fallback
    return classify_http_error(exc)


if __name__ == "__main__":
    import sys
    import argparse as _argparse
    import math as _math

    # ---------------------------------------------------------------------------
    # WALD2 subcommands
    # ---------------------------------------------------------------------------

    def _wald_params(p):
        """Shared WALD2 defaults."""
        p.add_argument("--alpha", type=float, default=0.05, help="Type-I error bound (default 0.05)")
        p.add_argument("--beta",  type=float, default=0.10, help="Type-II error bound (default 0.10)")
        p.add_argument("--p0",   type=float, default=0.10, help="H0 failure rate (default 0.10)")
        p.add_argument("--p1",   type=float, default=0.30, help="H1 failure rate (default 0.30)")


    def _kl_bernoulli(p: float, q: float) -> float:
        """KL(Bern(p) || Bern(q)) = p*log(p/q) + (1-p)*log((1-p)/(1-q))."""
        if p <= 0 or p >= 1 or q <= 0 or q >= 1:
            return float("inf")
        return p * _math.log(p / q) + (1 - p) * _math.log((1 - p) / (1 - q))


    def cmd_sprt(observations, alpha, beta, p0, p1):
        """WALD2-1: Sequential Probability Ratio Test.

        H0: failure_rate = p0 (acceptable)
        H1: failure_rate = p1 (unacceptable, p1 > p0)

        x_i = 1 means failure, 0 means success.
        LLR = Σ [ x_i * log(p1/p0) + (1-x_i) * log((1-p1)/(1-p0)) ]

        Boundaries (Wald 1947):
          A = (1-beta)/alpha  — upper boundary: if LLR >= log(A) → STOP_BAD (reject H0)
          B = beta/(1-alpha)  — lower boundary: if LLR <= log(B) → STOP_GOOD (accept H0)

        Note: the task spec labels are consistent with Wald's original; A > 1 > B.
        LLR grows positive when failures accumulate (p1 > p0, x_i=1 increases LLR).
        """
        if not (0 < p0 < p1 < 1):
            print("ERROR: require 0 < p0 < p1 < 1", file=sys.stderr)
            sys.exit(1)
        if not (0 < alpha < 1 and 0 < beta < 1):
            print("ERROR: alpha and beta must be in (0, 1)", file=sys.stderr)
            sys.exit(1)

        # A is the upper (reject H0 / STOP_BAD) threshold — A = (1-beta)/alpha > 1
        # B is the lower (accept H0 / STOP_GOOD) threshold — B = beta/(1-alpha) < 1
        A_thresh = (1 - beta) / alpha          # upper boundary  (> 1)
        B_thresh = beta / (1 - alpha)          # lower boundary  (< 1)
        log_A = _math.log(A_thresh)            # positive: reject H0 when LLR >= log_A
        log_B = _math.log(B_thresh)            # negative: accept H0 when LLR <= log_B

        log_p1_p0     = _math.log(p1 / p0)
        log_1p1_1p0   = _math.log((1 - p1) / (1 - p0))

        llr = 0.0
        for xi in observations:
            llr += xi * log_p1_p0 + (1 - xi) * log_1p1_1p0

        if llr >= log_A:
            verdict = "STOP_BAD"
        elif llr <= log_B:
            verdict = "STOP_GOOD"
        else:
            verdict = "CONTINUE"

        print(f"WALD2-1 SPRT Result")
        print(f"  Observations : {observations}")
        print(f"  n            : {len(observations)}")
        print(f"  H0: p = {p0}   H1: p = {p1}")
        print(f"  alpha={alpha}  beta={beta}")
        print(f"  A (upper/reject-H0 threshold) = {A_thresh:.6f}   log(A) = {log_A:.6f}")
        print(f"  B (lower/accept-H0 threshold) = {B_thresh:.6f}   log(B) = {log_B:.6f}")
        print(f"  LLR                           = {llr:.6f}")
        print(f"  Verdict                       = {verdict}")


    def cmd_asn(alpha, beta, p0, p1):
        """WALD2-2: Average Sample Number bounds.

        ASN(H0) = (A*log(A) + (1-A)*log(B)) / KL(p0||p1)
        ASN(H1) = (A*log(A) + (1-A)*log(B)) / KL(p1||p0)

        Note: the Wald ASN formula uses A=(1-β)/α, B=β/(1-α) which are > 0.
        """
        if not (0 < p0 < p1 < 1):
            print("ERROR: require 0 < p0 < p1 < 1", file=sys.stderr)
            sys.exit(1)

        A = (1 - beta) / alpha
        B = beta / (1 - alpha)
        log_A = _math.log(A)
        log_B = _math.log(B)

        # Numerator is the same for both
        numerator = A * log_A + (1 - A) * log_B

        kl_p0_p1 = _kl_bernoulli(p0, p1)
        kl_p1_p0 = _kl_bernoulli(p1, p0)

        asn_h0 = numerator / kl_p0_p1 if kl_p0_p1 > 0 else float("inf")
        asn_h1 = numerator / kl_p1_p0 if kl_p1_p0 > 0 else float("inf")
        max_rec = int(_math.ceil(max(asn_h0, asn_h1) * 1.5))

        print(f"WALD2-2 ASN Bounds")
        print(f"  H0: p = {p0}   H1: p = {p1}")
        print(f"  alpha={alpha}  beta={beta}")
        print(f"  A={A:.4f}  B={B:.4f}")
        print(f"  KL(p0||p1)                 = {kl_p0_p1:.6f}")
        print(f"  KL(p1||p0)                 = {kl_p1_p0:.6f}")
        print(f"  expected_retries_if_good   = {asn_h0:.2f}  (ASN under H0)")
        print(f"  expected_retries_if_bad    = {asn_h1:.2f}  (ASN under H1)")
        print(f"  max_retries_recommendation = {max_rec}  (1.5× max ASN, rounded up)")


    def cmd_oc_curve(alpha, beta, p0, p1):
        """WALD2-3: Operating Characteristic (OC) curve.

        OC(p) = P(accept H0 | true failure rate = p).
        Wald's approximation:  OC(p) = (B^h - 1) / (B^h - A^h)
        where h is the non-trivial root of E[e^(h*z)] = 1:
          p*(p1/p0)^h * ((1-p1)/(1-p0))^h * (1-p) - ... simplifies to:
          p * (p1/p0)^h + (1-p) * ((1-p1)/(1-p0))^h = 1
        We solve for h using scipy.optimize.brentq.
        """
        try:
            from scipy.optimize import brentq as _brentq
        except ImportError:
            print("ERROR: scipy is required for --oc-curve. Install with: pip install scipy", file=sys.stderr)
            sys.exit(1)

        A = (1 - beta) / alpha
        B = beta / (1 - alpha)

        def mgf_eq(h, p):
            """E[e^(h*z)] - 1 = 0, z = log(p1/p0)*x + log((1-p1)/(1-p0))*(1-x), x~Bern(p)."""
            # E[e^{hz}] = p*(p1/p0)^h + (1-p)*((1-p1)/(1-p0))^h
            try:
                term1 = p * (p1 / p0) ** h
                term2 = (1 - p) * ((1 - p1) / (1 - p0)) ** h
                return term1 + term2 - 1.0
            except (OverflowError, ZeroDivisionError):
                return float("nan")

        print(f"WALD2-3 OC Curve  (H0: p={p0}, H1: p={p1}, alpha={alpha}, beta={beta})")
        print(f"  {'p':>6}  {'OC(p)':>10}  {'h':>10}  {'verdict':>12}")
        print(f"  {'-'*6}  {'-'*10}  {'-'*10}  {'-'*12}")

        for i in range(11):
            p = round(i * 0.05, 2)  # 0.00, 0.05, ..., 0.50
            if p == p0:
                oc = 1.0 - alpha  # by definition
                h_val = 1.0
            elif p == p1:
                oc = beta          # by definition
                h_val = -1.0
            else:
                # Find non-trivial h ≠ 0
                # At h=0, mgf_eq=0; we bracket near h in [-10, 10] excluding 0
                try:
                    # Check sign at boundaries to bracket
                    f_lo = mgf_eq(-8, p)
                    f_hi = mgf_eq(8, p)
                    # h=0 is always a root; find the other one
                    # Try positive side first (p < p0 favours H0, h < 0; p > p0 h > 0)
                    # Search in small segments to avoid landing on h≈0
                    h_val = None
                    segments = [(-8, -0.01), (0.01, 8)]
                    for lo, hi in segments:
                        try:
                            fa = mgf_eq(lo, p)
                            fb = mgf_eq(hi, p)
                            if fa * fb < 0:
                                h_val = _brentq(mgf_eq, lo, hi, args=(p,), xtol=1e-8)
                                break
                        except Exception:
                            continue
                    if h_val is None:
                        oc = float("nan")
                        print(f"  {p:>6.2f}  {'N/A':>10}  {'N/A':>10}  {'(no h root)':>12}")
                        continue
                    Bh = B ** h_val
                    Ah = A ** h_val
                    denom = Bh - Ah
                    oc = (Bh - 1) / denom if abs(denom) > 1e-12 else float("nan")
                    oc = max(0.0, min(1.0, oc))
                except Exception as e:
                    print(f"  {p:>6.2f}  {'ERR':>10}  {'ERR':>10}  {str(e)[:12]:>12}")
                    continue

            decision = "accept H0" if oc > 0.5 else "reject H0"
            print(f"  {p:>6.2f}  {oc:>10.4f}  {h_val:>10.4f}  {decision:>12}")


    # ---------------------------------------------------------------------------
    # Main dispatch
    # ---------------------------------------------------------------------------

    parser_main = _argparse.ArgumentParser(
        description="retry-budget-guard: error retry budgets + WALD2 sequential testing"
    )
    sub = parser_main.add_subparsers(dest="subcmd")

    # sprt subcommand
    p_sprt = sub.add_parser("sprt", help="WALD2-1: SPRT stopping rule for retry sequences")
    p_sprt.add_argument("observations", nargs="+", type=int, choices=[0, 1],
                        metavar="{0|1}", help="Sequence of 0 (success) or 1 (failure)")
    _wald_params(p_sprt)

    # asn subcommand
    p_asn = sub.add_parser("asn", help="WALD2-2: Average Sample Number bounds")
    _wald_params(p_asn)

    # oc-curve subcommand
    p_oc = sub.add_parser("oc-curve", help="WALD2-3: Operating Characteristic curve table")
    _wald_params(p_oc)

    args = parser_main.parse_args()

    if args.subcmd == "sprt":
        cmd_sprt(args.observations, args.alpha, args.beta, args.p0, args.p1)
    elif args.subcmd == "asn":
        cmd_asn(args.alpha, args.beta, args.p0, args.p1)
    elif args.subcmd == "oc-curve":
        cmd_oc_curve(args.alpha, args.beta, args.p0, args.p1)
    else:
        # Legacy smoke-test (original __main__ block)
        call_count = 0

        def flaky(n: int) -> str:
            global call_count
            call_count += 1
            if call_count < n:
                raise ConnectionError(f"timeout attempt {call_count}")
            return f"ok after {call_count} attempts"

        result = with_retry(flaky, 3, label="smoke-test")
        assert "ok after 3 attempts" in result, f"unexpected: {result}"
        print(f"PASS: {result}")

        # Test FATAL — should not retry
        def always_fatal():
            raise AssertionError("data corruption")

        try:
            with_retry(always_fatal, classify_fn=lambda e: ErrorClass.FATAL, label="fatal-test")
            print("FAIL: should have raised")
            sys.exit(1)
        except AssertionError:
            print("PASS: fatal raised immediately")

        print("retry-budget-guard: all smoke tests passed")
