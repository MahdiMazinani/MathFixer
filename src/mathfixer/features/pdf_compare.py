from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..core.reporting import write_json_report


class PdfComparisonError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PageVisualDiff:
    page: int
    changed_ratio: float
    maximum_delta: int
    image_path: str
    before_size: tuple[int, int]
    after_size: tuple[int, int]


@dataclass(slots=True)
class PdfVisualReport:
    before_path: str
    after_path: str
    threshold: int
    tolerance: float
    pages: list[PageVisualDiff] = field(default_factory=list)
    changed_ratio: float = 0.0
    passed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _canvas(image, size):
    from PIL import Image

    if image.size == size:
        return image.convert("RGB")
    canvas = Image.new("RGB", size, "white")
    canvas.paste(image.convert("RGB"), (0, 0))
    return canvas


def _compare_images(before, after, *, threshold: int):
    from PIL import Image, ImageChops, ImageEnhance

    size = (max(before.width, after.width), max(before.height, after.height))
    left = _canvas(before, size)
    right = _canvas(after, size)
    difference = ImageChops.difference(left, right)
    gray = difference.convert("L")
    mask = gray.point(lambda value: 255 if value > threshold else 0)
    histogram = mask.histogram()
    changed = histogram[255]
    ratio = changed / max(1, size[0] * size[1])
    maximum = max(channel[1] for channel in difference.getextrema())
    emphasized = ImageEnhance.Contrast(difference).enhance(2.5)
    red = Image.new("RGB", size, (239, 68, 68))
    heatmap = right.copy()
    heatmap.paste(red, mask=mask)
    heatmap = Image.blend(heatmap, emphasized, 0.22)
    return ratio, maximum, heatmap


def _render_pages(path: Path, *, dpi: int):
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise PdfComparisonError(
            "Visual comparison requires pypdfium2. Install MathFixer with its visual dependencies."
        ) from exc
    try:
        document = pdfium.PdfDocument(str(path))
        scale = dpi / 72
        if len(document) > 500:
            raise PdfComparisonError("PDF has more than the 500-page comparison limit.")
        images = []
        try:
            for index in range(len(document)):
                page = document[index]
                try:
                    width, height = page.get_size()
                    if width * scale * height * scale > 50_000_000:
                        raise PdfComparisonError(
                            f"Page {index + 1} exceeds the 50-megapixel render limit."
                        )
                    bitmap = page.render(scale=scale)
                    try:
                        images.append(bitmap.to_pil().convert("RGB"))
                    finally:
                        bitmap.close()
                finally:
                    page.close()
        finally:
            document.close()
    except Exception as exc:
        raise PdfComparisonError(f"Could not render PDF {path.name}: {exc}") from exc
    if not images:
        raise PdfComparisonError(f"PDF contains no renderable pages: {path}")
    return images


def compare_pdfs(
    before_path: str | Path,
    after_path: str | Path,
    output_directory: str | Path,
    *,
    dpi: int = 120,
    threshold: int = 12,
    tolerance: float = 0.002,
) -> PdfVisualReport:
    before = Path(before_path).expanduser().resolve()
    after = Path(after_path).expanduser().resolve()
    output = Path(output_directory).expanduser().resolve()
    for path in (before, after):
        if path.suffix.lower() != ".pdf" or not path.is_file():
            raise ValueError("Visual comparison requires two existing PDF files.")
    if not 72 <= dpi <= 300:
        raise ValueError("dpi must be between 72 and 300.")
    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be between 0 and 255.")
    if not 0 <= tolerance <= 1:
        raise ValueError("tolerance must be between 0 and 1.")
    output.mkdir(parents=True, exist_ok=True)
    before_pages = _render_pages(before, dpi=dpi)
    after_pages = _render_pages(after, dpi=dpi)
    count = max(len(before_pages), len(after_pages))
    from PIL import Image

    results: list[PageVisualDiff] = []
    weighted_changed = 0.0
    total_pixels = 0
    for index in range(count):
        left = before_pages[index] if index < len(before_pages) else Image.new(
            "RGB", after_pages[index].size, "white"
        )
        right = after_pages[index] if index < len(after_pages) else Image.new(
            "RGB", before_pages[index].size, "white"
        )
        ratio, maximum, heatmap = _compare_images(left, right, threshold=threshold)
        image_path = output / f"page-{index + 1:03d}-diff.png"
        heatmap.save(image_path, format="PNG", optimize=True)
        pixels = max(left.width, right.width) * max(left.height, right.height)
        weighted_changed += ratio * pixels
        total_pixels += pixels
        results.append(
            PageVisualDiff(
                index + 1,
                ratio,
                maximum,
                str(image_path),
                left.size,
                right.size,
            )
        )
    report = PdfVisualReport(
        str(before),
        str(after),
        threshold,
        tolerance,
        results,
        weighted_changed / max(1, total_pixels),
    )
    same_geometry = all(page.before_size == page.after_size for page in results)
    report.passed = (
        len(before_pages) == len(after_pages)
        and same_geometry
        and report.changed_ratio <= tolerance
    )
    write_json_report(output / "visual-comparison.json", report.to_dict())
    return report
