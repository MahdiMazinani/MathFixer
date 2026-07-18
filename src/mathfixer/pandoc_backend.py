from __future__ import annotations

import copy
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from lxml import etree

from .models import ConversionWarning, FormulaCandidate

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NS = {"w": W_NS, "m": M_NS}


class PandocNotFoundError(RuntimeError):
    pass


PandocProgressCallback = Callable[[int, int, str], None]


def _stop_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Stop a timed-out Pandoc process without an unbounded follow-up wait."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        taskkill = shutil.which("taskkill.exe") or shutil.which("taskkill")
        if taskkill:
            with suppress(OSError, subprocess.SubprocessError):
                subprocess.run(
                    [taskkill, "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    check=False,
                )
    else:
        with suppress(OSError, ProcessLookupError):
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    if process.poll() is None:
        with suppress(OSError):
            process.kill()
    # Never turn timeout cleanup into another indefinite wait.
    with suppress(OSError, subprocess.TimeoutExpired):
        process.wait(timeout=5)


def _run_bounded(command: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    """Run a console child with file-backed output and deterministic timeout cleanup."""
    startupinfo = None
    creationflags = 0
    popen_options: dict[str, object] = {}
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        popen_options["start_new_session"] = True

    with tempfile.TemporaryFile() as stdout_log, tempfile.TemporaryFile() as stderr_log:
        process = subprocess.Popen(
            command,
            stdout=stdout_log,
            stderr=stderr_log,
            startupinfo=startupinfo,
            creationflags=creationflags,
            **popen_options,
        )
        try:
            return_code = process.wait(timeout=max(0.1, timeout))
        except subprocess.TimeoutExpired as exc:
            _stop_process_tree(process)
            raise subprocess.TimeoutExpired(command, timeout) from exc
        stdout_log.seek(0)
        stderr_log.seek(0)
        stdout = stdout_log.read().decode("utf-8", errors="replace")
        stderr = stderr_log.read().decode("utf-8", errors="replace")
    return subprocess.CompletedProcess(command, return_code, stdout, stderr)


class PandocBackend:
    """Converts only math fragments. Pandoc never reads or rebuilds the user's DOCX."""

    _version_cache: dict[str, str] = {}

    def __init__(
        self,
        executable: str | None = None,
        *,
        timeout: float = 30,
        total_timeout: float = 45,
        batch_size: int = 200,
    ):
        self.executable = self._resolve(executable)
        self.timeout = max(0.1, float(timeout))
        self.total_timeout = max(0.1, float(total_timeout))
        self.batch_size = max(1, batch_size)
        self._cache: dict[str, etree._Element] = {}

    @staticmethod
    def _resolve(executable: str | None) -> str:
        binary_name = "pandoc.exe" if os.name == "nt" else "pandoc"
        bundle_root = getattr(sys, "_MEIPASS", None)
        bundled = Path(bundle_root, binary_name) if bundle_root else None
        beside_executable = Path(sys.executable).resolve().parent / binary_name
        candidates = [
            executable,
            os.environ.get("MATHFIXER_PANDOC"),
            bundled,
            beside_executable,
            shutil.which("pandoc"),
        ]
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                return str(Path(candidate).resolve())
        raise PandocNotFoundError(
            "Pandoc was not found. Install Pandoc or set MATHFIXER_PANDOC to its executable."
        )

    @property
    def version(self) -> str:
        cached = self._version_cache.get(self.executable)
        if cached is not None:
            return cached
        try:
            result = _run_bounded([self.executable, "--version"], timeout=5)
            if result.returncode != 0:
                version = "pandoc (version unavailable)"
            else:
                version = result.stdout.splitlines()[0].strip()
        except (OSError, subprocess.SubprocessError, IndexError):
            version = "pandoc (version unavailable)"
        self._version_cache[self.executable] = version
        return version

    @staticmethod
    def _formula_key(candidate: FormulaCandidate) -> str:
        return candidate.normalized.strip()

    @staticmethod
    def _marker(index: int) -> tuple[str, str]:
        return f"MFXS{index:06d}Q", f"MFXE{index:06d}Q"

    def convert_many(
        self,
        candidates: list[FormulaCandidate],
        *,
        progress: PandocProgressCallback | None = None,
    ) -> tuple[dict[str, etree._Element], list[ConversionWarning]]:
        result: dict[str, etree._Element] = {}
        warnings: list[ConversionWarning] = []
        unique: dict[str, list[FormulaCandidate]] = {}
        for candidate in candidates:
            if candidate.enabled:
                unique.setdefault(self._formula_key(candidate), []).append(candidate)

        pending = [key for key in unique if key not in self._cache]
        started = time.monotonic()
        for offset in range(0, len(pending), self.batch_size):
            formulas = pending[offset : offset + self.batch_size]
            remaining = self.total_timeout - (time.monotonic() - started)
            if remaining <= 0:
                warnings.append(
                    ConversionWarning(
                        code="PANDOC_TOTAL_TIMEOUT",
                        message=(
                            "Pandoc reached the total conversion limit of "
                            f"{self.total_timeout:g} seconds."
                        ),
                    )
                )
                break
            if progress:
                progress(
                    offset,
                    len(pending),
                    f"Converting formula batch with Pandoc ({offset}/{len(pending)})",
                )
            converted, batch_warnings = self._convert_batch(
                formulas, timeout=min(self.timeout, remaining)
            )
            self._cache.update(converted)
            warnings.extend(batch_warnings)
            completed = min(len(pending), offset + len(formulas))
            if progress:
                progress(
                    completed,
                    len(pending),
                    f"Pandoc formula conversion ({completed}/{len(pending)})",
                )
            if any(item.code == "PANDOC_TIMEOUT" for item in batch_warnings):
                # A hung converter is not retried batch by batch; that previously
                # multiplied one 90-second stall into several minutes.
                break

        for source, occurrences in unique.items():
            omath = self._cache.get(source)
            if omath is None:
                for candidate in occurrences:
                    warnings.append(
                        ConversionWarning(
                            code="PANDOC_FORMULA_FAILED",
                            message="Pandoc could not convert this formula to native Office Math.",
                            part=candidate.part,
                            paragraph_index=candidate.paragraph_index,
                            formula=candidate.normalized,
                        )
                    )
                continue
            for candidate in occurrences:
                native = copy.deepcopy(omath)
                if candidate.display:
                    block = etree.Element(f"{{{M_NS}}}oMathPara", nsmap={"m": M_NS})
                    block.append(native)
                    native = block
                result[candidate.candidate_id] = native
        return result, warnings

    def _convert_batch(
        self, formulas: list[str], *, timeout: float | None = None
    ) -> tuple[dict[str, etree._Element], list[ConversionWarning]]:
        converted: dict[str, etree._Element] = {}
        warnings: list[ConversionWarning] = []
        if not formulas:
            return converted, warnings

        lines: list[str] = []
        markers: dict[str, tuple[str, str, str]] = {}
        for index, formula in enumerate(formulas):
            start, end = self._marker(index)
            markers[start] = (end, formula, start)
            safe_formula = formula.replace("\r", " ").replace("\n", " ")
            lines.append(f"{start} ${safe_formula}$ {end}")
            lines.append("")

        with tempfile.TemporaryDirectory(prefix="mathfixer-pandoc-") as temp_dir:
            source_path = Path(temp_dir, "math.md")
            output_path = Path(temp_dir, "math.docx")
            source_path.write_text("\n".join(lines), encoding="utf-8")
            command = [
                self.executable,
                str(source_path),
                "--from=markdown+tex_math_dollars+raw_tex",
                "--to=docx",
                "--output",
                str(output_path),
            ]
            try:
                process = _run_bounded(command, timeout=timeout or self.timeout)
            except subprocess.TimeoutExpired:
                return {}, [
                    ConversionWarning(
                        code="PANDOC_TIMEOUT",
                        message=(
                            "Pandoc exceeded the "
                            f"{(timeout or self.timeout):g}-second batch timeout and was stopped."
                        ),
                    )
                ]
            except OSError as exc:
                return {}, [ConversionWarning(code="PANDOC_EXECUTION_ERROR", message=str(exc))]

            if process.returncode != 0 or not output_path.exists():
                detail = process.stderr.strip()[-1200:]
                return {}, [
                    ConversionWarning(
                        code="PANDOC_BATCH_FAILED",
                        message=f"Pandoc failed with exit code {process.returncode}: {detail}",
                    )
                ]

            try:
                with ZipFile(output_path) as archive:
                    root = etree.fromstring(archive.read("word/document.xml"))
            except (BadZipFile, KeyError, etree.XMLSyntaxError) as exc:
                return {}, [ConversionWarning(code="PANDOC_OUTPUT_INVALID", message=str(exc))]

            for paragraph in root.xpath(".//w:p", namespaces=NS):
                plain = "".join(paragraph.xpath(".//w:t/text()", namespaces=NS))
                marker = re.search(r"MFXS\d{6}Q", plain)
                if not marker or marker.group(0) not in markers:
                    continue
                end, formula, _ = markers[marker.group(0)]
                if end not in plain:
                    continue
                nodes = paragraph.xpath(".//m:oMath", namespaces=NS)
                if nodes:
                    converted[formula] = copy.deepcopy(nodes[0])

        return converted, warnings
