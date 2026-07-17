from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..core.reporting import write_html_report, write_json_report
from ..plugins.thesis import THESIS_PROFILES
from .citations import find_missing_citations, find_missing_references
from .latex_log import parse_latex_log
from .persian import analyze_persian_latex

FRACTION = re.compile(r"\\frac\s*([A-Za-z0-9])\s*([A-Za-z0-9])")
MISSING_SLASH_FRACTION = re.compile(r"(?<![\\A-Za-z])frac\s*([A-Za-z0-9])\s*([A-Za-z0-9])")
PACKAGE_HINTS = {
    r"\begin{align": ("amsmath", r"\usepackage{amsmath}"),
    r"\includegraphics": ("graphicx", r"\usepackage{graphicx}"),
    r"\mathbb": ("amssymb", r"\usepackage{amssymb}"),
}


@dataclass(slots=True)
class LatexChange:
    before: str
    after: str
    reason: str
    line: int


@dataclass(slots=True)
class LatexFinding:
    code: str
    message: str
    suggestion: str = ""
    line: int | None = None
    severity: str = "warning"


@dataclass(slots=True)
class LatexReport:
    input_path: str
    thesis_profile: str = "generic"
    output_path: str = ""
    detected: int = 0
    converted: int = 0
    skipped: int = 0
    changes: list[LatexChange] = field(default_factory=list)
    findings: list[LatexFinding] = field(default_factory=list)
    pdf_path: str = ""
    success: bool = False

    def to_dict(self) -> dict:
        candidates = [
            {
                "source": item.before, "normalized": item.after, "repairs": [item.reason],
                "part": Path(self.input_path).name, "paragraph_index": max(0, item.line - 1), "enabled": True,
            }
            for item in self.changes
        ]
        return {**asdict(self), "candidates": candidates}


def _line_number(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def analyze_latex(path: str | os.PathLike[str], *, thesis_profile: str = "generic") -> LatexReport:
    source_path = Path(path).expanduser().resolve()
    if source_path.suffix.lower() != ".tex" or not source_path.is_file():
        raise ValueError("LaTeX analysis requires an existing .tex file.")
    source = source_path.read_text(encoding="utf-8", errors="replace")
    known_profiles = {profile.key for profile in THESIS_PROFILES}
    if thesis_profile not in known_profiles:
        raise ValueError(f"Unknown thesis profile: {thesis_profile}")
    report = LatexReport(input_path=str(source_path), thesis_profile=thesis_profile)
    if thesis_profile != "generic" and not any(source_path.parent.glob("*.cls")) and not any(source_path.parent.glob("*.sty")):
        report.findings.append(
            LatexFinding(
                "THESIS_TEMPLATE_MISSING",
                "A university compatibility profile was selected, but no local .cls or .sty template was found.",
                "Place the licensed or university-provided template beside the TEX project.",
            )
        )
    for pattern, reason in (
        (FRACTION, "Missing braces around fraction arguments"),
        (MISSING_SLASH_FRACTION, "Missing backslash and braces in fraction command"),
    ):
        for match in pattern.finditer(source):
            fixed = rf"\frac{{{match.group(1)}}}{{{match.group(2)}}}"
            report.changes.append(LatexChange(match.group(0), fixed, reason, _line_number(source, match.start())))
    for token, (package, command) in PACKAGE_HINTS.items():
        if token in source and not re.search(rf"\\usepackage(?:\[[^]]*\])?\{{[^}}]*\b{package}\b[^}}]*\}}", source):
            report.findings.append(LatexFinding("MISSING_PACKAGE", f"{package} appears to be required.", command))
    for item in analyze_persian_latex(source):
        report.findings.append(LatexFinding(item["code"], item["message"], item["suggestion"]))
    for key in find_missing_citations(source, base_dir=source_path.parent):
        report.findings.append(LatexFinding("MISSING_CITATION", f"Citation key '{key}' was not found in local .bib files.", f"Add a BibTeX entry for {key}."))
    for key in find_missing_references(source):
        report.findings.append(LatexFinding("MISSING_REFERENCE", f"Reference '{key}' has no matching label.", rf"Add \label{{{key}}} or correct the reference key."))
    if source.count("{") != source.count("}"):
        report.findings.append(LatexFinding("UNBALANCED_BRACES", "The document has unbalanced curly braces.", "Review the nearest LaTeX group before compiling.", severity="error"))
    if len(re.findall(r"\\begin\{(?:tabular|longtable)\}", source)) != len(
        re.findall(r"\\end\{(?:tabular|longtable)\}", source)
    ):
        report.findings.append(
            LatexFinding(
                "TABLE_ENVIRONMENT_MISMATCH",
                "A tabular/longtable environment is not opened and closed consistently.",
                "Match every table environment begin/end pair before compiling.",
                severity="error",
            )
        )
    log_path = source_path.with_suffix(".log")
    if log_path.is_file():
        for item in parse_latex_log(log_path.read_text(encoding="utf-8", errors="replace")):
            report.findings.append(
                LatexFinding(
                    str(item["code"]), str(item["message"]), str(item["suggestion"]),
                    line=item.get("line"), severity=str(item["severity"]),
                )
            )
    report.detected = len(report.changes) + len(report.findings)
    return report


def repair_latex(
    input_path: str | os.PathLike[str], output_path: str | os.PathLike[str], *,
    overwrite: bool = False, create_pdf: bool = False, report_path: str | os.PathLike[str] | None = None,
    html_report_path: str | os.PathLike[str] | None = None, language: str = "en",
    thesis_profile: str = "generic",
) -> LatexReport:
    source_path = Path(input_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    if source_path == target:
        raise ValueError("Output must be different from the source file.")
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    report = analyze_latex(source_path, thesis_profile=thesis_profile)
    source = source_path.read_text(encoding="utf-8", errors="replace")
    repaired = FRACTION.sub(lambda m: rf"\frac{{{m.group(1)}}}{{{m.group(2)}}}", source)
    repaired = MISSING_SLASH_FRACTION.sub(lambda m: rf"\frac{{{m.group(1)}}}{{{m.group(2)}}}", repaired)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=f".{target.stem}-", suffix=".tex", dir=target.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(repaired)
    try:
        os.replace(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)
    report.output_path = str(target)
    report.converted = len(report.changes)
    if create_pdf:
        engine = shutil.which("xelatex")
        if not engine:
            raise RuntimeError("XeLaTeX was not found; the repaired .tex file was created without PDF.")
        process = subprocess.run([engine, "-interaction=nonstopmode", "-halt-on-error", target.name], cwd=target.parent, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=False)
        pdf = target.with_suffix(".pdf")
        if process.returncode != 0 or not pdf.exists():
            raise RuntimeError("XeLaTeX could not build the PDF. " + process.stdout[-1200:])
        report.pdf_path = str(pdf)
    report.success = True
    data = report.to_dict()
    if report_path:
        write_json_report(Path(report_path), data)
    if html_report_path:
        write_html_report(Path(html_report_path), data, language=language)
    return report
