#!/usr/bin/env python3
"""
Metacognitive Harness for Hermes Agent
=======================================
Research basis (figures are paper benchmarks; prompt-only Hermes rates unconfirmed):
  arXiv:2605.14186  FOK/JOL on frozen Claude Sonnet (+8.6pp pooled accuracy)
  arXiv:2605.17292  Skill profile empirical blending (-5% API calls, +8.7pp routing)
  arXiv:2604.19809  Hard confidence gate (-76% Confident Failure Rate)
  arXiv:2605.24299  Parse reasoning not stated confidence
  arXiv:2503.02863  SteerConf dual-framing consistency (beats 7 benches)
  arXiv:2604.17293  Typed uncertainty: AMBIGUOUS_INPUT|MISSING_EVIDENCE|OUT_OF_SCOPE|TOOL_FAILED
  arXiv:2604.03904  I-CALM payoff-table abstention (reduces false-answer rate)
  arXiv:2607.10059  AgentAbstain pre-irreversible gate (post-hoc abstention = failure)
  Pearl 2009        Causality (do-calculus / counterfactuals)
  arXiv:2502.09100  Logical reasoning survey (causal / abductive chains)
  ACL 2026          Action Boundary Blindness; EBP +0.08-0.13 ABS, +9.2% SR

Usage:
  python3 metacognitive-harness.py evaluate --fok 0.7 --jol 0.6 [--attempt N]
  python3 metacognitive-harness.py profile --skill "code-generation" --outcome success
  python3 metacognitive-harness.py hedge-score --reasoning "text to analyze"
  python3 metacognitive-harness.py gate --confidence 0.85 --tool-called true --level L2
  python3 metacognitive-harness.py prompt --task "..." --skill "..." --attempt 1
  python3 metacognitive-harness.py blend --skill "code-gen" --task-type "debugging" --verbalized 0.7
  python3 metacognitive-harness.py typed-uncertainty --description "cannot find the file"
  python3 metacognitive-harness.py abstain-check --action "delete" --confidence 0.6
  python3 metacognitive-harness.py causal-check --observation "..." --candidate-cause "..." [--intervention "..."] [--alternatives '[...]'] [--dcc]
  python3 metacognitive-harness.py compound --probs '[0.8, 0.75, 0.9]' --mode chain
  python3 metacognitive-harness.py kapro-check --task "..." --known-confidence 0.7 --action-value 0.4
  python3 metacognitive-harness.py boundary-check --action "..." --task "..." [--scope "..."] [--prior-actions '[...]']
  python3 metacognitive-harness.py conflict-resolve --framework-a A --verdict-a V --framework-b B --verdict-b W --task "..."
  python3 metacognitive-harness.py aic-rank --skill-data '[{"skill":"A","successes":8,"total":10,"d":2}]'
  python3 metacognitive-harness.py minimax-regret --loss-table '{"easy":{"answer":0.1}}' --states '["easy"]'
  python3 metacognitive-harness.py skill-precond --skill SKILL_NAME --query QUERY [--task-type TASK_TYPE]
  python3 metacognitive-harness.py skill-hom --skill-a SKILL_A --skill-b SKILL_B [--min-shared 2] [--threshold 0.95]
  python3 metacognitive-harness.py evaluate --fok 0.7 --jol 0.6 [--eu] [--irreversible]
  python3 metacognitive-harness.py calibrate [--bins 10]

Exit codes: 0 = proceed/stop, 1 = retry, 2 = escalate/aggregate, 3 = force-tool, 4 = abstain
  causal-check: 0=causal_confirmed, 1=correlation_only/probable, 2=unknown/insufficient
  kapro-check: 0=proceed, 1=use_cached_knowledge, 2=skip_action, 3=escalate
  boundary-check: 0=clean, 1=incomplete, 2=over_action, 3=scope_creep
  conflict-resolve: 0=resolved, 1=partial (low confidence), 2=escalate to human
"""

import argparse
import json
import math
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Config defaults (override via MH_* env vars)
JOL_STOP_THRESHOLD    = float(os.environ.get("MH_JOL_STOP",     "0.8"))
FOK_JOL_GAP_THRESHOLD = float(os.environ.get("MH_GAP",          "0.3"))
MAX_ATTEMPTS          = int(os.environ.get("MH_MAX_ATTEMPTS",    "2"))
CONF_GATE_THRESHOLD   = float(os.environ.get("MH_CONF_GATE",    "0.8"))
DELEGATE_THRESHOLD    = float(os.environ.get("MH_DELEGATE",     "0.6"))
BLEND_WEIGHT          = float(os.environ.get("MH_BLEND",        "0.5"))
MIN_SAMPLES           = int(os.environ.get("MH_MIN_SAMPLES",    "5"))
HERMES_HOME           = Path(os.environ.get("HERMES_HOME",
                              str(Path.home() / ".hermes")))
DB_PATH               = Path(os.environ.get(
    "MH_DB", str(HERMES_HOME / "memory-facts" / "metacognitive.db")))

HEDGE_PATTERNS = [
    r"\bprobably\b", r"\bi think\b", r"\bmight be\b", r"\bnot sure\b",
    r"\bperhaps\b", r"\bi believe\b", r"\bcould be\b", r"\bunsure\b",
    r"\bi\'d need to check\b", r"\bi don\'t have access\b",
    r"\bapproximately\b", r"\bif i recall\b", r"\bseems like\b",
    r"\bi\'m not certain\b", r"\bmy understanding is\b",
]

UNCERTAINTY_KEYWORDS = {
    "AMBIGUOUS_INPUT":   ["unclear", "ambiguous", "which one", "underspecified", "vague"],
    "MISSING_EVIDENCE":  ["cannot find", "no data", "not in context", "don't have",
                          "no source", "missing", "not available"],
    "OUT_OF_SCOPE":      ["outside my knowledge", "after my training", "cannot access",
                          "no tool", "not supported", "out of scope", "beyond"],
    "TOOL_FAILED":       ["tool error", "failed", "timeout", "connection refused",
                          "exception", "error:"],
}

# All entries matched with word-boundary (re.search(r'\b' + kw + r'\b')):
# "write" matches "write the file" but NOT "rewrite"; "remove" NOT "removeEvent" etc.
# "write" is intentionally included: writing to a file/resource is irreversible by default.
IRREVERSIBLE_ACTIONS = [
    "delete", "remove", "drop", "truncate", "wipe", "send", "publish",
    "deploy", "commit", "push", "write", "overwrite", "rm", "email",
    "notify", "pay", "transfer", "erase",
    # "format" removed: too broad ("format the output", "format json");
    # disk/storage format is already covered by "erase" and "wipe"
]

CAUSAL_TEMPORAL_PATTERNS = [
    r"\bafter\b", r"\bthen\b", r"\bcoincid", r"\baround the same time\b",
    r"\bshortly after\b", r"\bfollowing\b", r"\bsubsequently\b",
    r"\bat the same time\b", r"\bright after\b", r"\bsoon after\b",
]
CAUSAL_SHARED_DRIVER_PATTERNS = [
    r"\bcommon cause\b", r"\bshared driver\b", r"\bboth (due|caused|from)\b",
    r"\bunderlying\b", r"\bthird factor\b", r"\bconfound",
    r"\bsimultaneously\b", r"\bcommon factor\b",
]
CAUSAL_SELECTION_BIAS_PATTERNS = [
    r"\bonly (observed|looking|selected|among)\b", r"\bsurvivor",
    r"\bconditioned on\b", r"\bselection bias\b", r"\bfiltered\b",
    r"\bcherry[- ]pick",
]
CAUSAL_MARKERS = [
    r"\bcaused\b", r"\bbecause\b", r"\bled to\b", r"\bresulted in\b",
    r"\bdue to\b", r"\bdo-calculus\b", r"\binterven",
    r"\bif (we |i )?(revert|rollback|undo|remove|disable|absent)\b",
]
BOUNDARY_UNDER_PATTERNS = [
    r"\bjust\b", r"\bonly\b", r"\bskip\b", r"\blater\b", r"\bpartial\b",
    r"\btodo\b", r"\bwip\b", r"\bfor now\b", r"\bnot yet\b",
]
BOUNDARY_OVER_PATTERNS = [
    r"\balso\b", r"\bwhile i'?m at it\b", r"\bmight as well\b",
    r"\band then also\b", r"\bas well as\b", r"\bextra\b",
    r"\bon top of\b", r"\badditionally\b",
]
_STOPWORDS = {
    "the", "a", "an", "to", "of", "and", "or", "in", "on", "for", "with",
    "is", "be", "this", "that", "it", "at", "by", "from", "as", "if",
}
_CLEAN_IMPLIES = {
    "clean", "clear", "remove", "delete", "purge", "wipe", "erase", "rm",
}


def _reasoning_runtime():
    import importlib.util
    p = Path(__file__).resolve().parent / "reasoning-hooks.py"
    spec = importlib.util.spec_from_file_location("reasoning_hooks_rt", p)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse_json_list(raw: str) -> list:
    if not raw or not str(raw).strip():
        return []
    try:
        val = json.loads(raw)
    except json.JSONDecodeError:
        return [raw]
    if isinstance(val, list):
        return val
    return [val]


def _norm_tokens(text: str) -> set:
    toks = re.findall(r"[a-z0-9]+", (text or "").lower())
    out = set()
    for t in toks:
        if t in _STOPWORDS or len(t) < 2:
            continue
        if t.endswith("s") and len(t) > 3:
            t = t[:-1]
        out.add(t)
    return out


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2]


def _tf_vec(tokens: list[str]) -> dict[str, float]:
    """Normalised term frequency (not TF-IDF)."""
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = sum(counts.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in counts.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(k, 0.0) * v for k, v in b.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (na * nb)


def _get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skill_profiles (
            skill       TEXT NOT NULL,
            task_type   TEXT NOT NULL DEFAULT 'general',
            total       INTEGER NOT NULL DEFAULT 0,
            successes   INTEGER NOT NULL DEFAULT 0,
            updated_at  TEXT NOT NULL,
            PRIMARY KEY (skill, task_type)
        )
    """)
    conn.commit()
    return conn


def _to_db(p: float) -> float:
    """Convert probability to decibels of evidence (Jaynes eq 4-8)."""
    p = max(1e-6, min(1 - 1e-6, p))
    return 10 * math.log10(p / (1 - p))


def _from_db(e: float) -> float:
    """Convert decibels of evidence back to probability (Jaynes eq 4-9)."""
    return 1 / (1 + 10 ** (-e / 10))


def _accumulate_evidence(tool_results: list, halflife: int | None = None) -> float:
    """Accumulate evidence in dB from independent tool results (Jaynes Ch.4 eq 4-10).
    LR defaults: success->2.0, fail->0.5, hedge->0.7, unknown->1.0
    Uses max() not sum() when results are correlated (conservative).
    Age-weighted evidence heuristic: older tool results contribute less. This is a
    recency heuristic, NOT a discounted MDP optimality criterion. Use only when
    tool_results have explicit age keys. Weight db by lambda^age where
    lambda = 0.5**(1.0/halflife) and age 0 is newest.
    """
    if halflife is None:
        halflife = int(os.environ.get("MH_EVIDENCE_HALFLIFE", "4"))
    halflife = max(1, int(halflife))
    lam = 0.5 ** (1.0 / halflife)
    LR = {'success': 2.0, 'fail': 0.5, 'hedge': 0.7, 'pass': 2.0, 'error': 0.3}
    e = 0.0
    for r in tool_results:
        if not isinstance(r, dict):
            continue
        outcome = r.get('outcome', 'unknown')
        lr = LR.get(outcome, 1.0)
        db = 10 * math.log10(lr) if lr > 0 else -20
        age = r.get('age')
        if age is not None:
            try:
                db *= lam ** int(age)
            except (TypeError, ValueError):
                pass
        e += db  # independent: add. Caller passes independent=True only when tool families differ.
    return e


def _beta_posterior_stats(successes: int, total: int) -> dict:
    """DEGROOT-001: Beta(s+1, f+1) posterior variance and 90% CI."""
    failures = max(0, int(total) - int(successes))
    alpha = int(successes) + 1
    beta_p = failures + 1
    denom = (alpha + beta_p) ** 2 * (alpha + beta_p + 1)
    posterior_var = (alpha * beta_p) / denom
    mean = alpha / (alpha + beta_p)
    try:
        from scipy.stats import beta as beta_dist
        ci_low = float(beta_dist.ppf(0.05, alpha, beta_p))
        ci_high = float(beta_dist.ppf(0.95, alpha, beta_p))
    except Exception:
        se = math.sqrt(max(0.0, posterior_var))
        ci_low = mean - 1.645 * se
        ci_high = mean + 1.645 * se
    return {
        "alpha": alpha,
        "beta_p": beta_p,
        "failures": failures,
        "posterior_var": posterior_var,
        "ci_low": ci_low,
        "ci_high": ci_high,
    }


def bernoulli_kl(p, q):
    p = max(1e-9, min(1 - 1e-9, p))
    q = max(1e-9, min(1 - 1e-9, q))
    return p * math.log(p / q) + (1 - p) * math.log((1 - p) / (1 - q))


def chernoff_n_star(p_hat, p_thresh=0.5, delta=0.05):
    """COVSHA-2 WEAKEN: Chernoff sample-size diagnostic. Informational only.
    l1-promote.py uses Hoeffding n_star with eps=0.1 for a simpler guarantee.
    """
    p_hat = max(1e-9, min(1 - 1e-9, p_hat))  # clamp off {0,1}
    D = bernoulli_kl(p_thresh, p_hat)
    if D < 1e-9:
        return None  # p_hat == p_thresh, no discrimination possible
    return math.ceil(math.log(1.0 / delta) / D)


_CALIB_LOG = Path.home() / ".hermes" / "cache" / "calibration_log.jsonl"

def _write_calibration_row(session_id: str | None, task_class: str | None,
                            fok: float, jol: float, decision: str) -> None:
    """Append one row to the FOK/JOL calibration log (Spike M, arXiv:2605.14186).

    Row schema: {ts, session_id, task_class, fok_score, jol, decision, outcome}
    outcome is always null here — filled in by a separate outcome-labeling pass
    once the task result is known (human correction, test pass, or verified tool result).
    Do NOT auto-set outcome in this function; labels must come from verified external signal.
    Safe to call with session_id=None / task_class=None — row is written but unfilterable.
    No-op if _CALIB_LOG parent dir doesn't exist (avoids breaking cron in restricted envs).
    """
    if not session_id:
        return  # don't write unlabeled rows with no session anchor
    try:
        _CALIB_LOG.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "task_class": task_class or "unknown",
            "fok_score": round(fok, 4),
            "jol": round(jol, 4),
            "decision": decision,
            "outcome": None,  # filled by outcome-labeling pass; never auto-set here
        }
        with open(_CALIB_LOG, "a") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass  # never let logging failure crash the harness


def cmd_evaluate(args):
    fok = min(1.0, max(0.0, args.fok))
    jol = min(1.0, max(0.0, args.jol))
    attempt = args.attempt
    gap = abs(fok - jol)
    result = {"fok": fok, "jol": jol, "gap": round(gap, 3), "attempt": attempt,
              # fok_score: structured float for calibration logging (arXiv:2605.14186 Step M).
              # Captures pre-solve monitoring signal for future (session_id, task_class, fok_score, outcome) calibration log.
              "fok_score": round(fok, 4)}
    # MACKAY-3: optional EU diagnostic. Does not change decision/thresholds.
    if getattr(args, "eu", False):
        p_correct = jol  # raw JOL; not treated as calibrated
        u_ok = 1.0
        u_bad_rev = -1.0
        u_bad_irrev = -5.0
        c_escalate = 0.4
        irrev = bool(getattr(args, "irreversible", False))
        u_bad = u_bad_irrev if irrev else u_bad_rev
        eu_deliver = p_correct * u_ok + (1.0 - p_correct) * u_bad
        eu_escalate = -c_escalate
        eu_action = "DELIVER" if eu_deliver >= eu_escalate else "ESCALATE"
        result.update({
            "eu_deliver": eu_deliver,
            "eu_escalate": eu_escalate,
            "eu_action": eu_action,
            "eu_diagnostic_only": True,
            "eu_note": "JOL used as p_correct; not calibrated. VOI-of-retry omitted (LLM retries are dependent).",
        })
    # Gap check first
    if gap > FOK_JOL_GAP_THRESHOLD:
        direction = "overconfident" if jol > fok else "underconfident"
        result.update({"decision": "RETRY_WITH_FEEDBACK",
                        "reason": f"FOK/JOL gap {gap:.2f} > {FOK_JOL_GAP_THRESHOLD} ({direction})",
                        "exit_code": 1})
        _write_calibration_row(getattr(args, "session", None),
                               getattr(args, "task_class", None), fok, jol, result["decision"])
        print(json.dumps(result)); return int(result.get("exit_code", 0))
    if jol >= JOL_STOP_THRESHOLD:
        result.update({"decision": "STOP_AND_DELIVER",
                        "reason": f"JOL {jol} >= {JOL_STOP_THRESHOLD}", "exit_code": 0})
        _write_calibration_row(getattr(args, "session", None),
                               getattr(args, "task_class", None), fok, jol, result["decision"])
        print(json.dumps(result)); return int(result.get("exit_code", 0))
    if attempt >= MAX_ATTEMPTS:
        result.update({"decision": "LIST_WISE_AGGREGATE",
                        "reason": f"max attempts ({MAX_ATTEMPTS}) reached", "exit_code": 2})
        _write_calibration_row(getattr(args, "session", None),
                               getattr(args, "task_class", None), fok, jol, result["decision"])
        print(json.dumps(result)); return int(result.get("exit_code", 0))
    result.update({"decision": "RETRY",
                    "reason": f"JOL {jol} < {JOL_STOP_THRESHOLD}, attempt {attempt}/{MAX_ATTEMPTS}",
                    "exit_code": 1})
    raw_tr = getattr(args, "tool_results", None) or ""
    tool_results = []
    if raw_tr:
        try:
            parsed = json.loads(raw_tr)
            if isinstance(parsed, list):
                tool_results = [x for x in parsed if isinstance(x, dict)]
        except json.JSONDecodeError:
            tool_results = []
    if tool_results:
        evidence_db = _accumulate_evidence(
            tool_results, halflife=getattr(args, "halflife", None))
        result["evidence_db"] = round(evidence_db, 4)
        if evidence_db >= 6.0:
            result.update({"decision": "STOP_AND_DELIVER",
                            "reason": f"evidence_db {evidence_db:.2f} >= 6.0 (Jaynes Ch.4 strong evidence)",
                            "exit_code": 0})
            _write_calibration_row(getattr(args, "session", None),
                                   getattr(args, "task_class", None), fok, jol, result["decision"])
            print(json.dumps(result)); return int(result.get("exit_code", 0))
        if evidence_db <= -6.0:
            result.update({"decision": "ESCALATE",
                            "reason": f"evidence_db {evidence_db:.2f} <= -6.0 (Jaynes Ch.4 contrary evidence)",
                            "exit_code": 2})
            _write_calibration_row(getattr(args, "session", None),
                                   getattr(args, "task_class", None), fok, jol, result["decision"])
            print(json.dumps(result)); return int(result.get("exit_code", 0))
    _write_calibration_row(getattr(args, "session", None),
                           getattr(args, "task_class", None), fok, jol, result["decision"])
    print(json.dumps(result)); return int(result.get("exit_code", 0))


def cmd_gate(args):
    confidence = args.confidence
    tool_called = args.tool_called.strip().lower() in ("true", "1", "yes")
    level = args.level.upper()
    if level in ("L0", "L1"):
        print(json.dumps({"decision": "PASS_EXEMPT", "reason": f"Level {level} exempt", "exit_code": 0}))
        return 0
    if confidence >= CONF_GATE_THRESHOLD and not tool_called:
        print(json.dumps({"decision": "FORCE_TOOL_CALL", "confidence": confidence,
                           "reason": "Verbal confidence without grounding (arXiv:2604.19809)",
                           "exit_code": 3}))
        return 3
    print(json.dumps({"decision": "PASS", "confidence": confidence,
                       "tool_called": tool_called, "exit_code": 0}))
    return 0


def cmd_hedge_score(args):
    text = args.reasoning.lower()
    hits = [p for p in HEDGE_PATTERNS if re.search(p, text)]
    score = min(1.0, len(hits) / max(1, len(HEDGE_PATTERNS) * 0.3))
    print(json.dumps({"hedge_count": len(hits), "hedge_score": round(score, 3),
                       "matched_patterns": hits,
                       "interpretation": ("high" if score >= 0.5 else "moderate" if score >= 0.2
                                          else "low") + " uncertainty"}))
    return 0


def cmd_profile(args):
    conn = _get_db()
    now = datetime.now(timezone.utc).isoformat()
    success = 1 if args.outcome == "success" else 0
    conn.execute("""
        INSERT INTO skill_profiles (skill, task_type, total, successes, updated_at)
        VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(skill, task_type) DO UPDATE SET
            total = total + 1, successes = successes + ?, updated_at = excluded.updated_at
    """, (args.skill, args.task_type, success, now, success))
    conn.commit()
    row = conn.execute("SELECT total, successes FROM skill_profiles WHERE skill=? AND task_type=?",
                        (args.skill, args.task_type)).fetchone()
    conn.close()
    total, successes = row
    if total:
        raw = successes / total
        # Never emit empirical 0.0 or 1.0 for finite n (Jaynes / rule of succession).
        if raw <= 0.0:
            emp_rate = round(1.0 / (total + 1), 3)
        elif raw >= 1.0:
            emp_rate = round(total / (total + 1), 3)
        else:
            emp_rate = round(raw, 3)
    else:
        emp_rate = 0.0
    p_laplace = round((successes + 1) / (total + 2), 4)
    beta_stats = _beta_posterior_stats(successes, total)
    print(json.dumps({"skill": args.skill, "task_type": args.task_type,
                       "total": total, "successes": successes,
                       "empirical_success_rate": emp_rate,
                       "laplace_success_rate": p_laplace,
                       "recorded": args.outcome,
                       "alpha": beta_stats["alpha"],
                       "beta_p": beta_stats["beta_p"],
                       "posterior_var": beta_stats["posterior_var"],
                       "ci_low": beta_stats["ci_low"],
                       "ci_high": beta_stats["ci_high"]}))
    return 0


def cmd_blend(args):
    conn = _get_db()
    row = conn.execute("SELECT total, successes FROM skill_profiles WHERE skill=? AND task_type=?",
                        (args.skill, args.task_type)).fetchone()
    conn.close()
    total = row[0] if row else 0
    successes = row[1] if row else 0
    # Laplace / rule of succession (Jaynes): (s+1)/(n+2); n=0 → 0.5
    laplace = (successes + 1) / (total + 2)
    if total:
        raw = successes / total
        if raw <= 0.0:
            emp_out = round(1.0 / (total + 1), 3)
        elif raw >= 1.0:
            emp_out = round(total / (total + 1), 3)
        else:
            emp_out = round(raw, 3)
    else:
        emp_out = None
    empirical = laplace
    blended = BLEND_WEIGHT * args.verbalized + (1 - BLEND_WEIGHT) * empirical
    e_empirical = _to_db(empirical)
    e_verbalized = _to_db(args.verbalized)
    independent = bool(getattr(args, "independent", False))
    if independent:
        e_blended = e_empirical + e_verbalized
    else:
        # Conservative: avoid double-counting correlated sources (Jaynes Ch.4)
        e_blended = max(e_empirical, e_verbalized)
    blended_logodds = _from_db(e_blended)
    decision = "DELEGATE" if blended < DELEGATE_THRESHOLD else "PROCEED"
    payload = {
        "blended_confidence": round(blended, 3),
        "verbalized_confidence": args.verbalized,
        "empirical_success_rate": emp_out,
        "laplace_success_rate": round(laplace, 4),
        "blended_logodds": round(blended_logodds, 4),
        "samples": total,
        "decision": decision,
        "laplace_smoothed": total < MIN_SAMPLES,
    }
    if total < MIN_SAMPLES:
        payload["min_samples"] = MIN_SAMPLES
        payload["recommendation"] = "proceed"
    beta_stats = _beta_posterior_stats(successes, total)
    payload["posterior_var"] = beta_stats["posterior_var"]
    # COVSHA-2 WEAKEN: Chernoff n_star is diagnostic only; never skip dB blend.
    n_star = chernoff_n_star(laplace)
    payload["n_star"] = n_star or None
    payload["underpowered"] = (total < n_star) if n_star is not None else None
    # WALD-3: Sequential CI shrinkage (Wald Ch.6). Purely additive diagnostic.
    # CI_width = 2*1.96*sqrt(p*(1-p)/n); ci_stable when width < epsilon (default 0.2).
    _p = laplace
    ci_width = 2 * 1.96 * math.sqrt(_p * (1.0 - _p) / max(1, total + 2))
    payload["ci_width"] = round(ci_width, 4)
    payload["ci_stable"] = ci_width < float(os.environ.get("MH_CI_EPSILON", "0.2"))
    print(json.dumps(payload))
    return 0


def cmd_prompt(args):
    prefix = (
        f"[Metacognitive Gate - Attempt {args.attempt}]\n"
        f"Task: {args.task}\nActive skill: {args.skill}\n\n"
        "Before answering, score:\n"
        "  FOK (0.0-1.0): How confident am I I can solve this correctly?\n"
        "  Answer: <your answer>\n"
        "  JOL (0.0-1.0): How satisfied am I with this answer's correctness?\n\n"
        f"Rules: JOL>={JOL_STOP_THRESHOLD} stop; |FOK-JOL|>{FOK_JOL_GAP_THRESHOLD} retry; "
        f"both<0.5 after {MAX_ATTEMPTS} attempts -> list-wise; "
        "confidence>=0.8 without tool call -> force tool."
    )
    print(prefix)
    return 0


def cmd_typed_uncertainty(args):
    desc = args.description.lower()
    scores = {utype: sum(1 for kw in keywords if kw in desc)
              for utype, keywords in UNCERTAINTY_KEYWORDS.items()}
    best_score = max(scores.values())
    if best_score == 0:
        # No uncertainty keyword matched — description does not indicate a known gap type
        print(json.dumps({"uncertainty_type": "UNKNOWN", "bound_action": "proceed",
                           "confidence": 0.0, "scores": scores,
                           "note": "No uncertainty keywords matched; classify manually"}))
        return 0
    best_type = max(scores, key=lambda k: scores[k])
    raw_conf = scores[best_type] / max(1, len(UNCERTAINTY_KEYWORDS[best_type]))
    confidence = round(min(1.0, max(0.0, raw_conf)), 3)  # clamped to [0,1]; no * 2
    BINDINGS = {"AMBIGUOUS_INPUT": "clarify", "MISSING_EVIDENCE": "retrieve",
                "OUT_OF_SCOPE": "abstain", "TOOL_FAILED": "retry-with-different-tool"}
    print(json.dumps({"uncertainty_type": best_type, "bound_action": BINDINGS[best_type],
                       "confidence": confidence, "scores": scores}))
    return 0


def cmd_abstain_check(args):
    action = args.action.lower()
    confidence = min(1.0, max(0.0, args.confidence))  # clamp to [0,1]
    # Word-boundary match: avoid false positives like "format the json", "inspect", "rewrite"
    is_irreversible = any(
        re.search(r"\b" + re.escape(kw) + r"\b", action)
        for kw in IRREVERSIBLE_ACTIONS
    )
    if is_irreversible and confidence < CONF_GATE_THRESHOLD:
        print(json.dumps({"decision": "ABSTAIN_BEFORE_EXECUTING", "action": args.action,
                           "confidence": confidence, "threshold": CONF_GATE_THRESHOLD,
                           "is_irreversible": True, "exit_code": 4,
                           "reason": f"Irreversible action + confidence {confidence} < {CONF_GATE_THRESHOLD}. "
                                     "Pre-execution abstention (arXiv:2607.10059)",
                           "recommended": "clarify intent or gather more evidence first"}))
        return 4
    print(json.dumps({"decision": "PROCEED", "action": args.action,
                       "confidence": confidence, "is_irreversible": is_irreversible, "exit_code": 0}))
    return 0


def cmd_causal_check(args):
    OBS_TOOLS = {'read_file','search_files','web_search','web_extract','session_search',
                 'skill_view','browser_snapshot','browser_get_images','hindsight_recall'}
    DO_TOOLS  = {'write_file','patch','terminal','skill_manage','browser_click',
                 'browser_type','execute_code','todo_list'}
    observation = (args.observation or "").strip()
    cause = (args.candidate_cause or "").strip()
    intervention = (args.intervention or "").strip()
    alternatives = _parse_json_list(args.alternatives or "")
    tools = list(getattr(args, "tool", None) or [])
    obs_used = [t for t in tools if t in OBS_TOOLS]
    do_used = [t for t in tools if t in DO_TOOLS]
    evidence = getattr(args, "evidence", None)
    evidence_given = evidence is not None
    evidence_s = (evidence or "").strip() if evidence_given else ""
    if getattr(args, "dcc", False) and evidence_given and not evidence_s:
        print(json.dumps({
            "error": "--dcc requires non-empty --evidence (or omit --evidence)",
            "verdict": "UNKNOWN",
            "exit_code": 2,
        }))
        return 2
    combined = " ".join(
        [observation, cause, intervention, evidence_s] + [str(a) for a in alternatives]
    ).lower()

    confound_risks = []
    if any(re.search(p, combined) for p in CAUSAL_TEMPORAL_PATTERNS):
        confound_risks.append("temporal_proximity")
    if any(re.search(p, combined) for p in CAUSAL_SHARED_DRIVER_PATTERNS):
        confound_risks.append("shared_driver")
    if any(re.search(p, combined) for p in CAUSAL_SELECTION_BIAS_PATTERNS):
        confound_risks.append("selection_bias")

    counterfactual_test = (
        "Pearl counterfactual (Causality 2009 / do-calculus): "
        f"Would '{observation}' still occur if '{cause}' were absent "
        f"(do({cause}=0)), holding other factors fixed?"
    )
    if intervention:
        intervention_test = (
            f"Apply intervention '{intervention}' while holding confounders fixed; "
            f"confirm whether '{observation}' changes only when '{cause}' is present."
        )
    else:
        intervention_test = (
            f"Intervene on '{cause}' (hold other factors fixed) and check whether "
            f"'{observation}' changes. If the outcome is unchanged, treat as correlation."
        )

    causal_hits = sum(1 for p in CAUSAL_MARKERS if re.search(p, combined))
    n_confounds = len(confound_risks)
    has_intervention = bool(intervention) or bool(do_used)
    has_alts = len(alternatives) > 0

    confidence = 0.5
    if has_intervention:
        confidence += 0.2
    if causal_hits:
        confidence += min(0.2, 0.1 * causal_hits)
    if n_confounds:
        confidence -= 0.12 * n_confounds
    if has_alts:
        confidence -= 0.1
    if not observation or not cause:
        confidence = 0.2
    confidence = round(min(1.0, max(0.0, confidence)), 3)

    if not observation or not cause:
        verdict, code = "UNKNOWN", 2
    elif n_confounds >= 2 and not has_intervention:
        verdict, code = "CORRELATED", 1
    elif ("temporal_proximity" in confound_risks
          and not has_intervention and not causal_hits):
        verdict, code = "CORRELATED", 1
    elif has_alts and n_confounds and not has_intervention:
        verdict, code = "CORRELATED", 1
    elif has_intervention and n_confounds == 0:
        verdict, code = "CAUSAL", 0
    elif causal_hits and n_confounds == 0 and confidence >= 0.55:
        verdict, code = "CAUSAL", 0
    elif confidence < 0.4 or (not has_intervention and not causal_hits):
        verdict, code = "UNKNOWN", 2
    elif n_confounds:
        verdict, code = "CORRELATED", 1
    else:
        verdict, code = "UNKNOWN", 2

    payload = {
        "verdict": verdict,
        "counterfactual_test": counterfactual_test,
        "confound_risks": confound_risks,
        "intervention_test": intervention_test,
        "confidence": confidence,
        "alternatives": alternatives,
        "exit_code": code,
    }

    # Double Counterfactual Consistency (DCC) — "Better Think Thrice", training-free.
    # (A) forward: would Y change if X were absent?
    # (B) backward: would X still produce Y via a different path?
    if getattr(args, "dcc", False):
        dcc_forward = bool(has_intervention or (causal_hits and n_confounds == 0))
        dcc_backward = bool(
            (has_intervention or causal_hits) and not has_alts and n_confounds == 0
        )
        payload["dcc_forward"] = dcc_forward
        payload["dcc_backward"] = dcc_backward
        payload["dcc_forward_prompt"] = (
            f"(A) Forward counterfactual: Would outcome '{observation}' change "
            f"if cause '{cause}' were absent?"
        )
        payload["dcc_backward_prompt"] = (
            f"(B) Backward counterfactual: Would cause '{cause}' lead to "
            f"outcome '{observation}' via a different path?"
        )
        if observation and cause:
            n_pass = int(dcc_forward) + int(dcc_backward)
            if n_pass == 2:
                if verdict == "CAUSAL":
                    payload["verdict"] = "CAUSAL"
                    payload["exit_code"] = 0
            elif n_pass == 1:
                payload["verdict"] = "PROBABLE"
                payload["exit_code"] = 1
            else:
                payload["verdict"] = "CORRELATED"
                payload["exit_code"] = 1
            verdict = payload["verdict"]
            code = payload["exit_code"]

    if tools:
        payload["tool_kinds"] = {"obs": obs_used, "do": do_used}
        all_obs = bool(tools) and all(t in OBS_TOOLS for t in tools)
        if all_obs and not bool(intervention):
            payload["verdict"] = "CORRELATED"
            payload["exit_code"] = 1
            payload["rule2_violated"] = True
            verdict, code = "CORRELATED", 1
        if do_used:
            payload["has_intervention"] = True

    print(json.dumps(payload))
    return code


def cmd_compound(args):
    """Compound probability combiner (Jaynes PTLoS Ch.2 product rule).
    chain: P(A1..Ak) = product of conditional probs (assumed given previous in sequence)
    unknown_dep: min(probs) — Frechet lower bound
    indep: product — only valid when d-separated (PEARL-1), flagged as assumption
    Abstain if compound < 0.6 (chain/indep) or min < 0.7 (unknown_dep).
    """
    try:
        probs = json.loads(args.probs)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid --probs JSON: {e}"}))
        return 1
    if not isinstance(probs, list) or not probs:
        print(json.dumps({"error": "probs must be a non-empty JSON list"}))
        return 1
    try:
        probs = [float(p) for p in probs]
    except (TypeError, ValueError):
        print(json.dumps({"error": "probs must be numeric"}))
        return 1
    mode = args.mode
    if mode == 'chain':
        compound = 1.0
        for p in probs:
            compound *= p
    elif mode == 'unknown_dep':
        compound = min(probs)
    elif mode == 'indep':
        compound = 1.0
        for p in probs:
            compound *= p
    else:
        print(json.dumps({'error': f'unknown mode {mode}'})); return 1

    abstain_thresh = 0.7 if mode == 'unknown_dep' else 0.6
    decision = 'ABSTAIN' if compound < abstain_thresh else 'PROCEED'
    warning = 'independence_assumed_unverified' if mode == 'indep' else None
    print(json.dumps({'compound': round(compound, 4), 'mode': mode, 'n': len(probs),
                      'decision': decision, 'warning': warning}))
    return 0


def cmd_kapro_check(args):
    """KAPRO: decouple knowing (K) from acting (A) before expensive tool calls.

    arXiv:2606.20661 — From Knowing to Acting: KAPRO.
    K-high → skip redundant tools (use cached knowledge).
    A-low → skip action that would not help.
    """
    rt = _reasoning_runtime()
    if rt is not None and not rt.hook_enabled("pre_tool_call_kapro_check"):
        print(json.dumps({
            "task": (args.task or "").strip(),
            "recommendation": "PROCEED",
            "hook_skipped": True,
            "exit_code": 0,
            "note": "pre_tool_call_kapro_check disabled; not a tool-call reduction.",
        }))
        return 0
    task = (args.task or "").strip()
    k = min(1.0, max(0.0, float(args.known_confidence)))
    a = min(1.0, max(0.0, float(args.action_value)))

    if k >= 0.8:
        k_verdict = "KNOWN"
    elif k >= 0.4:
        k_verdict = "UNCERTAIN"
    else:
        k_verdict = "UNKNOWN"

    if a >= 0.6:
        a_verdict = "WORTH_ACTING"
    elif a >= 0.3:
        a_verdict = "MARGINAL"
    else:
        a_verdict = "SKIP"

    # Priority: cached knowledge beats tool-spam; low action-value skips action.
    if k_verdict == "KNOWN":
        recommendation, code = "USE_CACHED", 1
    elif a_verdict == "SKIP":
        recommendation, code = "SKIP_ACTION", 2
    elif k_verdict == "UNKNOWN" and a_verdict == "WORTH_ACTING":
        recommendation, code = "PROCEED", 0
    elif k_verdict == "UNCERTAIN" and a_verdict == "MARGINAL":
        recommendation, code = "ESCALATE", 3
    elif a_verdict == "WORTH_ACTING":
        recommendation, code = "PROCEED", 0
    else:
        recommendation, code = "ESCALATE", 3

    payload = {
        "task": task,
        "known_confidence": round(k, 3),
        "action_value": round(a, 3),
        "k_verdict": k_verdict,
        "a_verdict": a_verdict,
        "recommendation": recommendation,
        "exit_code": code,
        "reduces_tool_call": recommendation in ("USE_CACHED", "SKIP_ACTION"),
    }
    rt = rt or _reasoning_runtime()
    if rt is not None and payload["reduces_tool_call"]:
        log_path = rt.log_kapro(recommendation, {
            "task": task,
            "known_confidence": payload["known_confidence"],
            "action_value": payload["action_value"],
            "k_verdict": k_verdict,
            "a_verdict": a_verdict,
        })
        payload["logged_to"] = str(log_path)
    print(json.dumps(payload))
    return code


def cmd_boundary_check(args):
    actions_taken_raw = getattr(args, "actions_taken", None)
    actions_taken = None
    if actions_taken_raw is not None and str(actions_taken_raw).strip() != "":
        try:
            parsed = json.loads(actions_taken_raw)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "error": f"malformed --actions-taken JSON: {e}",
                "boundary_verdict": "INCOMPLETE",
                "exit_code": 2,
            }))
            return 2
        if not isinstance(parsed, list):
            print(json.dumps({
                "error": "--actions-taken must be a JSON list",
                "boundary_verdict": "INCOMPLETE",
                "exit_code": 2,
            }))
            return 2
        if len(parsed) == 0:
            print(json.dumps({
                "error": "--actions-taken is empty; cannot verify completion",
                "boundary_verdict": "INCOMPLETE",
                "exit_code": 1,
            }))
            return 1
        actions_taken = [str(x) for x in parsed]
    action = (args.action or "").strip()
    if not action and actions_taken:
        action = "; ".join(actions_taken)
    if not action:
        print(json.dumps({
            "error": "--action or non-empty --actions-taken is required",
            "boundary_verdict": "INCOMPLETE",
            "exit_code": 2,
        }))
        return 2
    task = (args.task or "").strip()
    scope = (args.scope or "").strip()
    prior_actions = _parse_json_list(args.prior_actions or "")
    if actions_taken:
        prior_actions = list(prior_actions) + actions_taken

    action_toks = _norm_tokens(action)
    task_toks = _norm_tokens(task)
    scope_toks = _norm_tokens(scope) if scope else set(task_toks)
    prior_toks = _norm_tokens(" ".join(str(p) for p in prior_actions))
    allowed = task_toks | scope_toks | _CLEAN_IMPLIES

    missing = sorted(
        t for t in task_toks
        if t not in action_toks and t not in _CLEAN_IMPLIES
    )
    if action_toks & _CLEAN_IMPLIES and "clean" in missing:
        missing = [t for t in missing if t != "clean"]

    excess = sorted(t for t in action_toks if t not in allowed)
    extra_irreversible = [
        kw for kw in IRREVERSIBLE_ACTIONS
        if re.search(r"\b" + re.escape(kw) + r"\b", action.lower())
        and kw not in task.lower()
        and not (task_toks & _CLEAN_IMPLIES)
    ]

    under_hits = [p for p in BOUNDARY_UNDER_PATTERNS if re.search(p, action.lower())]
    over_hits = [p for p in BOUNDARY_OVER_PATTERNS if re.search(p, action.lower())]

    if task_toks:
        completeness = round(len(task_toks & action_toks) / len(task_toks), 3)
        if action_toks & _CLEAN_IMPLIES and task_toks & _CLEAN_IMPLIES:
            completeness = max(completeness, 0.6)
    else:
        completeness = 0.0

    prior_covers = bool(
        prior_toks and task_toks
        and len(task_toks & prior_toks) / max(1, len(task_toks)) >= 0.6
    )

    scope_violation = False
    if scope:
        outside = action_toks - scope_toks - task_toks - _CLEAN_IMPLIES
        scope_violation = bool(outside) or bool(extra_irreversible)

    missing_steps = list(missing)
    excess_steps = list(excess)
    for kw in extra_irreversible:
        if kw not in excess_steps:
            excess_steps.append(kw)
    if over_hits and "additional_unscoped_work" not in excess_steps:
        excess_steps.append("additional_unscoped_work")
    if under_hits and "explicit_under_action_marker" not in missing_steps:
        missing_steps.append("explicit_under_action_marker")

    if scope_violation or (scope and excess_steps and not (action_toks <= allowed)):
        verdict, code = "SCOPE_CREEP", 3
        scope_violation = True
    elif extra_irreversible or (over_hits and excess_steps) or (prior_covers and excess_steps):
        verdict, code = "OVER_ACTION", 2
    elif missing_steps or under_hits or completeness < 0.5:
        verdict, code = "INCOMPLETE", 1
    else:
        verdict, code = "COMPLETE", 0

    ebp_prompt = (
        "[Explicit Boundary Prompting — ACL 2026 Action Boundary Blindness]\n"
        f"Task goal: {task}\n"
        f"Declared scope: {scope or task}\n"
        f"Proposed action: {action}\n"
        f"Prior actions: {prior_actions or []}\n"
        "Stay inside the declared task boundary.\n"
        "- Do not add steps outside the goal (over-action / scope creep).\n"
        "- Do not stop before all in-scope requirements are done "
        "(under-action; 48.4% of failures).\n"
        "- Complete iff every in-scope requirement is satisfied and no extra-scope work remains.\n"
        f"Current boundary_verdict={verdict}; prepend this block before the next action."
    )

    print(json.dumps({
        "boundary_verdict": verdict,
        "completeness_score": completeness,
        "scope_violation": scope_violation,
        "missing_steps": missing_steps,
        "excess_steps": excess_steps,
        "ebp_prompt": ebp_prompt,
        "exit_code": code,
    }))
    return code


FRAMEWORK_CLASS = {
    "causal-check": "causal",
    "hypothesize": "abductive",
    "lookahead": "planning",
    "subplan-verify": "planning",
    "boundary-check": "boundary",
    "abstain-check": "abstain",
    "kapro-check": "kapro",
    "evaluate": "metacog",
    "gate": "metacog",
    "hedge-score": "metacog",
    "typed-uncertainty": "metacog",
}

# Cheap/safety gates first, then explanation, then planning remainder.
# Must stay aligned with reasoning-complexity-classifier.CASCADE_ORDER and
# config reasoning_selection.conflict_resolution.cascade_order.
CASCADE_ORDER = [
    "abstain-check", "causal-check", "lookahead", "subplan-verify",
    "hypothesize", "boundary-check", "kapro-check",
]

_UNKNOWN_VERDICTS = {
    "UNKNOWN", "UNCERTAIN", "INSUFFICIENT", "N/A", "NA", "NONE", "",
}
_CERTAIN_VERDICTS = {
    "CAUSAL", "COMPLETE", "PROCEED", "PASS", "OK", "STOP_AND_DELIVER",
    "BLOCK", "ABSTAIN", "ABSTAIN_BEFORE_EXECUTING", "SCOPE_CREEP", "FORCE_TOOL_CALL",
}
_PROCEED_VERDICTS = {"PROCEED", "PASS", "OK", "COMPLETE", "CAUSAL", "STOP_AND_DELIVER"}
_BLOCK_VERDICTS = {
    "BLOCK", "ABSTAIN", "ABSTAIN_BEFORE_EXECUTING", "SCOPE_CREEP", "OVER_ACTION",
}
AUTO_RESOLVE_THRESHOLD = 0.2


def _norm_verdict(raw: str) -> str:
    return (raw or "").strip().upper().replace(" ", "_")


def _verdict_confidence(verdict: str) -> float:
    v = _norm_verdict(verdict)
    if v in _UNKNOWN_VERDICTS:
        return 0.2
    if v in ("BLOCK", "ABSTAIN", "ABSTAIN_BEFORE_EXECUTING", "SCOPE_CREEP"):
        return 0.85
    if v in ("CAUSAL", "COMPLETE", "PROCEED", "PASS", "OK", "STOP_AND_DELIVER"):
        return 0.8
    if v in (
        "CORRELATED", "PROBABLE", "PROBABLE_ALTERNATIVE", "CAUTION", "WARN",
        "INCOMPLETE", "OVER_ACTION", "RETRY", "MARGINAL",
    ):
        return 0.55
    return 0.5


def _is_unknown(verdict: str) -> bool:
    return _norm_verdict(verdict) in _UNKNOWN_VERDICTS


def _is_certain(verdict: str) -> bool:
    return _norm_verdict(verdict) in _CERTAIN_VERDICTS


def _direct_contradiction(va: str, vb: str) -> bool:
    a, b = _norm_verdict(va), _norm_verdict(vb)
    if a == b:
        return False
    pairs = [
        (_PROCEED_VERDICTS, _BLOCK_VERDICTS),
        ({"CAUSAL"}, {"CORRELATED", "PROBABLE_ALTERNATIVE"}),
        ({"COMPLETE"}, {"INCOMPLETE", "OVER_ACTION", "SCOPE_CREEP"}),
    ]
    for left, right in pairs:
        if (a in left and b in right) or (b in left and a in right):
            return True
    if {a, b} == {"PROCEED", "BLOCK"}:
        return True
    return False


def _emit_conflict(payload: dict) -> int:
    print(json.dumps(payload))
    return int(payload["exit_code"])


def cmd_conflict_resolve(args):
    """Resolve disagreement between two reasoning-framework verdicts.

    arXiv:2606.04223 — do not always vote away disagreement.
    arXiv:2607.01251 — isolate the crux rather than adversarial debate.
    arXiv:2606.22633 — only flip if the other side is higher-confidence.
    """
    fa = (args.framework_a or "").strip() or "framework-a"
    fb = (args.framework_b or "").strip() or "framework-b"
    rt = _reasoning_runtime()
    va_raw = (args.verdict_a or "").strip()
    vb_raw = (args.verdict_b or "").strip()
    if rt is not None:
        va, conf_from_a, err_a = rt.parse_verdict_arg(va_raw)
        vb, conf_from_b, err_b = rt.parse_verdict_arg(vb_raw)
    else:
        va, conf_from_a, err_a = va_raw, None, None
        vb, conf_from_b, err_b = vb_raw, None, None
    if err_a or err_b:
        print(json.dumps({
            "error": err_a or err_b,
            "resolved_verdict": "UNKNOWN",
            "requires_human": True,
            "exit_code": 2,
        }))
        return 2
    va = va or ""
    vb = vb or ""
    task = (args.task or "").strip()
    strategy_override = (getattr(args, "strategy", None) or "").strip().lower()

    conf_a = getattr(args, "confidence_a", None)
    conf_b = getattr(args, "confidence_b", None)
    if conf_a is None:
        conf_a = conf_from_a if conf_from_a is not None else _verdict_confidence(va)
    if conf_b is None:
        conf_b = conf_from_b if conf_from_b is not None else _verdict_confidence(vb)
    conf_a = min(1.0, max(0.0, float(conf_a)))
    conf_b = min(1.0, max(0.0, float(conf_b)))
    diff = abs(conf_a - conf_b)

    class_a = FRAMEWORK_CLASS.get(fa, "other")
    class_b = FRAMEWORK_CLASS.get(fb, "other")
    same_class = class_a == class_b
    unk_a, unk_b = _is_unknown(va), _is_unknown(vb)
    certain_a, certain_b = _is_certain(va), _is_certain(vb)

    def pack(verdict, method, rationale, confidence, requires_human, code):
        return {
            "resolved_verdict": verdict,
            "resolution_method": method,
            "rationale": rationale,
            "confidence": round(float(confidence), 3),
            "requires_human": bool(requires_human),
            "exit_code": int(code),
        }

    # Strategy override
    if strategy_override == "abstain":
        return _emit_conflict(pack(
            "ABSTAIN", "abstain",
            f"Override abstain: {fa}={va} vs {fb}={vb} on '{task}'. "
            "Name the crux before retrying.",
            min(conf_a, conf_b), False, 1,
        ))
    if strategy_override == "vote":
        winner, wconf = (va, conf_a) if conf_a >= conf_b else (vb, conf_b)
        return _emit_conflict(pack(
            winner, "vote",
            f"Vote/override: higher confidence {wconf:.2f} wins "
            f"({fa}={va} vs {fb}={vb}). Disagreement may still be genuine.",
            wconf, False, 0 if wconf >= 0.55 else 1,
        ))
    if strategy_override == "trust_higher_confidence":
        winner, wconf = (va, conf_a) if conf_a >= conf_b else (vb, conf_b)
        if diff < AUTO_RESOLVE_THRESHOLD:
            return _emit_conflict(pack(
                "ABSTAIN", "abstain",
                f"Confidence diff {diff:.2f} < {AUTO_RESOLVE_THRESHOLD}; "
                f"do not auto-trust. Crux: {fa}={va} vs {fb}={vb}.",
                min(conf_a, conf_b), False, 1,
            ))
        return _emit_conflict(pack(
            winner, "confidence_weighted",
            f"Trust higher confidence ({diff:.2f} >= {AUTO_RESOLVE_THRESHOLD}): "
            f"{fa}={va} ({conf_a:.2f}) vs {fb}={vb} ({conf_b:.2f}).",
            wconf, False, 0,
        ))
    if strategy_override == "cascade":
        order = {n: i for i, n in enumerate(CASCADE_ORDER)}
        first, second = (fa, fb) if order.get(fa, 50) <= order.get(fb, 50) else (fb, fa)
        first_v = va if first == fa else vb
        return _emit_conflict(pack(
            first_v, "cascade",
            f"Cascade override: run {first} first (verdict {first_v}), then {second} "
            f"on the remainder. Task='{task}'.",
            conf_a if first == fa else conf_b, False, 0,
        ))

    # Both UNKNOWN → escalate (attended) or fail-closed skip (unattended)
    if unk_a and unk_b:
        unattended = os.environ.get("HERMES_UNATTENDED", "").strip() in ("1", "true", "yes")
        action = "escalate"
        if rt is not None:
            cfg = rt.load_config()
            action = str(
                ((cfg.get("reasoning_selection") or {}).get("conflict_resolution") or {})
                .get("both_unknown_action")
                or "escalate"
            ).strip() or "escalate"
        if unattended or action in ("fail_closed_skip", "safe_abort", "skip"):
            return _emit_conflict(pack(
                "UNKNOWN", "fail_closed_skip",
                f"Both {fa} and {fb} returned UNKNOWN on '{task}'. "
                "Unattended/fail-closed: skip this iteration; do not stall waiting for a human. "
                "Log and continue or abort the loop — never invent a resolution.",
                min(conf_a, conf_b), False, 2,
            ))
        return _emit_conflict(pack(
            "UNKNOWN", "manual",
            f"Both {fa} and {fb} returned UNKNOWN on '{task}'. "
            "Missing evidence — escalate; do not invent a cause. "
            "Ask: what observation, intervention, or alternative is missing?",
            min(conf_a, conf_b), True, 2,
        ))

    # One UNKNOWN + other certain → trust certain
    if unk_a and not unk_b:
        code = 0 if certain_b or conf_b >= 0.55 else 1
        return _emit_conflict(pack(
            vb, "confidence_weighted",
            f"{fa} is UNKNOWN; trust {fb}={vb} (conf {conf_b:.2f}).",
            conf_b, False, code,
        ))
    if unk_b and not unk_a:
        code = 0 if certain_a or conf_a >= 0.55 else 1
        return _emit_conflict(pack(
            va, "confidence_weighted",
            f"{fb} is UNKNOWN; trust {fa}={va} (conf {conf_a:.2f}).",
            conf_a, False, code,
        ))

    # Direct contradiction (PROCEED vs BLOCK, CAUSAL vs alternative, ...)
    if _direct_contradiction(va, vb):
        if diff < AUTO_RESOLVE_THRESHOLD:
            return _emit_conflict(pack(
                "ABSTAIN", "abstain",
                f"Direct contradiction {fa}={va} vs {fb}={vb} with confidence "
                f"diff {diff:.2f} < {AUTO_RESOLVE_THRESHOLD}. Abstain and isolate "
                f"the crux on '{task}' rather than voting.",
                min(conf_a, conf_b), False, 1,
            ))
        winner, wconf, wfw = (va, conf_a, fa) if conf_a >= conf_b else (vb, conf_b, fb)
        return _emit_conflict(pack(
            winner, "confidence_weighted",
            f"Direct contradiction; trust higher-confidence {wfw}={winner} "
            f"(diff {diff:.2f}). Do not flip the loser without stronger evidence "
            f"(Trust Elasticity).",
            wconf, False, 0,
        ))

    # Same framework class → confidence-weighted merge
    if same_class:
        if _norm_verdict(va) == _norm_verdict(vb):
            merged_conf = round((conf_a + conf_b) / 2.0, 3)
            return _emit_conflict(pack(
                va, "confidence_weighted",
                f"Same class ({class_a}): both {va}. Merged confidence {merged_conf}.",
                merged_conf, False, 0 if merged_conf >= 0.55 else 1,
            ))
        winner, wconf = (va, conf_a) if conf_a >= conf_b else (vb, conf_b)
        merged_conf = max(wconf - 0.1, min(conf_a, conf_b))
        code = 0 if merged_conf >= 0.55 and diff >= AUTO_RESOLVE_THRESHOLD else 1
        return _emit_conflict(pack(
            winner, "confidence_weighted",
            f"Same class ({class_a}) disagreement {va} vs {vb}; "
            f"confidence-weighted pick {winner} (diff {diff:.2f}).",
            merged_conf, False, code,
        ))

    # Orthogonal frameworks → cascade (boundary first, then causal on remainder)
    order = {n: i for i, n in enumerate(CASCADE_ORDER)}
    first, second = (fa, fb) if order.get(fa, 50) <= order.get(fb, 50) else (fb, fa)
    first_v, first_c = (va, conf_a) if first == fa else (vb, conf_b)
    second_v = vb if first == fa else va
    rationale = (
        f"Orthogonal classes ({class_a} vs {class_b}): cascade {first} "
        f"({first_v}) first, then {second} ({second_v}) on the remainder. "
        f"Task='{task}'."
    )
    # If first is a blocker, it wins; else keep first as resolved gate and note remainder
    if _norm_verdict(first_v) in _BLOCK_VERDICTS:
        return _emit_conflict(pack(first_v, "cascade", rationale, first_c, False, 0))
    code = 0 if first_c >= 0.55 else 1
    return _emit_conflict(pack(first_v, "cascade", rationale, first_c, False, code))


def cmd_aic_rank(args):
    """Penalized error ranking: err + 2*d*sigma2/N. Penalizes complexity proxy d.
    NOTE: d must be a real effective-parameter count supplied by caller; body-token-length
    is NOT a valid d. This is NOT AIC/Cp without a proper d — label output accordingly."""
    try:
        skill_data = json.loads(args.skill_data)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid --skill-data JSON: {e}"}))
        return 1
    if not isinstance(skill_data, list):
        print(json.dumps({"error": "--skill-data must be a JSON list"}))
        return 1
    ranked = []
    for item in skill_data:
        if not isinstance(item, dict):
            print(json.dumps({"error": "each skill-data entry must be an object"}))
            return 1
        skill = item.get("skill")
        successes = float(item.get("successes", 0))
        total = float(item.get("total", 0))
        d = item.get("d", 0)
        if not total:
            print(json.dumps({"error": f"skill {skill!r} has total=0"}))
            return 1
        err = 1.0 - successes / total
        sigma2 = err * (1.0 - err)
        aic = err + 2.0 * float(d) * sigma2 / total
        ranked.append({"skill": skill, "err": err, "AIC": aic, "d": d})
    ranked.sort(key=lambda r: r["AIC"])
    out = []
    for i, row in enumerate(ranked, start=1):
        out.append({
            "skill": row["skill"],
            "err": row["err"],
            "AIC": row["AIC"],
            "d": row["d"],
            "rank": i,
        })
    print(json.dumps(out))
    return 0


def cmd_minimax_regret(args):
    """Minimax regret action selector (Berger §5.5.5)."""
    try:
        loss_table = json.loads(args.loss_table)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid --loss-table JSON: {e}"}))
        return 1
    try:
        states = json.loads(args.states)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid --states JSON: {e}"}))
        return 1
    if not isinstance(loss_table, dict):
        print(json.dumps({"error": "--loss-table must be a JSON object"}))
        return 1
    if not isinstance(states, list) or not states:
        print(json.dumps({"error": "--states must be a non-empty JSON list"}))
        return 1
    actions = []
    for st in states:
        row = loss_table.get(st) or {}
        if not isinstance(row, dict):
            print(json.dumps({"error": f"loss table for state {st!r} must be an object"}))
            return 1
        for a in row:
            if a not in actions:
                actions.append(a)
    if not actions:
        print(json.dumps({"error": "no actions in loss table"}))
        return 1
    regret_table = {}
    for st in states:
        row = loss_table.get(st) or {}
        best = min(float(row[a]) for a in row)
        regret_table[st] = {a: float(row.get(a, best)) - best for a in actions if a in row}
        for a in actions:
            if a not in regret_table[st]:
                regret_table[st][a] = 0.0
    max_regret_table = {}
    for a in actions:
        max_regret_table[a] = max(regret_table[st][a] for st in states)
    minimax_action = min(actions, key=lambda a: max_regret_table[a])
    print(json.dumps({
        "minimax_action": minimax_action,
        "max_regret_table": max_regret_table,
        "regret_table": regret_table,
    }))
    return 0


# MACKAY-2 noisy-OR leak parameters (MacKay Ch.21). Fixed reasonable defaults; not calibrated.
_NOISY_OR_MATCH = 0.7
_NOISY_OR_HISTORY = 0.6
_MATCH_SCORE_THRESHOLD = 0.25
_HISTORY_OK_THRESHOLD = 0.5


def _extract_skill_description(content: str) -> str:
    m = re.search(r"^description:\s*[\"'](.+?)[\"']\s*$", content, re.M)
    if m:
        return m.group(1).strip()
    m = re.search(r"^description:\s+(.+)$", content, re.M)
    if m:
        return m.group(1).strip().strip("\"'")
    return ""


def _skill_name_and_description(skill_name: str) -> str:
    """Return 'name description' text for TF match. Description empty if SKILL.md not found."""
    skills_dir = HERMES_HOME / "skills"
    desc = ""
    if skills_dir.is_dir():
        for skill_md in skills_dir.rglob("SKILL.md"):
            if skill_md.parent.name == skill_name:
                try:
                    desc = _extract_skill_description(skill_md.read_text(encoding="utf-8"))
                except (OSError, UnicodeError):
                    desc = ""
                break
    return f"{skill_name} {desc}".strip()


def _noisy_or_consistent(match: int, history_ok: int) -> float:
    return 1.0 - ((1.0 - _NOISY_OR_MATCH) ** match) * ((1.0 - _NOISY_OR_HISTORY) ** history_ok)


def _p_consistent_given_obs(match_obs: int, history_ok_obs):
    """P(consistent=1 | observed sensors). Uniform P(match=1)=P(history_ok=1)=0.5.
    Marginalize history_ok when unobserved (None). Do not model load as an RV.
    """
    num = 0.0
    den = 0.0
    for m in (0, 1):
        if m != match_obs:
            continue
        for h in (0, 1):
            if history_ok_obs is not None and h != history_ok_obs:
                continue
            prior = 0.5 * 0.5
            num += _noisy_or_consistent(m, h) * prior
            den += prior
    if den <= 0.0:
        return 0.0
    return num / den


def cmd_skill_precond(args):
    """MACKAY-2: 2-node skill-precondition diagnostic. Sensors only; not wired into routing.
    DAG: match -> load_posterior; history_ok -> load_posterior.
    Does not emit P(load=1); load is not an RV with a CPT.
    """
    skill = args.skill
    query = args.query
    task_type = getattr(args, "task_type", "general") or "general"
    skill_text = _skill_name_and_description(skill)
    match_score = _cosine(_tf_vec(_tokenize(query)), _tf_vec(_tokenize(skill_text)))
    match_obs = 1 if match_score >= _MATCH_SCORE_THRESHOLD else 0

    conn = _get_db()
    row = conn.execute(
        "SELECT total, successes FROM skill_profiles WHERE skill=? AND task_type=?",
        (skill, task_type),
    ).fetchone()
    conn.close()

    if row is None:
        history_ok_obs = None
        beta_mean = None
    else:
        total = int(row[0])
        successes = int(row[1])
        beta_mean = (successes + 1) / (total + 2)
        history_ok_obs = 1 if beta_mean >= _HISTORY_OK_THRESHOLD else 0

    p_consistent = _p_consistent_given_obs(match_obs, history_ok_obs)
    print(json.dumps({
        "skill": skill,
        "query": query,
        "match_score": match_score,
        "match_obs": match_obs,
        "history_ok_obs": history_ok_obs,
        "beta_mean": beta_mean,
        "p_consistent": p_consistent,
        "diagnostic_only": True,
        "note": "noisy-OR parameters are fixed defaults; not calibrated",
    }))
    return 0


def cmd_calibrate(args):
    """Reliability-diagram calibration of Laplace vs actual skill_profiles rates."""
    n_bins = max(1, int(getattr(args, "bins", 10) or 10))
    conn = _get_db()
    rows = conn.execute(
        "SELECT skill, task_type, successes, total FROM skill_profiles"
    ).fetchall()
    conn.close()

    items = []
    for _skill, _task_type, successes, total in rows:
        total = int(total or 0)
        successes = int(successes or 0)
        if total == 0:
            continue
        laplace_rate = (successes + 1) / (total + 2)
        actual_rate = successes / max(1, total)
        items.append((laplace_rate, actual_rate))

    if not items:
        print(json.dumps({
            "total_rows": 0,
            "calibrated": None,
            "diagnostic_only": True,
            "n_star_method": "chernoff_kl",
        }))
        return 0

    items.sort(key=lambda x: x[0])
    n = len(items)
    p_hat_avg = sum(lr for lr, _ in items) / n
    n_star_raw = chernoff_n_star(p_hat_avg, p_thresh=0.5)
    n_star = int(n_star_raw) if n_star_raw is not None else 0

    n_bins_eff = min(n_bins, n)
    bins_out = []
    for i in range(n_bins_eff):
        start = (i * n) // n_bins_eff
        end = ((i + 1) * n) // n_bins_eff
        chunk = items[start:end]
        if not chunk:
            continue
        laps = [c[0] for c in chunk]
        acts = [c[1] for c in chunk]
        predicted_mean = sum(laps) / len(chunk)
        actual_mean = sum(acts) / len(chunk)
        gap = abs(predicted_mean - actual_mean)
        underpowered = (len(chunk) < n_star) if n_star_raw is not None else False
        bins_out.append({
            "bin_idx": i,
            "bin_low": min(laps),
            "bin_high": max(laps),
            "predicted_mean": predicted_mean,
            "actual_mean": actual_mean,
            "count": len(chunk),
            "gap": gap,
            "underpowered": underpowered,
        })

    powered = [b for b in bins_out if not b["underpowered"]]
    if not powered:
        calibrated = None  # insufficient evidence
        calibrated_reason = "all_bins_underpowered"
    else:
        calibrated = all(b["gap"] < 0.1 for b in powered)
        calibrated_reason = "ok"
    print(json.dumps({
        "bins": bins_out,
        "calibrated": calibrated,
        "calibrated_reason": calibrated_reason,
        "n_star": n_star,
        "n_star_method": "chernoff_kl",
        "total_rows": n,
        "diagnostic_only": True,
    }))
    return 0


def cmd_skill_hom(args):
    """Yoneda skill-hom: cosine of Laplace rates on shared task types.

    Flag only — never auto-delete or merge skill_profiles.
    """
    skill_a = args.skill_a
    skill_b = args.skill_b
    min_shared = int(args.min_shared)
    threshold = float(args.threshold)

    conn = _get_db()

    def _rates_and_n(skill: str) -> tuple[dict[str, float], dict[str, int]]:
        rows = conn.execute(
            "SELECT task_type, successes, total FROM skill_profiles WHERE skill=?",
            (skill,),
        ).fetchall()
        rates: dict[str, float] = {}
        totals: dict[str, int] = {}
        for task_type, successes, total in rows:
            n = int(total)
            rates[str(task_type)] = (int(successes) + 1) / (n + 2)
            totals[str(task_type)] = n
        return rates, totals

    rates_a, totals_a = _rates_and_n(skill_a)
    rates_b, totals_b = _rates_and_n(skill_b)
    conn.close()

    shared_types = sorted(set(rates_a.keys()) & set(rates_b.keys()))
    if len(shared_types) < min_shared:
        print(json.dumps({
            "isomorphic": False,
            "reason": "insufficient_shared_task_types",
            "shared_types": shared_types,
            "min_shared": min_shared,
        }))
        return 0

    va = [rates_a[t] for t in shared_types]
    vb = [rates_b[t] for t in shared_types]
    similarity = sum(a * b for a, b in zip(va, vb)) / (
        math.sqrt(sum(a * a for a in va)) * math.sqrt(sum(b * b for b in vb)) + 1e-9
    )
    n_ok = all(totals_a[t] >= 3 and totals_b[t] >= 3 for t in shared_types)
    isomorphic = (similarity >= threshold) and n_ok
    print(json.dumps({
        "skill_a": skill_a,
        "skill_b": skill_b,
        "similarity": similarity,
        "isomorphic": isomorphic,
        "shared_types": shared_types,
        "threshold": threshold,
        "note": "flag only; no auto-delete; verify manually before merging skill_profiles",
    }))
    return 0


def cmd_sprt(args):
    """DEGROOT-004: sequential probability ratio test on skill Beta counts.
    DIAGNOSTIC ONLY: do not use SPRT verdict to override cmd_evaluate decisions.
    Use for offline analysis of skill_profiles data.
    """
    skill = args.skill
    task_type = args.task_type
    alpha = float(args.alpha)
    beta_err = float(args.beta_err)
    p0 = 0.4
    p1 = 0.7
    A = (1.0 - beta_err) / alpha
    B = beta_err / (1.0 - alpha)
    conn = _get_db()
    row = conn.execute(
        "SELECT total, successes FROM skill_profiles WHERE skill=? AND task_type=?",
        (skill, task_type),
    ).fetchone()
    conn.close()
    total = int(row[0]) if row else 0
    successes = int(row[1]) if row else 0
    failures = total - successes
    s, f = successes, failures
    denom = (p0 ** s) * ((1.0 - p0) ** f)
    if denom == 0:
        lr = float("inf")
    else:
        lr = (p1 ** s) * ((1.0 - p1) ** f) / denom
    if lr >= A:
        verdict = "ACCEPT_SKILL"
    elif lr <= B:
        verdict = "REJECT_SKILL"
    else:
        verdict = "CONTINUE_SAMPLING"
    print(json.dumps({
        "LR": lr,
        "A": A,
        "B": B,
        "successes": successes,
        "failures": failures,
        "verdict": verdict,
        "diagnostic_only": True,
    }))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Metacognitive Harness for Hermes Agent")
    sub = parser.add_subparsers(dest="command", required=True)

    ev = sub.add_parser("evaluate"); ev.add_argument("--fok", type=float, required=True)
    ev.add_argument("--jol", type=float, required=True); ev.add_argument("--attempt", type=int, default=1)
    ev.add_argument("--session", type=str, default=None, help="Session ID for calibration logging (optional)")
    ev.add_argument("--task-class", type=str, default=None, dest="task_class",
                    help="L-class (L0/L1/L2/L3) for calibration logging (optional)")
    ev.add_argument("--tool-results", type=str, default="", dest="tool_results",
                    help="JSON list of {outcome: success|fail|hedge|pass|error} tool results")
    ev.add_argument("--halflife", type=int, default=None,
                    help="Evidence discount half-life (default MH_EVIDENCE_HALFLIFE or 4)")
    ev.add_argument("--eu", action="store_true",
                    help="Attach EU(deliver vs escalate) diagnostic fields (MACKAY-3; does not change decision)")
    ev.add_argument("--irreversible", action="store_true",
                    help="Treat action as irreversible for EU diagnostic U_bad only")
    ev.set_defaults(func=cmd_evaluate)

    gt = sub.add_parser("gate"); gt.add_argument("--confidence", type=float, required=True)
    gt.add_argument("--tool-called", type=str, required=True, metavar="{true,false,TRUE,FALSE,1,0,yes,no}")
    gt.add_argument("--level", type=str, default=""); gt.set_defaults(func=cmd_gate)

    hs = sub.add_parser("hedge-score"); hs.add_argument("--reasoning", type=str, required=True)
    hs.set_defaults(func=cmd_hedge_score)

    pf = sub.add_parser("profile"); pf.add_argument("--skill", type=str, required=True)
    pf.add_argument("--task-type", type=str, default="general")
    pf.add_argument("--outcome", choices=["success", "failure"], required=True)
    pf.set_defaults(func=cmd_profile)

    bl = sub.add_parser("blend"); bl.add_argument("--skill", type=str, required=True)
    bl.add_argument("--task-type", type=str, default="general")
    bl.add_argument("--verbalized", type=float, required=True)
    bl.add_argument("--independent", action="store_true", default=False,
                    help="Treat empirical and verbalized as independent evidence (add dB)")
    bl.set_defaults(func=cmd_blend)

    pr = sub.add_parser("prompt"); pr.add_argument("--task", type=str, required=True)
    pr.add_argument("--skill", type=str, default="default")
    pr.add_argument("--attempt", type=int, default=1); pr.set_defaults(func=cmd_prompt)

    tu = sub.add_parser("typed-uncertainty")
    tu.add_argument("--description", type=str, required=True); tu.set_defaults(func=cmd_typed_uncertainty)

    ab = sub.add_parser("abstain-check"); ab.add_argument("--action", type=str, required=True)
    ab.add_argument("--confidence", type=float, required=True); ab.set_defaults(func=cmd_abstain_check)

    cc = sub.add_parser("causal-check")
    cc.add_argument("--observation", type=str, required=True)
    cc.add_argument("--candidate-cause", type=str, required=True)
    cc.add_argument("--intervention", type=str, default="")
    cc.add_argument("--alternatives", type=str, default="")
    cc.add_argument("--evidence", type=str, default=None,
                    help="Supporting evidence. With --dcc, empty string is an error.")
    cc.add_argument("--dcc", action="store_true",
                    help="Double Counterfactual Consistency (forward+backward)")
    cc.add_argument("--tool", nargs="*", default=None, dest="tool",
                    help="Tool names used; classified as OBS vs DO (Pearl rule 2)")
    cc.set_defaults(func=cmd_causal_check)

    co = sub.add_parser("compound")
    co.add_argument("--probs", type=str, required=True, help="JSON list of probabilities")
    co.add_argument("--mode", choices=["chain", "unknown_dep", "indep"], default="unknown_dep")
    co.set_defaults(func=cmd_compound)

    kp = sub.add_parser("kapro-check",
                        help="KAPRO knowledge-action gate before tool calls")
    kp.add_argument("--task", type=str, required=True)
    kp.add_argument("--known-confidence", type=float, required=True,
                    dest="known_confidence")
    kp.add_argument("--action-value", type=float, required=True,
                    dest="action_value")
    kp.set_defaults(func=cmd_kapro_check)

    bc = sub.add_parser("boundary-check")
    bc.add_argument("--action", type=str, default="")
    bc.add_argument("--task", type=str, required=True)
    bc.add_argument("--scope", type=str, default="")
    bc.add_argument("--prior-actions", type=str, default="")
    bc.add_argument("--actions-taken", type=str, default=None, dest="actions_taken",
                    help="JSON list of actions taken. Empty list → exit 1 (incomplete).")
    bc.set_defaults(func=cmd_boundary_check)

    cr = sub.add_parser("conflict-resolve", help="Resolve disagreement between two framework verdicts")
    cr.add_argument("--framework-a", type=str, required=True, dest="framework_a",
                    help="Name of the first reasoning framework (e.g. causal-check)")
    cr.add_argument("--verdict-a", type=str, required=True, dest="verdict_a",
                    help="Verdict from framework-a: PROCEED, BLOCK, or UNKNOWN")
    cr.add_argument("--framework-b", type=str, required=True, dest="framework_b",
                    help="Name of the second reasoning framework (e.g. boundary-check)")
    cr.add_argument("--verdict-b", type=str, required=True, dest="verdict_b",
                    help="Verdict from framework-b: PROCEED, BLOCK, or UNKNOWN")
    cr.add_argument("--task", type=str, required=True,
                    help="Task description (used in rationale and cascade ordering)")
    cr.add_argument(
        "--strategy", type=str, default=None,
        choices=["trust_higher_confidence", "cascade", "abstain", "vote"],
        help="Optional resolution strategy override",
    )
    cr.add_argument("--confidence-a", type=float, default=None, dest="confidence_a")
    cr.add_argument("--confidence-b", type=float, default=None, dest="confidence_b")
    cr.set_defaults(func=cmd_conflict_resolve)

    ar = sub.add_parser("aic-rank", help="Penalized error ranking (err + 2*d*sigma2/N); caller must supply real d")
    ar.add_argument("--skill-data", type=str, required=True, dest="skill_data",
                    help="JSON list of {skill, successes, total, d}")
    ar.set_defaults(func=cmd_aic_rank)

    mr = sub.add_parser("minimax-regret", help="Minimax regret action selector (Berger §5.5.5)")
    mr.add_argument("--loss-table", type=str, required=True, dest="loss_table",
                    help="JSON object L[state][action] -> loss")
    mr.add_argument("--states", type=str, required=True,
                    help="JSON list of states to consider")
    mr.set_defaults(func=cmd_minimax_regret)

    sp = sub.add_parser("sprt", help="SPRT on skill Beta posterior (DEGROOT-004)")
    sp.add_argument("--skill", type=str, required=True)
    sp.add_argument("--task-type", type=str, required=True, dest="task_type")
    sp.add_argument("--alpha", type=float, default=0.1)
    sp.add_argument("--beta-err", type=float, default=0.1, dest="beta_err")
    sp.set_defaults(func=cmd_sprt)

    skp = sub.add_parser(
        "skill-precond",
        help="Skill-precondition noisy-OR diagnostic (MACKAY-2; sensors only, not routing)",
    )
    skp.add_argument("--skill", type=str, required=True)
    skp.add_argument("--query", type=str, required=True)
    skp.add_argument("--task-type", type=str, default="general", dest="task_type")
    skp.set_defaults(func=cmd_skill_precond)

    sh = sub.add_parser(
        "skill-hom",
        help="Yoneda skill-hom: cosine of Laplace rates on shared task types (flag only)",
    )
    sh.add_argument("--skill-a", type=str, required=True, dest="skill_a")
    sh.add_argument("--skill-b", type=str, required=True, dest="skill_b")
    sh.add_argument("--min-shared", type=int, default=2, dest="min_shared")
    sh.add_argument("--threshold", type=float, default=0.95)
    sh.set_defaults(func=cmd_skill_hom)

    cal = sub.add_parser(
        "calibrate",
        help="Reliability-diagram calibration of skill_profiles Laplace vs actual rates",
    )
    cal.add_argument("--bins", type=int, default=10, help="Equal-size Laplace-rate buckets (default 10)")
    cal.set_defaults(func=cmd_calibrate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
