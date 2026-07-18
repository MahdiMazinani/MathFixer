from __future__ import annotations

import ipaddress
import json
import os
import urllib.error
import urllib.request
from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib.parse import urlparse


class AIProviderError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def _open_without_redirect(request: urllib.request.Request, *, timeout: int):
    return urllib.request.build_opener(_NoRedirect).open(request, timeout=timeout)


@runtime_checkable
class AIProvider(Protocol):
    name: str

    def complete(self, prompt: str, *, timeout: int = 90) -> str: ...


def _validated_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("AI endpoint must be an HTTP(S) URL without embedded credentials.")
    if parsed.scheme == "http":
        hostname = parsed.hostname.lower()
        local = hostname in {"localhost", "127.0.0.1", "::1"}
        with suppress(ValueError):
            local = local or ipaddress.ip_address(hostname).is_private
        if not local:
            raise ValueError("Remote AI endpoints must use HTTPS; HTTP is allowed only for local/private hosts.")
    return endpoint.rstrip("/")


def _request_json(
    url: str,
    body: dict,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 90,
) -> dict:
    request = urllib.request.Request(
        _validated_endpoint(url),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with _open_without_redirect(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise AIProviderError(f"AI provider request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise AIProviderError("AI provider returned a non-object JSON response.")
    return payload


@dataclass(slots=True)
class OpenAIResponsesProvider:
    api_key: str
    model: str = "gpt-5-mini"
    endpoint: str = "https://api.openai.com/v1/responses"
    name: str = "openai"

    def complete(self, prompt: str, *, timeout: int = 90) -> str:
        if not self.api_key:
            raise AIProviderError("OpenAI API key is missing.")
        payload = _request_json(
            self.endpoint,
            {"model": self.model, "input": prompt},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=timeout,
        )
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"]
        chunks: list[str] = []
        for item in payload.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and isinstance(content.get("text"), str):
                    chunks.append(content["text"])
        return "\n".join(chunks)


@dataclass(slots=True)
class OpenAICompatibleProvider:
    endpoint: str
    model: str
    api_key: str = ""
    name: str = "openai-compatible"

    def complete(self, prompt: str, *, timeout: int = 90) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = _request_json(
            self.endpoint,
            {"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            headers=headers,
            timeout=timeout,
        )
        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("Compatible provider response is missing choices[0].message.content.") from exc


@dataclass(slots=True)
class OllamaProvider:
    model: str
    endpoint: str = "http://127.0.0.1:11434/api/generate"
    name: str = "ollama"

    def complete(self, prompt: str, *, timeout: int = 90) -> str:
        payload = _request_json(
            self.endpoint,
            {"model": self.model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=timeout,
        )
        if not isinstance(payload.get("response"), str):
            raise AIProviderError("Ollama response is missing the response field.")
        return payload["response"]


def provider_from_environment(name: str = "openai") -> AIProvider:
    selected = name.strip().lower()
    if selected == "openai":
        return OpenAIResponsesProvider(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=os.environ.get("MATHFIXER_AI_MODEL", "gpt-5-mini"),
            endpoint=os.environ.get("MATHFIXER_AI_ENDPOINT", "https://api.openai.com/v1/responses"),
        )
    if selected in {"compatible", "openai-compatible"}:
        endpoint = os.environ.get("MATHFIXER_AI_ENDPOINT", "")
        model = os.environ.get("MATHFIXER_AI_MODEL", "")
        if not endpoint or not model:
            raise AIProviderError("Set MATHFIXER_AI_ENDPOINT and MATHFIXER_AI_MODEL for a compatible provider.")
        return OpenAICompatibleProvider(
            endpoint=endpoint,
            model=model,
            api_key=os.environ.get("MATHFIXER_AI_API_KEY", ""),
        )
    if selected == "ollama":
        return OllamaProvider(
            model=os.environ.get("MATHFIXER_AI_MODEL", "qwen2.5-coder:7b"),
            endpoint=os.environ.get("MATHFIXER_AI_ENDPOINT", "http://127.0.0.1:11434/api/generate"),
        )
    raise AIProviderError(f"Unknown AI provider: {name}")
