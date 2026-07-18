import tempfile
import unittest
from pathlib import Path

from mathfixer import API_VERSION, scan


class PublicApiTests(unittest.TestCase):
    def test_v2_scan_contract_handles_latex_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "main.tex")
            source.write_text(r"$\frac12$", encoding="utf-8")
            report = scan(source)
            self.assertEqual(API_VERSION, "2.0")
            self.assertEqual(report.changes[0].after, r"\frac{1}{2}")


if __name__ == "__main__":
    unittest.main()
