"""Computer-use provider registry.

Plugins register backends via :meth:`PluginContext.register_computer_use_provider`.
The dispatcher selects one by ``computer_use.backend`` in config.yaml.

Unlike web search / browser, there is no auto-detect walk and no "only one
registered, so use it" shortcut. A computer-use backend owns a machine's
keyboard and mouse. Silently picking a plugin because it is the only one
installed would mean a container-pool plugin (or a leftover test stub) starts
driving the gateway host — or worse, a remote desktop the user did not name.
An unrecognized name is an error, not a fall-through to the host.
"""

from __future__ import annotations

import logging
from typing import Optional

from agent.computer_use_provider import ComputerUseProvider
from agent.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)

HOST_PROVIDER_NAME = "cua"

# Names the host provider has been known by. ``local`` / ``cua-driver`` are the
# legacy values from before this registry existed; all resolve to the host driver.
_HOST_ALIASES = frozenset({HOST_PROVIDER_NAME, "local", "cua-driver"})


class UnknownComputerUseProvider(ValueError):
    """``computer_use.provider`` names something that is not registered."""


_registry: ProviderRegistry[ComputerUseProvider] = ProviderRegistry(
    label="Computer-use", provider_cls=ComputerUseProvider, logger=logger,
)
_registry.export(globals())


def resolve_provider(name: Optional[str]) -> ComputerUseProvider:
    """Return the provider for ``name``, or the host provider when *name* is empty.

    Empty / unset / a host alias → the host provider (must be registered; the
    in-tree ``tools.computer_use.host_provider`` module does that at import).
    Any other string must match a registered ``provider.name`` exactly
    (strip only). Raises :class:`UnknownComputerUseProvider` rather than
    falling back — see the module docstring.
    """
    key = (name or "").strip()
    snapshot = _registry.merged()
    if not key or key in _HOST_ALIASES:
        provider = snapshot.get(HOST_PROVIDER_NAME)
        if provider is not None:
            return provider
        raise UnknownComputerUseProvider(
            f"computer_use.provider {key!r} resolved to the host backend {HOST_PROVIDER_NAME!r}, "
            "but that provider is not registered. This is a bug: the in-tree host provider "
            "should have registered itself at import."
        )
    provider = snapshot.get(key)
    if provider is not None:
        return provider
    available = ", ".join(sorted(snapshot)) or "(none)"
    raise UnknownComputerUseProvider(
        f"computer_use.provider is {key!r}, but no plugin registered that name "
        f"(registered: {available}). Set computer_use.provider to a registered name, "
        "or omit it to use the host desktop."
    )
