from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


class AIAnalysisError(RuntimeError):
    pass


@dataclass(slots=True)
class AIFinding:
    title: str
    explanation: str
    suggestion: str
    severity: str = "warning"
    line: int | None = None


def _output_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "\n".join(chunks)


def analyze_latex_with_openai(
    source: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    timeout: int = 90,
) -> list[AIFinding]:
    """Optionally analyze LaTeX through OpenAI's Responses API.

    Source text is sent only when the caller explicitly invokes this function.
    Credentials are read from the process environment and are never persisted.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise AIAnalysisError("Set OPENAI_API_KEY before enabling AI analysis.")
    selected_model = model or os.environ.get("MATHFIXER_AI_MODEL", "gpt-5-mini")
    prompt = (
        "You are a conservative LaTeX diagnostics assistant. Return JSON only as an array of objects "
        "with title, explanation, suggestion, severity, and optional line. Do not rewrite prose. "
        "Report compilation, package, reference, font, bidi, and mathematical syntax problems.\n\n"
        + source[:120_000]
    )
    body = json.dumps({"model": selected_model, "input": prompt}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise AIAnalysisError(f"AI analysis failed: {exc}") from exc
    raw = _output_text(payload).strip()
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
