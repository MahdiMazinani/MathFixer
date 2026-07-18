import unittest

from mathfixer.features.latex_log import parse_latex_log


class LatexLogTests(unittest.TestCase):
    def test_undefined_command_has_line_and_action(self):
        log = "! Undefined control sequence.\nl.152 \\unknowncommand\n"
        findings = parse_latex_log(log)
        self.assertEqual(findings[0]["line"], 152)
        self.assertIn("usepackage", findings[0]["suggestion"])

    def test_nested_project_log_reports_active_file(self):
        log = "(./main.tex\n(./chapters/results.tex\n! Undefined control sequence.\nl.42 \\bad\n)\n)"
        findings = parse_latex_log(log)
        self.assertEqual(findings[0]["file"], "./chapters/results.tex")
        self.assertEqual(findings[0]["line"], 42)


if __name__ == "__main__":
    unittest.main()
