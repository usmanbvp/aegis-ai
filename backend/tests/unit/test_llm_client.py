from __future__ import annotations

import json

import httpx
import pytest

from app.config import Settings
from app.llm import LLMError, LLMProvider, ResilientLLMClient, configured_providers


def test_configured_providers_prioritize_primary_and_skip_missing_keys() -> None:
    settings = Settings(
        groq_api_key="groq-test-key",
        gemini_api_key="gemini-test-key",
        llm_primary_provider="gemini",
    )

    providers = configured_providers(settings)

    assert [provider.name for provider in providers] == ["gemini", "groq"]
    assert providers[0].model == settings.gemini_model


def test_provider_client_sends_auth_and_parses_json() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["url"] = str(request.url)
        observed["authorization"] = request.headers.get("Authorization")
        observed["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"status":"ok"}'}}]},
        )

    provider = LLMProvider(
        "groq", "https://api.groq.com/openai/v1", "private-test-key", "test-model"
    )
    client = ResilientLLMClient([provider], transport=httpx.MockTransport(handler))

    result = client.complete([{"role": "user", "content": "check"}])

    assert observed["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert observed["authorization"] == "Bearer private-test-key"
    assert observed["payload"]["model"] == "test-model"
    assert observed["payload"]["response_format"] == {"type": "json_object"}
    assert result.content == {"status": "ok"}
    assert result.provider == "groq"


def test_provider_failover_does_not_expose_credentials_or_provider_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "groq.com" in str(request.url):
            return httpx.Response(401, json={"error": {"message": "secret response content"}})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"status":"ok"}'}}]},
        )

    providers = [
        LLMProvider("groq", "https://api.groq.com/openai/v1", "groq-secret", "model-a"),
        LLMProvider("gemini", "https://example.test/v1", "gemini-secret", "model-b"),
    ]
    client = ResilientLLMClient(providers, max_retries=0, transport=httpx.MockTransport(handler))

    result = client.complete([{"role": "user", "content": "check"}])

    assert result.provider == "gemini"
    assert result.content == {"status": "ok"}


def test_provider_invalid_json_is_reported_without_echoing_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})

    client = ResilientLLMClient(
        [LLMProvider("groq", "https://example.test/v1", "test-key", "test-model")],
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMError) as raised:
        client.complete([{"role": "user", "content": "check"}])

    assert raised.value.code == "provider_failover_exhausted"
    assert "not json" not in str(raised.value)
    assert "test-key" not in str(raised.value)
