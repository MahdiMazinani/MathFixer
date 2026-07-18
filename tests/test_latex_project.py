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

    def test_html_report_includes_diagnostics_and_exact_location(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "input.tex")
            output = Path(directory, "fixed.tex")
            html = Path(directory, "report.html")
            source.write_text(r"\cite{missing}", encoding="utf-8")
            repair_latex(source, output, html_report_path=html)
            report = html.read_text(encoding="utf-8")
            self.assertIn("MISSING_CITATION", report)
            self.assertIn("input.tex:1", report)

    def test_user_opt_out_and_override_are_applied_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "input.tex")
            source.write_text(r"$\frac12$ and $\frac34$", encoding="utf-8")
            scan = analyze_latex(source)
            first, second = scan.changes
            output = Path(directory, "fixed.tex")
            report = repair_latex(
                source,
                output,
                enabled_change_ids={second.change_id},
                change_overrides={second.change_id: r"\frac{30}{40}"},
            )
            self.assertEqual(output.read_text(encoding="utf-8"), r"$\frac12$ and $\frac{30}{40}$")
            self.assertFalse(report.changes[0].applied)
            self.assertTrue(report.changes[1].applied)
            self.assertEqual(report.converted, 1)
            self.assertEqual(report.skipped, 1)


if __name__ == "__main__":
    unittest.main()
