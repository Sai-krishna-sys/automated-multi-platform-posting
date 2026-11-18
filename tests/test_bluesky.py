import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.platforms.bluesky import BlueskyPlatform


def _mock_client(auth_json, record_json=None, auth_error=None, record_error=None):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False

    auth_response = MagicMock()
    if auth_error is not None:
        auth_response.raise_for_status.side_effect = auth_error
    else:
        auth_response.json.return_value = auth_json
        auth_response.raise_for_status.return_value = None

    if record_json is not None or record_error is not None:
        record_response = MagicMock()
        if record_error is not None:
            record_response.raise_for_status.side_effect = record_error
        else:
            record_response.json.return_value = record_json
            record_response.raise_for_status.return_value = None
        client.post.side_effect = [auth_response, record_response]
    else:
        client.post.return_value = auth_response

    return client


def test_missing_credentials(monkeypatch):
    monkeypatch.delenv("BLUESKY_HANDLE", raising=False)
    monkeypatch.delenv("BLUESKY_APP_PASSWORD", raising=False)
    result = BlueskyPlatform().post("hello https://example.com")
    assert result.status == "not_configured"
    assert result.error == "missing Bluesky credentials"


@patch("app.platforms.bluesky.httpx.Client")
def test_success(mock_client_cls, monkeypatch):
    monkeypatch.setenv("BLUESKY_HANDLE", "user.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "secret")
    client = _mock_client(
        {"accessJwt": "jwt", "did": "did:plc:123", "handle": "user.bsky.social"},
        {"uri": "at://did:plc:123/app.bsky.feed.post/rkey123", "cid": "cid"},
    )
    mock_client_cls.return_value = client

    result = BlueskyPlatform().post("hello https://example.com")
    assert result.status == "success"
    assert result.posted_url == "https://bsky.app/profile/user.bsky.social/post/rkey123"
    assert result.public_access is True


@patch("app.platforms.bluesky.httpx.Client")
def test_auth_failure(mock_client_cls, monkeypatch):
    monkeypatch.setenv("BLUESKY_HANDLE", "user.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "wrong")
    err = httpx.HTTPStatusError(
        "unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )
    err.response.status_code = 401
    client = _mock_client({}, auth_error=err)
    mock_client_cls.return_value = client

    result = BlueskyPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "401" in (result.error or "")


@patch("app.platforms.bluesky.httpx.Client")
def test_http_error_on_publish(mock_client_cls, monkeypatch):
    monkeypatch.setenv("BLUESKY_HANDLE", "user.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "secret")
    err = httpx.HTTPStatusError(
        "bad request",
        request=MagicMock(),
        response=MagicMock(status_code=400),
    )
    err.response.status_code = 400
    client = _mock_client(
        {"accessJwt": "jwt", "did": "did:plc:123", "handle": "user.bsky.social"},
        record_error=err,
    )
    mock_client_cls.return_value = client

    result = BlueskyPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "400" in (result.error or "")


@patch("app.platforms.bluesky.httpx.Client")
def test_timeout(mock_client_cls, monkeypatch):
    monkeypatch.setenv("BLUESKY_HANDLE", "user.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "secret")
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.post.side_effect = httpx.TimeoutException("timed out")
    mock_client_cls.return_value = client

    result = BlueskyPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "timed out" in (result.error or "").lower()


@patch("app.platforms.bluesky.httpx.Client")
def test_malformed_response(mock_client_cls, monkeypatch):
    monkeypatch.setenv("BLUESKY_HANDLE", "user.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "secret")
    client = _mock_client(
        {"accessJwt": "jwt", "did": "did:plc:123", "handle": "user.bsky.social"},
        {"cid": "only-cid"},
    )
    mock_client_cls.return_value = client

    result = BlueskyPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "malformed" in (result.error or "").lower()
