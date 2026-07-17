from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ProgressCallback = Callable[[int, str], None]


class PdfExportError(RuntimeError):
    pass


@dataclass(slots=True)
class PdfExportResult:
    path: Path
    engine: str
    pages: int | None
    size_bytes: int


def _validate_pdf(path: Path) -> tuple[int | None, int]:
    if not path.is_file() or path.stat().st_size < 100:
        raise PdfExportError("The PDF engine did not create a usable output file.")
    data = path.read_bytes()
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-4096:]:
        raise PdfExportError("The generated file is not a valid PDF document.")
    # Conservative structural count; when pypdf is installed, use its authoritative count.
    pages: int | None = None
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]

        pages = len(PdfReader(str(path)).pages)
    except Exception:
        matches = re.findall(rb"/Type\s*/Page\b", data)
        pages = len(matches) or None
    return pages, len(data)


def _powershell() -> str | None:
    return shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh")


def _export_with_word(source: Path, output: Path, timeout: int) -> None:
    if os.name != "nt":
        raise PdfExportError("Microsoft Word PDF export is available only on Windows.")
    executable = _powershell()
    if not executable:
        raise PdfExportError("PowerShell was not found.")
    script = r'''
param([string]$InputPath, [string]$OutputPath)
$ErrorActionPreference = "Stop"
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    # Force-disable VBA before opening any untrusted DOCX/DOCM package.
    $word.AutomationSecurity = 3
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($InputPath, $false, $true)
    $document.ExportAsFixedFormat($OutputPath, 17)
}
finally {
    if ($null -ne $document) { $document.Close(0) }
    if ($null -ne $word) { $word.Quit() }
    if ($null -ne $document) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) }
    if ($null -ne $word) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
'''
    with tempfile.TemporaryDirectory(prefix="mathfixer-word-pdf-") as directory:
        script_path = Path(directory, "export_pdf.ps1")
        script_path.write_text(script, encoding="utf-8-sig")
        process = subprocess.run(
            [
                executable,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-InputPath",
                str(source),
                "-OutputPath",
                str(output),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout).strip()[-1200:]
        raise PdfExportError(
            "Microsoft Word could not export the PDF. Make sure desktop Word is installed and not showing a dialog. "
            + detail
        )


def _find_libreoffice() -> str | None:
    candidates = [shutil.which("soffice"), shutil.which("libreoffice")]
    if os.name == "nt":
        candidates.extend(
            [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
        )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    return None


def _export_with_libreoffice(source: Path, output: Path, timeout: int) -> None:
    executable = _find_libreoffice()
    if not executable:
        raise PdfExportError("LibreOffice was not found.")
    with tempfile.TemporaryDirectory(prefix="mathfixer-lo-pdf-") as directory:
        out_dir = Path(directory, "out")
        profile_dir = Path(directory, "profile")
        out_dir.mkdir()
        command = [
            executable,
            f"-env:UserInstallation={profile_dir.resolve().as_uri()}",
            "--headless",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            str(out_dir),
            str(source),
        ]
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        generated = out_dir / f"{source.stem}.pdf"
        if process.returncode != 0 or not generated.exists():
            detail = (process.stderr or process.stdout).strip()[-1200:]
            raise PdfExportError(f"LibreOffice could not export the PDF. {detail}")
        shutil.copyfile(generated, output)


def export_docx_to_pdf(
    input_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    *,
    engine: str = "auto",
    overwrite: bool = False,
    timeout: int = 180,
    progress: ProgressCallback | None = None,
) -> PdfExportResult:
    source = Path(input_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    if source.suffix.lower() not in {".docx", ".docm"} or not source.is_file():
        raise PdfExportError("PDF export requires an existing DOCX or DOCM file.")
    if target.suffix.lower() != ".pdf":
        raise PdfExportError("PDF output must use the .pdf extension.")
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized_engine = engine.lower().strip()
    if normalized_engine not in {"auto", "word", "libreoffice"}:
        raise ValueError("PDF engine must be auto, word, or libreoffice.")

    # LibreOffice's macro policy varies by installation. For macro-enabled input,
    # only Word automation with AutomationSecurityForceDisable is accepted.
    if source.suffix.lower() == ".docm" and normalized_engine == "libreoffice":
        raise PdfExportError("DOCM PDF export requires Microsoft Word so macros can be force-disabled.")

    order = [normalized_engine]
    if normalized_engine == "auto":
        if source.suffix.lower() == ".docm":
            if os.name != "nt":
                raise PdfExportError("Secure DOCM PDF export is available only with Microsoft Word on Windows.")
            order = ["word"]
        else:
            order = ["word", "libreoffice"] if os.name == "nt" else ["libreoffice"]
    errors: list[str] = []
    with tempfile.NamedTemporaryFile(
        prefix=f".{target.stem}-", suffix=".pdf", dir=target.parent, delete=False
    ) as temp_handle:
        temp_path = Path(temp_handle.name)
    try:
        for candidate in order:
            temp_path.unlink(missing_ok=True)
            if progress:
                progress(90, f"Exporting PDF with {candidate}")
            try:
                if candidate == "word":
                    _export_with_word(source, temp_path, timeout)
                else:
                    _export_with_libreoffice(source, temp_path, timeout)
                pages, size_bytes = _validate_pdf(temp_path)
                os.replace(temp_path, target)
                if progress:
                    progress(99, "PDF validated")
                return PdfExportResult(target, candidate, pages, size_bytes)
            except (OSError, subprocess.SubprocessError, PdfExportError) as exc:
                errors.append(f"{candidate}: {exc}")
        raise PdfExportError(
            "No PDF engine succeeded. Install Microsoft Word or LibreOffice. " + " | ".join(errors)
        )
    finally:
        temp_path.unlink(missing_ok=True)
