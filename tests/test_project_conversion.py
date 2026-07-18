import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from mathfixer.features.project_conversion import latex_project_to_word, word_to_latex_project


@unittest.skipUnless(shutil.which("pandoc"), "Pandoc is required for project conversion tests")
class ProjectConversionTests(unittest.TestCase):
    def test_word_latex_word_round_trip_keeps_project_media(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "plot.png"
            Image.new("RGB", (20, 12), (20, 110, 180)).save(image)
            markdown = root / "article.md"
            markdown.write_text("# Result\n\n![Plot](plot.png)\n\n$x^2 + y^2$", encoding="utf-8")
            source = root / "article.docx"
            created = subprocess.run(
                [shutil.which("pandoc"), str(markdown), "-o", str(source)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr)

            project = word_to_latex_project(source, root / "latex-project")

            self.assertTrue(Path(project.output_path).is_file())
            self.assertTrue(project.media_files)
            self.assertTrue(all((root / "latex-project" / item).is_file() for item in project.media_files))

            word = latex_project_to_word(project.output_path, root / "roundtrip.docx")
            self.assertTrue(Path(word.output_path).is_file())


if __name__ == "__main__":
    unittest.main()
