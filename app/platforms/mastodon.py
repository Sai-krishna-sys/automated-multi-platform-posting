import os
from datetime import datetime
from typing import Optional

import httpx

from app import config  # noqa: F401 - loads .env via python-dotenv
from app.platforms.base import Platform
from app.schemas import PlatformResult


class MastodonPlatform(Platform):
    @property
    def name(self) -> str:
        return "mastodon"

    def _credentials(self) -> tuple[Optional[str], Optional[str]]:
        base_url = os.getenv("MASTODON_BASE_URL")
        access_token = os.getenv("MASTODON_ACCESS_TOKEN")
        return base_url, access_token

    def post(self, message: str) -> PlatformResult:
        base_url, access_token = self._credentials()
        if not base_url or not access_token:
            return PlatformResult(
                platform=self.name,
                status="not_configured",
                error="missing Mastodon credentials",
            )

        endpoint = f"{base_url.rstrip('/')}/api/v1/statuses"
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                    data={"status": message, "visibility": "public"},
                )
                response.raise_for_status()
                data = response.json()
                status_id = data["id"]
                status_url = data["url"]
                created_at = data["created_at"]
                visibility = data.get("visibility", "public")

                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                posted_url = status_url if visibility == "public" else None
                public_access = visibility == "public" and bool(status_url)

                return PlatformResult(
                    platform=self.name,
                    status="success",
                    posted_url=posted_url,
                    public_access=public_access,
                    date=created_dt.date().isoformat(),
                    time=created_dt.timetz().replace(microsecond=0).isoformat(),
                )
        except httpx.TimeoutException:
            return PlatformResult(
                platform=self.name,
                status="failed",
                error="request timed out",
            )
        except httpx.HTTPStatusError as exc:
            return PlatformResult(
                platform=self.name,
                status="failed",
                error=f"HTTP {exc.response.status_code}",
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
