import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from mathfixer.features.pdf_compare import compare_pdfs


def write_blank_pdf(path: Path, width: float = 300, height: float = 400) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    with path.open("wb") as handle:
        writer.write(handle)


class PdfCompareTests(unittest.TestCase):
    def test_identical_pdfs_pass_and_emit_audit_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = root / "before.pdf"
            after = root / "after.pdf"
            write_blank_pdf(before)
            write_blank_pdf(after)
            report = compare_pdfs(before, after, root / "diff", dpi=72)
            self.assertTrue(report.passed)
            self.assertEqual(report.changed_ratio, 0)
            self.assertTrue(Path(report.pages[0].image_path).is_file())
            self.assertTrue((root / "diff" / "visual-comparison.json").is_file())

    def test_page_geometry_change_fails_even_when_pages_are_blank(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = root / "before.pdf"
            after = root / "after.pdf"
            write_blank_pdf(before, 300, 400)
            write_blank_pdf(after, 301, 400)
            report = compare_pdfs(before, after, root / "diff", dpi=72)
            self.assertFalse(report.passed)


if __name__ == "__main__":
    unittest.main()
