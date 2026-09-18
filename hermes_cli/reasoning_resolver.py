"""Deterministic multi-plugin reasoning-effort conflict resolution.

Plugins recommend an effort with a confidence and priority. Highest priority
wins; ties break toward the higher effort (conservative). Recommendations with
confidence below 0.5 are ignored. The resolved effort is never below a
configured floor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

EFFORT_ORDER: tuple[str, ...] = ("minimal", "low", "medium", "high", "xhigh", "max", "ultra")
EFFORT_INDEX: dict[str, int] = {name: i for i, name in enumerate(EFFORT_ORDER)}
MODE_TO_EFFORT: dict[str, str] = {"fast": "low", "default": "medium", "deep": "high"}
CONFIDENCE_FLOOR = 0.5
DEFAULT_EFFORT = "low"


def _norm_effort(value: str, fallback: Optional[str] = None) -> Optional[str]:
    effort = str(value or "").strip().lower()
    if effort in EFFORT_INDEX:
        return effort
    return fallback


def _clamp_confidence(value: float) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError):
        return 0.0
    if conf < 0.0:
        return 0.0
    if conf > 1.0:
        return 1.0
    return conf


@dataclass(frozen=True)
class _Recommendation:
    plugin: str
    effort: str
    confidence: float
    priority: int


class ReasoningConflictResolver:
    """Collects reasoning recommendations from multiple plugins and arbitrates."""

    def __init__(self) -> None:
        self._recs: List[_Recommendation] = []
        self._winner: Optional[_Recommendation] = None

    def add_recommendation(
        self,
        plugin_name: str,
        effort: str,
        confidence: float,
        priority: int = 0,
    ) -> None:
        """Record one plugin recommendation.

        ``confidence`` is 0.0-1.0 (how sure the plugin is).
        ``priority`` is higher = more authoritative (lambda-tuner=10, others=0).
        """
        normalized = _norm_effort(effort)
        if normalized is None:
            return
        try:
            prio = int(priority)
        except (TypeError, ValueError):
            prio = 0
        rec = _Recommendation(
            plugin=str(plugin_name or ""),
            effort=normalized,
            confidence=_clamp_confidence(confidence),
            priority=prio,
        )
        self._recs.append(rec)
        self._winner = None

    def resolve(self, configured_floor: str) -> str:
        """Return the winning effort, never below ``configured_floor``.

        1. Filter out confidence < 0.5
        2. Sort by (priority DESC, confidence DESC, effort_index DESC)
        3. Winner = first result, clamped to configured_floor
        4. Tie at same priority+confidence: take highest effort (conservative)
        """
        floor = _norm_effort(configured_floor, DEFAULT_EFFORT) or DEFAULT_EFFORT
        eligible = [r for r in self._recs if r.confidence >= CONFIDENCE_FLOOR]
        if not eligible:
            self._winner = None
            return floor
        eligible.sort(
            key=lambda r: (r.priority, r.confidence, EFFORT_INDEX[r.effort]),
            reverse=True,
        )
        winner = eligible[0]
        self._winner = winner
        if EFFORT_INDEX[winner.effort] < EFFORT_INDEX[floor]:
            return floor
        return winner.effort

    def clear(self) -> None:
        """Drop all recommendations for the next turn."""
        self._recs.clear()
        self._winner = None

    def recommendation_log(self) -> list[dict[str, Any]]:
        """All recommendations this turn, each marked with whether it won."""
        winner = self._winner
        return [
            {
                "plugin": rec.plugin,
                "effort": rec.effort,
                "confidence": rec.confidence,
                "priority": rec.priority,
                "won": winner is not None and rec is winner,
            }
            for rec in self._recs
        ]
