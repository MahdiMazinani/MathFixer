import unittest

from mathfixer.detector import detect_formulas
from mathfixer.models import DetectionMode, FormulaKind


class DetectorTests(unittest.TestCase):
    def detect(self, text, mode=DetectionMode.BALANCED):
        return detect_formulas(text, part="word/document.xml", paragraph_index=0, mode=mode)

    def test_multiple_inline_formulas_do_not_consume_prose(self):
        text = "Correlation is $r = 0.8$, while variables are $X$ and $Y$."
        candidates = self.detect(text)
        self.assertEqual([item.source for item in candidates], ["$r = 0.8$", "$X$", "$Y$"])
        self.assertTrue(all(item.kind is FormulaKind.LATEX_INLINE for item in candidates))

    def test_broken_display_is_one_repaired_candidate(self):
        text = r"$$\text{Diaper} \rightarrow \text{Beer } $$0.5\%, 75\%]$$"
        candidates = self.detect(text)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].kind, FormulaKind.LATEX_BROKEN)
        self.assertEqual(
            candidates[0].normalized,
            r"\text{Diaper} \rightarrow \text{Beer } [0.5\%, 75\%]",
        )

    def test_safe_mode_only_accepts_explicit_delimiters(self):
        self.assertEqual(self.detect("x = y + 1", DetectionMode.SAFE), [])
        self.assertEqual(len(self.detect("$x = y + 1$", DetectionMode.SAFE)), 1)
        self.assertEqual(self.detect(r"$x = y + 1", DetectionMode.SAFE), [])

    def test_balanced_mode_detects_plain_equation(self):
        candidates = self.detect("x = y + 1")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].kind, FormulaKind.PLAIN_EQUATION)

    def test_balanced_mode_normalizes_unicode_math(self):
        candidates = self.detect("σ² = √(x) ≤ ∑ xᵢ")
        self.assertEqual(len(candidates), 1)
        self.assertIn(r"\sigma ^{2}", candidates[0].normalized)
        self.assertIn(r"\sqrt{x}", candidates[0].normalized)
        self.assertIn(r"x_{i}", candidates[0].normalized)

    def test_balanced_mode_detects_standalone_unicode_math(self):
        candidates = self.detect("σ² + √x + ∑xᵢ")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].kind, FormulaKind.UNICODE_MATH)

    def test_regular_persian_prose_is_not_math(self):
        text = "این پاراگراف درباره داده‌کاوی، میانگین و تحلیل آماری توضیح می‌دهد."
        self.assertEqual(self.detect(text), [])


if __name__ == "__main__":
    unittest.main()
