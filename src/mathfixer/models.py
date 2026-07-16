from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class DetectionMode(str, Enum):
    SAFE = "safe"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class FormulaKind(str, Enum):
    LATEX_DISPLAY = "latex-display"
    LATEX_INLINE = "latex-inline"
    LATEX_ENVIRONMENT = "latex-environment"
    LATEX_BROKEN = "latex-broken"
    LATEX_RAW = "latex-raw"
    UNICODE_MATH = "unicode-math"
    PLAIN_EQUATION = "plain-equation"


@dataclass(slots=True)
class FormulaCandidate:
    part: str
    paragraph_index: int
    start: int
    end: int
    source: str
    normalized: str
    kind: FormulaKind
    display: bool
    confidence: float
    repairs: list[str] = field(default_factory=list)
    candidate_id: str = ""
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.candidate_id:
            self.candidate_id = f"{self.part}:{self.paragraph_index}:{self.start}:{self.end}"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data


@dataclass(slots=True)
class ConversionWarning:
    code: str
    message: str
    part: str | None = None
    paragraph_index: int | None = None
    formula: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PackageSnapshot:
    entries: set[str] = field(default_factory=set)
    unchanged_crc: dict[str, int] = field(default_factory=dict)
    tables: int = 0
    drawings: int = 0
    pictures: int = 0
    hyperlinks: int = 0
    bookmarks: int = 0
    comments: int = 0
    tracked_changes: int = 0
    sections: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["entries"] = sorted(self.entries)
        return data


@dataclass(slots=True)
class ConversionReport:
    input_path: str
    output_path: str = ""
    mode: str = DetectionMode.BALANCED.value
    scanned_parts: int = 0
    scanned_paragraphs: int = 0
    detected: int = 0
    converted: int = 0
    skipped: int = 0
    already_native: int = 0
    repaired: int = 0
    backend: str = "pandoc"
    pandoc_version: str = ""
    pdf_path: str = ""
    pdf_engine: str = ""
    pdf_pages: int | None = None
    pdf_size_bytes: int = 0
    candidates: list[FormulaCandidate] = field(default_factory=list)
    warnings: list[ConversionWarning] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    success: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_path": self.input_path,
            "output_path": self.output_path,
            "mode": self.mode,
            "scanned_parts": self.scanned_parts,
            "scanned_paragraphs": self.scanned_paragraphs,
            "detected": self.detected,
            "converted": self.converted,
            "skipped": self.skipped,
            "already_native": self.already_native,
            "repaired": self.repaired,
            "backend": self.backend,
            "pandoc_version": self.pandoc_version,
            "pdf_path": self.pdf_path,
            "pdf_engine": self.pdf_engine,
            "pdf_pages": self.pdf_pages,
            "pdf_size_bytes": self.pdf_size_bytes,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "validation": self.validation,
            "success": self.success,
        }

    @property
    def input_name(self) -> str:
        return Path(self.input_path).name
