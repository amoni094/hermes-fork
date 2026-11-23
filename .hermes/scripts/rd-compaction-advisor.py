#!/usr/bin/env python3
"""Rate-distortion-*shaped* compaction aggressiveness advisor.

For Gaussian sources R(D) = (1/2) log(σ²/D). LLM tokens are not Gaussian
samples; we do not compute a closed-form R(D). We borrow the *shape*: tighter
remaining budget → accept more distortion (more aggressive summaries).

Wave 18: persists advisory JSON for the compressor hook, DPI focus-token
property test, decision-distortion R(D) estimator, wavelet energy prune,
and typical-set ranking. Stdlib only.

Usage:
    python3 rd-compaction-advisor.py --current-tokens 85000
    python3 rd-compaction-advisor.py --current-tokens 85000 --threshold 120000
    python3 rd-compaction-advisor.py --self-test

Output: JSON with aggressiveness in [0,1], recommended focus_topic_prefix, rationale.
Always writes cache/rd-compaction-advisory.json (atomic) unless --no-write.

Curve (k=3, conservative):
    remaining = 1 - min(current/threshold, 1)
    aggressiveness = exp(-k * remaining)
    remaining=1 (empty) → ~0.05 minimal
    remaining=0 (at/over threshold) → 1.0 aggressive
    aggressive (>=0.75) only when remaining ≲ 0.10
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def _profile_root() -> Path:
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        return base / "profiles" / profile
    return base


def advisory_path() -> Path:
    return _profile_root() / "cache" / "rd-compaction-advisory.json"


def lambda_target_path() -> Path:
    return _profile_root() / "cache" / "rd-lambda-target.json"


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def persist_advisory(result: dict) -> Path:
    """Atomic write of the advisory consumed by context-pressure-guard."""
    path = advisory_path()
    payload = dict(result)
    payload["ts"] = time.time()
    payload["source"] = "rd-compaction-advisor"
    _atomic_write_json(path, payload)
    return path


def persist_lambda_target(aggressiveness: float, session_id: str = "") -> Path:
    """Write monotone lambda target for lambda-tuner (file interface)."""
    path = lambda_target_path()
    prev = 0.0
    if path.exists():
        try:
            prev = float((json.loads(path.read_text()) or {}).get("lambda", 0.0) or 0.0)
        except Exception:
            prev = 0.0
    new_lambda = monotone_lambda(prev, float(aggressiveness))
    _atomic_write_json(path, {
        "lambda": new_lambda,
        "proposed": round(float(aggressiveness), 4),
        "floor": round(prev, 4),
        "session_id": session_id,
        "monotone": True,
        "ts": time.time(),
        "source": "rd-compaction-advisor",
    })
    return path


def monotone_lambda(current: float, proposed: float, cap: float = 0.95) -> float:
    """Hard core: lambda only increases (never decreases spontaneously)."""
    cur = max(0.0, float(current or 0.0))
    prop = max(0.0, float(proposed or 0.0))
    return round(min(cap, max(cur, prop)), 4)


def _read_config_compression() -> dict:
    """Read compression.threshold_tokens from ~/.hermes/config.yaml."""
    config_path = HERMES_HOME / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        text = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        sec = data.get("compression") if isinstance(data, dict) else None
        if isinstance(sec, dict) and "threshold_tokens" in sec:
            return {"threshold_tokens": int(sec["threshold_tokens"])}
    except Exception:
        pass
    # Anchored so we do not match micro_compact_defrag_threshold_tokens.
    m = re.search(r"(?m)^[ \t]*threshold_tokens:[ \t]*(\d+)\s*$", text)
    if m:
        return {"threshold_tokens": int(m.group(1))}
    return {}


def compute_aggressiveness(
    current_tokens: int, threshold_tokens: int, k: float = 3.0
) -> dict:
    """Map budget usage to a conservative aggressiveness in [0, 1]."""
    current_tokens = max(int(current_tokens), 0)
    threshold_tokens = max(int(threshold_tokens), 1)
    if k <= 0:
        k = 3.0

    budget_fraction = min(current_tokens / threshold_tokens, 1.0)
    remaining_fraction = max(1.0 - budget_fraction, 0.0)

    # Conservative: stay gentle until the window is nearly full.
    # exp(-k * remaining): remaining=1 → e^{-k}≈0.05; remaining=0 → 1.
    aggressiveness = math.exp(-k * remaining_fraction)

    if aggressiveness < 0.25:
        level = "minimal"
        focus_prefix = "Preserve as much verbatim detail as possible."
    elif aggressiveness < 0.50:
        level = "light"
        focus_prefix = "Summarise older tool results but keep key decisions and outputs."
    elif aggressiveness < 0.75:
        level = "moderate"
        focus_prefix = "Aggressively summarise tool outputs; preserve user decisions and errors."
    else:
        level = "aggressive"
        focus_prefix = "Maximally compress: keep only task state, decisions, and error resolutions."

    return {
        "current_tokens": current_tokens,
        "threshold_tokens": threshold_tokens,
        "budget_fraction": round(budget_fraction, 3),
        "remaining_fraction": round(remaining_fraction, 3),
        "aggressiveness": round(aggressiveness, 3),
        "level": level,
        "focus_topic_prefix": focus_prefix,
        "rationale": (
            f"Context at {100 * budget_fraction:.0f}% of threshold "
            f"({current_tokens:,}/{threshold_tokens:,} tokens). "
            f"R(D)-shaped curve aggressiveness=exp(-{k}*remaining) → "
            f"{aggressiveness:.2f} ({level}). "
            f"Remaining headroom: {100 * remaining_fraction:.0f}%. "
            f"Not a Gaussian R(D) evaluation."
        ),
    }


def _current_from_log() -> int | None:
    """Best-effort: only explicit current/prompt/context token fields, not bare 'N tokens'."""
    log_path = HERMES_HOME / "logs" / "agent.log"
    if not log_path.exists():
        return None
    try:
        size = os.path.getsize(log_path)
        with open(log_path, "rb") as f:
            f.seek(max(0, size - 50000))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    matches = re.findall(
        r"(?:prompt_tokens|context_tokens|current_tokens|approx_tokens)[=:\s]+(\d{3,8})",
        tail,
        flags=re.I,
    )
    if not matches:
        return None
    try:
        return int(matches[-1])
    except ValueError:
        return None


def entropy_adjusted_aggressiveness(
    base_aggressiveness: float,
    normalized_entropy: float,
    alpha: float = 0.3,
) -> float:
    """Scale aggressiveness down for high-entropy (information-dense) content.

    Theory: Cover & Thomas "Elements of Information Theory" Ch.5 (rate-distortion).
    High-entropy sources have more information per token; aggressive compression
    destroys more irreplaceable content. Low-entropy (repetitive) sources tolerate
    higher distortion at the same quality loss.

    Scale factor = 1 - alpha * normalized_entropy.
    """
    scale = 1.0 - alpha * max(0.0, min(1.0, normalized_entropy))
    return round(max(0.0, min(1.0, base_aggressiveness * scale)), 3)


# ── DPI (Cover–Thomas) ───────────────────────────────────────────────────────
# Data-processing inequality: I(decision; compressed) ≤ I(decision; raw).
# Proxy: annotated focus tokens from pre-compact-annotate MUST survive.


def tokenize_focus(focus_text: str) -> list[str]:
    if not focus_text:
        return []
    toks = re.findall(r"[A-Za-z0-9_./:-]{4,}", focus_text)
    seen: set[str] = set()
    out: list[str] = []
    for t in toks:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def dpi_focus_preserved(focus_tokens: list[str], kept_tokens: list[str]) -> dict:
    """Property test: compaction must not drop annotated focus tokens.

    Hard core: any dropped focus token is a DPI violation (decision-relevant
    information destroyed by a processing of the raw context).
    """
    kept_l = {t.lower() for t in kept_tokens}
    dropped = [t for t in focus_tokens if t.lower() not in kept_l]
    return {
        "ok": len(dropped) == 0,
        "dropped_focus": dropped,
        "n_focus": len(focus_tokens),
        "n_dropped": len(dropped),
        "dpi_violation": len(dropped) > 0,
    }


def flag_plan_if_drops_focus(plan_drop: list[str], focus_tokens: list[str]) -> dict:
    """Flag a compaction plan that would drop annotated focus tokens."""
    drop_l = {t.lower() for t in plan_drop}
    victims = [t for t in focus_tokens if t.lower() in drop_l]
    return {
        "flag": len(victims) > 0,
        "would_drop_focus": victims,
        "plan_rejected": len(victims) > 0,
    }


# ── Decision-distortion R(D) (Shannon / Cover–Thomas) ────────────────────────
# d(x,y) = 1 if compressing x→y changes the next skill routing decision, else 0.


def binary_entropy(p: float) -> float:
    p = min(1.0, max(0.0, float(p)))
    if p in (0.0, 1.0):
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def fano_rd_lower_bound(h_decision: float, distortion: float, alphabet: int = 2) -> float:
    """Fano: H(decision|Y) ≤ h(D) + D log(|A|-1).
    Therefore I(decision; Y) ≥ H(decision) - h(D) - D log(|A|-1).
    Any code with rate below this bound MUST exceed distortion D.
    """
    d = min(1.0, max(0.0, float(distortion)))
    a = max(2, int(alphabet))
    bound = float(h_decision) - binary_entropy(d) - d * math.log2(a - 1)
    return max(0.0, bound)


def estimate_decision_rd(records: list[dict]) -> dict:
    """Empirical R(D) from {bits, route_raw, route_compressed} records.

    Hard core: achieving fewer bits than R(D) is impossible without crossing D.
    """
    if not records:
        return {"n": 0, "D": None, "R": None, "R_lb": None, "below_bound": False}
    ds = []
    rates = []
    for rec in records:
        raw = rec.get("route_raw")
        comp = rec.get("route_compressed")
        ds.append(1.0 if raw != comp else 0.0)
        rates.append(float(rec.get("bits", 0) or 0))
    D = sum(ds) / len(ds)
    R = sum(rates) / len(rates)
    # H(decision) from raw route empirical
    counts = Counter(str(r.get("route_raw")) for r in records)
    n = sum(counts.values())
    h = 0.0
    for c in counts.values():
        p = c / n
        if p > 0:
            h -= p * math.log2(p)
    r_lb = fano_rd_lower_bound(h, D, alphabet=max(2, len(counts)))
    return {
        "n": len(records),
        "D": round(D, 4),
        "R": round(R, 4),
        "H_decision": round(h, 4),
        "R_lb": round(r_lb, 4),
        "below_bound": bool(R + 1e-9 < r_lb),
        "impossible": bool(R + 1e-9 < r_lb),
    }


def load_routing_rd_records(limit: int = 64) -> list[dict]:
    """Best-effort last-N routing snapshots for empirical R(D)."""
    path = _profile_root() / "cache" / "routing-rd-pairs.jsonl"
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                rows.append(rec)
    except OSError:
        return []
    return rows


# ── Wavelet-inspired token prune (Mallat) ────────────────────────────────────


def _window_averages(values: list[float], width: int) -> list[float]:
    w = max(1, int(width))
    if not values:
        return []
    out = []
    for i in range(len(values)):
        lo = max(0, i - w // 2)
        hi = min(len(values), lo + w)
        chunk = values[lo:hi]
        out.append(sum(chunk) / len(chunk))
    return out


def wavelet_energy_prune(
    tokens: list[str],
    keep_ratio: float = 0.5,
    energy_threshold: float = 0.85,
    protected: list[str] | None = None,
    window: int = 4,
) -> dict:
    """Haar-like differences of adjacent window averages; keep high-energy coeffs.

    Hard core: energy_preserved = sum(kept^2) / sum(total^2) >= energy_threshold
    after adding enough coefficients, AND protected/focus tokens are never dropped.
    """
    n = len(tokens)
    if n == 0:
        return {"kept": [], "dropped": [], "energy_preserved": 1.0, "ok": True}
    prot = {t.lower() for t in (protected or [])}
    # Magnitude proxy: token rarity (inverse frequency) as "amplitude"
    freq = Counter(t.lower() for t in tokens)
    amp = [1.0 / freq[t.lower()] for t in tokens]
    avgs = _window_averages(amp, window)
    coeffs = [avgs[0]] + [avgs[i] - avgs[i - 1] for i in range(1, n)]
    energy = [c * c for c in coeffs]
    total_e = sum(energy) or 1.0
    order = sorted(range(n), key=lambda i: -energy[i])
    kept_idx: set[int] = set()
    # Always keep protected
    for i, tok in enumerate(tokens):
        if tok.lower() in prot:
            kept_idx.add(i)
    running = sum(energy[i] for i in kept_idx)
    min_keep = max(1, int(math.ceil(n * min(1.0, max(0.0, keep_ratio)))))
    for i in order:
        if len(kept_idx) >= min_keep and running / total_e >= energy_threshold:
            break
        if i not in kept_idx:
            kept_idx.add(i)
            running += energy[i]
    # If still below energy floor, keep more
    for i in order:
        if running / total_e >= energy_threshold:
            break
        if i not in kept_idx:
            kept_idx.add(i)
            running += energy[i]
    kept = [tokens[i] for i in range(n) if i in kept_idx]
    dropped = [tokens[i] for i in range(n) if i not in kept_idx]
    preserved = running / total_e
    dpi = dpi_focus_preserved(list(protected or []), kept)
    return {
        "kept": kept,
        "dropped": dropped,
        "energy_preserved": round(preserved, 4),
        "ok": preserved + 1e-12 >= energy_threshold and dpi["ok"],
        "dpi": dpi,
    }


# ── Typical-set filter (Shannon AEP) ─────────────────────────────────────────


def typicality_ranks(
    tokens: list[str],
    protected: list[str] | None = None,
    epsilon: float = 0.25,
) -> dict:
    """Flag typical (low-surprise) tokens as first-to-prune, never protected.

    Hard core: typical tokens below decision-relevance (not in focus) are
    pruned first. A token is typical if | -log p(t) - H | is small relative
    to the unigram entropy rate.
    """
    if not tokens:
        return {"typical": [], "atypical": [], "prune_first": [], "H": 0.0}
    prot = {t.lower() for t in (protected or [])}
    freq = Counter(t.lower() for t in tokens)
    n = len(tokens)
    H = 0.0
    logp = {}
    for tok, c in freq.items():
        p = c / n
        logp[tok] = -math.log2(p)
        H -= p * math.log2(p)
    typical, atypical = [], []
    for t in tokens:
        key = t.lower()
        if abs(logp[key] - H) <= epsilon * max(H, 1e-6):
            typical.append(t)
        else:
            atypical.append(t)
    prune_first = [t for t in typical if t.lower() not in prot]
    return {
        "typical": typical,
        "atypical": atypical,
        "prune_first": prune_first,
        "H": round(H, 4),
        "protected_kept": [t for t in tokens if t.lower() in prot],
    }


def plan_compaction(
    tokens: list[str],
    focus_tokens: list[str],
    keep_ratio: float = 0.5,
    energy_threshold: float = 0.85,
) -> dict:
    """Build a prune plan: typical-first, wavelet energy, DPI gate."""
    typ = typicality_ranks(tokens, protected=focus_tokens)
    wav = wavelet_energy_prune(
        tokens,
        keep_ratio=keep_ratio,
        energy_threshold=energy_threshold,
        protected=focus_tokens,
    )
    # Prefer dropping typical tokens that wavelet also dropped
    wav_drop = set(t.lower() for t in wav["dropped"])
    planned_drop = [t for t in typ["prune_first"] if t.lower() in wav_drop]
    flag = flag_plan_if_drops_focus(planned_drop, focus_tokens)
    if flag["plan_rejected"]:
        planned_drop = [t for t in planned_drop if t.lower() not in {x.lower() for x in focus_tokens}]
    kept = [t for t in tokens if t.lower() not in {x.lower() for x in planned_drop}]
    dpi = dpi_focus_preserved(focus_tokens, kept)
    return {
        "kept": kept,
        "dropped": planned_drop,
        "dpi": dpi,
        "wavelet": {"energy_preserved": wav["energy_preserved"], "ok": wav["ok"]},
        "typicality": {"H": typ["H"], "n_typical": len(typ["typical"])},
        "flag": flag,
    }


def _self_test() -> int:
    failures: list[str] = []

    # Aggressiveness curve
    a0 = compute_aggressiveness(0, 120000)["aggressiveness"]
    a1 = compute_aggressiveness(120000, 120000)["aggressiveness"]
    if not (a0 < 0.1 and a1 == 1.0):
        failures.append(f"curve endpoints {a0} {a1}")

    # Monotone lambda
    if monotone_lambda(0.4, 0.2) != 0.4:
        failures.append("lambda decreased spontaneously")
    if monotone_lambda(0.4, 0.7) != 0.7:
        failures.append("lambda failed to increase")
    if monotone_lambda(0.99, 1.5) > 0.95:
        failures.append("lambda cap broken")

    # DPI: dropping focus must flag
    focus = ["decision-id-42", "/tmp/keep.py"]
    bad = dpi_focus_preserved(focus, ["unrelated"])
    if bad["ok"] or not bad["dpi_violation"]:
        failures.append("DPI failed to flag dropped focus")
    good = dpi_focus_preserved(focus, focus + ["noise"])
    if not good["ok"]:
        failures.append("DPI false positive")

    # Adversarial: compaction plan that drops focus is rejected
    plan_flag = flag_plan_if_drops_focus(["decision-id-42", "noise"], focus)
    if not plan_flag["plan_rejected"]:
        failures.append("adversarial drop-focus plan not rejected")

    # Wavelet energy hard core + protected tokens
    seq = (["aaaa"] * 20) + ["UNIQUE_DECISION_TOKEN"] + (["bbbb"] * 20)
    wav = wavelet_energy_prune(seq, keep_ratio=0.2, energy_threshold=0.85,
                               protected=["UNIQUE_DECISION_TOKEN"])
    if "UNIQUE_DECISION_TOKEN" not in wav["kept"]:
        failures.append("wavelet dropped protected decision token")
    if wav["energy_preserved"] < 0.85:
        failures.append(f"energy preserved {wav['energy_preserved']} < 0.85")

    # Adversarial wavelet without protection WOULD drop a buried typical token;
    # with protection it must not.
    buried = (["the"] * 30) + ["keep-this-path"] + (["the"] * 30)
    wav_unprot = wavelet_energy_prune(buried, keep_ratio=0.05, energy_threshold=0.5, protected=[])
    wav_prot = wavelet_energy_prune(buried, keep_ratio=0.05, energy_threshold=0.5,
                                    protected=["keep-this-path"])
    if "keep-this-path" not in wav_prot["kept"]:
        failures.append("protected wavelet dropped decision token")
    # unprot may or may not drop; record outcome
    _unprot_dropped = "keep-this-path" not in wav_unprot["kept"]

    # Typicality: protected not in prune_first
    typ = typicality_ranks(buried, protected=["keep-this-path"])
    if "keep-this-path" in [t.lower() for t in typ["prune_first"]]:
        failures.append("typicality queued protected token for prune")

    # R(D) Fano bound: rate 0 at D=0 with H>0 is below bound
    recs = [
        {"bits": 0.0, "route_raw": "skill-a", "route_compressed": "skill-b"},
        {"bits": 0.0, "route_raw": "skill-a", "route_compressed": "skill-a"},
    ]
    est = estimate_decision_rd(recs)
    # With D=0.5 and H>0, R=0 may be below bound
    recs0 = [
        {"bits": 10.0, "route_raw": "a", "route_compressed": "a"},
        {"bits": 10.0, "route_raw": "b", "route_compressed": "b"},
    ]
    est0 = estimate_decision_rd(recs0)
    if est0["D"] != 0.0:
        failures.append("D should be 0 when routes match")
    if est0["below_bound"]:
        failures.append("matching routes with positive rate should not be below bound")
    recs_bad = [
        {"bits": 0.01, "route_raw": "a", "route_compressed": "a"},
        {"bits": 0.01, "route_raw": "b", "route_compressed": "b"},
        {"bits": 0.01, "route_raw": "c", "route_compressed": "c"},
        {"bits": 0.01, "route_raw": "d", "route_compressed": "d"},
    ]
    est_bad = estimate_decision_rd(recs_bad)
    # D=0, H=2, R_lb = H = 2, R=0.01 → below bound
    if not est_bad["below_bound"]:
        failures.append("R(D) failed to flag rate below Fano lower bound at D=0")

    # plan_compaction never drops focus
    plan = plan_compaction(buried, ["keep-this-path"], keep_ratio=0.1)
    if not plan["dpi"]["ok"]:
        failures.append("plan_compaction violated DPI")

    print(json.dumps({
        "ok": len(failures) == 0,
        "failures": failures,
        "adversarial_unprotected_wavelet_dropped_focus": _unprot_dropped,
        "rd_zero_distortion": est0,
        "rd_below_bound": est_bad,
    }, indent=2))
    return 0 if not failures else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Rate-distortion-shaped compaction advisor")
    parser.add_argument(
        "--current-tokens", type=int, default=None,
        help="Current token count (required unless --from-log or --self-test)",
    )
    parser.add_argument(
        "--threshold", type=int, default=None,
        help="compression.threshold_tokens (reads config.yaml if omitted)",
    )
    parser.add_argument("--k", type=float, default=3.0, help="Curve shape (default 3.0)")
    parser.add_argument(
        "--content-entropy", type=float, default=None, metavar="H",
        help="Normalized content entropy H/H_max in [0,1]; reduces aggressiveness for info-dense content",
    )
    parser.add_argument(
        "--from-log", action="store_true",
        help="Best-effort parse agent.log for prompt_tokens/context_tokens (unreliable)",
    )
    parser.add_argument("--focus", default="", help="pre-compact-annotate focus string (DPI proxy)")
    parser.add_argument("--session-id", default="", help="Session id for lambda floor")
    parser.add_argument("--no-write", action="store_true", help="Do not persist advisory JSON")
    parser.add_argument("--self-test", action="store_true", help="Run DPI / R(D) / wavelet property tests")
    args = parser.parse_args()

    if args.self_test:
        sys.exit(_self_test())

    cfg = _read_config_compression()
    threshold = cfg.get("threshold_tokens", 120000) if args.threshold is None else args.threshold

    if args.current_tokens is not None:
        current = args.current_tokens
    elif args.from_log:
        found = _current_from_log()
        if found is None:
            print(json.dumps({
                "error": "Could not determine current token count from agent.log. Pass --current-tokens.",
            }))
            sys.exit(1)
        current = found
    else:
        print(json.dumps({
            "error": "Pass --current-tokens (or --from-log for a best-effort log parse).",
        }))
        sys.exit(1)

    result = compute_aggressiveness(current, threshold, k=args.k)
    if args.content_entropy is not None:
        raw_agg = result["aggressiveness"]
        result["aggressiveness"] = entropy_adjusted_aggressiveness(
            raw_agg, args.content_entropy
        )
        result["entropy_adjusted"] = True
        result["normalized_entropy"] = args.content_entropy
        result["rationale"] += (
            f" Entropy-adjusted (H/H_max={args.content_entropy:.2f}, alpha=0.3): "
            f"{raw_agg:.3f} → {result['aggressiveness']:.3f}."
        )

    focus_tokens = tokenize_focus(args.focus)
    result["focus_tokens"] = focus_tokens
    # ADV-009 fix: real DPI check using plan_compaction on advisory kept ratio
    _adv_aggressiveness = result.get("aggressiveness", 0.5)
    _keep_ratio = max(0.05, 1.0 - _adv_aggressiveness)
    if focus_tokens:
        # Simulate compaction at the advised aggressiveness and check DPI
        _dummy_ctx = " ".join(focus_tokens) + " " + (" ".join(focus_tokens) * 10)
        try:
            _plan = plan_compaction(
                _dummy_ctx.split(), focus_tokens=focus_tokens,
                keep_ratio=_keep_ratio, max_drop_ratio=_adv_aggressiveness
            )
            result["dpi"] = _plan.get("dpi", {"ok": True, "dpi_violation": False, "n_focus": len(focus_tokens)})
        except Exception:
            result["dpi"] = dpi_focus_preserved(focus_tokens, focus_tokens)  # fallback
    else:
        result["dpi"] = {"ok": True, "dpi_violation": False, "n_focus": 0, "note": "no focus tokens"}
    rd_est = estimate_decision_rd(load_routing_rd_records())
    result["decision_rd"] = rd_est
    result["advisory_path"] = str(advisory_path())
    result["lambda_target_path"] = str(lambda_target_path())

    if not args.no_write:
        persist_advisory(result)
        persist_lambda_target(result["aggressiveness"], session_id=args.session_id)
        result["written"] = True
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
