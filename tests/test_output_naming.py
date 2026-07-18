import tempfile
import unittest
from pathlib import Path

from mathfixer.core.output_naming import choose_available_directory, choose_available_output


class OutputNamingTests(unittest.TestCase):
    def test_existing_output_gets_a_numbered_sibling(self):
        with tempfile.TemporaryDirectory() as directory:
            primary = Path(directory, "article_mathfixed.docx")
            primary.write_bytes(b"existing output")
            self.assertEqual(
                choose_available_output(primary),
                Path(directory, "article_mathfixed_2.docx"),
            )
            self.assertEqual(primary.read_bytes(), b"existing output")

    def test_companion_collision_advances_the_output_name(self):
        with tempfile.TemporaryDirectory() as directory:
            primary = Path(directory, "article_mathfixed.docx")
            primary.with_suffix(".pdf").write_bytes(b"existing PDF")
            second = Path(directory, "article_mathfixed_2.docx")
            second.with_suffix(".report.json").write_text("{}", encoding="utf-8")
            self.assertEqual(
                choose_available_output(
                    primary,
                    companion_suffixes=(".pdf", ".report.json"),
                ),
                Path(directory, "article_mathfixed_3.docx"),
            )

    def test_existing_project_directory_gets_a_numbered_sibling(self):
        with tempfile.TemporaryDirectory() as directory:
            primary = Path(directory, "thesis_mathfixed")
            primary.mkdir()
            self.assertEqual(
                choose_available_directory(primary),
                Path(directory, "thesis_mathfixed_2"),
            )


if __name__ == "__main__":
    unittest.main()
