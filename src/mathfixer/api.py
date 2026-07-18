from __future__ import annotations

import os
from pathlib import Path

from .docx_engine import convert_document, scan_document
from .features.latex_project import analyze_latex, repair_latex, repair_latex_workspace
from .features.pdf_compare import compare_pdfs
from .features.project_conversion import latex_project_to_word, word_to_latex_project
from .models import DetectionMode

API_VERSION = "2.0"


def scan(
    input_path: str | os.PathLike[str],
    *,
    mode: DetectionMode = DetectionMode.BALANCED,
    thesis_profile: str = "generic",
    template_adapter_path: str | os.PathLike[str] | None = None,
):
    """Scan a Word file or a complete LaTeX workspace without writing output."""
    path = Path(input_path).expanduser().resolve()
    if path.suffix.lower() == ".tex":
        return analyze_latex(
            path,
            thesis_profile=thesis_profile,
            template_adapter_path=template_adapter_path,
        )
    return scan_document(path, mode=mode).report


def repair(
    input_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    *,
    mode: DetectionMode = DetectionMode.BALANCED,
    overwrite: bool = False,
    create_pdf: bool = False,
    **options,
):
    """Repair a supported document while preserving the original source."""
    source = Path(input_path).expanduser().resolve()
    if source.suffix.lower() == ".tex":
        return repair_latex(
            source,
            output_path,
            overwrite=overwrite,
            create_pdf=create_pdf,
            **options,
        )
    return convert_document(
        source,
        output_path,
        mode=mode,
        overwrite=overwrite,
        create_pdf=create_pdf,
        **options,
    )


__all__ = [
    "API_VERSION",
    "compare_pdfs",
    "latex_project_to_word",
    "repair",
    "repair_latex_workspace",
    "scan",
    "word_to_latex_project",
]
