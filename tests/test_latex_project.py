import tempfile
import unittest
from pathlib import Path

from mathfixer.features.latex_project import analyze_latex, repair_latex


class LatexProjectTests(unittest.TestCase):
    def test_fraction_persian_and_citation_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "thesis.tex")
            source.write_text(r"\documentclass{report}\begin{document}متن $x=\frac12$ \cite{missing}\end{document}", encoding="utf-8")
            report = analyze_latex(source)
            self.assertTrue(any(change.after == r"\frac{1}{2}" for change in report.changes))
            codes = {finding.code for finding in report.findings}
            self.assertIn("PERSIAN_PACKAGE", codes)
            self.assertIn("MISSING_CITATION", codes)

    def test_repair_writes_new_file_and_html_diff(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "input.tex")
            output = Path(directory, "fixed.tex")
            html = Path(directory, "report.html")
            source.write_text("$x=frac12$", encoding="utf-8")
            report = repair_latex(source, output, html_report_path=html)
            self.assertTrue(report.success)
            self.assertEqual(output.read_text(encoding="utf-8"), r"$x=\frac{1}{2}$")
            self.assertIn("Before", html.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
