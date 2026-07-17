from __future__ import annotations

import copy
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from lxml import etree

from .models import ConversionWarning, FormulaCandidate

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NS = {"w": W_NS, "m": M_NS}


class PandocNotFoundError(RuntimeError):
    pass


class PandocBackend:
    """Converts only math fragments. Pandoc never reads or rebuilds the user's DOCX."""

    def __init__(self, executable: str | None = None, *, timeout: int = 90, batch_size: int = 80):
        self.executable = self._resolve(executable)
        self.timeout = timeout
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
        try:
            result = subprocess.run(
                [self.executable, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=10,
                check=True,
            )
            return result.stdout.splitlines()[0].strip()
        except (OSError, subprocess.SubprocessError, IndexError):
            return "pandoc (version unavailable)"

    @staticmethod
    def _formula_key(candidate: FormulaCandidate) -> str:
        return candidate.normalized.strip()

    @staticmethod
    def _marker(index: int) -> tuple[str, str]:
        return f"MFXS{index:06d}Q", f"MFXE{index:06d}Q"

    def convert_many(
        self, candidates: list[FormulaCandidate]
    ) -> tuple[dict[str, etree._Element], list[ConversionWarning]]:
        result: dict[str, etree._Element] = {}
        warnings: list[ConversionWarning] = []
        unique: dict[str, list[FormulaCandidate]] = {}
        for candidate in candidates:
            if candidate.enabled:
                unique.setdefault(self._formula_key(candidate), []).append(candidate)

        pending = [key for key in unique if key not in self._cache]
        for offset in range(0, len(pending), self.batch_size):
            formulas = pending[offset : offset + self.batch_size]
            converted, batch_warnings = self._convert_batch(formulas)
            self._cache.update(converted)
            warnings.extend(batch_warnings)

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
        self, formulas: list[str]
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
                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return {}, [
                    ConversionWarning(
                        code="PANDOC_TIMEOUT",
                        message=f"Pandoc exceeded the {self.timeout}-second conversion timeout.",
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
