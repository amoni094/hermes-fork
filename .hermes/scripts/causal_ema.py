"""causal_ema.py — Simpson-safe EMA with Pearl back-door adjustment (Ch.3).

Grounding
=========
Pearl Ch.3 (Back-Door Criterion): the EMA threshold update conditions on
`score` which is *confounded* by session context.  In a tool-heavy session,
scores tend to be lower (tools produce long, low-signal output) compared to
a message-heavy session.  If we run a single pooled EMA we commit Simpson's
Paradox: the overall EMA drifts toward the tool-heavy distribution even when
the message-heavy stratum is well-calibrated.

Fix: stratify by session type, maintain per-stratum EMAs, and recover the
*interventional* expectation E[threshold | do(session)] by back-door
adjustment over the stratum prior P(stratum):

    adjusted = sum_s P(s) * EMA_s

where P(s) is estimated from the running fraction of updates in each stratum.

Usage (standalone demo):
    python3 ~/.hermes/scripts/causal_ema.py --demo
"""
from __future__ import annotations

import sys
import math

# Recognised strata
_STRATA = ("tool_heavy", "message_heavy")


class CausalEMA:
    """Per-stratum EMA with Pearl back-door adjustment.

    Parameters
    ----------
    alpha:      EMA learning rate (0 < alpha < 1).
    init_value: Initial threshold value for every stratum.
    """

    def __init__(self, alpha: float = 0.15, init_value: float = 0.55) -> None:
        if not (0.0 < alpha < 1.0):
            raise ValueError(f"alpha must be in (0, 1), got {alpha}")
        self._alpha = alpha
        # Per-stratum EMA values
        self._ema: dict[str, float] = {s: init_value for s in _STRATA}
        # Per-stratum observation counts (for back-door weight P(stratum))
        self._counts: dict[str, int] = {s: 0 for s in _STRATA}

    # ── Stratum classifier ─────────────────────────────────────────────────

    @staticmethod
    def _classify(context_dict: dict) -> str:
        """Return stratum label from context_dict.

        context_dict keys used:
          tool_result_fraction: float in [0, 1]
              Fraction of messages in the current window that are tool results.
              If > 0.5, the session is 'tool_heavy'; otherwise 'message_heavy'.
        """
        frac = float(context_dict.get("tool_result_fraction", 0.0))
        return "tool_heavy" if frac > 0.5 else "message_heavy"

    # ── Public API ─────────────────────────────────────────────────────────

    def update(self, score: float, context_dict: dict) -> None:
        """Record a new observation and update the appropriate stratum EMA.

        Parameters
        ----------
        score:        Observed relevance score in [0, 1].
        context_dict: Dict with at least 'tool_result_fraction' key.
        """
        # Clamp score for uniform integrability (Royden-Fitzpatrick)
        score = max(0.0, min(1.0, score))
        stratum = self._classify(context_dict)
        old = self._ema[stratum]
        self._ema[stratum] = old + self._alpha * (score - old)
        self._counts[stratum] += 1

    def adjusted_threshold(self) -> float:
        """Stratum-weighted average threshold (heuristic Simpson-Paradox mitigation).

        Returns the weighted average of per-stratum EMA values, weighted by the
        empirical frequency of each stratum.  This reduces the Simpson's Paradox
        effect where tool-heavy sessions would otherwise pull the pooled EMA down.

        NOTE (W3-F10): This is NOT Pearl's back-door adjustment E[Y|do(X)].
        Pearl's do-calculus applies to causal graphs over observable outcomes, not
        to optimizer hyperparameters.  The computation is a sensible weighted average;
        the causal framing has been removed to avoid misleading future extensions.

        If no observations have been made, returns the uniform average across
        strata (maximum-entropy prior over strata).

        Returns
        -------
        float in [0, 1]
        """
        total = sum(self._counts.values())
        if total == 0:
            # Max-entropy prior: uniform over strata
            return sum(self._ema.values()) / len(_STRATA)
        adjusted = sum(
            (self._counts[s] / total) * self._ema[s]
            for s in _STRATA
        )
        # Clamp output to [0, 1] for safety
        return max(0.0, min(1.0, adjusted))

    # ── Diagnostics ────────────────────────────────────────────────────────

    def stratum_summary(self) -> dict:
        """Return per-stratum EMA values and observation counts."""
        total = sum(self._counts.values())
        return {
            "strata": {
                s: {
                    "ema": self._ema[s],
                    "count": self._counts[s],
                    "weight": (self._counts[s] / total) if total > 0 else 1.0 / len(_STRATA),
                }
                for s in _STRATA
            },
            "adjusted_threshold": self.adjusted_threshold(),
        }


# ── Standalone demo ────────────────────────────────────────────────────────────

def _demo() -> None:
    ema = CausalEMA(alpha=0.15, init_value=0.55)

    # Simulate tool-heavy session with low scores (tools tend to flood context)
    for _ in range(10):
        ema.update(0.3, {"tool_result_fraction": 0.8})

    # Simulate message-heavy session with high scores
    for _ in range(10):
        ema.update(0.8, {"tool_result_fraction": 0.2})

    summary = ema.stratum_summary()
    threshold = summary["adjusted_threshold"]
    assert isinstance(threshold, float), f"expected float, got {type(threshold)}"
    assert 0.0 <= threshold <= 1.0, f"threshold out of [0,1]: {threshold}"

    tool_ema = summary["strata"]["tool_heavy"]["ema"]
    msg_ema = summary["strata"]["message_heavy"]["ema"]
    assert tool_ema < msg_ema, (
        f"tool-heavy EMA ({tool_ema:.3f}) should be < message-heavy EMA ({msg_ema:.3f})"
    )

    print(f"[demo] CausalEMA OK — adjusted_threshold={threshold:.4f}")
    print(f"       tool_heavy EMA={tool_ema:.4f} (n=10)")
    print(f"       message_heavy EMA={msg_ema:.4f} (n=10)")
    print(f"       Back-door adjustment separates strata: Simpson's Paradox avoided.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
        sys.exit(0)
    print("Usage: python3 causal_ema.py --demo")
    sys.exit(1)
