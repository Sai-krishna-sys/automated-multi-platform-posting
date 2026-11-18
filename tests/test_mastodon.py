import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.platforms.mastodon import MastodonPlatform


def _mock_client(response_json=None, status_error=None, network_error=None):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    response = MagicMock()
    if status_error is not None:
        response.raise_for_status.side_effect = status_error
    else:
        response.json.return_value = response_json
        response.raise_for_status.return_value = None
    if network_error is not None:
        client.post.side_effect = network_error
    else:
        client.post.return_value = response
    return client


def test_missing_credentials(monkeypatch):
    monkeypatch.delenv("MASTODON_BASE_URL", raising=False)
    monkeypatch.delenv("MASTODON_ACCESS_TOKEN", raising=False)
    result = MastodonPlatform().post("hello https://example.com")
    assert result.status == "not_configured"
    assert result.error == "missing Mastodon credentials"


@patch("app.platforms.mastodon.httpx.Client")
def test_success(mock_client_cls, monkeypatch):
    monkeypatch.setenv("MASTODON_BASE_URL", "https://mastodon.social")
    monkeypatch.setenv("MASTODON_ACCESS_TOKEN", "token")
    client = _mock_client(
        {
            "id": "123",
            "url": "https://mastodon.social/@user/123",
            "created_at": "2024-01-01T00:00:00.000Z",
            "visibility": "public",
        }
    )
    mock_client_cls.return_value = client

    result = MastodonPlatform().post("hello https://example.com")
    assert result.status == "success"
    assert result.posted_url == "https://mastodon.social/@user/123"
    assert result.public_access is True


@patch("app.platforms.mastodon.httpx.Client")
def test_invalid_token(mock_client_cls, monkeypatch):
    monkeypatch.setenv("MASTODON_BASE_URL", "https://mastodon.social")
    monkeypatch.setenv("MASTODON_ACCESS_TOKEN", "bad")
    err = httpx.HTTPStatusError(
        "unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )
    err.response.status_code = 401
    client = _mock_client(status_error=err)
    mock_client_cls.return_value = client

    result = MastodonPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "401" in (result.error or "")


@patch("app.platforms.mastodon.httpx.Client")
def test_permission_error(mock_client_cls, monkeypatch):
    monkeypatch.setenv("MASTODON_BASE_URL", "https://mastodon.social")
    monkeypatch.setenv("MASTODON_ACCESS_TOKEN", "token")
    err = httpx.HTTPStatusError(
        "forbidden",
        request=MagicMock(),
        response=MagicMock(status_code=403),
    )
    err.response.status_code = 403
    client = _mock_client(status_error=err)
    mock_client_cls.return_value = client

    result = MastodonPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "403" in (result.error or "")


@patch("app.platforms.mastodon.httpx.Client")
def test_timeout(mock_client_cls, monkeypatch):
    monkeypatch.setenv("MASTODON_BASE_URL", "https://mastodon.social")
    monkeypatch.setenv("MASTODON_ACCESS_TOKEN", "token")
    client = _mock_client(network_error=httpx.TimeoutException("timed out"))
    mock_client_cls.return_value = client

    result = MastodonPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "timed out" in (result.error or "").lower()


@patch("app.platforms.mastodon.httpx.Client")
def test_malformed_response(mock_client_cls, monkeypatch):
    monkeypatch.setenv("MASTODON_BASE_URL", "https://mastodon.social")
    monkeypatch.setenv("MASTODON_ACCESS_TOKEN", "token")
    client = _mock_client({"id": "123"})
    mock_client_cls.return_value = client

    result = MastodonPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "malformed" in (result.error or "").lower()
