import unittest
from unittest.mock import patch

from mathfixer.features.ai_assistant import (
    AIAnalysisError,
    analyze_latex_with_configured_provider,
    analyze_latex_with_provider,
)
from mathfixer.features.ai_providers import _validated_endpoint


class FakeProvider:
    name = "fake"

    def complete(self, prompt: str, *, timeout: int = 90) -> str:
        self.prompt = prompt
        return '[{"title":"Issue","explanation":"Why","suggestion":"Fix","severity":"warning","line":7}]'


class AIProviderTests(unittest.TestCase):
    def test_provider_boundary_parses_structured_findings(self):
        provider = FakeProvider()
        findings = analyze_latex_with_provider("$x$", provider=provider)
        self.assertEqual(findings[0].line, 7)
        self.assertIn("conservative LaTeX", provider.prompt)

    def test_remote_http_is_rejected_but_local_http_is_allowed(self):
        self.assertEqual(
            _validated_endpoint("http://127.0.0.1:11434/api/generate"),
            "http://127.0.0.1:11434/api/generate",
        )
        with self.assertRaises(ValueError):
            _validated_endpoint("http://example.com/v1/chat/completions")

    def test_missing_private_provider_configuration_uses_public_analysis_error(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            self.assertRaises(AIAnalysisError),
        ):
            analyze_latex_with_configured_provider("$x$", provider_name="openai-compatible")


if __name__ == "__main__":
    unittest.main()
