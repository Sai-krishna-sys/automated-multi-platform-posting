import os
from typing import Optional

import tweepy

from app import config  # noqa: F401 - loads .env via python-dotenv
from app.platforms.base import Platform
from app.schemas import PlatformResult


class XTwitterPlatform(Platform):
    @property
    def name(self) -> str:
        return "x"

    def _credentials(self) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        return (
            os.getenv("X_API_KEY"),
            os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"),
            os.getenv("X_ACCESS_TOKEN_SECRET"),
        )

    def _extract(self, obj, key):
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    def _http_error(self, exc: tweepy.errors.HTTPException) -> str:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        title = None
        detail = None
        error_type = None
        response_status = None
        errors = None
        if response is not None:
            try:
                payload = response.json()
            except (ValueError, TypeError, AttributeError):
                payload = None
            if isinstance(payload, dict):
                title = payload.get("title")
                detail = payload.get("detail")
                error_type = payload.get("type")
                response_status = payload.get("status")
                errors = payload.get("errors")

        if status == 401:
            prefix = "authentication failed"
        elif status == 403:
            prefix = "insufficient permissions"
        elif status == 429:
            prefix = "rate limit exceeded"
        elif status == 402:
            prefix = "billing or credits required"
        else:
            prefix = "HTTP error"

        parts = []
        if title:
            parts.append(f"title={title}")
        if detail:
            parts.append(f"detail={detail}")
        if error_type:
            parts.append(f"type={error_type}")
        if response_status is not None:
            parts.append(f"status={response_status}")
        if errors:
            parts.append(f"errors={errors}")

        if status is not None:
            if parts:
                return f"{prefix} (HTTP {status}): " + "; ".join(parts)
            return f"{prefix} (HTTP {status})"
        if parts:
            return f"{prefix}: " + "; ".join(parts)
        return prefix

    def _is_credits_depleted(self, exc: tweepy.errors.HTTPException) -> bool:
        response = getattr(exc, "response", None)
        if response is None:
            return False
        try:
            payload = response.json()
        except (ValueError, TypeError, AttributeError):
            payload = None
        text = ""
        if isinstance(payload, dict):
            text = " ".join(str(value) for value in payload.values())
        try:
            text = f"{text} {response.text}"
        except (AttributeError, TypeError):
            pass
        return "credits-depleted" in text.lower()

    def post(self, message: str) -> PlatformResult:
        api_key, api_secret, access_token, access_token_secret = self._credentials()
        if not all([api_key, api_secret, access_token, access_token_secret]):
            return PlatformResult(
                platform=self.name,
                status="not_configured",
                error="missing X credentials",
            )

        try:
            client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=False,
            )
            me_response = client.get_me()
            me_data = getattr(me_response, "data", None)
            username = self._extract(me_data, "username")
            if not username:
                raise ValueError("missing username in response")

            tweet_response = client.create_tweet(text=message)
            tweet_data = getattr(tweet_response, "data", None)
            tweet_id = self._extract(tweet_data, "id")
            if not tweet_id:
                raise ValueError("missing tweet id in response")

            return PlatformResult(
                platform=self.name,
                status="success",
                posted_url=f"https://x.com/{username}/status/{tweet_id}",
                public_access=True,
            )
        except tweepy.errors.HTTPException as exc:
            if exc.response is not None and exc.response.status_code == 402 and self._is_credits_depleted(exc):
                return PlatformResult(
                    platform=self.name,
                    status="billing_required",
                    error=self._http_error(exc),
                )
            return PlatformResult(
                platform=self.name,
                status="failed",
                error=self._http_error(exc),
            )
        except tweepy.errors.TweepyException:
            return PlatformResult(
                platform=self.name,
                status="failed",
                error="request failed",
            )
        except (KeyError, ValueError, TypeError, AttributeError):
            return PlatformResult(
                platform=self.name,
                status="failed",
                error="malformed response",
            )
        except Exception:
            return PlatformResult(
                platform=self.name,
                status="failed",
                error="request failed",
            )
