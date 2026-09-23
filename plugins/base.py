"""The contract and runtime context shared by Daily Brief plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, ClassVar, Mapping

from .http import fetch_json as default_fetch_json
from .http import fetch_text as default_fetch_text


JsonFetcher = Callable[[str, int, int, Mapping[str, str] | None], dict | list]
TextFetcher = Callable[[str, int, int, Mapping[str, str] | None], str]
PricingSchedule = Callable[[str, datetime | None], bool]


@dataclass(frozen=True)
class FetchResult:
    """A plugin fetch result.

    ``ok`` means that at least one renderable payload exists.  A successful
    partial result may still contain ``missing`` labels for individual items.
    """

    ok: bool
    data: Any = None
    error: str | None = None
    missing: tuple[str, ...] = ()


@dataclass(frozen=True)
class PluginContext:
    """Immutable inputs and stateless services available to a plugin."""

    settings: Mapping[str, Any]
    timezone: str
    lat: float
    lon: float
    city: str
    max_retries: int = 2
    retry_delay: int = 3
    now: datetime | None = None
    force_pricing: bool = False
    fetch_json: JsonFetcher = default_fetch_json
    fetch_text: TextFetcher = default_fetch_text
    pricing_due: PricingSchedule | None = None
    schedules: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    secrets: Mapping[str, str] = field(default_factory=dict)

    def setting(self, name: str, default: Any = None) -> Any:
        return self.settings.get(name, default)

    def secret(self, name: str, default: str = "") -> str:
        return self.secrets.get(name, default)

    def schedule_for(self, plugin_name: str) -> tuple[str, ...] | None:
        return self.schedules.get(plugin_name)


@dataclass(frozen=True)
class PluginBlock:
    """Rendered output plus the generic layout group used by the composer."""

    name: str
    display_name: str
    text: str
    group: str | None = None


class BasePlugin(ABC):
    """Base contract implemented by every discovered plugin."""

    name: ClassVar[str]
    display_name: ClassVar[str]
    section_group: ClassVar[str | None] = None

    def should_run(self, context: PluginContext) -> bool:
        """Return whether this plugin is applicable for this run."""
        return True

    @abstractmethod
    def fetch(self, context: PluginContext) -> FetchResult:
        """Fetch data without allowing provider errors to escape."""

    @abstractmethod
    def render(self, data: Any) -> str:
        """Render a successful payload as a plain-text section."""
