from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def choose_available_output(
    primary: Path,
    *,
    companion_suffixes: Iterable[str] = (),
) -> Path:
    """Return a non-conflicting output path without replacing an existing file."""
    suffixes = tuple(companion_suffixes)

    def conflicts(candidate: Path) -> bool:
        return candidate.exists() or any(candidate.with_suffix(suffix).exists() for suffix in suffixes)

    if not conflicts(primary):
        return primary
    counter = 2
    while True:
        candidate = primary.with_name(f"{primary.stem}_{counter}{primary.suffix}")
        if not conflicts(candidate):
            return candidate
        counter += 1


def choose_available_directory(primary: Path) -> Path:
    """Return a sibling directory name that does not already exist."""
    if not primary.exists():
        return primary
    counter = 2
    while True:
        candidate = primary.with_name(f"{primary.name}_{counter}")
        if not candidate.exists():
            return candidate
        counter += 1
