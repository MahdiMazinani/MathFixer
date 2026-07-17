from __future__ import annotations

import re
from pathlib import Path

CITE_PATTERN = re.compile(r"\\(?:cite|parencite|textcite|autocite)\*?(?:\[[^]]*\]){0,2}\{([^}]+)\}")
BIB_ENTRY_PATTERN = re.compile(r"@\w+\s*\{\s*([^,\s]+)", re.IGNORECASE)
REF_PATTERN = re.compile(r"\\(?:ref|eqref|autoref)\{([^}]+)\}")
LABEL_PATTERN = re.compile(r"\\label\{([^}]+)\}")


def find_missing_citations(source: str, *, base_dir: Path | None = None) -> list[str]:
    cited = {key.strip() for match in CITE_PATTERN.findall(source) for key in match.split(",") if key.strip()}
    available: set[str] = set()
    if base_dir and base_dir.is_dir():
        for bib in base_dir.glob("*.bib"):
            try:
                available.update(BIB_ENTRY_PATTERN.findall(bib.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                continue
    return sorted(cited - available)


def find_missing_references(source: str) -> list[str]:
    referenced = {key.strip() for key in REF_PATTERN.findall(source) if key.strip()}
    labels = {key.strip() for key in LABEL_PATTERN.findall(source) if key.strip()}
    return sorted(referenced - labels)
