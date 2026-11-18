import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from app import config  # noqa: F401 - loads .env via python-dotenv
from app.platforms.base import Platform
from app.schemas import PlatformResult


class LinkedInPlatform(Platform):
    @property
    def name(self) -> str:
        return "linkedin"

    def _credentials(self) -> tuple[Optional[str], Optional[str]]:
        return os.getenv("LINKEDIN_ACCESS_TOKEN"), os.getenv("LINKEDIN_PERSON_URN")

    def post(self, message: str) -> PlatformResult:
        access_token, person_urn = self._credentials()
        if not access_token or not person_urn:
            return PlatformResult(
                platform=self.name,
                status="not_configured",
                error="missing LinkedIn credentials",
            )

        url = "https://api.linkedin.com/v2/ugcPosts"
        payload = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": message},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()

                post_id = response.headers.get("x-restli-id")
                try:
                    body = response.json()
                except (ValueError, TypeError):
                    body = {}
                if not post_id and isinstance(body, dict):
                    post_id = body.get("id")

                posted_url = (
                    f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else None
                )
                now = datetime.now(timezone.utc)
                return PlatformResult(
                    platform=self.name,
                    status="success",
                    posted_url=posted_url,
                    public_access=True,
                    date=now.date().isoformat(),
                    time=now.timetz().replace(microsecond=0).isoformat(),
                )
        except httpx.TimeoutException:
            return PlatformResult(
                platform=self.name,
                status="failed",
                error="request timed out",
            )
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                error = "expired or invalid access token (HTTP 401)"
            elif status == 403:
                error = "insufficient permissions (HTTP 403)"
            elif status == 429:
                error = "rate limit exceeded (HTTP 429)"
            else:
                error = f"HTTP {status}"
            return PlatformResult(
                platform=self.name,
                status="failed",
                error=error,
            )
        except httpx.HTTPError:
            return PlatformResult(
                platform=self.name,
                status="failed",
                error="network error",
            )
        except (KeyError, ValueError, TypeError, OSError):
            return PlatformResult(
                platform=self.name,
                status="failed",
                error="malformed response",
            )
