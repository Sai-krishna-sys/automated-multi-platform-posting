import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.platforms.linkedin import LinkedInPlatform


def _mock_client(response_json=None, headers=None, status_error=None, network_error=None):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    response = MagicMock()
    if status_error is not None:
        response.raise_for_status.side_effect = status_error
    else:
        response.json.return_value = response_json if response_json is not None else {}
        response.headers = headers or {}
        response.raise_for_status.return_value = None
    if network_error is not None:
        client.post.side_effect = network_error
    else:
        client.post.return_value = response
    return client


def test_missing_credentials(monkeypatch):
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("LINKEDIN_PERSON_URN", raising=False)
    result = LinkedInPlatform().post("hello https://example.com")
    assert result.status == "not_configured"
    assert result.error == "missing LinkedIn credentials"


@patch("app.platforms.linkedin.httpx.Client")
def test_success_from_header(mock_client_cls, monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "token")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:123")
    client = _mock_client(headers={"x-restli-id": "urn:li:share:456"})
    mock_client_cls.return_value = client

    result = LinkedInPlatform().post("hello https://example.com")
    assert result.status == "success"
    assert result.posted_url == "https://www.linkedin.com/feed/update/urn:li:share:456/"
    assert result.public_access is True


@patch("app.platforms.linkedin.httpx.Client")
def test_success_from_body(mock_client_cls, monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "token")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:123")
    client = _mock_client(response_json={"id": "urn:li:ugcPost:789"}, headers={})
    mock_client_cls.return_value = client

    result = LinkedInPlatform().post("hello https://example.com")
    assert result.status == "success"
    assert result.posted_url == "https://www.linkedin.com/feed/update/urn:li:ugcPost:789/"


@patch("app.platforms.linkedin.httpx.Client")
def test_expired_token(mock_client_cls, monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "token")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:123")
    err = httpx.HTTPStatusError("unauthorized", request=MagicMock(), response=MagicMock(status_code=401))
    err.response.status_code = 401
    client = _mock_client(status_error=err)
    mock_client_cls.return_value = client

    result = LinkedInPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "401" in (result.error or "")


@patch("app.platforms.linkedin.httpx.Client")
def test_permission_error(mock_client_cls, monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "token")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:123")
    err = httpx.HTTPStatusError("forbidden", request=MagicMock(), response=MagicMock(status_code=403))
    err.response.status_code = 403
    client = _mock_client(status_error=err)
    mock_client_cls.return_value = client

    result = LinkedInPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "403" in (result.error or "")


@patch("app.platforms.linkedin.httpx.Client")
def test_rate_limit(mock_client_cls, monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "token")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:123")
    err = httpx.HTTPStatusError("too many", request=MagicMock(), response=MagicMock(status_code=429))
    err.response.status_code = 429
    client = _mock_client(status_error=err)
    mock_client_cls.return_value = client

    result = LinkedInPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "429" in (result.error or "")


@patch("app.platforms.linkedin.httpx.Client")
def test_timeout(mock_client_cls, monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "token")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:123")
    client = _mock_client(network_error=httpx.TimeoutException("timed out"))
    mock_client_cls.return_value = client

    result = LinkedInPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "timed out" in (result.error or "").lower()


@patch("app.platforms.linkedin.httpx.Client")
def test_malformed_response_does_not_fail_success(mock_client_cls, monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "token")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:123")
    client = _mock_client(response_json=None, headers={})
    mock_client_cls.return_value = client

    result = LinkedInPlatform().post("hello https://example.com")
    assert result.status == "success"
    assert result.posted_url is None
