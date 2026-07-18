from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .citations import BIB_ENTRY_PATTERN, CITE_PATTERN, LABEL_PATTERN, REF_PATTERN

INCLUDE_PATTERN = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")
BIBLIOGRAPHY_PATTERN = re.compile(r"\\bibliography\s*\{([^}]+)\}")
ADD_BIB_RESOURCE_PATTERN = re.compile(r"\\addbibresource(?:\[[^]]*\])?\s*\{([^}]+)\}")


@dataclass(frozen=True, slots=True)
class SourceUnit:
    path: Path
    relative_path: str
    text: str


@dataclass(frozen=True, slots=True)
class WorkspaceFinding:
    code: str
    message: str
    suggestion: str = ""
    file: str = ""
    line: int | None = None
    severity: str = "warning"


@dataclass(slots=True)
class LatexWorkspace:
    root: Path
    main: Path
    sources: list[SourceUnit] = field(default_factory=list)
    bibliography_files: list[Path] = field(default_factory=list)
    findings: list[WorkspaceFinding] = field(default_factory=list)

    @property
    def source_map(self) -> dict[str, str]:
        return {unit.relative_path: unit.text for unit in self.sources}


def _line_number(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def _inside_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _resolve_tex(reference: str, *, parent: Path, root: Path) -> Path | None:
    raw = reference.strip()
    if not raw or "\\" in raw:
        return None
    candidate = Path(raw)
    if candidate.is_absolute():
        return None
    if candidate.suffix == "":
        candidate = candidate.with_suffix(".tex")
    resolved = (parent / candidate).resolve()
    return resolved if _inside_root(resolved, root) else None


def _declared_bibliographies(unit: SourceUnit, root: Path) -> list[Path]:
    values: list[str] = []
    for group in BIBLIOGRAPHY_PATTERN.findall(unit.text):
        values.extend(part.strip() for part in group.split(","))
    values.extend(item.strip() for item in ADD_BIB_RESOURCE_PATTERN.findall(unit.text))
    result: list[Path] = []
    for value in values:
        if not value or "\\" in value:
            continue
        candidate = Path(value)
        if candidate.is_absolute():
            continue
        if candidate.suffix == "":
            candidate = candidate.with_suffix(".bib")
        path = (unit.path.parent / candidate).resolve()
        if _inside_root(path, root) and path.is_file():
            result.append(path)
    return result


def build_latex_workspace(
    main_path: str | Path,
    *,
    max_files: int = 256,
    max_total_bytes: int = 16 * 1024 * 1024,
) -> LatexWorkspace:
    main = Path(main_path).expanduser().resolve()
    if main.suffix.lower() != ".tex" or not main.is_file():
        raise ValueError("A LaTeX workspace requires an existing main .tex file.")
    root = main.parent
    workspace = LatexWorkspace(root=root, main=main)
    pending = [main]
    visited: set[Path] = set()
    total_bytes = 0

    while pending:
        path = pending.pop(0)
        if path in visited:
            continue
        if len(visited) >= max_files:
            raise ValueError(f"LaTeX project contains more than {max_files} source files.")
        payload = path.read_bytes()
        total_bytes += len(payload)
        if total_bytes > max_total_bytes:
            raise ValueError("LaTeX project source exceeds the configured safety limit.")
        text = payload.decode("utf-8", errors="replace")
        visited.add(path)
        unit = SourceUnit(path=path, relative_path=_relative(path, root), text=text)
        workspace.sources.append(unit)

        for match in INCLUDE_PATTERN.finditer(text):
            resolved = _resolve_tex(match.group(1), parent=path.parent, root=root)
            if resolved is None:
                workspace.findings.append(
                    WorkspaceFinding(
                        "UNSAFE_INCLUDE",
                        f"Include path '{match.group(1)}' is absolute, malformed, or leaves the project root.",
                        "Keep included TEX files inside the project folder and use a relative path.",
                        unit.relative_path,
                        _line_number(text, match.start()),
                        "error",
                    )
                )
            elif not resolved.is_file():
                workspace.findings.append(
                    WorkspaceFinding(
                        "MISSING_INCLUDE",
                        f"Included file '{match.group(1)}' was not found.",
                        "Restore the file or correct the \\input/\\include path.",
                        unit.relative_path,
                        _line_number(text, match.start()),
                        "error",
                    )
                )
            elif resolved not in visited and resolved not in pending:
                pending.append(resolved)

    declared: set[Path] = set()
    for unit in workspace.sources:
        declared.update(_declared_bibliographies(unit, root))
    if not declared:
        declared.update(path.resolve() for path in root.rglob("*.bib") if path.is_file())
    workspace.bibliography_files = sorted(declared)
    workspace.findings.extend(_cross_reference_findings(workspace))
    return workspace


def _cross_reference_findings(workspace: LatexWorkspace) -> list[WorkspaceFinding]:
    available_citations: set[str] = set()
    for bib in workspace.bibliography_files:
        try:
            available_citations.update(
                BIB_ENTRY_PATTERN.findall(bib.read_text(encoding="utf-8", errors="replace"))
            )
        except OSError:
            continue

    labels: dict[str, list[tuple[str, int]]] = {}
    citations: list[tuple[str, str, int]] = []
    references: list[tuple[str, str, int]] = []
    for unit in workspace.sources:
        for match in LABEL_PATTERN.finditer(unit.text):
            labels.setdefault(match.group(1).strip(), []).append(
                (unit.relative_path, _line_number(unit.text, match.start()))
            )
        for match in CITE_PATTERN.finditer(unit.text):
            line = _line_number(unit.text, match.start())
            citations.extend(
                (key.strip(), unit.relative_path, line)
                for key in match.group(1).split(",")
                if key.strip()
            )
        for match in REF_PATTERN.finditer(unit.text):
            references.append(
                (match.group(1).strip(), unit.relative_path, _line_number(unit.text, match.start()))
            )

    findings: list[WorkspaceFinding] = []
    for key, file, line in citations:
        if key not in available_citations:
            findings.append(
                WorkspaceFinding(
                    "MISSING_CITATION",
                    f"Citation key '{key}' was not found in project bibliography files.",
                    f"Add a BibTeX entry for {key} or correct the citation key.",
                    file,
                    line,
                )
            )
    for key, file, line in references:
        if key not in labels:
            findings.append(
                WorkspaceFinding(
                    "MISSING_REFERENCE",
                    f"Reference '{key}' has no matching label in the LaTeX project.",
                    rf"Add \label{{{key}}} or correct the reference key.",
                    file,
                    line,
                )
            )
    for key, locations in labels.items():
        if len(locations) > 1:
            for file, line in locations:
                findings.append(
                    WorkspaceFinding(
                        "DUPLICATE_LABEL",
                        f"Label '{key}' is defined more than once.",
                        "Rename duplicate labels so every reference target is unique.",
                        file,
                        line,
                    )
                )
    return findings
