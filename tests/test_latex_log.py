import unittest

from mathfixer.features.latex_log import parse_latex_log


class LatexLogTests(unittest.TestCase):
    def test_undefined_command_has_line_and_action(self):
        log = "! Undefined control sequence.\nl.152 \\unknowncommand\n"
        findings = parse_latex_log(log)
        self.assertEqual(findings[0]["line"], 152)
        self.assertIn("usepackage", findings[0]["suggestion"])


if __name__ == "__main__":
    unittest.main()
