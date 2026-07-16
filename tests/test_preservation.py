import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

from mathfixer import DetectionMode, convert_document


CONTENT_TYPES = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
</Types>'''
RELS = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
DOCUMENT = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
  <w:body>
    <w:p><w:r><w:t>Before $x^2 + \\frac{1}{2}$ after</w:t></w:r></w:p>
    <w:tbl><w:tr><w:tc><w:p><w:r><w:t>$$y = \\sqrt{x}$$</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
    <w:sectPr/>
  </w:body>
</w:document>'''
HEADER = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>$r=0.9$</w:t></w:r></w:p></w:hdr>'''


@unittest.skipUnless(shutil.which("pandoc"), "Pandoc is required for the integration test")
class PreservationTests(unittest.TestCase):
    @staticmethod
    def write_source(source: Path) -> bytes:
        media = b"not-a-real-image-but-byte-preservation-matters"
        with ZipFile(source, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", CONTENT_TYPES)
            archive.writestr("_rels/.rels", RELS)
            archive.writestr("word/document.xml", DOCUMENT)
            archive.writestr("word/header1.xml", HEADER)
            archive.writestr("word/media/image1.bin", media)
        return media

    def test_conversion_preserves_package_and_non_math_content(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "source.docx")
            output = Path(directory, "output.docx")
            media = self.write_source(source)

            report = convert_document(source, output, mode=DetectionMode.BALANCED)

            self.assertTrue(report.success)
            self.assertEqual(report.converted, 3)
            self.assertEqual(report.warnings, [])
            self.assertTrue(report.validation["valid"])
            self.assertEqual(report.validation["native_math_objects"], 3)
            with ZipFile(source) as before, ZipFile(output) as after:
                self.assertEqual(set(before.namelist()), set(after.namelist()))
                self.assertEqual(after.read("word/media/image1.bin"), media)
                root = etree.fromstring(after.read("word/document.xml"))
                namespaces = {
                    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
                    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
                }
                ordinary_text = "".join(root.xpath(".//w:t/text()", namespaces=namespaces))
                self.assertEqual(ordinary_text, "Before  after")
                self.assertEqual(len(root.xpath(".//w:tbl", namespaces=namespaces)), 1)
                self.assertEqual(len(root.xpath(".//w:sectPr", namespaces=namespaces)), 1)

    def test_pdf_failure_does_not_publish_partial_docx(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "source.docx")
            output = Path(directory, "output.docx")
            self.write_source(source)
            with patch("mathfixer.docx_engine.export_docx_to_pdf", side_effect=RuntimeError("PDF failed")):
                with self.assertRaises(RuntimeError):
                    convert_document(
                        source,
                        output,
                        mode=DetectionMode.BALANCED,
                        create_pdf=True,
                    )
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix(".pdf").exists())


if __name__ == "__main__":
    unittest.main()
