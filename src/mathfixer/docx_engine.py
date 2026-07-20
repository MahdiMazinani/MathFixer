from __future__ import annotations

import copy
import os
import re
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from .core.reporting import write_html_report, write_json_report
from .core.security import UnsafePackageError, parse_xml, validate_ooxml_archive
from .detector import detect_formulas
from .models import (
    ConversionReport,
    ConversionWarning,
    DetectionMode,
    FormulaCandidate,
    PackageSnapshot,
)
from .pandoc_backend import M_NS, NS, W_NS, PandocBackend
from .pdf_export import export_docx_to_pdf

ProgressCallback = Callable[[int, str], None]
WORD_STORY_PATTERN = re.compile(
    r"^word/(?:document|header\d+|footer\d+|footnotes|endnotes|comments)\.xml$"
)
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
W = f"{{{W_NS}}}"
M = f"{{{M_NS}}}"
ALLOWED_RUN_CHILDREN = {f"{W}rPr", f"{W}t"}
# Word may split otherwise ordinary text into many runs and place non-visible,
# recalculable metadata between or inside them. These nodes do not contribute to
# the paragraph text stream and can be discarded when their text is replaced by
# native Office Math. Authored structures such as fields, bookmarks, hyperlinks,
# drawings and hard breaks deliberately remain outside these allow-lists.
DISCARDABLE_RUN_CHILDREN = {f"{W}lastRenderedPageBreak"}
DISCARDABLE_PARAGRAPH_CHILDREN = {f"{W}proofErr"}
INLINE_TEXT_WRAPPERS = {
    f"{W}hyperlink",
    f"{W}smartTag",
    f"{W}ins",
    f"{W}del",
}


class UnsafeDocumentError(UnsafePackageError):
    """Backward-compatible name for unsafe OOXML package failures."""


class ConversionAbortedError(RuntimeError):
    pass


@dataclass(slots=True)
class ScanResult:
    report: ConversionReport
    story_parts: dict[str, bytes]


def _progress(callback: ProgressCallback | None, value: int, message: str) -> None:
    if callback:
        callback(max(0, min(100, value)), message)


def _validate_input(path: Path) -> None:
    if path.suffix.lower() not in {".docx", ".docm"}:
        raise ValueError("Input must be a .docx or .docm file.")
    try:
        validate_ooxml_archive(path)
    except UnsafePackageError as exc:
        raise UnsafeDocumentError(str(exc)) from exc


def _story_names(archive: ZipFile) -> list[str]:
    return sorted(name for name in archive.namelist() if WORD_STORY_PATTERN.match(name))


def _paragraph_child_text(child: etree._Element) -> str:
    """Return the text that contributes offsets for one direct paragraph child."""
    if child.tag == f"{W}r":
        return "".join(child.xpath(".//w:t/text()", namespaces=NS))
    if child.tag in INLINE_TEXT_WRAPPERS:
        return "".join(child.xpath("./w:r//w:t/text()", namespaces=NS))
    return ""


def _paragraph_text(paragraph: etree._Element) -> str:
    # Keep this stream identical to the offsets used by _replace_span. Wrapper text
    # is visible and must consume offset space even though MathFixer will not edit it.
    return "".join(_paragraph_child_text(child) for child in paragraph)


def _count_native_math(root: etree._Element) -> int:
    return len(root.xpath(".//m:oMath", namespaces=NS))


def scan_document(
    input_path: str | os.PathLike[str],
    *,
    mode: DetectionMode = DetectionMode.BALANCED,
    progress: ProgressCallback | None = None,
) -> ScanResult:
    path = Path(input_path).expanduser().resolve()
    _validate_input(path)
    report = ConversionReport(input_path=str(path), mode=mode.value)
    story_parts: dict[str, bytes] = {}
    _progress(progress, 2, "Opening Word package")
    with ZipFile(path) as archive:
        names = _story_names(archive)
        report.scanned_parts = len(names)
        for part_index, name in enumerate(names):
            data = archive.read(name)
            story_parts[name] = data
            try:
                root = parse_xml(data)
            except etree.XMLSyntaxError as exc:
                report.warnings.append(
                    ConversionWarning(code="STORY_XML_INVALID", message=str(exc), part=name)
                )
                continue
            report.already_native += _count_native_math(root)
            paragraphs = root.xpath(".//w:p", namespaces=NS)
            for paragraph_index, paragraph in enumerate(paragraphs):
                report.scanned_paragraphs += 1
                # Existing equations are preserved; ordinary text in the same paragraph may still be scanned.
                text = _paragraph_text(paragraph)
                report.candidates.extend(
                    detect_formulas(
                        text,
                        part=name,
                        paragraph_index=paragraph_index,
                        mode=mode,
                    )
                )
            _progress(
                progress,
                5 + int(35 * (part_index + 1) / max(1, len(names))),
                f"Scanning {name}",
            )
    report.detected = len(report.candidates)
    report.repaired = sum(bool(item.repairs) for item in report.candidates)
    return ScanResult(report=report, story_parts=story_parts)


def _run_is_safe(run: etree._Element) -> bool:
    if run.tag != f"{W}r":
        return False
    return all(
        child.tag in ALLOWED_RUN_CHILDREN or child.tag in DISCARDABLE_RUN_CHILDREN
        for child in run
    )


def _paragraph_child_is_replaceable(child: etree._Element) -> bool:
    return _run_is_safe(child) or child.tag in DISCARDABLE_PARAGRAPH_CHILDREN


def _run_text(run: etree._Element) -> str:
    return "".join(run.xpath(".//w:t/text()", namespaces=NS))


def _clone_run_with_text(run: etree._Element, text: str) -> etree._Element | None:
    if not text:
        return None
    clone = etree.Element(f"{W}r", nsmap=run.nsmap)
    properties = run.find(f"{W}rPr")
    if properties is not None:
        clone.append(copy.deepcopy(properties))
    node = etree.SubElement(clone, f"{W}t")
    node.text = text
    if text[:1].isspace() or text[-1:].isspace():
        node.set(XML_SPACE, "preserve")
    return clone


def _replace_span(
    paragraph: etree._Element,
    candidate: FormulaCandidate,
    omath: etree._Element,
) -> tuple[bool, str, bool]:
    children = list(paragraph)
    cursor = 0
    ranges: list[tuple[int, int, int, etree._Element]] = []
    for index, child in enumerate(children):
        text = _paragraph_child_text(child)
        start = cursor
        cursor += len(text)
        if text and child.tag == f"{W}r":
            ranges.append((start, cursor, index, child))

    first = next((item for item in ranges if item[0] <= candidate.start < item[1]), None)
    last = next((item for item in ranges if item[0] < candidate.end <= item[1]), None)
    if first is None or last is None:
        return False, "formula offsets no longer map to Word text runs", False

    first_start, _, first_index, first_run = first
    last_start, _, last_index, last_run = last
    affected = children[first_index : last_index + 1]
    if not affected or any(not _paragraph_child_is_replaceable(child) for child in affected):
        return False, "formula crosses a field, hyperlink, bookmark, drawing, or complex Word run", False

    # A display equation that owns the complete paragraph is represented by the
    # block-level m:oMathPara element expected by Word. Embedded display markers
    # remain inline so surrounding prose and paragraph properties are preserved.
    block_math = omath.tag == f"{M}oMathPara"
    visible = _paragraph_text(paragraph)
    if block_math and not visible[: candidate.start].strip() and not visible[candidate.end :].strip():
        parent = paragraph.getparent()
        if parent is not None and all(
            child.tag == f"{W}pPr" or _paragraph_child_is_replaceable(child)
            for child in list(paragraph)
        ):
            parent.replace(paragraph, copy.deepcopy(omath))
            return True, "", True
    if block_math:
        inline = omath.find(f"{M}oMath")
        if inline is None:
            return False, "display equation does not contain an Office Math object", False
        omath = inline

    first_text = _run_text(first_run)
    last_text = _run_text(last_run)
    prefix = first_text[: candidate.start - first_start]
    suffix = last_text[candidate.end - last_start :]

    for child in affected:
        paragraph.remove(child)
    insertion = first_index
    prefix_run = _clone_run_with_text(first_run, prefix)
    if prefix_run is not None:
        paragraph.insert(insertion, prefix_run)
        insertion += 1
    paragraph.insert(insertion, copy.deepcopy(omath))
    insertion += 1
    suffix_run = _clone_run_with_text(last_run, suffix)
    if suffix_run is not None:
        paragraph.insert(insertion, suffix_run)
    # Proofing anchors are Word-generated caches without stable identifiers. If
    # one boundary was inside the replaced formula, keeping the other boundary
    # would leave stale proofing markup around ordinary text. Word safely rebuilds
    # these anchors when the document is opened, so remove them from this paragraph.
    for child in list(paragraph):
        if child.tag in DISCARDABLE_PARAGRAPH_CHILDREN:
            paragraph.remove(child)
    return True, "", False


def _snapshot(path: Path, *, story_parts: Iterable[str] = ()) -> PackageSnapshot:
    snapshot = PackageSnapshot()
    story_set = set(story_parts)
    with ZipFile(path) as archive:
        snapshot.entries = set(archive.namelist())
        snapshot.unchanged_crc = {
            item.filename: item.CRC for item in archive.infolist() if item.filename not in story_set
        }
        for name in _story_names(archive):
            try:
                root = parse_xml(archive.read(name))
            except etree.XMLSyntaxError:
                continue
            snapshot.tables += len(root.xpath(".//w:tbl", namespaces=NS))
            snapshot.drawings += len(root.xpath(".//w:drawing", namespaces=NS))
            snapshot.pictures += len(root.xpath(".//w:pict", namespaces=NS))
            snapshot.hyperlinks += len(root.xpath(".//w:hyperlink", namespaces=NS))
            snapshot.bookmarks += len(root.xpath(".//w:bookmarkStart", namespaces=NS))
            snapshot.comments += len(root.xpath(".//w:commentRangeStart", namespaces=NS))
            snapshot.tracked_changes += len(root.xpath(".//w:ins|.//w:del", namespaces=NS))
            snapshot.sections += len(root.xpath(".//w:sectPr", namespaces=NS))
    return snapshot


def _validate_output(
    input_path: Path,
    output_path: Path,
    modified_parts: set[str],
    expected_new_math: int,
) -> dict[str, object]:
    before = _snapshot(input_path, story_parts=modified_parts)
    after = _snapshot(output_path, story_parts=modified_parts)
    structure_fields = (
        "tables",
        "drawings",
        "pictures",
        "hyperlinks",
        "bookmarks",
        "comments",
        "tracked_changes",
        "sections",
    )
    structures = {field: getattr(before, field) == getattr(after, field) for field in structure_fields}
    unchanged_parts = all(
        after.unchanged_crc.get(name) == crc for name, crc in before.unchanged_crc.items()
    )
    package_ok = before.entries == after.entries
    native_math_before = 0
    with ZipFile(input_path) as archive:
        for name in _story_names(archive):
            native_math_before += _count_native_math(parse_xml(archive.read(name)))
    with ZipFile(output_path) as archive:
        bad_member = archive.testzip()
        native_math = 0
        for name in _story_names(archive):
            root = parse_xml(archive.read(name))
            native_math += _count_native_math(root)
    math_delta_ok = native_math - native_math_before == expected_new_math
    valid = package_ok and unchanged_parts and all(structures.values()) and bad_member is None and math_delta_ok
    return {
        "valid": valid,
        "zip_integrity": bad_member is None,
        "entry_set_preserved": package_ok,
        "unmodified_parts_byte_identical": unchanged_parts,
        "structures_preserved": structures,
        "native_math_objects": native_math,
        "native_math_delta": native_math - native_math_before,
        "native_math_delta_valid": math_delta_ok,
        "modified_parts": sorted(modified_parts),
    }


def convert_document(
    input_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    *,
    mode: DetectionMode = DetectionMode.BALANCED,
    enabled_candidate_ids: set[str] | None = None,
    formula_overrides: dict[str, str] | None = None,
    pandoc_path: str | None = None,
    pandoc_timeout: float = 30,
    pandoc_total_timeout: float = 45,
    overwrite: bool = False,
    fail_on_formula_error: bool = True,
    create_pdf: bool = False,
    pdf_output_path: str | os.PathLike[str] | None = None,
    pdf_engine: str = "auto",
    pdf_timeout: int = 180,
    fail_on_pdf_error: bool = True,
    report_path: str | os.PathLike[str] | None = None,
    html_report_path: str | os.PathLike[str] | None = None,
    report_language: str = "en",
    progress: ProgressCallback | None = None,
) -> ConversionReport:
    source = Path(input_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    if source == target:
        raise ValueError("Output must be a different file. MathFixer never overwrites the source document.")
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    scan = scan_document(source, mode=mode, progress=progress)
    report = scan.report
    report.output_path = str(target)
    if enabled_candidate_ids is not None:
        for candidate in report.candidates:
            candidate.enabled = candidate.candidate_id in enabled_candidate_ids
    if formula_overrides:
        for candidate in report.candidates:
            override = formula_overrides.get(candidate.candidate_id)
            if override is not None and override.strip():
                candidate.normalized = override.strip()
                if "edited in preview" not in candidate.repairs:
                    candidate.repairs.append("edited in preview")
    selected = [item for item in report.candidates if item.enabled]
    report.skipped = report.detected - len(selected)
    converted: dict[str, etree._Element] = {}
    warnings: list[ConversionWarning] = []
    if selected:
        _progress(progress, 43, f"Converting {len(selected)} formula(s) to Office Math")
        backend = PandocBackend(
            pandoc_path,
            timeout=pandoc_timeout,
            total_timeout=pandoc_total_timeout,
        )
        report.pandoc_version = backend.version

        def pandoc_progress(done: int, total: int, message: str) -> None:
            value = 43 + int(19 * done / max(1, total))
            _progress(progress, value, message)

        converted, warnings = backend.convert_many(selected, progress=pandoc_progress)
    else:
        report.pandoc_version = "not required (no formulas selected)"
        _progress(progress, 62, "No convertible formulas found; preserving the document")
    report.warnings.extend(warnings)
    missing = [item for item in selected if item.candidate_id not in converted]
    if missing and fail_on_formula_error:
        raise ConversionAbortedError(
            f"Atomic conversion stopped: {len(missing)} formula(s) could not be converted. "
            "The source document was not changed. Review the detected items, disable or correct "
            "the failed candidates, and retry."
        )

    modified: dict[str, bytes] = {}
    by_part: dict[str, list[FormulaCandidate]] = {}
    for candidate in selected:
        if candidate.candidate_id in converted:
            by_part.setdefault(candidate.part, []).append(candidate)

    for part_number, (part, candidates) in enumerate(by_part.items()):
        root = parse_xml(scan.story_parts[part])
        paragraphs = root.xpath(".//w:p", namespaces=NS)
        grouped: dict[int, list[FormulaCandidate]] = {}
        for candidate in candidates:
            grouped.setdefault(candidate.paragraph_index, []).append(candidate)
        for paragraph_index, paragraph_candidates in grouped.items():
            paragraph = paragraphs[paragraph_index]
            before_text = _paragraph_text(paragraph)
            expected_text = before_text
            paragraph_block_replaced = False
            for candidate in sorted(paragraph_candidates, key=lambda item: item.start, reverse=True):
                ok, reason, block_replaced = _replace_span(
                    paragraph, candidate, converted[candidate.candidate_id]
                )
                if ok:
                    expected_text = expected_text[: candidate.start] + expected_text[candidate.end :]
                    paragraph_block_replaced = paragraph_block_replaced or block_replaced
                    report.converted += 1
                else:
                    if fail_on_formula_error:
                        raise ConversionAbortedError(
                            f"Atomic conversion stopped in {part}, paragraph {paragraph_index}: {reason}."
                        )
                    report.skipped += 1
                    report.warnings.append(
                        ConversionWarning(
                            code="UNSAFE_WORD_STRUCTURE",
                            message=reason,
                            part=part,
                            paragraph_index=paragraph_index,
                            formula=candidate.source,
                        )
                    )
            text_preserved = (
                not expected_text.strip()
                if paragraph_block_replaced
                else _paragraph_text(paragraph) == expected_text
            )
            if not text_preserved:
                raise ConversionAbortedError(
                    f"Text-preservation check failed in {part}, paragraph {paragraph_index}."
                )
        modified[part] = etree.tostring(
            root, xml_declaration=True, encoding="UTF-8", standalone=True
        )
        _progress(
            progress,
            64 + int(16 * (part_number + 1) / max(1, len(by_part))),
            f"Patching {part}",
        )

    if selected and report.converted == 0:
        raise ConversionAbortedError("No selected formula could be converted safely.")

    _progress(progress, 82, "Writing an atomic, layout-preserving copy")
    with tempfile.NamedTemporaryFile(
        prefix=f".{target.stem}-", suffix=target.suffix, dir=target.parent, delete=False
    ) as temp_handle:
        temp_path = Path(temp_handle.name)
    pdf_temp_path: Path | None = None
    pdf_target: Path | None = None
    pdf_result = None
    try:
        with ZipFile(source) as original, ZipFile(temp_path, "w") as output:
            for info in original.infolist():
                data = modified.get(info.filename, original.read(info.filename))
                output.writestr(info, data)
        report.validation = _validate_output(source, temp_path, set(modified), report.converted)
        if not report.validation.get("valid"):
            raise ConversionAbortedError("Package-preservation validation failed; no output was published.")
        if create_pdf:
            pdf_target = (
                Path(pdf_output_path).expanduser().resolve()
                if pdf_output_path
                else target.with_suffix(".pdf")
            )
            if pdf_target.exists() and not overwrite:
                raise FileExistsError(pdf_target)
            pdf_target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                prefix=f".{pdf_target.stem}-",
                suffix=".pdf",
                dir=pdf_target.parent,
                delete=False,
            ) as pdf_handle:
                pdf_temp_path = Path(pdf_handle.name)
            try:
                pdf_result = export_docx_to_pdf(
                    temp_path,
                    pdf_temp_path,
                    engine=pdf_engine,
                    overwrite=True,
                    timeout=pdf_timeout,
                    progress=progress,
                )
            except Exception as exc:
                if fail_on_pdf_error:
                    raise
                report.warnings.append(
                    ConversionWarning(
                        code="PDF_EXPORT_FAILED",
                        message=f"The repaired Word file is valid, but PDF export failed: {exc}",
                    )
                )
                if progress:
                    progress(99, "PDF export failed; publishing the validated Word file")
        os.replace(temp_path, target)
        if pdf_result is not None and pdf_temp_path is not None and pdf_target is not None:
            os.replace(pdf_temp_path, pdf_target)
    finally:
        temp_path.unlink(missing_ok=True)
        if pdf_temp_path is not None:
            pdf_temp_path.unlink(missing_ok=True)

    if pdf_result is not None and pdf_target is not None:
        report.pdf_path = str(pdf_target)
        report.pdf_engine = pdf_result.engine
        report.pdf_pages = pdf_result.pages
        report.pdf_size_bytes = pdf_result.size_bytes

    report.success = True
    data = report.to_dict()
    try:
        if report_path:
            write_json_report(Path(report_path), data)
        if html_report_path:
            write_html_report(Path(html_report_path), data, language=report_language)
    except OSError as exc:
        report.warnings.append(
            ConversionWarning(code="REPORT_WRITE_FAILED", message=str(exc))
        )
    _progress(progress, 100, "Conversion and validation completed")
    return report
