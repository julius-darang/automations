"""Automatic plugin discovery for the Daily Brief."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import TypeAlias

from .base import BasePlugin

PluginType: TypeAlias = type[BasePlugin]


class PluginRegistryError(ValueError):
    """Raised when plugin discovery or configuration is invalid."""


def discover_plugins() -> dict[str, PluginType]:
    """Discover concrete ``BasePlugin`` subclasses in this package."""
    discovered: dict[str, PluginType] = {}
    for module_info in pkgutil.iter_modules(__path__):
        if module_info.ispkg or module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if (
                candidate is BasePlugin
                or not issubclass(candidate, BasePlugin)
                or candidate.__module__ != module.__name__
            ):
                continue
            name = getattr(candidate, "name", "")
            display_name = getattr(candidate, "display_name", "")
            if (
                not isinstance(name, str)
                or not isinstance(display_name, str)
                or not name
                or not display_name
            ):
                raise PluginRegistryError(
                    f"Plugin class {candidate.__name__} must declare name and display_name"
                )
            if name in discovered:
                other = discovered[name].__name__
                raise PluginRegistryError(f"Duplicate plugin name {name!r}: {other} and {candidate.__name__}")
            discovered[name] = candidate
    return dict(sorted(discovered.items()))


def instantiate_plugins() -> dict[str, BasePlugin]:
    return {name: plugin_type() for name, plugin_type in discover_plugins().items()}


__all__ = ["BasePlugin", "PluginRegistryError", "discover_plugins", "instantiate_plugins"]
