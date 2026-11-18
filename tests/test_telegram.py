import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.platforms.telegram import TelegramPlatform


def _response(json_data=None, status_error=None):
    response = MagicMock()
    if status_error is not None:
        response.raise_for_status.side_effect = status_error
    else:
        response.json.return_value = json_data
        response.raise_for_status.return_value = None
    return response


def _mock_client(
    getme_json=None,
    getme_error=None,
    send_json=None,
    send_error=None,
    network_error=None,
):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False

    getme_response = _response(getme_json, getme_error)
    send_response = _response(send_json, send_error)

    if network_error is not None:
        client.get.side_effect = network_error
        client.post.side_effect = network_error
    else:
        client.get.return_value = getme_response
        client.post.return_value = send_response

    return client


def test_missing_credentials(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    result = TelegramPlatform().post("hello https://example.com")
    assert result.status == "not_configured"
    assert result.error == "missing Telegram credentials"


@patch("app.platforms.telegram.httpx.Client")
def test_success_public_channel(mock_client_cls, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "@channel")
    client = _mock_client(
        getme_json={"ok": True, "result": {"username": "bot"}},
        send_json={
            "ok": True,
            "result": {
                "message_id": 42,
                "date": 1700000000,
                "chat": {"username": "channel"},
            },
        },
    )
    mock_client_cls.return_value = client

    result = TelegramPlatform().post("hello https://example.com")
    assert result.status == "success"
    assert result.posted_url == "https://t.me/channel/42"
    assert result.public_access is True


@patch("app.platforms.telegram.httpx.Client")
def test_success_private_channel(mock_client_cls, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123")
    client = _mock_client(
        getme_json={"ok": True, "result": {"username": "bot"}},
        send_json={
            "ok": True,
            "result": {
                "message_id": 7,
                "date": 1700000000,
                "chat": {"id": -100123},
            },
        },
    )
    mock_client_cls.return_value = client

    result = TelegramPlatform().post("hello https://example.com")
    assert result.status == "success"
    assert result.posted_url is None
    assert result.public_access is False


@patch("app.platforms.telegram.httpx.Client")
def test_invalid_token_404(mock_client_cls, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bad:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "@channel")
    err = httpx.HTTPStatusError(
        "not found",
        request=MagicMock(),
        response=MagicMock(status_code=404),
    )
    err.response.status_code = 404
    err.response.json.return_value = {"ok": False, "description": "Not Found"}
    client = _mock_client(getme_error=err)
    mock_client_cls.return_value = client

    result = TelegramPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "404" in (result.error or "")


@patch("app.platforms.telegram.httpx.Client")
def test_auth_failure(mock_client_cls, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bad:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "@channel")
    err = httpx.HTTPStatusError(
        "unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )
    err.response.status_code = 401
    err.response.json.return_value = {"ok": False, "description": "Unauthorized"}
    client = _mock_client(getme_error=err)
    mock_client_cls.return_value = client

    result = TelegramPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "401" in (result.error or "")


@patch("app.platforms.telegram.httpx.Client")
def test_invalid_chat_id(mock_client_cls, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "invalid")
    client = _mock_client(
        getme_json={"ok": True, "result": {"username": "bot"}},
        send_json={"ok": False, "description": "chat not found"},
    )
    mock_client_cls.return_value = client

    result = TelegramPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "chat not found" in (result.error or "")


@patch("app.platforms.telegram.httpx.Client")
def test_api_error_ok_false(mock_client_cls, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "@channel")
    client = _mock_client(
        getme_json={"ok": True, "result": {"username": "bot"}},
        send_json={"ok": False, "description": "Bad Request"},
    )
    mock_client_cls.return_value = client

    result = TelegramPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "Bad Request" in (result.error or "")


@patch("app.platforms.telegram.httpx.Client")
def test_timeout(mock_client_cls, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "@channel")
    client = _mock_client(network_error=httpx.TimeoutException("timed out"))
    mock_client_cls.return_value = client

    result = TelegramPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "timed out" in (result.error or "").lower()


@patch("app.platforms.telegram.httpx.Client")
def test_malformed_response(mock_client_cls, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "@channel")
    client = _mock_client(
        getme_json={"ok": True, "result": {"username": "bot"}},
        send_json={"ok": True, "result": {}},
    )
    mock_client_cls.return_value = client

    result = TelegramPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "malformed" in (result.error or "").lower()
