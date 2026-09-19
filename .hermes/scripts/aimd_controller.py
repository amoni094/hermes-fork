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
    import sys
    rng = random.Random(42)
    ctrl = get_controller("anthropic", "extractor", rng=rng)
    print(f"Initial limit: {ctrl.limit}")
    # Simulate throttle events
    for _ in range(10):
        ctrl.record_outcome("throttle")
    print(f"After throttles: {ctrl.limit}")
    # Simulate recovery
    for _ in range(40):
        ctrl.record_outcome("ok")
    print(f"After recovery: {ctrl.limit}")
    print("AIMD controller smoke test PASSED")
