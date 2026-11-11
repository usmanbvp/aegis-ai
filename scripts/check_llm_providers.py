from __future__ import annotations

from app.config import get_settings
from app.llm import LLMError, ResilientLLMClient, configured_providers


def main() -> int:
    settings = get_settings()
    providers = configured_providers(settings)
    if not providers:
        print("No LLM providers are configured. Set GROQ_API_KEY and/or GEMINI_API_KEY in .env.")
        return 2

    messages = [
        {
            "role": "system",
            "content": 'Return only a JSON object with the string field "status" set to "ok".',
        },
        {"role": "user", "content": "Provider connectivity check. Reply with status ok."},
    ]
    failed = False
    for provider in providers:
        client = ResilientLLMClient(
            [provider],
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            retry_backoff_seconds=settings.llm_retry_backoff_seconds,
        )
        try:
            result = client.complete(messages)
            if result.content.get("status") != "ok":
                print(f"{provider.name}: FAIL (unexpected_response)")
                failed = True
                continue
            print(f"{provider.name}: PASS ({provider.model})")
        except LLMError as error:
            print(f"{provider.name}: FAIL ({error.code})")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
