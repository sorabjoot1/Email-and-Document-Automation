from typing import Any

import httpx

from .config import get_settings


class LLMError(Exception):
    pass


def _auth_error_message(status_code: int, detail: str) -> str:
    if status_code == 401:
        return (
            "OpenRouter rejected the API key (401 User not found). "
            "Create a new key at https://openrouter.ai/keys, put it in this project's .env as "
            "OPENROUTER_API_KEY=sk-or-v1-..., then restart the server. "
            "Also unset any stale OPENROUTER_API_KEY in your system/user environment variables."
        )
    return f"LLM provider error ({status_code}): {detail}"
    pass


async def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.4,
    max_tokens: int = 2500,
) -> str:
    settings = get_settings()
    if not settings.openrouter_api_key or settings.openrouter_api_key.startswith("your_"):
        raise LLMError(
            "OPENROUTER_API_KEY is not configured. Copy .env.example to .env and add your key."
        )

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8004",
        "X-Title": settings.app_name,
    }
    payload: dict[str, Any] = {
        "model": settings.openrouter_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise LLMError(f"Failed to reach LLM provider: {exc}") from exc

    if response.status_code >= 400:
        raise LLMError(f"LLM provider error ({response.status_code}): {response.text[:500]}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise LLMError("Unexpected LLM response format.") from exc

