from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .sdk import PLUGIN_API_VERSION, PluginContext, PluginDiagnostic


@dataclass(frozen=True, slots=True)
class TemplateAdapter:
    name: str
    version: str
    profile: str
    required_files: tuple[str, ...] = ()
    required_commands: tuple[str, ...] = ()
    engine: str = "xelatex"
    api_version: str = PLUGIN_API_VERSION

    def analyze(self, context: PluginContext) -> list[PluginDiagnostic]:
        findings: list[PluginDiagnostic] = []
        for relative in self.required_files:
            if not (context.project_root / relative).is_file():
                findings.append(
                    PluginDiagnostic(
                        "TEMPLATE_FILE_MISSING",
                        f"Template adapter requires '{relative}', but it was not found.",
                        "Place the licensed or university-provided template file in the project.",
                        "error",
                        plugin=self.name,
                    )
                )
        combined = "\n".join(context.sources.values())
        for command in self.required_commands:
            if command not in combined:
                findings.append(
                    PluginDiagnostic(
                        "TEMPLATE_COMMAND_MISSING",
                        f"Template command '{command}' was not found in the project.",
                        "Follow the template documentation and add the required declaration.",
                        plugin=self.name,
                    )
                )
        return findings


def _safe_relative_file(value: object) -> str:
    text = str(value).strip().replace("\\", "/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts or not re.fullmatch(r"[\w./ -]+", text):
        raise ValueError(f"Unsafe template file path: {text!r}")
    if path.suffix.lower() not in {".cls", ".sty", ".tex", ".cfg", ".def"}:
        raise ValueError(f"Unsupported template file type: {text!r}")
    return text


def load_template_adapter(path: str | Path) -> TemplateAdapter:
    manifest = Path(path).expanduser().resolve()
    if manifest.suffix.lower() != ".json" or not manifest.is_file():
        raise ValueError("Template adapter must be an existing JSON manifest.")
    if manifest.stat().st_size > 256 * 1024:
        raise ValueError("Template adapter manifest is too large.")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Template adapter manifest must contain a JSON object.")
    name = str(data.get("name", "")).strip()
    version = str(data.get("version", "")).strip()
    profile = str(data.get("profile", "custom")).strip()
    api_version = str(data.get("api_version", PLUGIN_API_VERSION)).strip()
    if not name or not version:
        raise ValueError("Template adapter requires non-empty name and version fields.")
    if api_version.split(".", 1)[0] != PLUGIN_API_VERSION.split(".", 1)[0]:
        raise ValueError(
            f"Template adapter API {api_version} is incompatible with {PLUGIN_API_VERSION}."
        )
    required_files = tuple(_safe_relative_file(value) for value in data.get("required_files", []))
    required_commands = tuple(str(value).strip() for value in data.get("required_commands", []))
    if any(not command or len(command) > 200 for command in required_commands):
        raise ValueError("Template commands must be non-empty and at most 200 characters.")
    return TemplateAdapter(
        name=name,
        version=version,
        profile=profile,
        required_files=required_files,
        required_commands=required_commands,
        engine=str(data.get("engine", "xelatex")).strip().lower(),
        api_version=api_version,
    )
