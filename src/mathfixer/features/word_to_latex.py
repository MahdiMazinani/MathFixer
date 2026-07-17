from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..pandoc_backend import PandocBackend


def export_word_to_latex(
    input_path: str | os.PathLike[str], output_path: str | os.PathLike[str], *, pandoc_path: str | None = None,
) -> Path:
    source = Path(input_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    if source.suffix.lower() not in {".docx", ".docm"} or not source.is_file():
        raise ValueError("Word to LaTeX export requires an existing DOCX or DOCM file.")
    if target.suffix.lower() != ".tex":
        raise ValueError("LaTeX output must use the .tex extension.")
    target.parent.mkdir(parents=True, exist_ok=True)
    backend = PandocBackend(pandoc_path)
    process = subprocess.run(
        [backend.executable, str(source), "--from=docx", "--to=latex", "--standalone", "--output", str(target)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=False,
    )
    if process.returncode != 0 or not target.is_file():
        raise RuntimeError("Pandoc could not export Word to LaTeX. " + process.stderr.strip()[-1000:])
    return target
