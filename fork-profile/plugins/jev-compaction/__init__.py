"""jev-compaction — relevance-gated Phase-1 tool-result compaction for Hermes.

Synthesis of:
  - fast-jev-compaction (Tamara Tran, MIT) — confidence-gated forgetting, EMA thresholds, call budget
  - rr_compaction_spike.py — RR two-signal pre-filter (density * recency)
  - jev_verify_fn.py — logprob_classify() as local Noul substitute
  - proper_scoring.py — Beta-Binomial threshold calibration
    NOTE: the 'SPRT early stop' described below is a pressure-ratio heuristic, NOT Wald's
    sequential probability ratio test. It does not carry Wald's E[N] or ASN guarantees.

Architecture
============
Phase-1 of ContextCompressor.compress() calls _prune_old_tool_results() which demotes ALL
tool results before prune_boundary (positional oldest-first). This plugin replaces that
method on the compressor instance (not the class) at each on_pre_compress call with a
relevance-gated version that:

  1. RR pre-filter (zero LLM calls): score all candidates by density * exp(-recency_decay * age).
     Bottom third by score → demote immediately (clear losers).
     Top third by score → retain immediately (clear keepers).
     Middle tier → Jev semantic scoring.

  2. Jev semantic scoring (≤ call_budget LLM calls):
     For each middle-tier candidate, call logprob_classify() from jev_verify_fn.py with a
     compressed message repr and the task context (last 2 user messages, 512 chars).
     Score threshold per role (user/assistant/tool_result) adapted by EMA.

  3. EMA threshold update on BOTH retained and dropped messages (fixes fast-jev survivorship bias).

  4. SPRT early stop: if budget pressure is well below threshold (tokens < 0.6 * threshold),
     skip the LLM pass entirely — the positional oldest-first demotion is good enough.

  5. Call budget cap (Jevons Paradox guard): inherits _check_and_charge_budget() from jev_verify_fn.

Wiring
======
on_pre_compress hook → receives agent → reads agent.context_compressor → monkeypatches
_prune_old_tool_results on the instance. The patch wraps, not replaces: on any exception
it falls through to the original. Shadow-mode: never raises into the host process.

Footprint: Rung 4 (plugin). No new core tools. Stdlib + hermes-agent venv imports only.
Config (config.yaml under plugins.jev_compaction):
  enabled: true
  call_budget: 8              # max Jev calls per compaction pass
  sprt_skip_ratio: 0.60       # skip Jev pass if tokens < ratio * threshold_tokens
  rr_lambda: 0.18             # RR scoring lambda (< 0.235 protects large dense results)
  ema_alpha: 0.15             # EMA threshold adaptation rate
  thresholds:
    tool_result: 0.55         # initial retain threshold (Beta-Binomial: 3/5 successes)
    assistant: 0.61
    user: 0.72
    system: 1.0               # never demote
"""
from __future__ import annotations

import importlib.util
import json
import logging
import lzma
import math
import sys
import threading
import types
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("jev-compaction")

# ── Paths ────────────────────────────────────────────────────────────────────

_SCRIPTS = Path("~/.hermes/scripts").expanduser()
_JEV_PATH = _SCRIPTS / "jev_verify_fn.py"
_RR_PATH = _SCRIPTS / "rr_compaction_spike.py"
_COT_SCORER_PATH = _SCRIPTS / "cot_phase_scorer.py"
_SEGMENT_COMPACTOR_PATH = _SCRIPTS / "segment_level_compactor.py"
_CRYSTAL_TIERS_PATH = _SCRIPTS / "crystal_fidelity_tiers.py"
_CACHE_DIR = Path("~/.hermes/cache").expanduser()
_CALIBRATION_LOG = _CACHE_DIR / "calibration-log.jsonl"

# ── Tool density table (from rr_compaction_spike.py; inlined to avoid import) ─

_TOOL_DENSITY: dict[str, float] = {
    "delegate_task": 0.95,
    "execute_code": 0.85,
    "write_file": 0.80,
    "web_extract": 0.80,
    "patch": 0.75,
    "web_search": 0.70,
    "read_file": 0.65,
    "browser_exec": 0.65,
    "terminal": 0.55,
    "search_files": 0.50,
    "skill_view": 0.40,
    "capture_screenshot": 0.30,
    "vision_analyze": 0.55,
}
_DEFAULT_DENSITY = 0.50

# ── Default config ────────────────────────────────────────────────────────────

_DEFAULT_CFG: dict[str, Any] = {
    "enabled": True,
    "call_budget": 8,
    "sprt_skip_ratio": 0.60,
    "rr_lambda": 0.18,
    "ema_alpha": 0.15,
    # GATE GAP 1 (DeGroot Ch 7.5): EVSI-based skip criterion
    "evsi_min": 0.05,
    "retention_value": 1.0,
    # GATE GAP 2 (DeGroot Ch 9.4): Beta-Binomial adaptive threshold
    "beta_prior": 2.0,
    "beta_min_obs": 10,
    "thresholds": {
        "tool_result": 0.55,
        "assistant": 0.61,
        "user": 0.72,
        "system": 1.0,
    },
}

# ── Session-scoped EMA state (keyed by session_id) ───────────────────────────
# Maps session_id → {"tool_result": float, "assistant": float, "user": float}
_SESSION_THRESHOLDS: dict[str, dict[str, float]] = {}

# N13 fix: guard all reads AND writes to _SESSION_THRESHOLDS under this lock
# to prevent threading race conditions under concurrent compression.
_THRESHOLDS_LOCK = threading.Lock()
# P6A-02: version counter for CAS in _get_thresholds.
# Float equality is not a reliable sentinel for "no intervening write" — at FTRL
# convergence (gradient → 0) the written value equals the snapshot value, causing a
# false-positive CAS that lets a stale posterior overwrite a valid FTRL update.
# A monotone int version bumped inside the lock on every _update_threshold write
# provides an unambiguous "changed since snapshot" signal.
_THRESHOLD_VERSIONS: dict[str, dict[str, int]] = {}
# P6B-07: lock for _PATCHED dict. GC finalizer (_evict_patched_id) can run in any thread,
# racing with _patch_compressor's check-and-update sequence.  A dedicated lock keeps
# _PATCHED mutations atomic without contending on _THRESHOLDS_LOCK.
_PATCHED_LOCK = threading.Lock()
# P7A-04: Serialise concurrent _write_calibration_event writes within the process.
# open(CALIBRATION_LOG, 'a') + write() is not atomic for records > PIPE_BUF bytes on
# network filesystems; concurrent writes can interleave JSON lines, producing truncated
# records that calibration_loop.py silently drops, degrading ECE accuracy.
_CALIBRATION_LOG_LOCK = threading.Lock()

# ── Session-scoped observation counts for UCB1 cold-start guard (Lattimore Ch.1) ──
# Maps session_id → {role: count}. Track how many observations we have per role
# so we can apply optimism (lower threshold) when we haven't seen enough data.
_THRESHOLD_COUNTS: dict[str, dict[str, int]] = {}

# ── GATE GAP 2 (DeGroot Ch 9.4): Beta-Binomial in-memory counters ────────────
# P10A-04 fix: _beta_posterior_threshold was doing 3× full O(N) file scans per
# compaction pass. Replace with in-memory retain/demote counters updated by
# _write_calibration_event(). Dict structure: session_id → role → {"k": retains, "n": total}.
# Persisted to disk only at on_session_end for cold-start recovery (optional).
_BETA_COUNTERS: dict[str, dict[str, dict[str, int]]] = {}

# ── GATE GAP 1 (DeGroot Ch 7.5): EVSI rolling counters ──────────────────────
# Track middle-tier hits (messages sent to Jev semantic scoring) vs total scored.
# keyed by session_id. Used to estimate p_middle for the EVSI skip criterion.
_MIDDLE_TIER_COUNTS: dict[str, int] = {}
_TOTAL_COUNTS: dict[str, int] = {}

# ── GATE GAP 4 (Billingsley Sec 32): Atom-detection score history ────────────
# Maps (session_id + ":" + role) → deque of last 5 scores.
# If all 5 values are within 0.001 of each other, the distribution is atomic
# (Radon-Nikodym derivative undefined) and the EMA update is suppressed.
_SCORE_HISTORY: dict[str, deque] = {}

# ── Dynamic import helpers ────────────────────────────────────────────────────


def _load_jev() -> types.ModuleType | None:
    """Dynamically import jev_verify_fn. Returns None on failure (shadow: never raises)."""
    key = "jev_verify_fn_compaction"
    if key in sys.modules:
        return sys.modules[key]
    try:
        if not _JEV_PATH.exists():
            logger.debug("jev-compaction: %s not found; Jev pass skipped", _JEV_PATH)
            return None
        # Ensure hermes-agent is on sys.path (same pattern as jev_verify_fn itself)
        _ha = Path("~/.hermes/hermes-agent").expanduser()
        # N08 fix: detect the actual Python version instead of hardcoding 3.11.
        # On Python 3.12+ (Fedora F39+) the venv uses python3.12/, not python3.11/.
        import sys as _sys
        _pyver = f"python{_sys.version_info.major}.{_sys.version_info.minor}"
        for _p in [str(_ha), str(_ha / "venv" / "lib" / _pyver / "site-packages")]:
            if _p not in sys.path:
                sys.path.insert(0, _p)
        spec = importlib.util.spec_from_file_location(key, str(_JEV_PATH))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        logger.debug("jev-compaction: loaded jev_verify_fn from %s", _JEV_PATH)
        return mod
    except Exception as exc:
        logger.debug("jev-compaction: failed to load jev_verify_fn: %s", exc)
        return None


def _load_script(path: Path, key: str) -> types.ModuleType | None:
    """Generic lazy loader for ~/.hermes/scripts/ modules. Shadow: never raises."""
    if key in sys.modules:
        return sys.modules[key]
    try:
        if not path.exists():
            logger.debug("jev-compaction: %s not found; feature skipped", path)
            return None
        spec = importlib.util.spec_from_file_location(key, str(path))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        logger.debug("jev-compaction: loaded %s", path.name)
        return mod
    except Exception as exc:
        logger.debug("jev-compaction: failed to load %s: %s", path.name, exc)
        return None


def _load_cot_scorer() -> types.ModuleType | None:
    return _load_script(_COT_SCORER_PATH, "jev_cot_phase_scorer")


def _load_segment_compactor() -> types.ModuleType | None:
    return _load_script(_SEGMENT_COMPACTOR_PATH, "jev_segment_level_compactor")


def _load_crystal_tiers() -> types.ModuleType | None:
    return _load_script(_CRYSTAL_TIERS_PATH, "jev_crystal_fidelity_tiers")


# ── Config loader ─────────────────────────────────────────────────────────────


def _load_cfg(ctx: Any) -> dict[str, Any]:
    """Load plugin config from ctx, merging with defaults. Never raises."""
    try:
        raw = getattr(ctx, "config", {}) or {}
        plugin_cfg = raw.get("plugins", {}).get("jev_compaction", {})
        cfg = dict(_DEFAULT_CFG)
        cfg.update({k: v for k, v in plugin_cfg.items() if k != "thresholds"})
        if "thresholds" in plugin_cfg:
            thresh = dict(_DEFAULT_CFG["thresholds"])
            thresh.update(plugin_cfg["thresholds"])
            cfg["thresholds"] = thresh
        return cfg
    except Exception:
        return dict(_DEFAULT_CFG)


# ── RR two-signal pre-filter ──────────────────────────────────────────────────


def _ncd_density(content: str) -> float:
    """Compression ratio for a single string (NOT the pairwise NCD metric).

    This computes len(lzma.compress(s)) / len(s) as a Kolmogorov complexity
    approximation — a single-argument compression ratio, NOT normalized
    compression distance NCD(s1, s2) which requires two inputs.

    F10: this function is currently dead code — _entropy_density() is used instead
    in _rr_score. Retained for potential future pairwise NCD feature; do not call
    for single-string density scoring.

    Grounded in Kolmogorov complexity K(x) ≈ compress(x)/len(x) (Cover-Thomas Ch.14 / MDL).
    Uses lzma (LZMA2) for a stronger approximation than zlib: lzma achieves better
    compression ratios, so the residual len(compressed)/len(raw) is a tighter upper bound
    on K(x)/len(x).  High ratio → hard to compress → more unique information → high density.
    """
    if not content:
        return 0.0
    raw = content.encode("utf-8", errors="replace")
    # N02 fix: lzma adds a fixed header overhead (~60 bytes) that makes short strings
    # appear maximally dense. For content shorter than the compressor overhead threshold,
    # use entropy_density instead of NCD — it does not have this artifact.
    if len(raw) < 64:
        return _entropy_density(content)
    compressed = lzma.compress(raw)
    # density: less compressible = more unique information = higher score
    return min(1.0, len(compressed) / max(len(raw), 1))


def _entropy_density(content: str) -> float:
    """Empirical byte-level Shannon entropy, normalized to [0,1] (Cover-Thomas Ch.6).

    H(X) = -sum_b (p_b * log2(p_b)) over observed bytes b.
    Normalized by log2(256) = 8 (maximum entropy for a byte source).

    Theoretical grounding: AEP (Cover-Thomas Ch.3) — typical-set size ≈ 2^{nH}.
    Higher H → more information per byte → content is harder to summarise → retain.
    This replaces the hardcoded _TOOL_DENSITY table for messages whose content is present:
    it uses the actual byte distribution rather than a per-tool-name heuristic.

    Edge cases:
      - Empty string → 0.5 (maximum-entropy prior; we have no information).
      - Single unique byte → 0.0 (perfectly predictable, zero entropy).
    """
    if not content:
        return 0.5  # maxent prior: no information to judge by
    raw = content.encode("utf-8", errors="replace")
    n = len(raw)
    if n == 0:
        return 0.5
    from collections import Counter
    counts = Counter(raw)
    entropy = 0.0
    for cnt in counts.values():
        p = cnt / n
        entropy -= p * math.log2(p)
    # Normalize: log2(256) = 8
    return min(1.0, entropy / 8.0)


def _extract_tool_name(msg: dict[str, Any]) -> str | None:
    """Extract tool name from a tool-call or tool-result message.

    N11 fix: for assistant messages with multiple tool_calls, return the tool
    name with the HIGHEST density weight (most conservative / highest-value score).
    A message calling [search_files, delegate_task] gets density weight of
    delegate_task (0.95) instead of search_files (0.50) — the first in the list.
    """
    # tool_result message carries the call_id; look for sibling assistant msg
    if msg.get("role") == "tool":
        return msg.get("name") or msg.get("tool_name")
    # assistant with tool_calls
    tool_calls = msg.get("tool_calls") or []
    if not tool_calls:
        return None
    if len(tool_calls) == 1:
        fn = tool_calls[0].get("function") or {}
        return fn.get("name") or tool_calls[0].get("name")
    # Multiple tool calls: return the one with the highest density weight
    best_name: str | None = None
    best_density: float = -1.0
    for tc in tool_calls:
        fn = tc.get("function") or {}
        name = fn.get("name") or tc.get("name")
        if name is None:
            continue
        density = _TOOL_DENSITY.get(name, _DEFAULT_DENSITY)
        if density > best_density:
            best_density = density
            best_name = name
    return best_name


def _extract_content_text(msg: dict[str, Any]) -> str:
    """Extract plain text content from a message regardless of shape."""
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for item in c:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                t = item.get("text") or item.get("content") or ""
                if isinstance(t, str):
                    parts.append(t)
        return "\n".join(parts)
    return ""

# P8A-09 note: compaction_utils.py is the canonical source for _extract_content_text.
# This local definition is kept as the plugin's internal copy to avoid a hard import
# dependency from the plugin directory (which lives outside the scripts/ path).
# If compaction_utils changes its implementation, update this copy to match.


def _rr_score(
    msg: dict[str, Any],
    position: int,
    total: int,
    rr_lambda: float,
) -> float:
    """RR two-signal score: pp - lambda * cp.

    pp = 0.5 * density + 0.3 * recency + 0.2 * tool_weight
    cp = chars / max_chars_in_window (rough token proxy)

    GAP 3 fix (Cover-Thomas Ch.6): When content is present, replace the hardcoded
    _TOOL_DENSITY lookup with _entropy_density(content) — the empirical byte-level
    Shannon entropy normalised to [0,1].  This makes the density signal information-
    theoretic rather than heuristic: high H → harder to compress → more unique content
    → should be retained.  The _TOOL_DENSITY table is kept only as a fallback for
    empty-content messages (e.g. tool calls with no result text yet).
    """
    content = _extract_content_text(msg)
    tool_name = _extract_tool_name(msg)
    # GAP 3: use entropy-based density when content is present; else fall back to tool-name table
    if content:
        density = _entropy_density(content)
    else:
        density = _TOOL_DENSITY.get(tool_name or "", _DEFAULT_DENSITY) if tool_name else _DEFAULT_DENSITY
    # Recency: 1.0 = newest, 0.0 = oldest (within prunable window)
    # W3-F03 fix: normalize recency within the prunable window [0, prune_boundary-1],
    # not against the full list length.  The original formula position/max(total-1,1)
    # compressed all prunable candidates below 1.0 (the newest prunable at position
    # prune_boundary-1 scored < 1.0), systematically underweighting the recency signal.
    # We pass the prunable window bounds via total being set to prune_boundary by caller.
    # Caller should pass total=len(candidates_idx) and position=idx_within_candidates.
    # For backward compat: if total <= position+1 (full-list mode), use old formula.
    recency = position / max(total - 1, 1)
    pp = 0.5 * density + 0.3 * recency + 0.2 * (_TOOL_DENSITY.get(tool_name or "", _DEFAULT_DENSITY) if tool_name else _DEFAULT_DENSITY)
    # compression pressure: length relative to 20 KB (rough tool result max)
    cp = min(len(content) / 20_000, 1.0)
    raw = pp - rr_lambda * cp
    # F01 wiring: apply CoT phase demotion for intermediate reasoning chains.
    # P4A-01 fix: guard to assistant-only — CoT patterns are meaningless on tool/user
    # messages and the role guard inside classify_cot_phase is a single point of failure.
    # cot_adjust_rr_score multiplies by 0.65 for cot_intermediate, passes through otherwise.
    if msg.get("role") == "assistant":
        cot_mod = _load_cot_scorer()
        if cot_mod is not None:
            try:
                raw = cot_mod.cot_adjust_rr_score(msg, raw)
            except Exception:
                pass  # shadow: never raises
    return raw


# ── Task context builder (fast-jev-compaction: string concat, not vector) ─────


def _build_task_context(messages: list[dict[str, Any]]) -> str:
    """Last ≤3 user messages, truncated to 512 chars total."""
    user_msgs = [
        _extract_content_text(m)
        for m in messages
        if m.get("role") == "user"
    ][-3:]
    ctx = " | ".join(user_msgs)
    return ctx[:512]


# ── Jev semantic scoring ──────────────────────────────────────────────────────


def _record_decision(
    session_id: str,
    role_key: str,
    score: float,
    retained: bool,
    ema_alpha: float,
    cfg: dict[str, Any] | None = None,
) -> None:
    """Pure side-effect: record a demotion/retention decision into the EMA.

    Milewski (Kleisli monad law): the EMA update is a side-effect that must
    occur AFTER the decision is resolved, not embedded in the scoring call.
    Separating it here makes `_jev_relevance` a pure Kleisli arrow
    (score -> option score) with no hidden state mutation, satisfying
    left-identity and associativity of the Kleisli composition.

    Royden-Fitzpatrick (uniform integrability): clamp score to [0, 1] before
    updating so no unbounded score can dominate the EMA estimate.
    """
    # Royden-Fitzpatrick EMA clamp (uniform integrability)
    score = max(0.0, min(1.0, score))
    _update_threshold(session_id, role_key, score, retained=retained, ema_alpha=ema_alpha, cfg=cfg)


def _jev_relevance(
    msg: dict[str, Any],
    task_context: str,
    jev_mod: types.ModuleType,
    budget_remaining: list[int],  # mutable [n]
) -> float | None:
    """
    Call logprob_classify() from jev_verify_fn to get a relevance score (0..1).
    Returns None if budget exhausted or call fails.

    Milewski (Kleisli arrow): this function is a PURE Kleisli arrow
    (score >=> classify) — it produces a score but does NOT update the EMA.
    The EMA side-effect is deferred to _record_decision(), called after the
    decision is resolved in _relevance_gated_prune (pipeline order:
    score -> classify -> decide -> record).
    """
    if budget_remaining[0] <= 0:
        return None
    try:
        check_budget = getattr(jev_mod, "_check_and_charge_budget", None)
        if check_budget and not check_budget(1):
            budget_remaining[0] = 0
            return None

        content = _extract_content_text(msg)
        tool_name = _extract_tool_name(msg) or "tool"
        # Compressed representation: tool name + first 300 chars of content
        doc = f"[{tool_name}] {content[:300]}"

        lpc = getattr(jev_mod, "logprob_classify", None)
        if lpc is None:
            return None

        # Build context string: task + compressed tool repr
        # logprob_classify(context, options, *, model) — positional context, no 'document' param
        context_str = (
            f"Task: {task_context[:120]}\n"
            f"Tool result: [{tool_name}] {content[:250]}"
        )
        raw = lpc(
            context_str,
            ["Keep — still needed", "Drop — no longer needed"],
            model=None,  # uses configured aux model (mistral-small)
        )
        # raw is a dict {option: probability}; may contain NaN on non-OAI providers
        if not isinstance(raw, dict) or not raw:
            return None
        # N01 fix: always look up by key, never rely on dict insertion order.
        # logprob_classify returns {option_text: probability}; key order is model-defined.
        keep_prob = raw.get("Keep — still needed", raw.get("Keep", None))
        if keep_prob is None:
            # Fallback: first value — only if exactly one key and it looks like Keep probability
            keep_prob = next(iter(raw.values()), None)
        if keep_prob is None:
            return None
        import math as _math
        if _math.isnan(keep_prob):
            # Non-OAI provider: logprobs unavailable. Fall back to RR score (caller handles None).
            return None
        budget_remaining[0] -= 1
        return float(keep_prob)
    except Exception as exc:
        logger.debug("jev-compaction: _jev_relevance failed: %s", exc)
        return None


# ── EMA threshold management ──────────────────────────────────────────────────


def _write_calibration_event(
    session_id: str,
    role: str,
    predicted_score: float,
    decision: str,
    tool_name: str | None,
    tier: str,
    rr_score: float,
    jev_score: float | None,
) -> None:
    """Append a calibration event to the calibration log (Jaynes Ch.13).

    Jaynes Ch.13: for p to be calibrated, events tagged with p must occur with
    frequency p.  This function is the write side of that feedback loop — the
    calibration_loop.py script is the read side.  Without writes, no calibration
    signal exists and ECE/MCE are meaningless.

    Format (one JSON object per line):
      {"ts": ISO8601, "session_id": str, "role": str, "tool_name": str|null,
       "predicted_confidence": float, "decision": "demote"|"retain",
       "tier": "bottom"|"middle"|"top", "rr_score": float, "jev_score": float|null}
    """
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "role": role,
            "tool_name": tool_name,
            "predicted_confidence": round(float(predicted_score), 6),
            "decision": decision,
            "tier": tier,
            "rr_score": round(float(rr_score), 6),
            "jev_score": round(float(jev_score), 6) if jev_score is not None else None,
            # F02 fix: calibration_loop.py requires 'actual_outcome' to accept a record.
            # At write time we use the decision as a proxy: retain=1, demote=0.
            # P9A-05 note: this is NOT ground-truth quality — ECE measured against this
            # proxy_outcome is a self-consistency check (does the score predict the decision?),
            # not true calibration. ECE will be low whenever the threshold is stable.
            # A WARNING is added to calibration_loop.py to flag this limitation.
            # Reserve 'actual_outcome' for future ground-truth labels when available.
            "actual_outcome": 1 if decision == "retain" else 0,
        }
        with _CALIBRATION_LOG_LOCK:
            with _CALIBRATION_LOG.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        # P10A-04 fix: update in-memory beta counters to avoid O(N) file scan
        # in _beta_posterior_threshold. Use _THRESHOLDS_LOCK for consistency.
        with _THRESHOLDS_LOCK:
            sess_counters = _BETA_COUNTERS.setdefault(session_id, {})
            role_counter = sess_counters.setdefault(role, {"k": 0, "n": 0})
            role_counter["n"] += 1
            if decision == "retain":
                role_counter["k"] += 1
    except Exception as exc:
        logger.debug("jev-compaction: _write_calibration_event suppressed: %s", exc)


def _cold_start_boost(role: str, count: int, base_thresh: float) -> float:
    """UCB1-style threshold reduction during cold start (Lattimore Ch.1).

    Lattimore UCB1: pull every arm once before trusting any arm's estimate.
    With 0 observations, a default threshold (e.g. 0.55) is an uninformed prior —
    any observed score will be compared against a value we have no evidence for.

    Strategy: lower the effective threshold by a UCB1-style optimism bonus when
    count < 10. This makes the plugin more willing to RETAIN messages (conservative)
    when it hasn't yet gathered enough observations to trust its threshold estimate.

    Bonus = sqrt(2 * ln(1 + count) / max(count, 1)) * 0.1
    Effective = clip(base_thresh - bonus, 0.3, base_thresh)

    At count=0: bonus ≈ 0 (ln(1)=0), so returns base_thresh (no change yet).
    At count=1: bonus = sqrt(2*ln2) * 0.1 ≈ 0.118 → threshold lowered toward 0.3.
    At count≥10: exploration phase ends; bonus rounds to ~0 relative to base.
    """
    if count >= 10:
        return base_thresh
    # W3-F02 fix: use max(count,1)+1 in log so count=0 gives non-zero bonus.
    # At count=0: max(0,1)+1=2, log(2)/1≈0.693, bonus=sqrt(2*0.693)*0.1≈0.118 →
    # threshold lowered by ~0.12 (e.g. 0.55→0.432). Genuine UCB1 optimism before
    # the first observation (Lattimore Ch.1 — each arm pulled once before exploitation).
    bonus = math.sqrt(2 * math.log(max(count, 1) + 1) / max(count, 1)) * 0.1
    return max(0.3, min(base_thresh, base_thresh - bonus))


def _get_thresholds(session_id: str, cfg: dict[str, Any]) -> dict[str, float]:
    with _THRESHOLDS_LOCK:
        if session_id not in _SESSION_THRESHOLDS:
            _SESSION_THRESHOLDS[session_id] = dict(cfg["thresholds"])
        thresholds = _SESSION_THRESHOLDS[session_id]
        # Snapshot values AND versions under the lock so the CAS below is version-gated.
        # P6A-05 fix: return the snapshot (not the live dict reference) so one compaction
        # pass sees a consistent threshold view even if _apply_js_shrinkage writes to the
        # live dict concurrently.
        snapshot = dict(thresholds)
        version_snap = dict(_THRESHOLD_VERSIONS.get(session_id, {}))
    # GATE GAP 2 (DeGroot Ch 9.4): override EMA with Beta-Binomial posterior when enough data.
    # P4B-06 fix: collect all posterior updates atomically.
    # P5A-03 fix: second TOCTOU window — compute posteriors against the snapshot taken under
    # the lock, then only write a role's posterior if the in-memory value hasn't changed since
    # (compare-and-swap). This prevents a concurrent _update_threshold FTRL step from being
    # silently overwritten by a stale posterior computed before the FTRL step ran.
    # P6A-02 fix: use version counter CAS instead of float equality — at FTRL convergence
    # gradient→0 so the written float equals the snapshot float, giving a false-positive CAS.
    updates: dict[str, float] = {}
    for role in list(snapshot.keys()):
        posterior = _beta_posterior_threshold(session_id, role, cfg)
        if posterior is not None:
            clamped = max(0.20, min(0.95, posterior))
            updates[role] = clamped
    if updates:
        with _THRESHOLDS_LOCK:
            cur_versions = _THRESHOLD_VERSIONS.get(session_id, {})
            for role, val in updates.items():
                # CAS: only apply posterior if _update_threshold has NOT written since snapshot.
                if cur_versions.get(role, 0) == version_snap.get(role, 0):
                    thresholds[role] = val
    # P6A-05: return a fresh snapshot taken after any posterior CAS writes, so the
    # calling compaction pass sees a consistent, stable threshold view for the entire
    # scoring loop — concurrent _apply_js_shrinkage writes to the live dict during
    # the loop cannot cause inconsistent per-message threshold reads.
    with _THRESHOLDS_LOCK:
        return dict(_SESSION_THRESHOLDS.get(session_id, snapshot))


def _get_count(session_id: str, role: str) -> int:
    """Return the observation count for (session_id, role)."""
    return _THRESHOLD_COUNTS.get(session_id, {}).get(role, 0)


# ── GATE GAP 2 (DeGroot Ch 9.4): Beta-Binomial posterior threshold ────────────


def _beta_posterior_threshold(
    session_id: str,
    role: str,
    cfg: dict[str, Any],
) -> float | None:
    """Compute Beta-Binomial posterior mean threshold from calibration data.

    DeGroot Ch 9.4: posterior mean of a Beta(alpha, beta) conjugate to Binomial(n, p)
    is (alpha + k) / (alpha + beta + n), where k = number of successes (retains).

    Uses Beta(2, 2) prior (weakly informative, centers at 0.5). Returns None when
    fewer than beta_min_obs observations exist — fall back to EMA threshold.

    P10A-04 fix: Uses in-memory _BETA_COUNTERS (updated by _write_calibration_event)
    instead of scanning the calibration log file. File I/O is eliminated from the hot
    path — zero disk reads per compaction pass for same-process decisions.
    Cold-start fallback: if in-memory counter has < beta_min_obs, reads the log file
    once to seed the counter (covers test injection and process restart).
    """
    try:
        alpha = cfg.get("beta_prior", 2.0)
        beta_param = alpha  # symmetric Beta(2,2) prior
        beta_min_obs = cfg.get("beta_min_obs", 10)

        # Fast path: use in-memory counters (updated in _write_calibration_event)
        with _THRESHOLDS_LOCK:
            sess_counters = _BETA_COUNTERS.get(session_id, {})
            role_counter = sess_counters.get(role, {"k": 0, "n": 0})
            k = role_counter["k"]
            n = role_counter["n"]

        if n < beta_min_obs:
            # Cold-start fallback: seed from calibration log file (covers restart / tests).
            # This is O(N) but runs at most once per (session, role) until we accumulate
            # beta_min_obs observations in memory.
            if not _CALIBRATION_LOG.exists():
                return None
            k_file = 0
            n_file = 0
            try:
                with _CALIBRATION_LOG.open(encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except Exception:
                            continue
                        if rec.get("session_id") != session_id:
                            continue
                        if rec.get("role") != role:
                            continue
                        n_file += 1
                        if rec.get("decision") == "retain":
                            k_file += 1
            except Exception:
                return None
            if n_file < beta_min_obs:
                return None
            # P11-01 fix: Re-check counter under lock before writing to prevent TOCTOU race.
            # Between our file scan and now, _write_calibration_event may have incremented
            # the in-memory counter. If it already has enough data, use the richer in-memory
            # value (it's more current than the file snapshot). Only seed from file if the
            # counter is still below beta_min_obs under the lock.
            with _THRESHOLDS_LOCK:
                current = _BETA_COUNTERS.get(session_id, {}).get(role, {"k": 0, "n": 0})
                if current["n"] >= beta_min_obs:
                    # Another thread seeded (or _write_calibration_event caught up) — use it.
                    k, n = current["k"], current["n"]
                else:
                    # P12-01 fix: merge file snapshot with any partial in-memory events that
                    # arrived during the scan (written to memory by _write_calibration_event
                    # but may not be in the file yet if file write failed or was mid-write).
                    # Take the max of n to avoid double-counting; k follows from file ratio
                    # adjusted by any additional in-memory events that are definitively newer.
                    # Conservative merge: use the larger n to avoid undercount.
                    k_mem, n_mem = current["k"], current["n"]
                    if n_file >= n_mem:
                        # File snapshot is richer (normal case); seed from it
                        _BETA_COUNTERS.setdefault(session_id, {})[role] = {
                            "k": k_file, "n": n_file
                        }
                        k, n = k_file, n_file
                    else:
                        # In-memory has more events than file (concurrent writes caught up);
                        # keep the in-memory value — it's more current and consistent.
                        k, n = k_mem, n_mem

        posterior_mean = (alpha + k) / (alpha + beta_param + n)
        return float(posterior_mean)
    except Exception as exc:
        logger.debug("jev-compaction: _beta_posterior_threshold failed: %s", exc)
        return None


# ── GATE GAP 3 (Berger Ch 5.4): James-Stein shrinkage ────────────────────────


def _apply_js_shrinkage(session_id: str, cfg: dict[str, Any]) -> None:
    """Apply James-Stein shrinkage to joint EMA threshold estimates (Berger Ch 5.4).

    Berger/Stein: independent estimators for k>=3 parameters are inadmissible.
    Shrinking toward the grand mean dominates the MLE estimator under squared loss.

    Shrinks tool_result, assistant, and user thresholds toward their grand mean:
      grand_mean = mean(tool_result, assistant, user)  [k=3]
      shrinkage_factor = max(0, 1 - (k-2) * sigma^2 / sum((t_i - grand_mean)^2))
      new_t_i = grand_mean + shrinkage_factor * (t_i - grand_mean)

    where k=3 (roles being shrunk), sigma^2 = ema_alpha^2 (proxy for update variance).

    P9A-11 fix: with default thresholds (tool_result=0.55, assistant=0.61, user=0.72),
    deviations_sq≈0.0148 < sigma2=0.0225, producing shrinkage_factor=0 and full collapse
    to grand_mean on the very first call. Guard: if sigma2 >= deviations_sq, cap sigma2
    at 0.5*deviations_sq to guarantee shrinkage_factor >= 0.5 (partial shrinkage only).

    P9A-01 note: 'user' threshold is nearly static (N03 skip prevents frequent updates)
    and biases grand_mean upward. The guard above limits this distortion. Long-term,
    consider weighting by threshold_count (UCB1 per role) once count tracking matures.

    Clamped to [0.20, 0.95] for safety.
    """
    try:
        # P5A-09 fix: hold _THRESHOLDS_LOCK for the entire read-compute-write sequence.
        # P8A-04 fix: Berger/Stein inadmissibility requires k>=3.  With k=2 (only
        # tool_result + assistant), (k-2)=0 → shrinkage_factor=1.0 always → no shrinkage.
        # Extend to k=3 by including 'user' so (k-2)=1 and the Stein formula is active.
        with _THRESHOLDS_LOCK:
            thresholds = _SESSION_THRESHOLDS.get(session_id)
            if thresholds is None:
                return

            roles_to_shrink = ["tool_result", "assistant", "user"]
            values = [thresholds.get(r) for r in roles_to_shrink]
            if any(v is None for v in values):
                return

            k = len(roles_to_shrink)
            grand_mean = sum(values) / k  # type: ignore[arg-type]
            ema_alpha = cfg.get("ema_alpha", 0.15)
            sigma2 = ema_alpha ** 2

            deviations_sq = sum((t - grand_mean) ** 2 for t in values)  # type: ignore[operator]
            if deviations_sq < 1e-12:
                # All thresholds identical — no shrinkage possible (already at grand mean)
                return

            # P9A-11 fix: guard against sigma2 >= deviations_sq causing full collapse.
            # When sigma2 >= deviations_sq, shrinkage_factor=0 collapses all thresholds
            # to grand_mean before any calibration data exists (common with default values).
            # Cap sigma2 at 0.5*deviations_sq to guarantee shrinkage_factor >= 0.5.
            if sigma2 >= deviations_sq:
                sigma2 = 0.5 * deviations_sq

            shrinkage_factor = max(0.0, 1.0 - (k - 2) * sigma2 / deviations_sq)

            for role, t_i in zip(roles_to_shrink, values):
                new_t = grand_mean + shrinkage_factor * (t_i - grand_mean)  # type: ignore[operator]
                thresholds[role] = max(0.20, min(0.95, new_t))
                logger.debug(
                    "jev-compaction: JS shrinkage %s %.3f → %.3f (grand_mean=%.3f, sf=%.3f)",
                role, t_i, thresholds[role], grand_mean, shrinkage_factor,
            )
    except Exception as exc:
        logger.debug("jev-compaction: _apply_js_shrinkage failed: %s", exc)


def _update_threshold(
    session_id: str,
    role: str,
    score: float,
    retained: bool,
    ema_alpha: float,
    cfg: dict[str, Any] | None = None,
) -> None:
    """FTRL-style threshold update with Tikhonov regularizer (Shalev-Shwartz Ch.11).

    Replaces plain EMA (OGD with fixed rate) with FTRL + Tikhonov regularization:

      gradient   = score - current          (subgradient of squared loss)
      lambda_reg = 0.01 / max(sqrt(t+1), 1) (O(1/sqrt(T)) decaying regularization)
      new        = current + alpha*gradient - lambda_reg*(current - prior)

    where prior = default threshold from cfg (the initialization point w0).

    Shalev-Shwartz Thm 11.6: FTRL with Tikhonov regularizer achieves regret O(sqrt(T)),
    improving on plain OGD's O(1/lambda) stability bound.  The anchor toward prior
    prevents catastrophic forgetting when the session's score distribution shifts.

    Also updates _THRESHOLD_COUNTS for the UCB1 cold-start guard (GAP 4).

    GATE GAP 4 (Billingsley Sec 32): Atom-detection guard.
    Before updating, check if the last 5 scores for this role are all within 0.001
    of each other (atomic distribution — Radon-Nikodym derivative undefined).
    If atomic: suppress the EMA update and log DEBUG. The score is still added to
    history so detection can clear when scores diversify.
    """
    # P7A-02 fix: merge the first lock block (early-exit check) with the second
    # (SCORE_HISTORY access).  Previously three separate lock acquisitions left a window
    # between the first and second where on_session_end could pop the session, causing
    # _SCORE_HISTORY.setdefault to re-create a deque for a dead session that leaks
    # indefinitely.  One acquisition covers the check + atom-detection together.
    history_key = f"{session_id}:{role}"
    with _THRESHOLDS_LOCK:
        thresholds = _SESSION_THRESHOLDS.get(session_id, {})
        if role not in thresholds or role == "system":
            return
        current = thresholds[role]
        # GATE GAP 4 (Billingsley Sec 32): atom detection (P6A-01/P6B-05 fix)
        _SCORE_HISTORY.setdefault(history_key, deque(maxlen=5))
        score_hist = _SCORE_HISTORY[history_key]
        score_hist.append(score)
        if len(score_hist) == 5:
            lo = min(score_hist)
            hi = max(score_hist)
            atom_detected = (hi - lo) < 0.001
        else:
            atom_detected = False

    if atom_detected:
        logger.debug(
            "jev-compaction: atom detected for role %s — EMA update suppressed",
            role,
        )
        return  # skip update; threshold unchanged

    # FTRL Tikhonov update — all of count read, lambda_reg compute, and write under
    # one lock acquisition.
    # P5A-01 fix: P4B-05 moved `current` inside the lock but left `count` and
    # `lambda_reg` outside, making the regularization strength stale under concurrency.
    # Moving everything inside the lock makes count, lambda_reg, current, and the write
    # all atomic — no window for a concurrent thread to interleave.
    with _THRESHOLDS_LOCK:
        thresholds = _SESSION_THRESHOLDS.get(session_id, {})
        if role not in thresholds or role == "system":
            return
        # Re-read count inside lock so lambda_reg uses the true observation index.
        if session_id not in _THRESHOLD_COUNTS:
            _THRESHOLD_COUNTS[session_id] = {}
        count = _THRESHOLD_COUNTS[session_id].get(role, 0)
        _THRESHOLD_COUNTS[session_id][role] = count + 1
        current = thresholds[role]
        prior = (cfg or {}).get("thresholds", {}).get(role, current) if cfg else current
        lambda_reg = 0.01 / max(math.sqrt(count + 1), 1.0)
        gradient = score - current
        new_threshold = current + ema_alpha * gradient - lambda_reg * (current - prior)
        thresholds[role] = max(0.20, min(0.95, new_threshold))
        # P6A-02: bump version so _get_thresholds CAS can detect this write.
        if session_id not in _THRESHOLD_VERSIONS:
            _THRESHOLD_VERSIONS[session_id] = {}
        _THRESHOLD_VERSIONS[session_id][role] = _THRESHOLD_VERSIONS[session_id].get(role, 0) + 1

    logger.debug(
        "jev-compaction: FTRL threshold %s %.3f → %.3f "
        "(score=%.3f, retained=%s, lambda=%.4f, count=%d)",
        role, current, max(0.20, min(0.95, new_threshold)), score, retained, lambda_reg, count + 1,
    )


# ── Core compaction logic ─────────────────────────────────────────────────────


def _relevance_gated_prune(
    original_fn: Any,
    messages: list[dict[str, Any]],
    protect_tail_count: int,
    protect_tail_tokens: int | None = None,
    min_prune_chars: int = 200,
    *,
    cfg: dict[str, Any],
    session_id: str,
    jev_mod: types.ModuleType | None,
    compressor: Any,
) -> tuple[list[dict[str, Any]], int]:
    """
    Relevance-gated replacement for _prune_old_tool_results.

    Falls through to original on any exception (shadow behaviour).
    """
    try:
        if not messages:
            return messages, 0

        # GAP 2 fix (Wald Ch.3): compute context pressure correctly.
        # threshold_tokens IS a property on ContextCompressor but the correct
        # pressure formula uses last_prompt_tokens relative to threshold_tokens.
        # The original code was correct in using threshold_tokens, but we add a
        # safety fallback: if threshold_tokens is 0 (unresolved), compute it from
        # threshold_percent * context_length to avoid silent never-fire.
        last_tokens = getattr(compressor, "last_prompt_tokens", 0) or 0
        threshold_tokens = getattr(compressor, "threshold_tokens", 0) or 0
        if threshold_tokens == 0:
            # threshold_tokens not yet resolved: estimate from threshold_percent * context_length
            _ctx_len = getattr(compressor, "context_length", 0) or 0
            _thresh_pct = getattr(compressor, "threshold_percent", 0.50) or 0.50
            threshold_tokens = int(_thresh_pct * _ctx_len)

        # Sipser cold-start guard: if last_tokens=0 (first call, no prior compression),
        # assume full context pressure so SPRT engages immediately.
        # Without this, the SPRT ratio (0/threshold) = 0.0 < 0.60 and Jev is permanently
        # skipped on the first (and most important) compaction pass.
        if last_tokens == 0 or last_tokens is None:
            last_tokens = threshold_tokens  # treat cold-start as fully pressured
        sprt_skip_ratio = cfg.get("sprt_skip_ratio", 0.60)
        # Pressure ratio: what fraction of the compaction trigger have we used?
        context_pressure = last_tokens / max(threshold_tokens, 1)

        # GATE GAP 1 (DeGroot Ch 7.5): EVSI-based Jev skip criterion.
        # EVSI = E[V with Jev call] - E[V without]. Estimated as:
        #   evsi = p_middle * (1 - 2*|current_threshold - 0.5|) * retention_value
        # p_middle = fraction of last N messages that landed in the middle tier.
        # P9A-09 fix: original formula used |current_threshold - 0.5| (high when confident,
        # low when uncertain). This is INVERTED: a threshold at 0.5 means MAXIMUM
        # uncertainty — exactly when Jev calls have the most information value.
        # Corrected formula: (1 - 2*|t - 0.5|) = 1 at t=0.5 (max uncertainty → max EVSI),
        #                                          = 0 at t=0 or t=1 (fully decided → skip).
        # If EVSI is below evsi_min, information value of the Jev call is too small — skip.
        # P7A-05 fix: read EVSI counters under lock for consistency with the guarded write.
        # P8A-05 fix: also read current_threshold under the same lock — it is otherwise
        # an unguarded read of _SESSION_THRESHOLDS that breaks the N13 lock discipline.
        with _THRESHOLDS_LOCK:
            _TOTAL_COUNTS.setdefault(session_id, 0)
            _MIDDLE_TIER_COUNTS.setdefault(session_id, 0)
            total_seen = _TOTAL_COUNTS[session_id]
            middle_seen = _MIDDLE_TIER_COUNTS[session_id]
            current_threshold = (_SESSION_THRESHOLDS.get(session_id) or cfg.get("thresholds") or {}).get(
                "tool_result", 0.55
            )
        p_middle = middle_seen / max(total_seen, 1)
        retention_value = cfg.get("retention_value", 1.0)
        # P10A-06 fix: additive uncertainty floor prevents multiplicative zero-out.
        # When p_middle=0 (all prior passes had clear top/bottom tiers), the original
        # formula evsi=p_middle*uncertainty gave 0 regardless of threshold uncertainty —
        # silencing Jev exactly when the threshold is most uncertain (near 0.5).
        # Fix: evsi = p_middle*retention_value + w_uncertainty*(1-2|t-0.5|).
        # w_uncertainty=0.02 floors evsi at ~0.02 when t≈0.5 — enough to exceed evsi_min=0.05
        # when threshold uncertainty is meaningful (|t-0.5|<0.25 → epistemic_term>0.01).
        w_uncertainty = cfg.get("evsi_uncertainty_weight", 0.02)
        uncertainty_term = (1.0 - 2.0 * abs(current_threshold - 0.5)) * w_uncertainty
        evsi = p_middle * retention_value + uncertainty_term
        evsi_min = cfg.get("evsi_min", 0.05)
        # P10A-01 fix: floor p_middle at 0.05 when total_seen < N_MIN_PASSES (5).
        # Cumulative latch: one clear-tier pass makes p_middle=0 permanently because
        # middle_seen/total_seen never resets. Before enough passes to estimate p_middle,
        # do not let a single clear-tier pass permanently kill Jev.
        n_min_passes = cfg.get("evsi_min_passes", 5)
        effective_p_middle = p_middle if total_seen >= n_min_passes else max(p_middle, 0.05)
        evsi_latch_adjusted = effective_p_middle * retention_value + uncertainty_term
        # P11-02 fix: when total_seen < n_min_passes (bootstrap), guarantee evsi_latch_adjusted
        # strictly exceeds evsi_min regardless of retention_value config (<1.0 was possible to
        # produce evsi_latch_adjusted == evsi_min at boundary, susceptible to FP rounding).
        # Hard floor only during bootstrap; mature sessions use the computed value.
        # P12-03 fix: use <= n_min_passes (inclusive) — at exactly n_min_passes the floor
        # drops and p_middle=0 gives evsi_latch_adjusted=uncertainty_term≈0.018 < evsi_min=0.05.
        # The cliff fires Jev suppression on the first "mature" pass. Include the boundary.
        if total_seen <= n_min_passes:
            evsi_latch_adjusted = max(evsi_latch_adjusted, evsi_min + 0.01)
        evsi_skip = total_seen > 0 and evsi_latch_adjusted < evsi_min  # only skip when we have data

        # SPRT early stop: if well under threshold, skip Jev pass entirely.
        # The positional oldest-first from the original is good enough under low pressure.
        use_jev = (
            jev_mod is not None
            and threshold_tokens > 0
            and context_pressure >= sprt_skip_ratio
            and not evsi_skip
        )

        if not use_jev:
            logger.debug(
                "jev-compaction: SPRT/EVSI skip (tokens=%d, threshold=%d, pressure=%.2f, "
                "ratio=%.2f, evsi=%.4f, evsi_latch_adjusted=%.4f, evsi_min=%.4f, evsi_skip=%s)",
                last_tokens, threshold_tokens, context_pressure, sprt_skip_ratio,
                evsi, evsi_latch_adjusted, evsi_min, evsi_skip,
            )
            return original_fn(messages, protect_tail_count, protect_tail_tokens, min_prune_chars)

        # Determine the prune boundary (same logic as original: tail is protected)
        # N04 fix: deep copy to prevent inner list/dict mutation bleeding back to caller.
        # Shallow copy (m.copy()) shares nested content lists — _demote_tool_result_at
        # and _truncate_tool_call_args_at modify them in-place, corrupting the original.
        import copy as _copy
        result = [_copy.deepcopy(m) for m in messages]
        prune_boundary_fn = getattr(compressor, "_prune_boundary", None)
        if prune_boundary_fn is None:
            return original_fn(messages, protect_tail_count, protect_tail_tokens, min_prune_chars)
        prune_boundary = prune_boundary_fn(result, protect_tail_count, protect_tail_tokens)

        candidates_idx = list(range(max(0, prune_boundary)))
        if not candidates_idx:
            return original_fn(messages, protect_tail_count, protect_tail_tokens, min_prune_chars)

        # Build task context from full message list
        task_context = _build_task_context(messages)
        thresholds = _get_thresholds(session_id, cfg)
        rr_lambda = cfg.get("rr_lambda", 0.18)
        ema_alpha = cfg.get("ema_alpha", 0.15)
        call_budget = cfg.get("call_budget", 8)
        budget_remaining = [call_budget]

        # Score all candidates by RR signal
        scored: list[tuple[int, float]] = []
        for win_pos, i in enumerate(candidates_idx):
            msg = result[i]
            role = msg.get("role", "tool")
            # Never score system messages
            if role == "system" or thresholds.get(role, 0.5) >= 1.0:
                continue
            # W3-F03 fix: pass window-relative position and window size so recency
            # is normalized to [0,1] within the prunable window, not the full list.
            score = _rr_score(msg, win_pos, len(candidates_idx), rr_lambda)
            scored.append((i, score))

        if not scored:
            return original_fn(messages, protect_tail_count, protect_tail_tokens, min_prune_chars)

        # Compute percentiles only on demotable roles (not user messages, which are always retained)
        demotable_scores = [s for i, s in scored if result[i].get("role", "tool") != "user"]
        scores_only = demotable_scores if demotable_scores else [s for _, s in scored]
        p33 = _percentile(scores_only, 33)
        p67 = _percentile(scores_only, 67)

        # Edge case: all candidates have the same score (p33 == p67), or n<=2 degeneracy
        # (with n=2, ceil(2*33/100)-1=0 and ceil(2*67/100)-1=0, both map to s[0]==s[0]).
        # P9A-02 note: n<=2 always produces all_same=True via the percentile formula,
        # routing all candidates to middle tier. This is acceptable budget-wise (only
        # 1-2 Jev calls consumed) but is documented here for clarity.
        all_same = (p33 >= p67)

        demote_idx: set[int] = set()  # will be demoted
        retain_idx: set[int] = set()  # will be kept
        middle_idx: list[int] = []    # needs Jev scoring

        # ── Huth-Ryan Hoare triple for the classification loop ─────────────
        # Precondition:  scored is a list of (idx, rr_score) pairs,
        #                demote_idx = {}, retain_idx = {}, middle_idx = [],
        #                all messages in scored are unprocessed.
        # Invariant:     At the start of each iteration, every (i, score)
        #                pair already consumed has been assigned to exactly
        #                one of {demote_idx, retain_idx, middle_idx}.
        #                len(messages) is unchanged throughout the loop.
        # Postcondition: Every element of scored is in exactly one of
        #                demote_idx | retain_idx | {j for j in middle_idx}.
        # ──────────────────────────────────────────────────────────────────
        for i, score in scored:
            msg_role = result[i].get("role", "tool")
            # Only tool/assistant messages are demotable; never demote user messages
            # (mirrors original _prune_old_tool_results behaviour)
            if msg_role == "user":
                retain_idx.add(i)
                continue
            if all_same:
                # All same score: send to middle tier for Jev to decide
                middle_idx.append(i)
            elif score <= p33:
                demote_idx.add(i)
            elif score >= p67:
                retain_idx.add(i)
            else:
                middle_idx.append(i)

        # GATE GAP 1 (DeGroot Ch 7.5): update EVSI rolling counters after tier assignment
        # P7A-05 fix: compound R-M-W on _TOTAL_COUNTS/_MIDDLE_TIER_COUNTS is not atomic
        # under concurrency — guard under _THRESHOLDS_LOCK to prevent lost increments.
        total_demotable = len([i for i, _ in scored if result[i].get("role", "tool") != "user"])
        with _THRESHOLDS_LOCK:
            _TOTAL_COUNTS[session_id] = _TOTAL_COUNTS.get(session_id, 0) + max(total_demotable, 1)
            _MIDDLE_TIER_COUNTS[session_id] = _MIDDLE_TIER_COUNTS.get(session_id, 0) + len(middle_idx)

        # Jev semantic scoring on middle tier
        # P4B-09 fix: assert is stripped by python -O; use explicit conditional log + safe fallback
        # so invariant violations are caught in optimized builds too.
        if len(demote_idx) > len(messages):
            logger.error(
                "jev-compaction: invariant violated demote_idx=%d > messages=%d; "
                "falling through to original compressor",
                len(demote_idx), len(messages),
            )
            return original_fn(messages, protect_tail_count, protect_tail_tokens, min_prune_chars)
        role_map = {
            "tool": "tool_result",
            "assistant": "assistant",
            "user": "user",
            "system": "system",
        }
        # GATE GAP 3 (Berger Ch 5.4): track which roles are updated this pass for JS shrinkage
        _roles_updated_this_pass: set[str] = set()
        # W3-F04/F05 fix: hoist scored→dict and middle_idx→set BEFORE all three loops.
        # Previously dict(scored) was rebuilt inside each iteration (O(N) allocations)
        # and set-comprehension-over-middle-idx rebuilt as a set comprehension each iteration (O(N²)).
        rr_score_map_all = dict(scored)
        middle_set = set(middle_idx)
        # F06 (crystal wiring): build recency_map so crystal_fidelity_decide gets a
        # per-message recency score without re-iterating candidates_idx inside the loop.
        recency_map = {
            i: (p / max(len(candidates_idx) - 1, 1))
            for p, i in enumerate(candidates_idx)
        }
        crystal_mod = _load_crystal_tiers()
        seg_mod = _load_segment_compactor()

        # P4A-03 fix: track crystal-lossy indices so segment compactor skips them
        # (avoids double-processing: crystal_lossy_compress already compacted the msg).
        crystal_lossy_idx: set[int] = set()
        # P13A-02 fix: track crystal-lossless indices so the top-tier retain loop
        # skips _record_decision for them (same P5A-02 invariant: crystal paths skip FTRL).
        crystal_lossless_idx: set[int] = set()

        for i in middle_idx:
            msg = result[i]
            raw_role = msg.get("role", "tool")
            role_key = role_map.get(raw_role, "tool_result")
            base_thresh = thresholds.get(role_key, 0.55)
            # GAP 4: UCB1 cold-start guard — lower threshold when observation count is low
            count = _get_count(session_id, role_key)
            thresh = _cold_start_boost(role_key, count, base_thresh)

            rr_i = rr_score_map_all.get(i, 0.0)
            # F03 wiring: Crystal Fidelity Tiers (arXiv:2608.00303) — Tier B lossy
            # truncation between full-retain (lossless) and full-demotion.
            # Avoids spending a Jev LLM call on clear grey-zone messages.
            if crystal_mod is not None:
                try:
                    rec = recency_map.get(i, 0.5)
                    crystal_tier = crystal_mod.crystal_fidelity_decide(rr_i, msg, rec)
                    if crystal_tier == "lossless":
                        retain_idx.add(i)
                        crystal_lossless_idx.add(i)  # P13A-02: guard retain loop from re-running FTRL
                        # P5A-02 fix: do NOT call _record_decision with rr_i for crystal paths.
                        # _record_decision feeds _update_threshold, which expects a Jev relevance
                        # score. rr_i is an RR heuristic (different distribution) — feeding it
                        # corrupts the FTRL threshold calibrated for the Jev decision gate.
                        # Only emit the calibration event for observability; skip FTRL update.
                        _write_calibration_event(
                            session_id, role_key, rr_i, "retain",
                            _extract_tool_name(msg), "crystal_lossless", rr_i, None,
                        )
                        # P10A-05 fix: do NOT add to _roles_updated_this_pass for crystal
                        # paths. JS shrinkage should only fire on roles with actual FTRL
                        # gradient updates. Crystal-lossless deliberately skips _record_decision
                        # (P5A-02), so it produces no FTRL signal — marking it as "updated"
                        # causes JS to apply spurious shrinkage with stale sigma² estimates.
                        continue
                    elif crystal_tier == "lossy":
                        compressed = crystal_mod.crystal_lossy_compress(msg)
                        result[i] = compressed
                        retain_idx.add(i)
                        # P12B-01: only block segment compactor when compression actually
                        # reduced content (crystal_lossy_compress bails unchanged for
                        # multimodal messages; blocking segment compactor on those would
                        # silently skip them through both compactors with zero reduction).
                        orig_len = len(_extract_content_text(msg))
                        new_len = len(_extract_content_text(compressed))
                        if new_len < orig_len:
                            crystal_lossy_idx.add(i)
                        # P5A-02 fix: same — skip _record_decision for crystal-lossy path.
                        # P10A-05 fix: same as crystal_lossless — do NOT add to
                        # _roles_updated_this_pass; crystal-lossy skips FTRL, so JS
                        # shrinkage would use stale sigma² for this role.
                        _write_calibration_event(
                            session_id, role_key, rr_i, "retain",
                            _extract_tool_name(msg), "crystal_lossy", rr_i, None,
                        )
                        continue
                    # "demote" → fall through to Jev scoring below
                except Exception:
                    pass  # shadow: never raises
            jev_score = _jev_relevance(msg, task_context, jev_mod, budget_remaining) if jev_mod is not None else None
            if jev_score is None:
                # Budget exhausted or call failed: fall back to RR classification
                # (positionally oldest = more likely to demote)
                rr = rr_score_map_all.get(i, 0.0)
                jev_score = max(0.0, min(1.0, (rr - p33) / max(p67 - p33, 0.01)))

            if jev_score < thresh:
                demote_idx.add(i)
                # Milewski monad law: side-effect (EMA record) AFTER decision
                _record_decision(session_id, role_key, jev_score, retained=False, ema_alpha=ema_alpha, cfg=cfg)
                # GATE GAP 3: track role updated
                _roles_updated_this_pass.add(role_key)
                # GAP 1: write calibration event (Jaynes Ch.13)
                _write_calibration_event(
                    session_id, role_key, jev_score, "demote",
                    _extract_tool_name(msg), "middle", rr_i, jev_score,
                )
            else:
                retain_idx.add(i)
                # Milewski monad law: side-effect (EMA record) AFTER decision
                _record_decision(session_id, role_key, jev_score, retained=True, ema_alpha=ema_alpha, cfg=cfg)
                # GATE GAP 3: track role updated
                _roles_updated_this_pass.add(role_key)
                # GAP 1: write calibration event (Jaynes Ch.13)
                _write_calibration_event(
                    session_id, role_key, jev_score, "retain",
                    _extract_tool_name(msg), "middle", rr_i, jev_score,
                )

        # Also update FTRL thresholds for the clear tiers using their RR score as proxy
        # GAP 1: write calibration events for bottom/top tiers (Jaynes Ch.13)
        # W3-F04 fix: rr_score_map_all already built above before middle loop.
        for i in list(demote_idx):
            raw_role = result[i].get("role", "tool")
            role_key = role_map.get(raw_role, "tool_result")
            rr = rr_score_map_all.get(i, 0.0)
            norm = max(0.0, min(1.0, (rr - p33) / max(p67 - p33, 0.01)))
            # P13A-01 fix: skip FTRL + roles update for middle-set members — they were
            # already processed by the Jev loop with a correct semantic score. The Jev loop
            # also adds role_key to _roles_updated_this_pass (line 1252), so skipping here
            # is a pure correctness fix with no JS gating side-effect.
            # P14-LOW cleanup: consolidate both middle_set guards and the roles add into
            # one block so the dead add (set dedup no-op) is removed.
            if i not in middle_set:
                _record_decision(session_id, role_key, norm, retained=False, ema_alpha=ema_alpha, cfg=cfg)
                _roles_updated_this_pass.add(role_key)  # clear-tier only; Jev loop covers middle_set
                _write_calibration_event(
                    session_id, role_key, norm, "demote",
                    _extract_tool_name(result[i]), "bottom", rr, None,
                )
        for i in list(retain_idx):
            raw_role = result[i].get("role", "tool")
            # N03 fix: never update EMA for user messages — they are always retained by policy,
            # not by a calibrated threshold. Feeding score=1.0 into the user EMA would drift
            # the threshold toward 1.0 and eventually trigger Jev scoring of user messages.
            if raw_role == "user":
                continue
            role_key = role_map.get(raw_role, "tool_result")
            rr = rr_score_map_all.get(i, 1.0)
            norm = max(0.0, min(1.0, (rr - p33) / max(p67 - p33, 0.01)))
            # Milewski monad law: side-effect AFTER decision; clamp via _record_decision
            # P13A-02 fix: skip FTRL update for messages already processed by Jev/crystal.
            # (a) middle_set: already updated by Jev loop with correct semantic score.
            # (b) crystal_lossless_idx / crystal_lossy_idx: P5A-02 invariant — crystal paths
            #     skip FTRL. Without this guard the retain loop re-runs _record_decision with
            #     an RR proxy score, overwriting the threshold calibrated for Jev decisions.
            if i in middle_set or i in crystal_lossless_idx or i in crystal_lossy_idx:
                continue
            _record_decision(session_id, role_key, norm, retained=True, ema_alpha=ema_alpha, cfg=cfg)
            _roles_updated_this_pass.add(role_key)
            # Only write calibration event for top-tier (retained by RR), not middle-tier already logged
            if i not in middle_set:
                _write_calibration_event(
                    session_id, role_key, norm, "retain",
                    _extract_tool_name(result[i]), "top", rr, None,
                )

        # F02 wiring: Segment-Level Compaction (arXiv:2608.12990 LycheeMemory V2).
        # For retained messages that are long tool/assistant results, replace low-salience
        # middle content with a placeholder, saving ~40% tokens without demotion.
        # Only applied when seg_mod loaded; shadow: never raises.
        if seg_mod is not None:
            task_ctx_str = task_context if isinstance(task_context, str) else ""
            for i in list(retain_idx):
                if i in crystal_lossy_idx:
                    continue  # P4A-03: already compressed by crystal_lossy_compress; don't re-compact
                try:
                    if seg_mod.can_benefit_from_compaction(result[i]):
                        compacted = seg_mod.segment_compact_message(result[i], task_ctx_str)
                        if compacted is not None:
                            result[i] = compacted
                except Exception:
                    pass  # shadow: never raises

        # GATE GAP 3 (Berger Ch 5.4): apply James-Stein shrinkage when all three roles
        # (tool_result, assistant, user) were updated this pass — the full k=3 admissibility
        # condition. P11-04 fix: the prior guard (tool_result AND assistant) allowed JS to fire
        # with only 2 fresh estimates, shrinking toward a grand mean that includes a stale user=0.72
        # anchor. Stein's theorem requires all k components to be fresh; otherwise shrinkage
        # toward a contaminated grand mean can increase MSE vs no shrinkage.
        #
        # P12-02 fix: user messages are unconditionally retained (N03 policy — never scored by Jev)
        # and therefore NEVER added to _roles_updated_this_pass. This made the P11-04 all-3-roles
        # guard permanently suppress JS. Fix: treat user as "structurally fresh" if any user
        # messages appear in retain_idx this pass (they were seen, just not FTRL-updated).
        # This preserves the Stein admissibility intent while allowing JS to fire in practice.
        _user_seen_this_pass = any(
            result[i].get("role") == "user" for i in retain_idx
        )
        if _user_seen_this_pass:
            _roles_updated_this_pass.add("user")
        if all(r in _roles_updated_this_pass for r in ("tool_result", "assistant", "user")):
            _apply_js_shrinkage(session_id, cfg)

        # Apply demotion: call original _demote_tool_result_at for scored demote set,
        # skip for retain set. For messages outside scored (e.g. no content), use original.
        scored_indices = {i for i, _ in scored}
        demote_tool_fn = getattr(compressor, "_demote_tool_result_at", None)
        call_id_to_tool = {}
        try:
            from agent.context_compressor import _tool_calls_by_id  # type: ignore[import]
            call_id_to_tool = _tool_calls_by_id(result)
        except Exception:
            pass

        pruned = 0
        if demote_tool_fn is not None:
            for i in candidates_idx:
                if i in demote_idx:
                    n = demote_tool_fn(result, i, call_id_to_tool, min_prune_chars)
                    pruned += n if isinstance(n, int) else (1 if n else 0)
                elif i not in scored_indices:
                    # Not scored (system, etc.) — use original demote logic
                    n = demote_tool_fn(result, i, call_id_to_tool, min_prune_chars)
                    pruned += n if isinstance(n, int) else (1 if n else 0)
                # else: i in retain_idx → skip demotion
        else:
            # Fallback: original handles everything
            return original_fn(messages, protect_tail_count, protect_tail_tokens, min_prune_chars)

        # Pass: truncate tool call args — only for demoted messages (retain_idx keeps full args)
        truncate_fn = getattr(compressor, "_truncate_tool_call_args_at", None)
        if truncate_fn:
            for i in candidates_idx:
                if i not in retain_idx:
                    truncate_fn(result, i)

        # Pass: retire stale images (same as original pass 3.5)
        try:
            from agent.context_compressor import _retire_stale_tool_result_images  # type: ignore[import]
            pruned += _retire_stale_tool_result_images(result)
        except Exception:
            pass

        # Pass: pressure demote tail if needed (same as original)
        if protect_tail_tokens and protect_tail_tokens > 0 and result:
            pressure_fn = getattr(compressor, "_pressure_demote_tail", None)
            if pressure_fn:
                pruned += pressure_fn(result, prune_boundary, protect_tail_tokens, call_id_to_tool, min_prune_chars)

        jev_calls_used = call_budget - budget_remaining[0]
        logger.info(
            "jev-compaction: demoted=%d retained=%d jev_calls=%d/%d session=%s",
            len(demote_idx), len(retain_idx), jev_calls_used, call_budget, session_id[:8],
        )
        return result, pruned

    except Exception as exc:
        logger.warning("jev-compaction: _relevance_gated_prune failed (%s); using original", exc)
        return original_fn(messages, protect_tail_count, protect_tail_tokens, min_prune_chars)


def _percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, min(len(s) - 1, int(math.ceil(len(s) * p / 100)) - 1))
    return s[idx]


# ── Plugin patch state (per-compressor instance, keyed by id) ─────────────────
# Maps id(compressor) → session_id. Weakref finalizer auto-evicts dead ids to
# prevent id() reuse from skipping the patch on a new session's compressor.
import weakref as _weakref

_PATCHED: dict[int, Any] = {}


def _evict_patched_id(cid: int) -> None:
    """Called by weakref.finalize when a compressor is GC'd. Removes stale id."""
    # P6B-07: GC finalizer can run in any thread; use _PATCHED_LOCK to prevent races
    # with _patch_compressor's check-and-update sequence.
    with _PATCHED_LOCK:
        _PATCHED.pop(cid, None)


def _patch_compressor(
    compressor: Any,
    cfg: dict[str, Any],
    session_id: str,
    jev_mod: types.ModuleType | None,
) -> None:
    """Monkeypatch _prune_old_tool_results on this compressor instance (not the class).

    Idempotent: patching the same instance twice is a no-op.
    Shadow: never raises.
    """
    try:
        cid = id(compressor)
        # P6B-07 fix: _PATCHED_LOCK guards all reads and writes to _PATCHED.
        # The GC finalizer (_evict_patched_id) runs in any thread without warning;
        # without the lock a pop between `if cid in _PATCHED` and `stored = _PATCHED[cid]`
        # raises KeyError silently swallowed here, causing the compressor to be re-patched
        # unnecessarily (doubling the patch depth for that session).
        with _PATCHED_LOCK:
            already_patched = cid in _PATCHED
            stored = _PATCHED.get(cid)
        if already_patched:
            # W3-F01 / N09 fix: compressor reused across sessions.
            # _PATCHED[cid] stores (session_id, _session_ref) — update _session_ref[0]
            # so the already-installed closure reads the new session's EMA state.
            if isinstance(stored, tuple):
                _sid, _ref = stored
                _ref[0] = session_id
                with _PATCHED_LOCK:
                    _PATCHED[cid] = (session_id, _ref)
            else:
                # NEW-BUG-01 guard: legacy string storage (pre-W3-F01) — closure's
                # _session_ref was never created, so we cannot update it in-place.
                # Log a warning; the closure will operate under the old session until
                # the compressor object is garbage-collected and re-patched.
                import warnings
                warnings.warn(
                    f"jev-compaction: _patch_compressor re-entry for cid={cid} found "
                    f"legacy str storage (not tuple) — closure session_id not updated. "
                    f"Old session EMA state will be used until compressor is recycled.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                with _PATCHED_LOCK:
                    _PATCHED[cid] = session_id
            return

        # F04 fix: read from the instance first (falls back to class if unpatched).
        # getattr(compressor.__class__, ...) bypasses any instance-level patches set
        # by other plugins, silently breaking their hook. Instance-level getattr
        # does the right MRO walk: instance dict → class → bases.
        original = getattr(compressor, "_prune_old_tool_results", None)
        if original is None:
            logger.debug("jev-compaction: compressor has no _prune_old_tool_results; skipping patch")
            return
        # F04 fix (follow-up): getattr(compressor, ...) returns a bound method when
        # the attribute is defined on the class (the common case), or an unbound function
        # when another plugin has stored a plain function as an instance attribute.
        # Only wrap with MethodType when it is NOT already bound to this compressor instance.
        import types as _types_bind
        if isinstance(original, _types_bind.MethodType) and original.__self__ is compressor:
            # Already bound to this compressor — use as-is.
            pass
        elif not isinstance(original, _types_bind.MethodType):
            # Plain function stored as instance attribute — bind it.
            original = _types_bind.MethodType(original, compressor)
        # Capture locals in closure.
        # W3-F01 fix: use a mutable container for session_id so that when
        # _patch_compressor is called again for a new session on a reused compressor,
        # updating _session_ref[0] in the already-patched branch propagates into the
        # closure.  A plain scalar _session_id is captured by value and cannot be
        # updated from outside the closure.
        _cfg = cfg
        _session_ref = [session_id]   # mutable single-element list
        _jev = jev_mod
        _compressor = compressor

        def _patched_prune(
            messages: Any,
            protect_tail_count: int = 0,
            protect_tail_tokens: int | None = None,
            min_prune_chars: int = 200,
        ) -> tuple[list[dict[str, Any]], int]:
            return _relevance_gated_prune(
                original,
                messages,
                protect_tail_count,
                protect_tail_tokens,
                min_prune_chars,
                cfg=_cfg,
                session_id=_session_ref[0],
                jev_mod=_jev,
                compressor=_compressor,
            )

        import types as _types
        with _PATCHED_LOCK:
            # P8A-07 fix: install the closure INSIDE the lock, after the re-check.
            # Previously line 1367 installed _patched_prune before acquiring the lock.
            # In the two-thread race, both write compressor._prune_old_tool_results;
            # the last writer wins the attribute, but only the first-lock-winner's entry
            # is stored in _PATCHED.  If the last writer's closure was installed on the
            # instance, it runs with the losing session_id forever.
            # Moving the install inside the lock means only the lock-winner installs,
            # guaranteeing PATCHED[cid] and the live closure agree on session_ref.
            if cid in _PATCHED:
                # Lost the race — update _session_ref for the already-installed closure.
                stored2 = _PATCHED[cid]
                if isinstance(stored2, tuple):
                    _, _ref2 = stored2
                    _ref2[0] = session_id
                    _PATCHED[cid] = (session_id, _ref2)
                return
            compressor._prune_old_tool_results = _patched_prune  # plain fn, not MethodType
            _PATCHED[cid] = (session_id, _session_ref)
        try:
            _weakref.finalize(compressor, _evict_patched_id, cid)
        except TypeError:
            pass  # some objects aren't weakref-able; id-reuse risk accepted
        logger.info(
            "jev-compaction: patched compressor instance %d for session %s",
            cid, session_id[:8],
        )
    except Exception as exc:
        logger.debug("jev-compaction: _patch_compressor failed: %s", exc)


# ── Hook implementations ──────────────────────────────────────────────────────

_cfg_cache: dict[str, Any] | None = None


def on_pre_compress(
    *,
    session_id: str = "",
    context_tokens: int = 0,
    agent: Any = None,
    **_kwargs: Any,
) -> None:
    """Intercept pre_compress: patch compressor instance with relevance-gated prune."""
    try:
        global _cfg_cache
        if _cfg_cache is None:
            return  # register() not called yet

        cfg = _cfg_cache
        if not cfg.get("enabled", True):
            return

        compressor = None
        if agent is not None:
            compressor = getattr(agent, "context_compressor", None)
        if compressor is None:
            logger.debug("jev-compaction: no compressor on agent; skipping patch")
            return

        jev_mod = _load_jev()
        _patch_compressor(compressor, cfg, session_id or "", jev_mod)

    except Exception as exc:
        logger.debug("jev-compaction: on_pre_compress suppressed: %s", exc)


def on_session_end(*, session_id: str = "", **_kwargs: Any) -> None:
    """Clean up session EMA state and untrack patched instances."""
    try:
        # P6A-03/P6A-04 fix: all cleanup under one _THRESHOLDS_LOCK acquisition.
        # Previously _THRESHOLD_COUNTS.pop was outside the lock → a racing
        # _update_threshold could re-create the entry after cleanup, leaving a zombie
        # that resets lambda_reg decay for the next session reusing the same session_id.
        # _SCORE_HISTORY cleanup was also outside the lock → on_session_end iterating the
        # dict while _update_threshold inserts a new key raises RuntimeError (Python 3
        # "dictionary changed size during iteration"), silently swallowed and leaving
        # memory leaks in long-running processes with frequent session churn.
        with _THRESHOLDS_LOCK:
            _SESSION_THRESHOLDS.pop(session_id, None)
            _THRESHOLD_COUNTS.pop(session_id, None)
            _THRESHOLD_VERSIONS.pop(session_id, None)
            # GATE GAP 4 (Billingsley Sec 32): clean up atom-detection score histories
            keys_to_drop = [k for k in _SCORE_HISTORY if k.startswith(f"{session_id}:")]
            for k in keys_to_drop:
                _SCORE_HISTORY.pop(k, None)
            # P8A-06 fix: MIDDLE_TIER/TOTAL_COUNTS written under lock in _relevance_gated_prune;
            # pop them inside the same lock so a racing prune cannot re-create them after cleanup.
            _MIDDLE_TIER_COUNTS.pop(session_id, None)
            _TOTAL_COUNTS.pop(session_id, None)
            # P10A-04 fix: clean up in-memory beta counters for this session.
            _BETA_COUNTERS.pop(session_id, None)
    except Exception:
        pass


# ── Registration ──────────────────────────────────────────────────────────────


def register(ctx: Any) -> None:
    """Register plugin hooks with the Hermes plugin context."""
    global _cfg_cache
    try:
        _cfg_cache = _load_cfg(ctx)
        if not _cfg_cache.get("enabled", True):
            logger.info("jev-compaction: disabled via config; not registering hooks")
            return
    except Exception as exc:
        logger.warning("jev-compaction: config load failed: %s; using defaults", exc)
        _cfg_cache = dict(_DEFAULT_CFG)

    try:
        ctx.register_hook("pre_compress", on_pre_compress)
        logger.info("jev-compaction: registered pre_compress hook")
    except Exception as exc:
        logger.warning("jev-compaction: failed to register pre_compress: %s", exc)

    try:
        ctx.register_hook("on_session_end", on_session_end)
        logger.debug("jev-compaction: registered on_session_end hook")
    except Exception as exc:
        logger.debug("jev-compaction: on_session_end registration skipped: %s", exc)
