import asyncio

import httpx

from app.config import settings

_GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiAPIError(Exception):
    """Raised when a Gemini API call fails (after retries, for retryable errors)."""


async def generate_text(
    prompt: str,
    *,
    model: str | None = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    retry_backoff_seconds: float = 1.0,
) -> str:
    """Call the Gemini API and return the generated text.

    Retries on timeouts/5xx/transport errors with linear backoff. Client errors
    (4xx — bad request, auth, quota) fail fast since retrying won't help.
    """
    if not settings.gemini_api_key:
        raise GeminiAPIError("GEMINI_API_KEY is not configured")

    url = _GEMINI_URL_TEMPLATE.format(model=model or settings.gemini_model)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            # FP-D5: the API key was previously passed as a `?key=` query
            # param, which proxies/CDNs/APM agents commonly log in full --
            # the header form is Google's documented alternative and is not
            # subject to that same default logging behavior.
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url, headers={"x-goog-api-key": settings.gemini_api_key}, json=payload
                )
            response.raise_for_status()
            return _extract_text(response.json())
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                raise GeminiAPIError(f"Gemini API client error: {exc}") from exc
            last_exc = exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc

        if attempt < max_retries:
            await asyncio.sleep(retry_backoff_seconds * attempt)

    raise GeminiAPIError(f"Gemini API call failed after {max_retries} attempts") from last_exc


def _extract_text(data: dict) -> str:
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiAPIError(f"Unexpected Gemini API response shape: {data}") from exc
