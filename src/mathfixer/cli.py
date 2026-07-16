from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .docx_engine import convert_document, scan_document
from .models import DetectionMode
from .pandoc_backend import PandocBackend, PandocNotFoundError


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
        description="Convert damaged LaTeX/UnicodeMath in Word to native Office Math without rebuilding the document.",
    )
    parser.add_argument("--version", action="version", version=f"MathFixer {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    scan = subparsers.add_parser("scan", help="detect formulas without writing a DOCX")
    scan.add_argument("input", type=Path)
    scan.add_argument("--mode", type=_mode, default=DetectionMode.BALANCED)
    scan.add_argument("--json", dest="json_path", type=Path, help="write the full scan report")

    convert = subparsers.add_parser("convert", help="convert one or more Word documents")
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
    convert.add_argument("--report", action="store_true", help="write a JSON report next to each output")
    convert.add_argument("--pdf", action="store_true", help="also export a PDF from the repaired DOCX")
    convert.add_argument(
        "--pdf-engine",
        choices=["auto", "word", "libreoffice"],
        default="auto",
        help="PDF engine; auto prefers Microsoft Word on Windows",
    )
    convert.add_argument("--quiet", action="store_true")

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
    if args.command == "scan":
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
        try:
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
