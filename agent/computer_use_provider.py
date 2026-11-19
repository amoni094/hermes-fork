"""Computer-use provider ABC: pluggable backends that own a machine's keyboard and mouse.

Providers register via :meth:`PluginContext.register_computer_use_provider`; the
active one (selected by ``computer_use.provider`` / ``computer_use.backend``) supplies
the backend the ``computer_use`` tool drives. Unlike web search, selection is always
explicit: registering never activates.

This is how a runtime that owns its own display (container pool, leased sandbox,
desktop-client bridge) supplies a backend without core knowing it exists.
"""

from __future__ import annotations

import abc
from typing import Any

from agent.provider_base import ProviderBase


class ComputerUseProvider(ProviderBase):
    """Abstract base class for a computer-use backend factory.

    Subclasses implement :attr:`name` (the ``computer_use.provider`` /
    ``computer_use.backend`` value), :meth:`is_available`, and
    :meth:`create_backend`. :meth:`emergency_cleanup` runs at process exit for
    providers that hold leases (containers, sandboxes) that outlive a backend.
    """

    @abc.abstractmethod
    def is_available(self) -> bool:
        """True when this provider can service calls. Cheap check only (env var,
        binary present, dep importable) — must NOT make network calls; runs at
        tool-registration time and on every ``hermes tools`` paint.
        """

    @abc.abstractmethod
    def create_backend(self, session_id: str = "", permission_mode: str = "standard") -> Any:
        """A fresh, unstarted backend for one Hermes session (the tool calls
        ``start()``/``stop()``). ``permission_mode`` is ``standard`` | ``bounded`` |
        ``unrestricted`` (approval bypass active). Exclusive plugins historically
        take only ``permission_mode``; PluginContext backends also receive
        ``session_id``.
        """

    def emergency_cleanup(self) -> None:
        """Best-effort teardown from atexit / signal handlers. Must not raise.

        Release anything this provider holds that outlives a backend object
        (container leases, sandbox handles). Default is a no-op.
        """
