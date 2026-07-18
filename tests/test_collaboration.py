import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from mathfixer.features.collaboration import create_review_bundle


class CollaborationTests(unittest.TestCase):
    def test_bundle_excludes_sources_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"
            report.write_text(
                json.dumps({"detected": 1, "input_path": "/private/user/thesis.tex"}),
                encoding="utf-8",
            )
            output = root / "review.mfxreview"
            result = create_review_bundle(report, output)
            self.assertFalse(result.includes_sources)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(set(archive.namelist()), {"manifest.json", "report.json"})
                bundled = json.loads(archive.read("report.json"))
                self.assertEqual(bundled["input_path"], "thesis.tex")

    def test_source_requires_explicit_consent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"
            report.write_text("{}", encoding="utf-8")
            source = root / "main.tex"
            source.write_text("text", encoding="utf-8")
            with self.assertRaises(ValueError):
                create_review_bundle(report, root / "review.mfxreview", source_paths=[source])


if __name__ == "__main__":
    unittest.main()
