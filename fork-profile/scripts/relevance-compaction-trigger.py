#!/usr/bin/env python3
"""Relevance-decay compaction trigger.

Tracks semantic relevance of context turns to the current task using TF
bag-of-words cosine similarity (no external embeddings). When the mean
relevance of the oldest 20% of turns drops below threshold, emit COMPACT
to cache/compaction-trigger-signal.json.

Kill test:
    rel = compute_relevance(turns, task)
    assert all(0.0 <= r <= 1.0 for r in rel)
    assert isinstance(should_compact(rel), bool)
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

HERMES_HOME = Path(__file__).resolve().parents[3]
PROFILE_ROOT = HERMES_HOME / "profiles" / "fork"
CACHE_DIR = PROFILE_ROOT / "cache"
SIGNAL_PATH = CACHE_DIR / "compaction-trigger-signal.json"

DEFAULT_THRESHOLD = 0.15
TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


def _turn_text(turn: Any) -> str:
    if isinstance(turn, str):
        return turn
    if isinstance(turn, dict):
        for key in ("text", "content", "message", "body"):
            val = turn.get(key)
            if isinstance(val, str) and val.strip():
                return val
        return " ".join(str(v) for v in turn.values() if isinstance(v, str))
    return str(turn or "")


def _vocab(*token_lists: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for tokens in token_lists:
        for tok in tokens:
            seen.setdefault(tok, None)
    return list(seen)


def _tf(tokens: list[str], vocab: list[str]) -> list[float]:
    counts = Counter(tokens)
    return [float(counts.get(w, 0.0)) for w in vocab]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    if HAS_NUMPY:
        va = np.asarray(a, dtype=float)
        vb = np.asarray(b, dtype=float)
        na = float(np.linalg.norm(va))
        nb = float(np.linalg.norm(vb))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(np.clip(np.dot(va, vb) / (na * nb), 0.0, 1.0))
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


def compute_relevance(turns: list[dict], task: str) -> list[float]:
    """Cosine similarity of each turn's TF vector vs the task TF vector."""
    task_toks = _tokenize(task or "")
    scores: list[float] = []
    for turn in turns or []:
        turn_toks = _tokenize(_turn_text(turn))
        vocab = _vocab(task_toks, turn_toks)
        if not vocab:
            scores.append(0.0)
            continue
        scores.append(_cosine(_tf(turn_toks, vocab), _tf(task_toks, vocab)))
    return scores


def should_compact(relevances: list[float], threshold: float = DEFAULT_THRESHOLD) -> bool:
    """True when mean relevance of the oldest 20% of turns is below threshold."""
    if not relevances:
        return False
    n = len(relevances)
    if n < 5:
        return False
    k = max(1, int(n * 0.2))
    old = relevances[:k]
    mean_old = sum(old) / float(len(old))
    return mean_old < threshold


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def emit_signal(payload: dict) -> dict:
    _atomic_write_json(SIGNAL_PATH, payload)
    return payload


def evaluate(
    turns: list[dict],
    task: str,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    rel = compute_relevance(turns, task)
    n = len(rel)
    k = max(1, int(n * 0.2)) if n else 1
    mean_old = (sum(rel[:k]) / float(k)) if rel else 0.0
    mean_recent = (sum(rel[-k:]) / float(k)) if rel else 0.0
    compact = should_compact(rel, threshold)
    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "signal": "COMPACT" if compact else "HOLD",
        "mean_relevance_old": round(mean_old, 6),
        "mean_relevance_recent": round(mean_recent, 6),
        "trigger_threshold": threshold,
        "n_turns": n,
    }
    if compact:
        emit_signal(payload)
    return payload


def _synthetic_turns() -> tuple[list[dict], str]:
    task = "implement relevance decay compaction trigger for context turns"
    relevant = [
        "compaction should drop stale context turns from the window",
        "relevance decay tracks cosine similarity of keyword vectors",
        "oldest turns lose relevance to the current compaction task",
        "emit a compact signal when mean relevance falls below threshold",
        "context window rolling mean of oldest slice drives the trigger",
        "task keyword vector compared against each turn bag of words",
        "threshold default is zero point one five for the oldest slice",
        "recent turns stay on topic about compaction and relevance scores",
    ]
    irrelevant = [
        "banana muffin recipe with extra chocolate chips",
        "soccer league standings from last weekend",
        "the weather in antarctica is mostly ice",
        "piano tuning frequencies for middle c",
        "gardening tips for growing tomatoes in clay soil",
        "unrelated trivia about roman emperors and bread",
        "stock prices of random fruit companies yesterday",
        "a poem about clouds that never mentions context",
    ]
    # Oldest-first: irrelevant head is the oldest 20%+; recent tail stays on-task.
    # (Newest-first this head is an irrelevant tail of the live window.)
    turns = [{"text": t} for t in irrelevant + relevant]
    return turns, task


def layer1_demo() -> None:
    try:
        turns, task = _synthetic_turns()
        rel = compute_relevance(turns, task)
        assert all(0.0 <= r <= 1.0 for r in rel), rel
        assert isinstance(should_compact(rel), bool)
        n = len(rel)
        k = max(1, int(n * 0.2))
        mean_old = sum(rel[:k]) / float(k)
        mean_recent = sum(rel[-k:]) / float(k)
        assert mean_old < DEFAULT_THRESHOLD, f"expected old mean < 0.15, got {mean_old}"
        assert mean_recent > mean_old, f"recent {mean_recent} should exceed old {mean_old}"
        assert should_compact(rel) is True
        payload = evaluate(turns, task)
        assert payload["signal"] == "COMPACT"
        assert SIGNAL_PATH.is_file()
        loaded = json.loads(SIGNAL_PATH.read_text(encoding="utf-8"))
        assert loaded["signal"] == "COMPACT"
        assert loaded["n_turns"] == n
        empty = compute_relevance([], "")
        assert empty == []
        assert should_compact([]) is False
        print(
            f"[layer1] PASS — n={n} mean_old={mean_old:.4f} "
            f"mean_recent={mean_recent:.4f} signal={payload['signal']}"
        )
    finally:
        # Always remove the demo compact signal — do not pollute real compaction consumers
        try:
            SIGNAL_PATH.unlink(missing_ok=True)
        except Exception:
            pass


def main() -> None:
    if "--layer1" in sys.argv:
        layer1_demo()
        return
    turns, task = _synthetic_turns()
    payload = evaluate(turns, task)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
