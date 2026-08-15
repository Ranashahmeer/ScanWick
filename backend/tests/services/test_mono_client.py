from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services import mono_client
from app.services.mono_client import (
    MonoAPIError,
    fetch_account_details,
    fetch_account_transactions_page,
    fetch_all_account_transactions,
)


def _response(status_code: int, json_body: dict) -> httpx.Response:
    return httpx.Response(status_code, json=json_body, request=httpx.Request("GET", "https://example.test"))


@pytest.fixture(autouse=True)
def _configured_secret_key(monkeypatch):
    monkeypatch.setattr(mono_client.settings, "mono_secret_key", "test-mono-key")


async def test_fetch_account_details_parses_nested_shape():
    body = {
        "data": {
            "account": {
                "id": "acc_123",
                "accountNumber": "1234567890",
                "currency": "NGN",
                "institution": {"name": "GTBank", "bankCode": "058"},
            }
        }
    }
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_response(200, body))):
        account = await fetch_account_details("acc_123")

    assert account["accountNumber"] == "1234567890"
    assert account["institution"]["name"] == "GTBank"


async def test_fetch_account_transactions_page_sends_secret_key_header_and_page_param():
    mock_get = AsyncMock(return_value=_response(200, {"data": [], "paging": {"totalPages": 1}}))
    with patch("httpx.AsyncClient.get", new=mock_get):
        await fetch_account_transactions_page("acc_123", page=2)

    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["mono-sec-key"] == "test-mono-key"
    assert kwargs["params"] == {"page": 2}


async def test_fetch_all_account_transactions_paginates_until_done():
    page1 = _response(200, {"data": [{"id": "t1"}], "paging": {"totalPages": 2}})
    page2 = _response(200, {"data": [{"id": "t2"}], "paging": {"totalPages": 2}})
    mock_get = AsyncMock(side_effect=[page1, page2])

    with patch("httpx.AsyncClient.get", new=mock_get):
        transactions = await fetch_all_account_transactions("acc_123")

    assert [t["id"] for t in transactions] == ["t1", "t2"]
    assert mock_get.await_count == 2


async def test_fetch_all_account_transactions_stops_on_empty_page():
    mock_get = AsyncMock(return_value=_response(200, {"data": [], "paging": {"totalPages": 5}}))
    with patch("httpx.AsyncClient.get", new=mock_get):
        transactions = await fetch_all_account_transactions("acc_123")

    assert transactions == []
    mock_get.assert_awaited_once()


async def test_mono_api_error_raised_on_4xx():
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_response(401, {"error": "unauthorized"}))):
        with pytest.raises(MonoAPIError):
            await fetch_account_details("acc_123")
