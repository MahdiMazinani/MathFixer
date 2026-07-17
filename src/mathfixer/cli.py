from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .docx_engine import convert_document, scan_document
from .features.latex_project import analyze_latex, repair_latex
from .features.word_to_latex import export_word_to_latex
from .models import DetectionMode
from .pandoc_backend import PandocBackend, PandocNotFoundError
from .plugins.thesis import THESIS_PROFILES


def _mode(value: str) -> DetectionMode:
    try:
        return DetectionMode(value.lower())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("mode must be safe, balanced, or aggressive") from exc


def _progress(value: int, message: str) -> None:
    if sys.stderr.isatty():
        print(f"\r[{value:3d}%] {message:<64}", end="", file=sys.stderr, flush=True)
        if value == 100:
            print(file=sys.stderr)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mathfixer",
        description="Repair formulas and scientific documents across Word, LaTeX, and Persian thesis workflows.",
    )
    parser.add_argument("--version", action="version", version=f"MathFixer {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    scan = subparsers.add_parser("scan", help="detect Word formulas or LaTeX project issues without writing output")
    scan.add_argument("input", type=Path)
    scan.add_argument("--mode", type=_mode, default=DetectionMode.BALANCED)
    scan.add_argument("--json", dest="json_path", type=Path, help="write the full scan report")
    scan.add_argument("--thesis-profile", choices=[item.key for item in THESIS_PROFILES], default="generic")

    convert = subparsers.add_parser("convert", help="repair one or more DOCX, DOCM, or TEX documents")
    convert.add_argument("inputs", nargs="+", type=Path)
    convert.add_argument("--output-dir", "-o", type=Path)
    convert.add_argument("--suffix", default="_mathfixed")
    convert.add_argument("--mode", type=_mode, default=DetectionMode.BALANCED)
    convert.add_argument("--pandoc", type=str)
    convert.add_argument("--overwrite", action="store_true")
    convert.add_argument(
        "--continue-on-error",
        action="store_true",
        help="publish successfully converted formulas even when another formula fails",
    )
    convert.add_argument("--report", action="store_true", help="write HTML and JSON reports next to each output")
    convert.add_argument("--pdf", action="store_true", help="also export a PDF from the repaired DOCX")
    convert.add_argument(
        "--pdf-engine",
        choices=["auto", "word", "libreoffice"],
        default="auto",
        help="PDF engine; auto prefers Microsoft Word on Windows",
    )
    convert.add_argument("--quiet", action="store_true")
    convert.add_argument("--thesis-profile", choices=[item.key for item in THESIS_PROFILES], default="generic")

    word_to_latex = subparsers.add_parser("word-to-latex", help="export a Word document to standalone LaTeX")
    word_to_latex.add_argument("input", type=Path)
    word_to_latex.add_argument("output", type=Path)
    word_to_latex.add_argument("--pandoc", type=str)

    subparsers.add_parser("doctor", help="check runtime dependencies")
    subparsers.add_parser("gui", help="launch the desktop interface")
    return parser


def _launch_gui() -> int:
    try:
        from .gui import run
    except ImportError as exc:
        print(
            "The desktop dependency is missing. Install it with: pip install 'mathfixer[gui]'",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 2
    return run()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command in {None, "gui"}:
        return _launch_gui()
    if args.command == "doctor":
        print(f"MathFixer: {__version__}")
        print(f"Python: {sys.version.split()[0]}")
        try:
            backend = PandocBackend()
            print(f"Pandoc: {backend.version} ({backend.executable})")
        except PandocNotFoundError as exc:
            print(f"Pandoc: MISSING — {exc}")
            return 1
        print("Core: ready")
        return 0
    if args.command == "word-to-latex":
        output = export_word_to_latex(args.input, args.output, pandoc_path=args.pandoc)
        print(f"OK  {args.input} -> {output}")
        return 0
    if args.command == "scan":
        if args.input.suffix.lower() == ".tex":
            report = analyze_latex(args.input, thesis_profile=args.thesis_profile)
            print(f"{args.input.name}: {report.detected} issue(s), {len(report.changes)} automatic repair(s)")
            for change in report.changes:
                print(f"  line {change.line}: {change.before!r} -> {change.after!r} ({change.reason})")
            for finding in report.findings:
                print(f"  {finding.severity.upper()} {finding.code}: {finding.message}")
            if args.json_path:
                args.json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            return 0
        report = scan_document(args.input, mode=args.mode, progress=_progress).report
        print(
            f"{report.input_name}: {report.detected} candidate(s), "
            f"{report.repaired} repaired, {report.already_native} already native"
        )
        for candidate in report.candidates:
            repairs = "; ".join(candidate.repairs) or "none"
            print(
                f"  p{candidate.paragraph_index + 1:<4} {candidate.kind.value:<18} "
                f"{candidate.confidence:>5.0%}  {candidate.source[:90]!r}  repairs={repairs}"
            )
        if args.json_path:
            args.json_path.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return 0

    failures = 0
    for input_path in args.inputs:
        output_dir = (args.output_dir or input_path.parent).resolve()
        output = output_dir / f"{input_path.stem}{args.suffix}{input_path.suffix.lower()}"
        report_path = output.with_suffix(".report.json") if args.report else None
        html_report_path = output.with_suffix(".report.html") if args.report else None
        try:
            if input_path.suffix.lower() == ".tex":
                report = repair_latex(
                    input_path,
                    output,
                    overwrite=args.overwrite,
                    create_pdf=args.pdf,
                    report_path=report_path,
                    html_report_path=html_report_path,
                    thesis_profile=args.thesis_profile,
                )
                print(f"OK  {input_path.name} -> {output} ({report.converted}/{report.detected} repaired)")
                continue
            report = convert_document(
                input_path,
                output,
                mode=args.mode,
                pandoc_path=args.pandoc,
                overwrite=args.overwrite,
                fail_on_formula_error=not args.continue_on_error,
                create_pdf=args.pdf,
                pdf_engine=args.pdf_engine,
                report_path=report_path,
                html_report_path=html_report_path,
                progress=None if args.quiet else _progress,
            )
            print(
                f"OK  {input_path.name} -> {output} "
                f"({report.converted}/{report.detected} converted, {len(report.warnings)} warning(s))"
            )
            if report.pdf_path:
                print(f"PDF {report.pdf_path} ({report.pdf_pages or '?'} page(s), {report.pdf_engine})")
        except Exception as exc:  # CLI boundary: report a clean per-file error and keep the batch moving.
            failures += 1
            print(f"ERROR  {input_path}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
