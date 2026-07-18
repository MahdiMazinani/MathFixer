import tempfile
import unittest
from pathlib import Path

from mathfixer.features.latex_project import analyze_latex, repair_latex_workspace
from mathfixer.features.latex_workspace import build_latex_workspace


class LatexWorkspaceTests(unittest.TestCase):
    def test_cross_file_references_citations_and_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chapters").mkdir()
            main = root / "main.tex"
            main.write_text(
                r"\input{chapters/results}\bibliography{references}\ref{eq:missing}",
                encoding="utf-8",
            )
            (root / "chapters" / "results.tex").write_text(
                "first\n" + r"$x=\frac\alpha\beta$ \cite{missing-key}",
                encoding="utf-8",
            )
            (root / "references.bib").write_text("@article{present, title={T}}", encoding="utf-8")

            report = analyze_latex(main)

            change = next(item for item in report.changes if item.file == "chapters/results.tex")
            self.assertEqual(change.line, 2)
            self.assertEqual(change.after, r"\frac{\alpha}{\beta}")
            missing_citation = next(item for item in report.findings if item.code == "MISSING_CITATION")
            self.assertEqual(missing_citation.file, "chapters/results.tex")
            self.assertEqual(missing_citation.line, 2)
            self.assertTrue(any(item.code == "MISSING_REFERENCE" for item in report.findings))

    def test_include_cannot_leave_project_root(self):
        with tempfile.TemporaryDirectory() as directory:
            main = Path(directory, "main.tex")
            main.write_text(r"\input{../secret}", encoding="utf-8")
            workspace = build_latex_workspace(main)
            self.assertEqual([item.code for item in workspace.findings], ["UNSAFE_INCLUDE"])

    def test_project_repair_updates_included_files_in_a_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            source.mkdir()
            main = source / "main.tex"
            main.write_text(r"\input{chapter}", encoding="utf-8")
            (source / "chapter.tex").write_text(r"$\frac12$", encoding="utf-8")
            output = base / "fixed"

            report = repair_latex_workspace(main, output)

            self.assertTrue(report.success)
            self.assertEqual((output / "chapter.tex").read_text(encoding="utf-8"), r"$\frac{1}{2}$")
            self.assertEqual((source / "chapter.tex").read_text(encoding="utf-8"), r"$\frac12$")


if __name__ == "__main__":
    unittest.main()
