from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings

LOGGER = logging.getLogger(__name__)
MAX_RETRY_DELAY_SECONDS = 8


class LLMError(RuntimeError):
    def __init__(self, message: str, *, code: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class LLMProvider:
    name: str
    base_url: str
    api_key: str
    model: str

    @property
    def endpoint(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"


@dataclass(frozen=True)
class LLMCompletion:
    content: dict[str, Any]
    provider: str
    model: str


def configured_providers(settings: Settings) -> list[LLMProvider]:
    providers = {
        "groq": LLMProvider(
            name="groq",
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key.strip(),
            model=settings.groq_model,
        ),
        "gemini": LLMProvider(
            name="gemini",
            base_url=settings.gemini_base_url,
            api_key=settings.gemini_api_key.strip(),
            model=settings.gemini_model,
        ),
    }
    order = [settings.llm_primary_provider]
    order.extend(name for name in providers if name != settings.llm_primary_provider)
    return [providers[name] for name in order if providers[name].api_key]


def _parse_json_object(content: Any) -> dict[str, Any]:
    if not isinstance(content, str) or not content.strip():
        raise LLMError("The provider returned an empty response.", code="provider_invalid_response")
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise LLMError(
            "The provider response was not valid JSON.", code="provider_invalid_json"
        ) from error
    if not isinstance(value, dict):
        raise LLMError("The provider response must be a JSON object.", code="provider_invalid_json")
    return value


class ResilientLLMClient:
    def __init__(
        self,
        providers: Sequence[LLMProvider],
        *,
        timeout_seconds: float = 45,
        max_retries: int = 1,
        retry_backoff_seconds: float = 0.5,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not providers:
            raise ValueError("At least one configured LLM provider is required.")
        self.providers = tuple(providers)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.transport = transport
        self.sleep = sleep

    def _complete_with_provider(
        self,
        provider: LLMProvider,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"
        payload = {
            "model": provider.model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = client.post(provider.endpoint, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.TimeoutException as error:
            raise LLMError(
                "The provider request timed out.", code="provider_timeout", retryable=True
            ) from error
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            code = "provider_quota_exceeded" if status == 429 else f"provider_http_{status}"
            raise LLMError(
                f"The provider returned HTTP {status}.",
                code=code,
                retryable=status in {408, 425, 429} or 500 <= status <= 599,
            ) from error
        except httpx.RequestError as error:
            raise LLMError(
                "Could not reach the configured provider.",
                code="provider_connection",
                retryable=True,
            ) from error

        try:
            message = response.json()["choices"][0]["message"]
            return _parse_json_object(message.get("content"))
        except LLMError:
            raise
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
            raise LLMError(
                "The provider returned an invalid response shape.", code="provider_invalid_response"
            ) from error

    def complete(self, messages: list[dict[str, Any]]) -> LLMCompletion:
        failures: list[tuple[str, LLMError]] = []
        for provider in self.providers:
            for attempt in range(self.max_retries + 1):
                try:
                    result = self._complete_with_provider(provider, messages)
                    return LLMCompletion(
                        content=result, provider=provider.name, model=provider.model
                    )
                except LLMError as error:
                    failures.append((provider.name, error))
                    should_retry = error.retryable and attempt < self.max_retries
                    delay = self.retry_backoff_seconds * (2**attempt)
                    if should_retry and delay <= MAX_RETRY_DELAY_SECONDS:
                        LOGGER.warning(
                            "LLM provider %s failed (%s); retrying.", provider.name, error.code
                        )
                        self.sleep(delay)
                        continue
                    LOGGER.warning(
                        "LLM provider %s failed (%s); moving to fallback.",
                        provider.name,
                        error.code,
                    )
                    break

        reasons = ", ".join(f"{name}:{error.code}" for name, error in failures)
        raise LLMError(
            f"All configured providers failed ({reasons}).", code="provider_failover_exhausted"
        ) from failures[-1][1]
