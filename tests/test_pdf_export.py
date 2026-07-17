import tempfile
import unittest
from pathlib import Path

from mathfixer.pdf_export import PdfExportError, _validate_pdf, export_docx_to_pdf


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

    def test_docm_rejects_libreoffice_to_prevent_macro_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "unsafe.docm")
            source.write_bytes(b"placeholder")
            with self.assertRaisesRegex(PdfExportError, "requires Microsoft Word"):
                export_docx_to_pdf(source, Path(directory, "out.pdf"), engine="libreoffice")


if __name__ == "__main__":
    unittest.main()
