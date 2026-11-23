#!/usr/bin/env python3
"""compaction-signal-fuser.py — Naive-Bayes log-odds fusion of compaction triggers.

Each independent trigger (relevance, prequential, context-ac-rate) emits a
soft COMPACT/HOLD recommendation. Combine likelihood ratios in log-odds
space and emit a single FUSE_COMPACT / FUSE_HOLD posterior.

Usage:
  HERMES_HOME=... python3 compaction-signal-fuser.py
  HERMES_HOME=... python3 compaction-signal-fuser.py --self-test
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LR_COMPACT = 3.0  # ~75% precision per independent signal
LR_HOLD = 0.5
LR_MISSING = 1.0
PRIOR_P_COMPACT = 0.3
THRESHOLD = 0.6

SIGNAL_SPECS = (
    ("relevance-compaction-trigger", "compaction-trigger-signal.json"),
    ("prequential-compaction-trigger", "prequential-state.json"),
    ("context-ac-rate", "context-ac-rate-state.json"),
)


def _hermes_home() -> Path:
    raw = os.environ.get("HERMES_HOME")
    return Path(raw) if raw else Path.home() / ".hermes"


def _profile_root() -> Path:
    hh = _hermes_home()
    if hh.name == "fork":
        return hh
    return hh / "profiles" / "fork"


def _cache_dir() -> Path:
    return _profile_root() / "cache"


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _normalize_recommend(payload: dict[str, Any]) -> str | None:
    for key in ("recommend", "recommendation", "signal"):
        val = payload.get(key)
        if not isinstance(val, str):
            continue
        token = val.strip().upper()
        if not token:
            continue
        if "COMPACT" in token and "HOLD" not in token:
            return "COMPACT"
        if token.endswith("HOLD") or token == "HOLD" or token == "KEEP":
            return "HOLD"
    return None


def _likelihood_ratio(recommend: str | None) -> float:
    if recommend == "COMPACT":
        return LR_COMPACT
    if recommend == "HOLD":
        return LR_HOLD
    return LR_MISSING


def _sigmoid(log_odds: float) -> float:
    if log_odds >= 0:
        p = 1.0 / (1.0 + math.exp(-log_odds))
    else:
        exp_x = math.exp(log_odds)
        p = exp_x / (1.0 + exp_x)
    return max(0.0, min(1.0, p))


def fuse_recommendations(recs: list[tuple[str, str | None]]) -> dict[str, Any]:
    """Naive-Bayes log-odds fusion. Missing recs contribute LR=1 (no evidence)."""
    log_odds = math.log(PRIOR_P_COMPACT / (1.0 - PRIOR_P_COMPACT))
    present: list[str] = []
    for name, rec in recs:
        lr = _likelihood_ratio(rec)
        if rec is not None:
            present.append(name)
            log_odds += math.log(lr)
    p_compact = _sigmoid(log_odds)
    recommend = "FUSE_COMPACT" if p_compact >= THRESHOLD else "FUSE_HOLD"
    return {
        "p_compact": p_compact,
        "recommend": recommend,
        "n_signals": len(present),
        "signals_present": present,
        "threshold_used": THRESHOLD,
    }


def collect_signals(cache_dir: Path) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    for name, filename in SIGNAL_SPECS:
        payload = _load_json(cache_dir / filename)
        rec = _normalize_recommend(payload) if payload else None
        out.append((name, rec))
    return out


def run(cache_dir: Path | None = None, write: bool = True) -> dict[str, Any]:
    cache = cache_dir if cache_dir is not None else _cache_dir()
    fused = fuse_recommendations(collect_signals(cache))
    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "p_compact": fused["p_compact"],
        "recommend": fused["recommend"],
        "n_signals": fused["n_signals"],
        "signals_present": fused["signals_present"],
        "threshold_used": fused["threshold_used"],
    }
    if write:
        _atomic_write_json(cache / "compaction-fused-signal.json", payload)
    return payload


def _self_test() -> int:
    two_compact = fuse_recommendations(
        [
            ("relevance-compaction-trigger", "COMPACT"),
            ("prequential-compaction-trigger", "COMPACT"),
            ("context-ac-rate", None),
        ]
    )
    assert two_compact["p_compact"] > 0.6, two_compact
    assert two_compact["recommend"] == "FUSE_COMPACT", two_compact
    assert two_compact["n_signals"] == 2, two_compact

    zero = fuse_recommendations(
        [
            ("relevance-compaction-trigger", None),
            ("prequential-compaction-trigger", None),
            ("context-ac-rate", None),
        ]
    )
    assert zero["p_compact"] < 0.6, zero
    assert zero["n_signals"] == 0, zero
    assert zero["recommend"] == "FUSE_HOLD", zero
    assert abs(zero["p_compact"] - PRIOR_P_COMPACT) < 1e-12, zero

    holds = fuse_recommendations(
        [
            ("relevance-compaction-trigger", "HOLD"),
            ("prequential-compaction-trigger", "HOLD"),
            ("context-ac-rate", "HOLD"),
        ]
    )
    assert holds["p_compact"] < 0.5, holds
    assert holds["recommend"] == "FUSE_HOLD", holds
    assert holds["n_signals"] == 3, holds

    # Missing cache files: no crash, treated as no evidence.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp)
        payload = run(cache_dir=empty, write=True)
        assert payload["n_signals"] == 0, payload
        assert payload["p_compact"] < 0.6, payload
        out = empty / "compaction-fused-signal.json"
        assert out.is_file()
        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded["recommend"] in ("FUSE_COMPACT", "FUSE_HOLD")
        assert loaded["threshold_used"] == THRESHOLD

        # Malformed JSON is skipped.
        (empty / "compaction-trigger-signal.json").write_text("{not-json", encoding="utf-8")
        payload2 = run(cache_dir=empty, write=False)
        assert payload2["n_signals"] == 0, payload2

        # Two COMPACT files on disk fuse above threshold.
        _atomic_write_json(
            empty / "compaction-trigger-signal.json",
            {"recommend": "COMPACT", "mean_relevance": 0.1},
        )
        _atomic_write_json(
            empty / "prequential-state.json",
            {"recommendation": "COMPACT", "rate_delta": -0.04},
        )
        payload3 = run(cache_dir=empty, write=True)
        assert payload3["p_compact"] > 0.6, payload3
        assert payload3["recommend"] == "FUSE_COMPACT", payload3
        assert payload3["n_signals"] == 2, payload3

    print(
        "[self-test] PASS compaction-signal-fuser "
        f"two_compact={two_compact['p_compact']:.4f} "
        f"zero={zero['p_compact']:.4f} holds={holds['p_compact']:.4f}"
    )
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()
    try:
        payload = run()
        print(json.dumps(payload, indent=2))
        return 0
    except Exception as exc:
        print(f"compaction-signal-fuser: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
