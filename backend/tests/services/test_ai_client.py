from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services import ai_client


def _response(status_code: int, json_body: dict) -> httpx.Response:
    return httpx.Response(status_code, json=json_body, request=httpx.Request("POST", "https://example.test"))


def _ok_body(text: str = "hello from gemini") -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


@pytest.fixture(autouse=True)
def _configured_api_key(monkeypatch):
    monkeypatch.setattr(ai_client.settings, "gemini_api_key", "test-key")


async def test_generate_text_success_first_try():
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_response(200, _ok_body("hi")))) as mock_post:
        result = await ai_client.generate_text("say hi")

    assert result == "hi"
    mock_post.assert_awaited_once()


async def test_generate_text_retries_on_timeout_then_succeeds():
    mock_post = AsyncMock(
        side_effect=[
            httpx.TimeoutException("timed out"),
            _response(200, _ok_body("recovered")),
        ]
    )
    with patch("httpx.AsyncClient.post", new=mock_post):
        result = await ai_client.generate_text("say hi", retry_backoff_seconds=0)

    assert result == "recovered"
    assert mock_post.await_count == 2


async def test_generate_text_retries_on_5xx_then_succeeds():
    mock_post = AsyncMock(
        side_effect=[
            _response(503, {"error": "unavailable"}),
            _response(200, _ok_body("recovered")),
        ]
    )
    with patch("httpx.AsyncClient.post", new=mock_post):
        result = await ai_client.generate_text("say hi", retry_backoff_seconds=0)

    assert result == "recovered"
    assert mock_post.await_count == 2


async def test_generate_text_raises_after_exhausting_retries():
    mock_post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(ai_client.GeminiAPIError):
            await ai_client.generate_text("say hi", max_retries=3, retry_backoff_seconds=0)

    assert mock_post.await_count == 3


async def test_generate_text_does_not_retry_on_client_error():
    mock_post = AsyncMock(return_value=_response(400, {"error": "bad request"}))
    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(ai_client.GeminiAPIError):
            await ai_client.generate_text("say hi", max_retries=3, retry_backoff_seconds=0)

    mock_post.assert_awaited_once()


async def test_generate_text_requires_api_key(monkeypatch):
    monkeypatch.setattr(ai_client.settings, "gemini_api_key", "")
    with pytest.raises(ai_client.GeminiAPIError):
        await ai_client.generate_text("say hi")


async def test_generate_text_raises_on_unexpected_response_shape():
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_response(200, {"unexpected": "shape"}))):
        with pytest.raises(ai_client.GeminiAPIError):
            await ai_client.generate_text("say hi")
