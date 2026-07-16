import tempfile
import unittest
from pathlib import Path

from mathfixer.pdf_export import PdfExportError, _validate_pdf


class PdfValidationTests(unittest.TestCase):
    def test_rejects_non_pdf_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "broken.pdf")
            path.write_bytes(b"not a pdf" * 20)
            with self.assertRaises(PdfExportError):
                _validate_pdf(path)

    def test_accepts_minimal_structural_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "minimal.pdf")
            path.write_bytes(b"%PDF-1.4\n1 0 obj<</Type /Page>>endobj\n" + b"x" * 100 + b"\n%%EOF")
            pages, size = _validate_pdf(path)
            self.assertEqual(pages, 1)
            self.assertEqual(size, path.stat().st_size)


if __name__ == "__main__":
    unittest.main()
