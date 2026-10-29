#!/usr/bin/env python3
"""
AIMD Concurrency Controller for Hermes scripts.

Additive Increase / Multiplicative Decrease for LLM API concurrency.
Ported from Denuto `src/aimd.py` (Chiu & Jain 1989 TCP congestion control).

Stdlib-only. No external dependencies.

Usage:
    from aimd_controller import get_controller

    ctrl = get_controller(provider="anthropic", node="extractor")
    with ctrl.control():
        result = call_llm(prompt)   # slot held; auto-released on exit

Design notes:
  - Per (provider, node) independent instances — throttling one does not affect others.
  - Full-jitter backoff uses explicitly-passed random.Random (Karn's algorithm) —
    never module-global, for reproducibility under test.
  - AIMD convergence warning: each instance has INDEPENDENT state. In Hermes parallel
    subagents, there is NO cross-agent fairness convergence. Each subagent may arrive at
    a different limit for the same provider if they see different throttle patterns.
    This is by design: local adaptation is better than nothing, but is not TCP-fair.
"""

from __future__ import annotations

import math
import random
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Generator


class NodePriority(IntEnum):
    """Priority for backpressure. Ordered so HIGH > MEDIUM > LOW.

    Puterman, Markov Decision Processes (1994): under constrained resources,
    prefer higher-reward (higher-priority) states. IntEnum makes ``>`` / ``<``
    well-defined; a string Enum is not ordered.
    """

    LOW = 0
    MEDIUM = 1
    HIGH = 2


# Default concurrency budgets per node type
DEFAULT_BUDGETS: dict[str, int] = {
    "extractor": 8,
    "compiler": 4,
    "profiler": 2,
    "structural": 2,
    "llm_checks": 2,
}

DEFAULT_PRIORITY: dict[str, NodePriority] = {
    "extractor": NodePriority.HIGH,
    "compiler": NodePriority.MEDIUM,
    "profiler": NodePriority.MEDIUM,
    "structural": NodePriority.LOW,
    "llm_checks": NodePriority.LOW,
}

# Sliding window size for throttle/error detection
_WINDOW_SIZE = 20
# Adjustment fires every N operations
_ADJUST_EVERY = 5
# LOW priority blocks if health ratio < this
_HEALTH_THRESHOLD = 0.5


@dataclass
class _Window:
    """Fixed-size sliding window tracking throttle/error events."""
    size: int = _WINDOW_SIZE
    _events: list[str] = field(default_factory=list)

    def record(self, event: str) -> None:
        """event: 'ok' | 'throttle' | 'error'"""
        self._events.append(event)
        if len(self._events) > self.size:
            self._events.pop(0)

    def count(self, event: str) -> int:
        return self._events.count(event)

    def full(self) -> bool:
        return len(self._events) >= self.size

    def health_ratio(self) -> float:
        if not self._events:
            return 1.0
        ok = self._events.count("ok")
        return ok / len(self._events)

    def __len__(self) -> int:
        return len(self._events)


class AIMDController:
    """
    Per-(provider, node) AIMD concurrency controller.

    Thread-safe. Uses a semaphore internally.
    """

    def __init__(
        self,
        provider: str,
        node: str,
        initial: int | None = None,
        priority: NodePriority | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.provider = provider
        self.node = node
        self.priority = priority or DEFAULT_PRIORITY.get(node, NodePriority.MEDIUM)
        self._initial = initial or DEFAULT_BUDGETS.get(node, 4)
        self._max_limit = self._initial * 3
        self._limit = self._initial
        self._rng = rng or random.Random()  # never module-global
        # Use Condition + _in_flight so _limit changes take effect immediately.
        # A plain Semaphore cannot shrink without draining slots; Condition can.
        self._cond = threading.Condition(threading.Lock())
        self._lock = self._cond  # _adjust() acquires _lock; works with Condition
        self._in_flight: int = 0
        self._window = _Window()
        self._op_count = 0
        # Strogatz §2.2: successive limits for discrete fixed-point detection.
        self._limit_history: deque[int] = deque(maxlen=5)
        # Astrom & Murray §10.1: error-count history for the derivative term.
        self._error_count_history: deque[int] = deque(maxlen=5)
        # TODO(Astrom & Murray §10.1): latency P-controller
        # update_with_latency(duration_ms, slo_ms) — Hermes callers do not yet
        # emit duration_ms per call; do not add until acquire/release can carry
        # it without an API break.

    @property
    def limit(self) -> int:
        return self._limit

    def _adjust(self) -> None:
        """AIMD adjustment based on sliding window. Call under _lock.

        Theory:
          - Chiu & Jain 1989: additive increase / multiplicative decrease.
          - Astrom & Murray, Feedback Systems §10.1: derivative term on beta;
            min-sample guard so the controller does not act on noise.
          - Strogatz, Nonlinear Dynamics and Chaos §2.2: record post-adjust
            limits for discrete fixed-point / oscillation detection.
        """
        # Min-sample guard: do not adjust on fewer than 5 observations.
        if len(self._window) < 5:
            return

        throttles = self._window.count("throttle")
        errors = self._window.count("error")
        self._error_count_history.append(errors)
        old = self._limit

        if throttles >= 2:
            # Multiplicative decrease with adaptive beta (Astrom & Murray §10.1)
            beta = self.adaptive_beta()
            new = max(1, int(self._limit * beta))
        elif errors >= 3:
            # Moderate decrease
            new = max(1, int(self._limit * 0.7))
        elif errors == 0 and throttles == 0:
            # Additive increase only on a clean window (Chiu & Jain fairness).
            # Health-ratio threshold alone allowed increase with errors > 0.
            new = min(self._max_limit, self._limit + 1)
        else:
            new = old

        if new != old:
            pass  # limit change handled below via _cond.notify_all()
        delta = new - old
        # Remove leftover semaphore release calls from the old increase path
        if delta > 0:
            pass  # _cond.notify_all() below wakes waiters; no separate semaphore
        # MD only writes _limit; slot release is via _cond.notify_all() so waiting
        # acquire()s re-check _in_flight < _limit themselves.
        self._limit = new
        self._cond.notify_all()

        # Strogatz §2.2: always record the post-adjust limit (even if unchanged).
        self._limit_history.append(self._limit)

    def is_near_fixed_point(self) -> bool:
        """True if the last 3 limits are within 5% relative tolerance of each other.

        Strogatz, Nonlinear Dynamics and Chaos §2.2: a fixed point x* of
        x_{n+1} = f(x_n) satisfies f(x*) = x*. Near-equality of successive
        AIMD limits is the discrete analogue of approaching x*; persistent
        oscillation around x* is detected as *not* near a fixed point.
        The controller is already per-node, so the node is ``self``.
        """
        if len(self._limit_history) < 3:
            return False
        last3 = list(self._limit_history)[-3:]
        for i, a in enumerate(last3):
            for b in last3[i + 1 :]:
                if abs(a - b) / max(abs(a), 1) > 0.05:
                    return False
        return True

    def adaptive_beta(self) -> float:
        """Derivative-shaped multiplicative decrease factor in [0.25, 0.75].

        Astrom & Murray, Feedback Systems §10.1: the D term uses d_err to
        strengthen the cut when error is rising (lower beta) and weaken it
        when error is falling (higher beta). d_err is the first difference
        of window error counts. The controller is already per-node.
        """
        hist = self._error_count_history
        if len(hist) < 2:
            return 0.5
        d_err = hist[-1] - hist[-2]
        if d_err > 0:
            return max(0.25, 0.5 - 0.05 * d_err)
        if d_err < 0:
            return min(0.75, 0.5 - 0.05 * d_err)
        return 0.5

    def record_outcome(self, outcome: str) -> None:
        """outcome: 'ok' | 'throttle' | 'error'"""
        with self._lock:
            self._window.record(outcome)
            self._op_count += 1
            if self._op_count % _ADJUST_EVERY == 0:
                self._adjust()

    def health_ratio(self) -> float:
        with self._lock:
            return self._window.health_ratio()

    def _backpressure_wait(self, timeout: float = 30.0) -> bool:
        """LOW priority nodes wait when provider is unhealthy. Returns True if healthy."""
        if self.priority != NodePriority.LOW:
            return True
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.health_ratio() >= _HEALTH_THRESHOLD:
                return True
            # Full-jitter sleep (Karn's algorithm): uniform in [0, cap]
            cap = min(2.0, deadline - time.monotonic())
            if cap <= 0:
                break
            time.sleep(self._rng.uniform(0, cap))
        return self.health_ratio() >= _HEALTH_THRESHOLD

    @contextmanager
    def control(self, timeout: float = 60.0) -> Generator[None, None, None]:
        """
        Acquire a concurrency slot. Yields. Records outcome on exit.
        Detects 429/throttle exceptions automatically.
        """
        if not self._backpressure_wait(timeout):
            # Even if health is bad, try anyway for HIGH priority; LOW gives up
            if self.priority == NodePriority.LOW:
                raise TimeoutError(
                    f"AIMD: provider={self.provider} node={self.node} "
                    f"health too low ({self.health_ratio():.2f}) for LOW priority"
                )

        # Acquire a slot: wait until in_flight < _limit (respects MD immediately)
        acquired = False
        deadline = time.monotonic() + timeout
        with self._cond:
            while True:
                if self._in_flight < self._limit:
                    self._in_flight += 1
                    acquired = True
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._cond.wait(timeout=remaining)
        if not acquired:
            raise TimeoutError(
                f"AIMD: timeout acquiring slot for {self.provider}/{self.node}"
            )
        outcome = "ok"
        try:
            yield
        except Exception as exc:
            exc_str = str(exc).lower()
            if any(t in exc_str for t in ("429", "rate limit", "throttl", "too many")):
                outcome = "throttle"
            else:
                outcome = "error"
            raise
        finally:
            with self._cond:
                self._in_flight -= 1
                self._cond.notify_all()
            self.record_outcome(outcome)

    def jitter_backoff(self, attempt: int, base: float = 1.0, cap: float = 32.0) -> float:
        """Full-jitter backoff (Karn's). Returns sleep duration in seconds."""
        slot = min(cap, base * (2 ** attempt))
        return self._rng.uniform(0, slot)


# --- Safe UCB (Lattimore) with failure envelope P(fail) <= 0.1 ---
# Recency window is required: all-time averages are stale and unsafe.

FAIL_BOUND = 0.1
UCB_MIN_SAMPLES = 10
UCB_RECENCY_SECONDS = 24 * 3600


def laplace_p_fail(failures: int, n: int) -> float:
    """Laplace-smoothed P(failure). Always in (0,1)."""
    n = max(int(n), 0)
    failures = max(int(failures), 0)
    return (failures + 1.0) / (n + 2.0)


def ucb_index(mean: float, n: int, t: int, c: float = 1.41421356237) -> float:
    if n <= 0:
        return float("inf")
    t = max(int(t), 1)
    return float(mean) + c * (math.log(t) / n) ** 0.5


def arm_is_safe(failures: int, n: int, last_ts: float | None, now: float,
                recency: float = UCB_RECENCY_SECONDS) -> bool:
    """Safety envelope. Stale (no observation in recency window) is unsafe to run
    except n==0 (no evidence yet — exploration allowed).

    ADV-026 fix: cold-start arms (n < UCB_MIN_SAMPLES) skip the stale-data recency
    gate — they need exploration, not conservation. 100%-fail cold arms are still
    blocked. The recency gate only applies once n >= UCB_MIN_SAMPLES.
    """
    if n <= 0:
        return True  # no evidence; exploration allowed
    if n < UCB_MIN_SAMPLES:
        # Cold-start block: light failure gate only — no timestamp required, no Laplace.
        # Laplace smoothing at small n is too conservative (laplace(0,1)=1/3 > 0.1 blocks
        # clean arms). Use simple majority: block only if failures dominate.
        if failures >= n:
            return False  # 100% failure rate — block
        if n >= 2 and failures / n > 0.5:
            return False  # majority-fail — block
        return True  # clean or ambiguous cold arm: allow exploration
    # Warm path (n >= UCB_MIN_SAMPLES): apply stale-data recency check.
    try:
        last = float(last_ts) if last_ts is not None else None
    except (TypeError, ValueError):
        last = None
    if last is None:
        return False
    if last > now + 1.0:
        return False  # future timestamp — do not certify
    if (now - last) > recency:
        return False  # stale — do not certify from old successes
    return laplace_p_fail(failures, n) <= FAIL_BOUND


def select_ucb_arm(arms: dict, t: int, now: float) -> str | None:
    """Pick argmax UCB among safe arms. Returns None if none are safe."""
    best_id, best = None, float("-inf")
    for arm_id, stats in arms.items():
        n = int(stats.get("n", 0) or 0)
        failures = int(stats.get("failures", 0) or 0)
        last_ts = stats.get("last_ts")
        if not arm_is_safe(failures, n, last_ts, now):
            continue
        successes = max(0, n - failures)
        mean = (successes / n) if n else 1.0
        idx = ucb_index(mean, n if n else 1, t)
        if idx > best:
            best_id, best = str(arm_id), idx
    return best_id


# --- Registry ---

_registry: dict[tuple[str, str], AIMDController] = {}
_registry_lock = threading.Lock()


def get_controller(
    provider: str,
    node: str,
    initial: int | None = None,
    priority: NodePriority | None = None,
    rng: random.Random | None = None,
) -> AIMDController:
    """Get or create a per-(provider, node) controller. Thread-safe."""
    key = (provider, node)
    with _registry_lock:
        if key not in _registry:
            _registry[key] = AIMDController(
                provider=provider,
                node=node,
                initial=initial,
                priority=priority,
                rng=rng,
            )
        return _registry[key]


def reset_registry() -> None:
    """Clear all controllers. Use in tests only."""
    with _registry_lock:
        _registry.clear()


def _self_test() -> None:
    """In-process checks for AIMD adaptive-beta / fixed-point / IntEnum."""
    reset_registry()

    # Puterman 1994: IntEnum ordering
    assert NodePriority.HIGH > NodePriority.MEDIUM > NodePriority.LOW
    assert NodePriority.LOW == 0 and NodePriority.MEDIUM == 1 and NodePriority.HIGH == 2

    rng = random.Random(42)
    ctrl = get_controller("anthropic", "extractor", rng=rng)
    initial = ctrl.limit
    assert initial == 8

    # Min-sample guard: 4 events must not change the limit (Astrom & Murray §10.1)
    for _ in range(4):
        ctrl.record_outcome("throttle")
    assert ctrl.limit == initial, "adjust must not fire before 5 samples"
    assert len(ctrl._limit_history) == 0

    # 5th throttle: first MD with history < 2 ⇒ beta = 0.5
    ctrl.record_outcome("throttle")
    assert ctrl.limit == max(1, int(initial * 0.5))
    assert list(ctrl._limit_history)[-1] == ctrl.limit

    # adaptive_beta: rising error counts lower beta (Astrom & Murray §10.1)
    ctrl._error_count_history.clear()
    ctrl._error_count_history.append(1)
    ctrl._error_count_history.append(5)  # d_err = 4 > 0
    assert ctrl.adaptive_beta() == max(0.25, 0.5 - 0.05 * 4)
    ctrl._error_count_history.clear()
    ctrl._error_count_history.append(5)
    ctrl._error_count_history.append(1)  # d_err = -4 < 0
    assert ctrl.adaptive_beta() == min(0.75, 0.5 - 0.05 * (-4))
    ctrl._error_count_history.clear()
    ctrl._error_count_history.append(3)
    ctrl._error_count_history.append(3)
    assert ctrl.adaptive_beta() == 0.5

    # Tight increase: errors > 0 must not additive-increase even if mostly ok.
    # Sprinkle errors so intermediate windows never look clean (old health_ratio
    # rule would still increase once the window is full at 18/20 ok).
    reset_registry()
    ctrl = get_controller("anthropic", "extractor", rng=random.Random(1), initial=4)
    start = ctrl.limit
    for i in range(20):
        ctrl.record_outcome("error" if i in (4, 9) else "ok")
    # 18 ok + 2 error, health_ratio = 0.9, errors != 0 ⇒ no increase
    assert ctrl.limit == start, "must not additive-increase while errors > 0"

    # Clean window does increase (adjust fires at ops 5 and 10)
    reset_registry()
    ctrl = get_controller("anthropic", "extractor", rng=random.Random(2), initial=4)
    start = ctrl.limit
    for _ in range(10):
        ctrl.record_outcome("ok")
    assert ctrl.limit == start + 2

    # Strogatz §2.2: last 3 limits within 5% ⇒ near fixed point
    ctrl._limit_history.clear()
    for v in (8, 8, 8):
        ctrl._limit_history.append(v)
    assert ctrl.is_near_fixed_point() is True
    ctrl._limit_history.clear()
    for v in (8, 4, 8):
        ctrl._limit_history.append(v)
    assert ctrl.is_near_fixed_point() is False
    ctrl._limit_history.clear()
    assert ctrl.is_near_fixed_point() is False

    now = 1_000_000.0
    safe = {"ok": {"n": 20, "failures": 1, "last_ts": now}}
    unsafe = {"bad": {"n": 20, "failures": 8, "last_ts": now}}
    stale = {"old": {"n": 20, "failures": 0, "last_ts": now - 48 * 3600}}
    assert select_ucb_arm(safe, t=20, now=now) == "ok"
    assert select_ucb_arm(unsafe, t=20, now=now) is None
    assert select_ucb_arm(stale, t=20, now=now) is None
    nostamp = {"ghost": {"n": 20, "failures": 0, "last_ts": None}}
    assert select_ucb_arm(nostamp, t=20, now=now) is None
    picked = select_ucb_arm({**safe, **unsafe, **stale}, t=20, now=now)
    assert picked == "ok"
    assert laplace_p_fail(1, 20) <= FAIL_BOUND
    reset_registry()
    print("AIMD controller --self-test PASSED")


if __name__ == "__main__":
    import sys

    if "--self-test" in sys.argv:
        _self_test()
    else:
        rng = random.Random(42)
        ctrl = get_controller("anthropic", "extractor", rng=rng)
        print(f"Initial limit: {ctrl.limit}")
        for _ in range(10):
            ctrl.record_outcome("throttle")
        print(f"After throttles: {ctrl.limit}")
        for _ in range(40):
            ctrl.record_outcome("ok")
        print(f"After recovery: {ctrl.limit}")
        _self_test()
        print("AIMD controller smoke test PASSED")
        print("UCB safety envelope self-test PASSED")
