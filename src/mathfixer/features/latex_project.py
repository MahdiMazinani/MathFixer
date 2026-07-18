from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..core.reporting import write_html_report, write_json_report
from ..plugins.sdk import PluginContext, PluginManager
from ..plugins.template_adapter import load_template_adapter
from ..plugins.thesis import THESIS_PROFILES
from .latex_log import parse_latex_log
from .latex_workspace import build_latex_workspace
from .persian import analyze_persian_latex

TEX_ATOM = r"(\\[A-Za-z]+|[A-Za-z0-9])"
FRACTION = re.compile(rf"\\frac\s*{TEX_ATOM}\s*{TEX_ATOM}")
MISSING_SLASH_FRACTION = re.compile(rf"(?<![\\A-Za-z])frac\s*{TEX_ATOM}\s*{TEX_ATOM}")
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
    file: str = ""
    start: int = 0
    end: int = 0
    change_id: str = ""
    applied: bool = False


@dataclass(slots=True)
class LatexFinding:
    code: str
    message: str
    suggestion: str = ""
    line: int | None = None
    severity: str = "warning"
    file: str = ""
    plugin: str = ""


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
                "part": item.file or Path(self.input_path).name,
                "paragraph_index": max(0, item.line - 1),
                "candidate_id": item.change_id,
                "enabled": item.applied if self.output_path else True,
            }
            for item in self.changes
        ]
        return {**asdict(self), "candidates": candidates}


def _line_number(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def analyze_latex(
    path: str | os.PathLike[str],
    *,
    thesis_profile: str = "generic",
    template_adapter_path: str | os.PathLike[str] | None = None,
    plugin_manager: PluginManager | None = None,
) -> LatexReport:
    source_path = Path(path).expanduser().resolve()
    if source_path.suffix.lower() != ".tex" or not source_path.is_file():
        raise ValueError("LaTeX analysis requires an existing .tex file.")
    workspace = build_latex_workspace(source_path)
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
    for unit in workspace.sources:
        for pattern, reason in (
            (FRACTION, "Missing braces around fraction arguments"),
            (MISSING_SLASH_FRACTION, "Missing backslash and braces in fraction command"),
        ):
            for match in pattern.finditer(unit.text):
                fixed = rf"\frac{{{match.group(1)}}}{{{match.group(2)}}}"
                report.changes.append(
                    LatexChange(
                        match.group(0), fixed, reason,
                        _line_number(unit.text, match.start()), unit.relative_path,
                        match.start(), match.end(),
                    )
                )
        for token, (package, command) in PACKAGE_HINTS.items():
            if token in unit.text and not re.search(
                rf"\\usepackage(?:\[[^]]*\])?\{{[^}}]*\b{package}\b[^}}]*\}}", source
            ):
                report.findings.append(
                    LatexFinding(
                        "MISSING_PACKAGE", f"{package} appears to be required.", command,
                        file=unit.relative_path,
                    )
                )
        for item in analyze_persian_latex(unit.text):
            report.findings.append(
                LatexFinding(
                    item["code"], item["message"], item["suggestion"], file=unit.relative_path
                )
            )
        if unit.text.count("{") != unit.text.count("}"):
            report.findings.append(
                LatexFinding(
                    "UNBALANCED_BRACES",
                    "The source file has unbalanced curly braces.",
                    "Review the nearest LaTeX group before compiling.",
                    severity="error",
                    file=unit.relative_path,
                )
            )
        if len(re.findall(r"\\begin\{(?:tabular|longtable)\}", unit.text)) != len(
            re.findall(r"\\end\{(?:tabular|longtable)\}", unit.text)
        ):
            report.findings.append(
                LatexFinding(
                    "TABLE_ENVIRONMENT_MISMATCH",
                    "A tabular/longtable environment is not opened and closed consistently.",
                    "Match every table environment begin/end pair before compiling.",
                    severity="error",
                    file=unit.relative_path,
                )
            )
    for item in workspace.findings:
        report.findings.append(
            LatexFinding(
                item.code, item.message, item.suggestion, item.line, item.severity, item.file
            )
        )
    log_path = source_path.with_suffix(".log")
    if log_path.is_file():
        for item in parse_latex_log(log_path.read_text(encoding="utf-8", errors="replace")):
            report.findings.append(
                LatexFinding(
                    str(item["code"]), str(item["message"]), str(item["suggestion"]),
                    line=item.get("line"), severity=str(item["severity"]),
                    file=str(item.get("file") or source_path.name),
                )
            )
    context = PluginContext(
        project_root=workspace.root,
        main_file=workspace.main,
        sources=workspace.source_map,
        metadata={"thesis_profile": thesis_profile},
    )
    plugins = plugin_manager or PluginManager().discover()
    if template_adapter_path:
        plugins.plugins.append(load_template_adapter(template_adapter_path))
    for item in plugins.analyze(context):
        report.findings.append(
            LatexFinding(
                item.code, item.message, item.suggestion, item.line, item.severity,
                item.file, item.plugin,
            )
        )
    for error in plugins.load_errors:
        report.findings.append(
            LatexFinding(
                "PLUGIN_LOAD_ERROR", error,
                "Update or remove the incompatible plugin.", severity="warning"
            )
        )
    for position, change in enumerate(report.changes):
        change.change_id = f"tex:{change.file}:{change.line}:{position}"
    report.detected = len(report.changes) + len(report.findings)
    return report


def _apply_latex_changes(
    source: str,
    changes: list[LatexChange],
    *,
    enabled_change_ids: set[str] | None = None,
    change_overrides: dict[str, str] | None = None,
) -> str:
    output = source
    overrides = change_overrides or {}
    for change in sorted(changes, key=lambda item: item.start, reverse=True):
        enabled = enabled_change_ids is None or change.change_id in enabled_change_ids
        if not enabled:
            continue
        replacement = overrides.get(change.change_id, change.after).strip()
        if not replacement or len(replacement) > 100_000:
            raise ValueError(f"Invalid replacement for LaTeX change {change.change_id}")
        if output[change.start:change.end] != change.before:
            raise RuntimeError(
                f"LaTeX source changed after analysis at {change.file}:{change.line}; rescan before repair."
            )
        output = output[:change.start] + replacement + output[change.end:]
        change.after = replacement
        change.applied = True
    return output


def repair_latex(
    input_path: str | os.PathLike[str], output_path: str | os.PathLike[str], *,
    overwrite: bool = False, create_pdf: bool = False, report_path: str | os.PathLike[str] | None = None,
    html_report_path: str | os.PathLike[str] | None = None, language: str = "en",
    thesis_profile: str = "generic",
    template_adapter_path: str | os.PathLike[str] | None = None,
    enabled_change_ids: set[str] | None = None,
    change_overrides: dict[str, str] | None = None,
) -> LatexReport:
    source_path = Path(input_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    if source_path == target:
        raise ValueError("Output must be different from the source file.")
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    report = analyze_latex(
        source_path,
        thesis_profile=thesis_profile,
        template_adapter_path=template_adapter_path,
    )
    source = source_path.read_text(encoding="utf-8", errors="replace")
    main_name = source_path.name
    main_changes = [change for change in report.changes if change.file == main_name]
    repaired = _apply_latex_changes(
        source,
        main_changes,
        enabled_change_ids=enabled_change_ids,
        change_overrides=change_overrides,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=f".{target.stem}-", suffix=".tex", dir=target.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(repaired)
    try:
        os.replace(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)
    report.output_path = str(target)
    report.converted = sum(change.applied for change in report.changes)
    report.skipped = len(report.changes) - report.converted
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


def repair_latex_workspace(
    main_path: str | os.PathLike[str],
    output_directory: str | os.PathLike[str],
    *,
    overwrite: bool = False,
    create_pdf: bool = False,
    report_path: str | os.PathLike[str] | None = None,
    html_report_path: str | os.PathLike[str] | None = None,
    language: str = "en",
    thesis_profile: str = "generic",
    template_adapter_path: str | os.PathLike[str] | None = None,
    enabled_change_ids: set[str] | None = None,
    change_overrides: dict[str, str] | None = None,
) -> LatexReport:
    source_path = Path(main_path).expanduser().resolve()
    workspace = build_latex_workspace(source_path)
    target_root = Path(output_directory).expanduser().resolve()
    if target_root == workspace.root or target_root.parent == workspace.root:
        raise ValueError("Project output directory must be outside the source project root.")
    if target_root.exists() and not target_root.is_dir():
        raise FileExistsError(f"Project output path is not a directory: {target_root}")
    if target_root.exists() and any(target_root.iterdir()) and not overwrite:
        raise FileExistsError(f"Project output directory is not empty: {target_root}")
    target_root.parent.mkdir(parents=True, exist_ok=True)
    report = analyze_latex(
        source_path,
        thesis_profile=thesis_profile,
        template_adapter_path=template_adapter_path,
    )
    staging = Path(tempfile.mkdtemp(prefix=f".{target_root.name}-", dir=target_root.parent))
    backup: Path | None = None
    published = False
    try:
        shutil.copytree(
            workspace.root,
            staging,
            dirs_exist_ok=True,
            symlinks=True,
            ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.aux", "*.toc"),
        )
        changes_by_file: dict[str, list[LatexChange]] = {}
        for change in report.changes:
            changes_by_file.setdefault(change.file, []).append(change)
        for relative, changes in changes_by_file.items():
            output_source = staging / relative
            text = output_source.read_text(encoding="utf-8", errors="replace")
            text = _apply_latex_changes(
                text,
                changes,
                enabled_change_ids=enabled_change_ids,
                change_overrides=change_overrides,
            )
            output_source.write_text(text, encoding="utf-8")
        if create_pdf:
            engine = shutil.which("xelatex")
            if not engine:
                raise RuntimeError("XeLaTeX was not found; project PDF was not created.")
            main_relative = source_path.relative_to(workspace.root)
            process = subprocess.run(
                [engine, "-interaction=nonstopmode", "-halt-on-error", main_relative.name],
                cwd=staging / main_relative.parent,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                check=False,
            )
            built_pdf = staging / main_relative.with_suffix(".pdf")
            if process.returncode != 0 or not built_pdf.is_file():
                raise RuntimeError("XeLaTeX could not build the repaired project. " + process.stdout[-1200:])
        if target_root.exists():
            backup = Path(
                tempfile.mkdtemp(prefix=f".{target_root.name}-backup-", dir=target_root.parent)
            )
            backup.rmdir()
            os.replace(target_root, backup)
        os.replace(staging, target_root)
        published = True
        if backup is not None:
            shutil.rmtree(backup)
        main_relative = source_path.relative_to(workspace.root)
        report.output_path = str(target_root / main_relative)
        report.converted = sum(change.applied for change in report.changes)
        report.skipped = len(report.changes) - report.converted
        if create_pdf:
            report.pdf_path = str(target_root / main_relative.with_suffix(".pdf"))
        report.success = True
        data = report.to_dict()
        if report_path:
            write_json_report(Path(report_path), data)
        if html_report_path:
            write_html_report(Path(html_report_path), data, language=language)
        return report
    except Exception:
        if backup is not None and backup.exists() and not target_root.exists():
            os.replace(backup, target_root)
        raise
    finally:
        if not published and staging.exists():
            shutil.rmtree(staging)
