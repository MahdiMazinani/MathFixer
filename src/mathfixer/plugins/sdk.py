from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

PLUGIN_API_VERSION = "2.0"


@dataclass(frozen=True, slots=True)
class PluginDiagnostic:
    code: str
    message: str
    suggestion: str = ""
    severity: str = "warning"
    file: str = ""
    line: int | None = None
    plugin: str = ""


@dataclass(frozen=True, slots=True)
class PluginContext:
    project_root: Path
    main_file: Path
    sources: Mapping[str, str]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sources", MappingProxyType(dict(self.sources)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@runtime_checkable
class MathFixerPlugin(Protocol):
    name: str
    version: str
    api_version: str

    def analyze(self, context: PluginContext) -> list[PluginDiagnostic]: ...


class PluginCompatibilityError(RuntimeError):
    """Raised when a plugin cannot safely run against this SDK."""


def validate_plugin(plugin: object) -> MathFixerPlugin:
    if not isinstance(plugin, MathFixerPlugin):
        raise PluginCompatibilityError(
            "Plugin must expose name, version, api_version, and analyze(context)."
        )
    plugin_major = str(plugin.api_version).split(".", 1)[0]
    sdk_major = PLUGIN_API_VERSION.split(".", 1)[0]
    if plugin_major != sdk_major:
        raise PluginCompatibilityError(
            f"Plugin {plugin.name!r} targets API {plugin.api_version}; MathFixer requires {PLUGIN_API_VERSION}."
        )
    return plugin


class PluginManager:
    """Discover and run read-only diagnostics plugins.

    Third-party Python plugins use the ``mathfixer.plugins`` entry-point group.
    A plugin receives immutable paths/text and returns diagnostics; source writing is
    intentionally outside the SDK contract.
    """

    def __init__(self, plugins: list[MathFixerPlugin] | None = None):
        self.plugins = [validate_plugin(plugin) for plugin in (plugins or [])]
        self.load_errors: list[str] = []

    def discover(self) -> PluginManager:
        discovered = metadata.entry_points()
        entries = (
            discovered.select(group="mathfixer.plugins")
            if hasattr(discovered, "select")
            else discovered.get("mathfixer.plugins", [])
        )
        for entry in entries:
            try:
                loaded = entry.load()
                plugin = loaded() if isinstance(loaded, type) else loaded
                self.plugins.append(validate_plugin(plugin))
            except Exception as exc:  # An incompatible third-party plugin must not stop the app.
                self.load_errors.append(f"{entry.name}: {exc}")
        return self

    def analyze(self, context: PluginContext) -> list[PluginDiagnostic]:
        findings: list[PluginDiagnostic] = []
        for plugin in self.plugins:
            try:
                for item in plugin.analyze(context):
                    findings.append(
                        item
                        if item.plugin
                        else PluginDiagnostic(
                            code=item.code,
                            message=item.message,
                            suggestion=item.suggestion,
                            severity=item.severity,
                            file=item.file,
                            line=item.line,
                            plugin=plugin.name,
                        )
                    )
            except Exception as exc:
                findings.append(
                    PluginDiagnostic(
                        code="PLUGIN_FAILURE",
                        message=f"Plugin {plugin.name!r} failed: {exc}",
                        suggestion="Disable or update this plugin before using its diagnostics.",
                        severity="error",
                        plugin=plugin.name,
                    )
                )
        return findings
