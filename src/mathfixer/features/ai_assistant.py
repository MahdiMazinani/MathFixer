from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .ai_providers import (
    AIProvider,
    AIProviderError,
    OpenAIResponsesProvider,
    provider_from_environment,
)


class AIAnalysisError(RuntimeError):
    pass


@dataclass(slots=True)
class AIFinding:
    title: str
    explanation: str
    suggestion: str
    severity: str = "warning"
    line: int | None = None


def analyze_latex_with_provider(
    source: str,
    *,
    provider: AIProvider,
    timeout: int = 90,
) -> list[AIFinding]:
    prompt = (
        "You are a conservative LaTeX diagnostics assistant. Return JSON only as an array of objects "
        "with title, explanation, suggestion, severity, and optional line. Do not rewrite prose. "
        "Report compilation, package, reference, font, bidi, and mathematical syntax problems.\n\n"
        + source[:120_000]
    )
    try:
        raw = provider.complete(prompt, timeout=timeout).strip()
    except AIProviderError as exc:
        raise AIAnalysisError(f"AI analysis failed: {exc}") from exc
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        findings = json.loads(raw)
        if not isinstance(findings, list):
            raise TypeError("response is not a list")
        return [
            AIFinding(
                title=str(item.get("title", "AI finding")),
                explanation=str(item.get("explanation", "")),
                suggestion=str(item.get("suggestion", "")),
                severity=str(item.get("severity", "warning")),
                line=int(item["line"]) if item.get("line") is not None else None,
            )
            for item in findings if isinstance(item, dict)
        ]
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AIAnalysisError("The AI response was not valid structured JSON.") from exc


def analyze_latex_with_openai(
    source: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    timeout: int = 90,
) -> list[AIFinding]:
    """Backward-compatible opt-in OpenAI analysis wrapper."""
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise AIAnalysisError("Set OPENAI_API_KEY before enabling AI analysis.")
    provider = OpenAIResponsesProvider(
        api_key=key,
        model=model or os.environ.get("MATHFIXER_AI_MODEL", "gpt-5-mini"),
        endpoint=os.environ.get("MATHFIXER_AI_ENDPOINT", "https://api.openai.com/v1/responses"),
    )
    return analyze_latex_with_provider(source, provider=provider, timeout=timeout)


def analyze_latex_with_configured_provider(
    source: str,
    *,
    provider_name: str = "openai",
    timeout: int = 90,
) -> list[AIFinding]:
    try:
        provider = provider_from_environment(provider_name)
    except AIProviderError as exc:
        raise AIAnalysisError(f"AI analysis failed: {exc}") from exc
    return analyze_latex_with_provider(
        source,
        provider=provider,
        timeout=timeout,
    )
