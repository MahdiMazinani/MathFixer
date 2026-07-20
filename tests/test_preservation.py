import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

from mathfixer import DetectionMode, convert_document
from mathfixer.docx_engine import _invalid_word_omml_placements, _validate_output

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
    def write_source(source: Path, document: bytes = DOCUMENT, header: bytes = HEADER) -> bytes:
        media = b"not-a-real-image-but-byte-preservation-matters"
        with ZipFile(source, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", CONTENT_TYPES)
            archive.writestr("_rels/.rels", RELS)
            archive.writestr("word/document.xml", document)
            archive.writestr("word/header1.xml", header)
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
            self.assertTrue(report.validation["word_omml_placement_valid"])
            self.assertEqual(report.validation["invalid_omml_placements"], [])
            self.assertTrue(report.validation["content_types_preserved"])
            self.assertTrue(report.validation["relationships_preserved"])
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
                self.assertEqual(len(root.xpath(".//m:oMathPara", namespaces=namespaces)), 1)
                self.assertEqual(
                    len(root.xpath(".//w:p/m:oMathPara", namespaces=namespaces)),
                    1,
                )
                self.assertEqual(_invalid_word_omml_placements(root), [])

    def test_word_incompatible_math_outside_paragraph_is_detected(self):
        invalid = etree.fromstring(
            b'''<w:document
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
  <w:body><m:oMathPara><m:oMath/></m:oMathPara></w:body>
</w:document>'''
        )

        issues = _invalid_word_omml_placements(invalid)

        self.assertEqual([etree.QName(node).localname for node in issues], ["oMathPara", "oMath"])

    def test_word_incompatible_math_blocks_output_validation(self):
        plain_document = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
  <w:body><w:p><w:r><w:t>$$x^2$$</w:t></w:r></w:p><w:sectPr/></w:body>
</w:document>'''
        incompatible_document = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
  <w:body><m:oMathPara><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></m:oMathPara><w:sectPr/></w:body>
</w:document>'''
        plain_header = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p><w:r><w:t>Ordinary header.</w:t></w:r></w:p>
</w:hdr>'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "source.docx")
            output = Path(directory, "incompatible.docx")
            self.write_source(source, plain_document, plain_header)
            self.write_source(output, incompatible_document, plain_header)

            validation = _validate_output(
                source,
                output,
                {"word/document.xml"},
                expected_new_math=1,
            )

            self.assertFalse(validation["valid"])
            self.assertFalse(validation["word_omml_placement_valid"])
            self.assertEqual(
                validation["invalid_omml_placements"],
                ["word/document.xml:oMathPara", "word/document.xml:oMath"],
            )

    def test_pdf_failure_does_not_publish_partial_docx(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "source.docx")
            output = Path(directory, "output.docx")
            self.write_source(source)
            with (
                patch("mathfixer.docx_engine.export_docx_to_pdf", side_effect=RuntimeError("PDF failed")),
                self.assertRaises(RuntimeError),
            ):
                convert_document(
                    source,
                    output,
                    mode=DetectionMode.BALANCED,
                    create_pdf=True,
                )
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix(".pdf").exists())

    def test_nonfatal_pdf_failure_keeps_validated_docx_and_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "source.docx")
            output = Path(directory, "output.docx")
            self.write_source(source)
            with patch(
                "mathfixer.docx_engine.export_docx_to_pdf",
                side_effect=RuntimeError("PDF engine timed out"),
            ):
                report = convert_document(
                    source,
                    output,
                    mode=DetectionMode.BALANCED,
                    create_pdf=True,
                    fail_on_pdf_error=False,
                )
            self.assertTrue(output.exists())
            self.assertFalse(output.with_suffix(".pdf").exists())
            self.assertTrue(report.success)
            self.assertEqual(report.warnings[-1].code, "PDF_EXPORT_FAILED")

    def test_document_without_formulas_never_starts_pandoc(self):
        plain_document = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Ordinary text without a formula.</w:t></w:r></w:p><w:sectPr/></w:body>
</w:document>'''
        plain_header = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p><w:r><w:t>Ordinary header.</w:t></w:r></w:p>
</w:hdr>'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "plain.docx")
            output = Path(directory, "plain_mathfixed.docx")
            self.write_source(source, plain_document, plain_header)
            with patch(
                "mathfixer.docx_engine.PandocBackend",
                side_effect=AssertionError("Pandoc must not run"),
            ):
                report = convert_document(source, output)
            self.assertTrue(report.success)
            self.assertEqual(report.detected, 0)
            self.assertEqual(report.pandoc_version, "not required (no formulas selected)")
            self.assertTrue(output.exists())

    def test_inline_wrapper_before_formula_does_not_shift_replacement_offsets(self):
        wrapped_document = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p>
      <w:hyperlink r:id="rId9"><w:r><w:t>Link</w:t></w:r></w:hyperlink>
      <w:r><w:t> before $x^2 + \\frac{1}{2}$ and ordinary trailing text.</w:t></w:r>
    </w:p>
    <w:sectPr/>
  </w:body>
</w:document>'''
        plain_header = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p><w:r><w:t>Ordinary header.</w:t></w:r></w:p>
</w:hdr>'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "wrapped.docx")
            output = Path(directory, "wrapped_mathfixed.docx")
            self.write_source(source, wrapped_document, plain_header)

            report = convert_document(source, output, mode=DetectionMode.BALANCED)

            self.assertTrue(report.success)
            self.assertEqual(report.converted, 1)
            with ZipFile(output) as archive:
                root = etree.fromstring(archive.read("word/document.xml"))
            text = "".join(root.xpath(".//w:t/text()", namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}))
            self.assertEqual(text, "Link before  and ordinary trailing text.")

    def test_word_generated_proofing_and_layout_markers_do_not_block_conversion(self):
        generated_metadata_document = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
  <w:body>
    <w:p>
      <w:r><w:lastRenderedPageBreak/><w:t>Before $x^</w:t></w:r>
      <w:proofErr w:type="spellStart"/>
      <w:r><w:t>2 + \\frac</w:t></w:r>
      <w:proofErr w:type="spellEnd"/>
      <w:r><w:t>{1}{2}$ after</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>$$y =</w:t></w:r>
      <w:proofErr w:type="spellStart"/>
      <w:r><w:t> \\sqrt{x}</w:t></w:r>
      <w:proofErr w:type="spellEnd"/>
      <w:r><w:t>$$</w:t></w:r>
    </w:p>
    <w:sectPr/>
  </w:body>
</w:document>'''
        plain_header = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p><w:r><w:t>Ordinary header.</w:t></w:r></w:p>
</w:hdr>'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "generated-metadata.docx")
            output = Path(directory, "generated-metadata_mathfixed.docx")
            self.write_source(source, generated_metadata_document, plain_header)

            report = convert_document(source, output, mode=DetectionMode.BALANCED)

            self.assertTrue(report.success)
            self.assertEqual(report.detected, 2)
            self.assertEqual(report.converted, 2)
            self.assertEqual(report.skipped, 0)
            self.assertEqual(report.warnings, [])
            with ZipFile(output) as archive:
                root = etree.fromstring(archive.read("word/document.xml"))
            namespaces = {
                "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
                "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
            }
            text = "".join(root.xpath(".//w:t/text()", namespaces=namespaces))
            self.assertEqual(text, "Before  after")
            self.assertEqual(len(root.xpath(".//m:oMath", namespaces=namespaces)), 2)
            self.assertEqual(len(root.xpath(".//w:proofErr", namespaces=namespaces)), 0)

    def test_non_atomic_mode_preserves_a_formula_that_is_unsafe_to_replace(self):
        mixed_document = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p>
      <w:hyperlink r:id="rId9"><w:r><w:t>$a+b$</w:t></w:r></w:hyperlink>
      <w:r><w:t> remains linked; convert $x^2 + \\frac{1}{2}$ safely.</w:t></w:r>
    </w:p>
    <w:sectPr/>
  </w:body>
</w:document>'''
        plain_header = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p><w:r><w:t>Ordinary header.</w:t></w:r></w:p>
</w:hdr>'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "mixed.docx")
            output = Path(directory, "mixed_mathfixed.docx")
            self.write_source(source, mixed_document, plain_header)

            report = convert_document(
                source,
                output,
                mode=DetectionMode.BALANCED,
                fail_on_formula_error=False,
            )

            self.assertTrue(report.success)
            self.assertEqual(report.converted, 1)
            self.assertEqual(report.skipped, 1)
            self.assertEqual(report.warnings[0].code, "UNSAFE_WORD_STRUCTURE")
            with ZipFile(output) as archive:
                root = etree.fromstring(archive.read("word/document.xml"))
            namespaces = {
                "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
                "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
            }
            text = "".join(root.xpath(".//w:t/text()", namespaces=namespaces))
            self.assertEqual(text, "$a+b$ remains linked; convert  safely.")
            self.assertEqual(len(root.xpath(".//m:oMath", namespaces=namespaces)), 1)


if __name__ == "__main__":
    unittest.main()
