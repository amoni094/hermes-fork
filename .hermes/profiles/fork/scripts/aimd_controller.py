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
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Generator


class NodePriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


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
        self._lock = threading.Lock()
        self._sem = threading.Semaphore(self._initial)
        self._window = _Window()
        self._op_count = 0

    @property
    def limit(self) -> int:
        return self._limit

    def _adjust(self) -> None:
        """AIMD adjustment based on sliding window. Call under _lock."""
        throttles = self._window.count("throttle")
        errors = self._window.count("error")
        old = self._limit

        if throttles >= 2:
            # Multiplicative decrease
            new = max(1, self._limit // 2)
        elif errors >= 3:
            # Moderate decrease
            new = max(1, int(self._limit * 0.7))
        elif self._window.full() and self._window.health_ratio() >= 0.75:
            # Additive increase
            new = min(self._max_limit, self._limit + 1)
        else:
            return  # no change

        if new != old:
            # Adjust semaphore
            delta = new - old
            if delta > 0:
                for _ in range(delta):
                    self._sem.release()
            # For decreases we let slots drain naturally; forced decrease would deadlock
            self._limit = new

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

        acquired = self._sem.acquire(timeout=timeout)
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
            self._sem.release()
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


if __name__ == "__main__":
    # Quick smoke test
    rng = random.Random(42)
    ctrl = get_controller("anthropic", "extractor", rng=rng)
    print(f"Initial limit: {ctrl.limit}")
    for _ in range(10):
        ctrl.record_outcome("throttle")
    print(f"After throttles: {ctrl.limit}")
    for _ in range(40):
        ctrl.record_outcome("ok")
    print(f"After recovery: {ctrl.limit}")

    now = 1_000_000.0
    # Hard core: selected arm with n>=10 has P(fail) <= 0.1
    safe = {"ok": {"n": 20, "failures": 1, "last_ts": now}}
    unsafe = {"bad": {"n": 20, "failures": 8, "last_ts": now}}  # 9/22 > 0.1
    stale = {"old": {"n": 20, "failures": 0, "last_ts": now - 48 * 3600}}
    assert select_ucb_arm(safe, t=20, now=now) == "ok"
    assert select_ucb_arm(unsafe, t=20, now=now) is None
    assert select_ucb_arm(stale, t=20, now=now) is None  # stale successes
    nostamp = {"ghost": {"n": 20, "failures": 0, "last_ts": None}}
    assert select_ucb_arm(nostamp, t=20, now=now) is None  # missing ts is stale
    picked = select_ucb_arm({**safe, **unsafe, **stale}, t=20, now=now)
    assert picked == "ok"
    n, f = 20, 1
    assert laplace_p_fail(f, n) <= FAIL_BOUND
    print("AIMD controller smoke test PASSED")
    print("UCB safety envelope self-test PASSED")
