import os
from unittest.mock import MagicMock, patch

import tweepy
import pytest

from app.platforms.x_twitter import XTwitterPlatform


def _mock_client(get_me_return=None, get_me_error=None, create_tweet_return=None, create_tweet_error=None):
    client = MagicMock()
    if get_me_error is not None:
        client.get_me.side_effect = get_me_error
    else:
        client.get_me.return_value = get_me_return
    if create_tweet_error is not None:
        client.create_tweet.side_effect = create_tweet_error
    else:
        client.create_tweet.return_value = create_tweet_return
    return client


def _http_exception(status_code, payload):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return tweepy.errors.HTTPException(response, response_json=payload)


def test_missing_credentials(monkeypatch):
    for var in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"):
        monkeypatch.delenv(var, raising=False)
    result = XTwitterPlatform().post("hello https://example.com")
    assert result.status == "not_configured"
    assert result.error == "missing X credentials"


@patch("app.platforms.x_twitter.tweepy.Client")
def test_success(mock_client_cls, monkeypatch):
    for k, v in (("X_API_KEY", "key"), ("X_API_SECRET", "secret"), ("X_ACCESS_TOKEN", "token"), ("X_ACCESS_TOKEN_SECRET", "token_secret")):
        monkeypatch.setenv(k, v)
    get_me = MagicMock()
    get_me.data = {"username": "exampleuser"}
    create_tweet = MagicMock()
    create_tweet.data = {"id": "12345", "text": "hello"}
    client = _mock_client(get_me_return=get_me, create_tweet_return=create_tweet)
    mock_client_cls.return_value = client

    result = XTwitterPlatform().post("hello https://example.com")
    assert result.status == "success"
    assert result.posted_url == "https://x.com/exampleuser/status/12345"
    assert result.public_access is True


@patch("app.platforms.x_twitter.tweepy.Client")
def test_auth_failure(mock_client_cls, monkeypatch):
    for k, v in (("X_API_KEY", "key"), ("X_API_SECRET", "secret"), ("X_ACCESS_TOKEN", "token"), ("X_ACCESS_TOKEN_SECRET", "token_secret")):
        monkeypatch.setenv(k, v)
    exc = _http_exception(401, {"title": "Unauthorized", "detail": "Invalid OAuth credentials"})
    client = _mock_client(get_me_error=exc)
    mock_client_cls.return_value = client

    result = XTwitterPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "401" in (result.error or "")


@patch("app.platforms.x_twitter.tweepy.Client")
def test_permission_error(mock_client_cls, monkeypatch):
    for k, v in (("X_API_KEY", "key"), ("X_API_SECRET", "secret"), ("X_ACCESS_TOKEN", "token"), ("X_ACCESS_TOKEN_SECRET", "token_secret")):
        monkeypatch.setenv(k, v)
    get_me = MagicMock()
    get_me.data = {"username": "exampleuser"}
    exc = _http_exception(403, {
        "title": "Forbidden",
        "detail": "You are not allowed to create a Tweet",
        "type": "https://api.twitter.com/2/problems/forbidden",
        "status": 403,
        "errors": [{"message": "duplicate content"}],
    })
    client = _mock_client(get_me_return=get_me, create_tweet_error=exc)
    mock_client_cls.return_value = client

    result = XTwitterPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "403" in (result.error or "")
    assert "title=Forbidden" in (result.error or "")


@patch("app.platforms.x_twitter.tweepy.Client")
def test_rate_limit(mock_client_cls, monkeypatch):
    for k, v in (("X_API_KEY", "key"), ("X_API_SECRET", "secret"), ("X_ACCESS_TOKEN", "token"), ("X_ACCESS_TOKEN_SECRET", "token_secret")):
        monkeypatch.setenv(k, v)
    get_me = MagicMock()
    get_me.data = {"username": "exampleuser"}
    exc = _http_exception(429, {"title": "Too Many Requests"})
    client = _mock_client(get_me_return=get_me, create_tweet_error=exc)
    mock_client_cls.return_value = client

    result = XTwitterPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "429" in (result.error or "")


@patch("app.platforms.x_twitter.tweepy.Client")
def test_billing_error(mock_client_cls, monkeypatch):
    for k, v in (("X_API_KEY", "key"), ("X_API_SECRET", "secret"), ("X_ACCESS_TOKEN", "token"), ("X_ACCESS_TOKEN_SECRET", "token_secret")):
        monkeypatch.setenv(k, v)
    get_me = MagicMock()
    get_me.data = {"username": "exampleuser"}
    exc = _http_exception(402, {"detail": "Credits required"})
    client = _mock_client(get_me_return=get_me, create_tweet_error=exc)
    mock_client_cls.return_value = client

    result = XTwitterPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "402" in (result.error or "")


@patch("app.platforms.x_twitter.tweepy.Client")
def test_timeout(mock_client_cls, monkeypatch):
    for k, v in (("X_API_KEY", "key"), ("X_API_SECRET", "secret"), ("X_ACCESS_TOKEN", "token"), ("X_ACCESS_TOKEN_SECRET", "token_secret")):
        monkeypatch.setenv(k, v)
    client = _mock_client(get_me_error=tweepy.errors.TweepyException("timed out"))
    mock_client_cls.return_value = client

    result = XTwitterPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "request failed" in (result.error or "").lower() or "timed" in (result.error or "").lower()


@patch("app.platforms.x_twitter.tweepy.Client")
def test_malformed_response(mock_client_cls, monkeypatch):
    for k, v in (("X_API_KEY", "key"), ("X_API_SECRET", "secret"), ("X_ACCESS_TOKEN", "token"), ("X_ACCESS_TOKEN_SECRET", "token_secret")):
        monkeypatch.setenv(k, v)
    get_me = MagicMock()
    get_me.data = {"username": "exampleuser"}
    create_tweet = MagicMock()
    create_tweet.data = {}
    client = _mock_client(get_me_return=get_me, create_tweet_return=create_tweet)
    mock_client_cls.return_value = client

    result = XTwitterPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "malformed" in (result.error or "").lower()


@patch("app.platforms.x_twitter.tweepy.Client")
def test_forbidden_403_detail_only(mock_client_cls, monkeypatch):
    for k, v in (("X_API_KEY", "key"), ("X_API_SECRET", "secret"), ("X_ACCESS_TOKEN", "token"), ("X_ACCESS_TOKEN_SECRET", "token_secret")):
        monkeypatch.setenv(k, v)
    get_me = MagicMock()
    get_me.data = {"username": "exampleuser"}
    exc = _http_exception(403, {"detail": "Insufficient app permissions"})
    client = _mock_client(get_me_return=get_me, create_tweet_error=exc)
    mock_client_cls.return_value = client

    result = XTwitterPlatform().post("hello https://example.com")
    assert result.status == "failed"
    assert "detail=Insufficient app permissions" in (result.error or "")
@patch("app.platforms.x_twitter.tweepy.Client")
def test_credits_depleted(mock_client_cls, monkeypatch):
    for k, v in (("X_API_KEY", "key"), ("X_API_SECRET", "secret"), ("X_ACCESS_TOKEN", "token"), ("X_ACCESS_TOKEN_SECRET", "token_secret")):
        monkeypatch.setenv(k, v)
    get_me = MagicMock()
    get_me.data = {"username": "exampleuser"}
    exc = _http_exception(402, {"title": "Credits Depleted", "detail": "credits-depleted", "type": "https://api.twitter.com/2/problems/credits-depleted"})
    client = _mock_client(get_me_return=get_me, create_tweet_error=exc)
    mock_client_cls.return_value = client

    result = XTwitterPlatform().post("hello https://example.com")
    assert result.status == "billing_required"
    assert "402" in (result.error or "")
