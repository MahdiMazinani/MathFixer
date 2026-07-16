import unittest

from mathfixer.repair import repair_formula


class RepairTests(unittest.TestCase):
    def test_empty_environment_infers_cases(self):
        source = (
            r"$$E[(X-\mu)^2$$=\begin{} "
            r"a & \text{if } X \text{ is discrete} \\ b & \text{if } X \text{ is continuous}\end{}$$"
        )
        normalized, repairs = repair_formula(source)
        self.assertIn(r"E[(X-\mu)^2]", normalized)
        self.assertIn(r"\begin{cases}", normalized)
        self.assertIn(r"\end{cases}", normalized)
        self.assertIn("inferred missing cases environment name", repairs)

    def test_unmatched_expectation_bracket_is_removed(self):
        source = r"$$E[X^2] - $$E(x)]^2$$"
        normalized, repairs = repair_formula(source)
        self.assertEqual(normalized, r"E[X^2] - E(x)^2")
        self.assertIn("removed unmatched closing bracket", repairs)

    def test_valid_latex_requires_no_repair(self):
        normalized, repairs = repair_formula(r"$\frac{a}{b}$")
        self.assertEqual(normalized, r"\frac{a}{b}")
        self.assertEqual(repairs, [])

    def test_half_open_interval_is_not_repaired(self):
        normalized, repairs = repair_formula(r"$[0, \infty)$")
        self.assertEqual(normalized, r"[0, \infty)")
        self.assertEqual(repairs, [])


if __name__ == "__main__":
    unittest.main()
