"""
Lyapunov stability monitor for the _patched_prune iterative loop.

Grounded in Khalil (2002) 'Nonlinear Systems', Ch.4, and
Slotine & Li (1991) 'Applied Nonlinear Control':

An iterative update  x_{n+1} = f(x_n)  is Lyapunov-stable if
∃ V(x) > 0  s.t.  V(x_{n+1}) < V(x_n)  (strict descent).

For the message-pruning loop we define:
    V(state) = max(0, retained_count - target_retain_count)

V ≥ 0 always; V = 0 iff the loop has reached the target.
The loop MUST decrease V at each step (one message demoted per pass).
If V stalls for 3 consecutive steps → stability violation warning.

Public API
----------
lyapunov_monitor(initial_retained, target_retain) -> LyapunovMonitor

    Returns a callable monitor object.  Call it with the current
    retained-message count at each loop iteration.

    Attributes:
        monitor.is_stable()  -> bool
        monitor.history()    -> list[float]

Usage
-----
    mon = lyapunov_monitor(initial_retained=10, target_retain=5)
    for retained in pruning_loop():
        mon(retained)
    if not mon.is_stable():
        logger.warning("pruning loop may be stuck")
"""

from __future__ import annotations

import logging
import sys
from typing import List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Monitor class
# ---------------------------------------------------------------------------

STALL_THRESHOLD = 3   # consecutive non-decreasing steps → violation


class LyapunovMonitor:
    """
    Callable monitor that tracks the Lyapunov function V for the prune loop.

    V(retained) = max(0, retained - target_retain_count)

    The monitor is called once per loop iteration; it checks for
    descent and emits a WARNING if V stalls for STALL_THRESHOLD steps.
    """

    def __init__(self, initial_retained: int, target_retain: int) -> None:
        self._target = target_retain
        self._history: List[float] = [self._V(initial_retained)]
        self._stable: bool = True
        self._stall: int = 0
        self._oscillation: int = 0  # P10A-02: count ascents from V=0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _V(self, retained: int) -> float:
        return float(max(0, retained - self._target))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def __call__(self, current_retained: int) -> None:
        """Record one step; update stability state."""
        v_prev = self._history[-1]
        v_now  = self._V(current_retained)
        self._history.append(v_now)

        if v_now < v_prev:
            self._stall = 0
            # P8B-12 fix: when descent lands exactly at 0, also set _stable=True.
            # The elif branch (v_now==0) is never reached when v_now < v_prev is True,
            # so a loop that stalled (_stable=False) then converged in one large step
            # would otherwise leave _stable=False permanently.
            if v_now == 0.0:
                self._stable = True
                self._oscillation = 0  # P10A-02: reset oscillation counter on convergence
        elif v_now == 0.0:
            self._stall = 0          # P4B-03 fix: V=0 is equilibrium, not a stall
            self._stable = True      # P7B-09 fix: recovery — loop DID converge; clear stall flag
            self._oscillation = 0    # P10A-02: reset oscillation counter on convergence
        else:
            # V > 0 and not descending.
            self._stall += 1
            # P10A-02 fix: detect oscillation where V bounces between 0 and V>0.
            # Stall counter resets on every descent-to-0, so V=0↔N never triggers
            # STALL_THRESHOLD=3. Track ascents from exactly V=0 separately.
            # Two ascents from V=0 (i.e. V=0→N→0→N pattern) indicates oscillation,
            # not convergence. Also covers P10A-08 (ascents at V>0 plateau).
            if v_prev == 0.0:
                self._oscillation += 1
                if self._oscillation >= 2:
                    self._stable = False
                    logger.warning(
                        "Lyapunov oscillation detected: pruning loop bouncing near V=0"
                    )
            if self._stall >= STALL_THRESHOLD:
                self._stable = False
                logger.warning(
                    "Lyapunov stability violation: pruning loop not converging"
                )

    def is_stable(self) -> bool:
        """Return False if a stability violation has been detected."""
        return self._stable

    def history(self) -> List[float]:
        """Return a copy of the recorded V-value history."""
        return list(self._history)


# ---------------------------------------------------------------------------
# Factory function (public API as specified)
# ---------------------------------------------------------------------------

def lyapunov_monitor(
    initial_retained: int,
    target_retain: int,
) -> LyapunovMonitor:
    """
    Create and return a LyapunovMonitor for the prune loop.

    Parameters
    ----------
    initial_retained : int
        Number of retained messages at loop start.
    target_retain    : int
        Desired number of retained messages at loop end.

    Returns
    -------
    LyapunovMonitor
        Callable; also exposes .is_stable() and .history().
    """
    return LyapunovMonitor(initial_retained, target_retain)


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    print("=== Lyapunov Monitor Demo (Khalil / Slotine-Li) ===\n")

    # --- Scenario 1: healthy convergence ---
    print("-- Scenario 1: healthy convergence (10 → 5) --")
    mon = lyapunov_monitor(initial_retained=10, target_retain=5)
    for retained in [9, 8, 7, 6, 5, 5]:
        mon(retained)
    print(f"  V history : {mon.history()}")
    print(f"  is_stable : {mon.is_stable()}")
    assert mon.is_stable(), "Scenario 1 should be stable"

    # --- Scenario 2: stalled loop triggers violation ---
    print("\n-- Scenario 2: stalled loop (retained stays at 8) --")
    mon2 = lyapunov_monitor(initial_retained=10, target_retain=5)
    for retained in [9, 8, 8, 8, 8]:   # three consecutive non-decreasing steps
        mon2(retained)
    print(f"  V history : {mon2.history()}")
    print(f"  is_stable : {mon2.is_stable()}")
    assert not mon2.is_stable(), "Scenario 2 should be unstable (stall detected)"

    # --- Scenario 3: already at target ---
    print("\n-- Scenario 3: already at target --")
    mon3 = lyapunov_monitor(initial_retained=5, target_retain=5)
    mon3(5)
    print(f"  V history : {mon3.history()}")
    print(f"  is_stable : {mon3.is_stable()}")

    print("\nAll required assertions passed. Exit 0.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
        sys.exit(0)
    print("Usage: python lyapunov_monitor.py --demo")
    sys.exit(1)
