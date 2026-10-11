#!/usr/bin/env python3
"""Rate-distortion-*shaped* compaction aggressiveness advisor.

For Gaussian sources R(D) = (1/2) log(σ²/D). LLM tokens are not Gaussian
samples; we do not compute R(D). We borrow the *shape*: tighter remaining
budget → accept more distortion (more aggressive summaries).

Usage:
    python3 rd-compaction-advisor.py --current-tokens 85000
    python3 rd-compaction-advisor.py --current-tokens 85000 --threshold 120000

Output: JSON with aggressiveness in [0,1], recommended focus_topic_prefix, rationale.

Integration (not wired): print JSON and, if a caller wants, prepend
focus_topic_prefix to a compress() / /compress focus_topic. There is no
run_compress_context() symbol in Hermes. Log scraping is best-effort only
and disabled unless --from-log is set.

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
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


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


def _profile_root() -> Path:
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        return base / "profiles" / profile
    return base


def advisory_path() -> Path:
    return _profile_root() / "cache" / "rd-compaction-advisory.json"


def persist_advisory(result: dict) -> Path:
    """Atomic write of the advisory consumed by context-pressure-guard."""
    path = advisory_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(result)
    payload["ts"] = time.time()
    payload["source"] = "rd-compaction-advisor"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def _eval_rd_paths() -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    for root in (_profile_root(), HERMES_HOME, Path.home() / ".hermes"):
        for p in (
            root / "cache" / "eval-compaction-results.json",
            root / "cache" / "scratch" / "eval-compaction-results.json",
        ):
            key = str(p)
            if key not in seen:
                seen.add(key)
                paths.append(p)
    return paths


def load_eval_rd_points() -> tuple[list[dict], str | None]:
    """Non-oracle (policy, D, rate) points from eval-compaction-results.json."""
    for path in _eval_rd_paths():
        try:
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        curve = data.get("rd_curve")
        if not isinstance(curve, list):
            continue
        pts: list[dict] = []
        for item in curve:
            if not isinstance(item, dict) or item.get("oracle_summary") is True:
                continue
            name = item.get("policy") or item.get("name")
            d = item.get("D", item.get("distortion"))
            rate = item.get("rate")
            try:
                d = float(d)
                rate = float(rate)
            except (TypeError, ValueError):
                continue
            if not name:
                continue
            pts.append({"policy": str(name), "D": d, "rate": rate})
        if pts:
            return pts, str(path)
    return [], None


def pareto_frontier(pts: list[dict]) -> list[dict]:
    """Keep policies no other policy weakly dominates (lower D, higher rate)."""
    nd: list[dict] = []
    for a in pts:
        dominated = False
        for b in pts:
            if b is a:
                continue
            if (
                b["D"] <= a["D"]
                and b["rate"] >= a["rate"]
                and (b["D"] < a["D"] or b["rate"] > a["rate"])
            ):
                dominated = True
                break
        if not dominated:
            nd.append(a)
    return nd


def recommend_from_eval() -> dict | None:
    """Pareto-filter, then min-D / max-rate (jev_tail40 > jev at D=0).

    aggressiveness = 1 - rate, so jev_tail40 rate≈0.39 → 0.61.
    """
    pts, source = load_eval_rd_points()
    if not pts:
        return None
    nd = pareto_frontier(pts)
    if not nd:
        return None
    nd.sort(key=lambda p: (p["D"], -p["rate"]))
    pick = nd[0]
    rate = float(pick["rate"])
    agg = round(1.0 - rate, 2)
    return {
        "recommended": pick["policy"],
        "aggressiveness": agg,
        "eval_rate": round(rate, 3),
        "eval_D": round(float(pick["D"]), 3),
        "pareto": [{"policy": p["policy"], "D": p["D"], "rate": p["rate"]} for p in nd],
        "eval_source": source,
        "rationale_eval": (
            f"Pareto-filter then min-D/max-rate among {len(nd)} non-dominated "
            f"of {len(pts)} non-oracle arms → {pick['policy']} "
            f"(rate={rate:.3f}, D={pick['D']:.3f}, aggressiveness={agg})."
        ),
    }


def apply_eval_recommendation(result: dict, eval_rec: dict) -> dict:
    result["recommended"] = eval_rec["recommended"]
    result["aggressiveness"] = eval_rec["aggressiveness"]
    result["eval_rate"] = eval_rec["eval_rate"]
    result["eval_D"] = eval_rec["eval_D"]
    result["pareto"] = eval_rec["pareto"]
    result["eval_source"] = eval_rec["eval_source"]
    extra = eval_rec["rationale_eval"]
    prev = result.get("rationale") or ""
    result["rationale"] = (extra + " " + prev).strip()
    agg = eval_rec["aggressiveness"]
    if agg < 0.25:
        result["level"] = "minimal"
    elif agg < 0.50:
        result["level"] = "light"
    elif agg < 0.75:
        result["level"] = "moderate"
    else:
        result["level"] = "aggressive"
    return result


def _current_from_cache() -> int | None:
    """Fallback used when pre-compact-annotate (or cron) omits --current-tokens.

    Reads cache/current-token-count.json written by eval-compaction-data-bridge
    or a live token probe. Accepts current_tokens / tokens / token_count.
    """
    roots = []
    for r in (_profile_root(), HERMES_HOME, Path.home() / ".hermes"):
        if r not in roots:
            roots.append(r)
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    paths = []
    if override:
        paths.append(Path(override) / "current-token-count.json")
    for root in roots:
        paths.append(root / "cache" / "current-token-count.json")
    for path in paths:
        try:
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            for key in ("current_tokens", "tokens", "token_count"):
                if key in data and data[key] is not None:
                    return int(data[key])
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return None


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Rate-distortion-shaped compaction advisor")
    parser.add_argument(
        "--current-tokens", type=int, default=None,
        help="Current token count (else --from-log, else cache/current-token-count.json)",
    )
    parser.add_argument(
        "--threshold", type=int, default=None,
        help="compression.threshold_tokens (reads config.yaml if omitted)",
    )
    parser.add_argument("--k", type=float, default=3.0, help="Curve shape (default 3.0)")
    parser.add_argument(
        "--from-log", action="store_true",
        help="Best-effort parse agent.log for prompt_tokens/context_tokens (unreliable)",
    )
    args = parser.parse_args()

    cfg = _read_config_compression()
    threshold = cfg.get("threshold_tokens", 120000) if args.threshold is None else args.threshold
    eval_rec = recommend_from_eval()

    result: dict | None = None
    if args.current_tokens is not None:
        result = compute_aggressiveness(args.current_tokens, threshold, k=args.k)
    elif args.from_log:
        found = _current_from_log()
        if found is None and eval_rec is None:
            print(json.dumps({
                "error": "Could not determine current token count from agent.log. Pass --current-tokens.",
            }))
            sys.exit(1)
        if found is not None:
            result = compute_aggressiveness(found, threshold, k=args.k)
    else:
        found = _current_from_cache()
        if found is not None:
            result = compute_aggressiveness(found, threshold, k=args.k)
        elif eval_rec is None:
            print(json.dumps({
                "error": "Pass --current-tokens, or --from-log, or write cache/current-token-count.json.",
            }))
            sys.exit(1)

    if result is None:
        assert eval_rec is not None
        result = {
            "aggressiveness": eval_rec["aggressiveness"],
            "level": "eval-pareto",
            "focus_topic_prefix": "",
            "rationale": eval_rec["rationale_eval"],
        }
    if eval_rec:
        result = apply_eval_recommendation(result, eval_rec)

    try:
        persist_advisory(result)
        result["written"] = True
        result["advisory_path"] = str(advisory_path())
    except OSError:
        result["written"] = False

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
