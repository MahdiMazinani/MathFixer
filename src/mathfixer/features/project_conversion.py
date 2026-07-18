from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..core.security import validate_ooxml_archive
from ..pandoc_backend import PandocBackend


@dataclass(frozen=True, slots=True)
class ProjectConversionResult:
    input_path: str
    output_path: str
    direction: str
    media_directory: str = ""
    media_files: tuple[str, ...] = ()


def _run_pandoc(command: list[str], *, cwd: Path | None = None) -> None:
    process = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout).strip()[-1600:]
        raise RuntimeError(f"Pandoc project conversion failed. {detail}")


def word_to_latex_project(
    input_path: str | os.PathLike[str],
    output_directory: str | os.PathLike[str],
    *,
    tex_name: str | None = None,
    pandoc_path: str | None = None,
    overwrite: bool = False,
) -> ProjectConversionResult:
    source = Path(input_path).expanduser().resolve()
    target = Path(output_directory).expanduser().resolve()
    if source.suffix.lower() not in {".docx", ".docm"} or not source.is_file():
        raise ValueError("Word project export requires an existing DOCX or DOCM file.")
    validate_ooxml_archive(source)
    filename = tex_name or f"{source.stem}.tex"
    if Path(filename).name != filename or not filename.lower().endswith(".tex"):
        raise ValueError("tex_name must be a plain .tex filename without directories.")
    if target.exists() and not target.is_dir():
        raise FileExistsError(f"Project output path is not a directory: {target}")
    if target.exists() and any(target.iterdir()) and not overwrite:
        raise FileExistsError(f"Project output directory is not empty: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    backend = PandocBackend(pandoc_path)

    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
    backup: Path | None = None
    published = False
    try:
        media = staging / "media"
        tex = staging / filename
        _run_pandoc(
            [
                backend.executable,
                str(source),
                "--from=docx",
                "--to=latex",
                "--standalone",
                f"--extract-media={media}",
                "--output",
                str(tex),
            ]
        )
        if not tex.is_file():
            raise RuntimeError("Pandoc completed without creating the project main TEX file.")
        tex_source = tex.read_text(encoding="utf-8", errors="replace")
        staging_prefixes = {
            str(staging) + os.sep,
            staging.as_posix() + "/",
            str(staging).replace("\\", "/") + "/",
        }
        for prefix in staging_prefixes:
            tex_source = tex_source.replace(prefix, "")
        tex.write_text(tex_source, encoding="utf-8")
        if target.exists():
            backup = Path(tempfile.mkdtemp(prefix=f".{target.name}-backup-", dir=target.parent))
            backup.rmdir()
            os.replace(target, backup)
        os.replace(staging, target)
        published = True
        if backup is not None:
            shutil.rmtree(backup)
        media_target = target / "media"
        files = (
            tuple(
                sorted(
                    path.relative_to(target).as_posix()
                    for path in media_target.rglob("*")
                    if path.is_file()
                )
            )
            if media_target.is_dir()
            else ()
        )
        return ProjectConversionResult(
            str(source), str(target / filename), "word-to-latex", str(media_target), files
        )
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            os.replace(backup, target)
        raise
    finally:
        if not published and staging.exists():
            shutil.rmtree(staging)


def latex_project_to_word(
    main_tex: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    *,
    pandoc_path: str | None = None,
    reference_docx: str | os.PathLike[str] | None = None,
    overwrite: bool = False,
) -> ProjectConversionResult:
    source = Path(main_tex).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    if source.suffix.lower() != ".tex" or not source.is_file():
        raise ValueError("LaTeX project import requires an existing main .tex file.")
    if target.suffix.lower() != ".docx":
        raise ValueError("Word project output must use the .docx extension.")
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    reference: Path | None = None
    if reference_docx:
        reference = Path(reference_docx).expanduser().resolve()
        if reference.suffix.lower() != ".docx" or not reference.is_file():
            raise ValueError("reference_docx must point to an existing DOCX file.")
        validate_ooxml_archive(reference)
    target.parent.mkdir(parents=True, exist_ok=True)
    backend = PandocBackend(pandoc_path)
    with tempfile.TemporaryDirectory(prefix=f".{target.stem}-", dir=target.parent) as directory:
        temporary = Path(directory, target.name)
        command = [
            backend.executable,
            str(source),
            "--from=latex",
            "--to=docx",
            "--resource-path",
            str(source.parent),
            "--output",
            str(temporary),
        ]
        if reference is not None:
            command.extend(["--reference-doc", str(reference)])
        _run_pandoc(command, cwd=source.parent)
        if not temporary.is_file():
            raise RuntimeError("Pandoc completed without creating the Word document.")
        validate_ooxml_archive(temporary)
        os.replace(temporary, target)
    media_files = tuple(
        sorted(
            path.relative_to(source.parent).as_posix()
            for path in source.parent.rglob("*")
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".pdf"}
        )
    )
    return ProjectConversionResult(str(source), str(target), "latex-to-word", "", media_files)
