import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from app import config  # noqa: F401 - loads .env via python-dotenv
from app.platforms.base import Platform
from app.schemas import PlatformResult


class BlueskyPlatform(Platform):
    @property
    def name(self) -> str:
        return "bluesky"

    def _credentials(self) -> tuple[Optional[str], Optional[str], str]:
        handle = os.getenv("BLUESKY_HANDLE")
        app_password = os.getenv("BLUESKY_APP_PASSWORD")
        service = os.getenv("BLUESKY_SERVICE", "https://bsky.social")
        return handle, app_password, service

    def post(self, message: str) -> PlatformResult:
        handle, app_password, service = self._credentials()
        if not handle or not app_password:
            return PlatformResult(
                platform=self.name,
                status="not_configured",
                error="missing Bluesky credentials",
            )

        try:
            with httpx.Client(timeout=10.0) as client:
                auth_response = client.post(
                    f"{service}/xrpc/com.atproto.server.createSession",
                    json={"identifier": handle, "password": app_password},
                )
                auth_response.raise_for_status()
                auth_data = auth_response.json()
                access_jwt = auth_data["accessJwt"]
                did = auth_data["did"]
                authenticated_handle = auth_data.get("handle", handle)

                now = datetime.now(timezone.utc)
                created_at = now.isoformat()
                record_response = client.post(
                    f"{service}/xrpc/com.atproto.repo.createRecord",
                    headers={"Authorization": f"Bearer {access_jwt}"},
                    json={
                        "repo": did,
                        "collection": "app.bsky.feed.post",
                        "record": {
                            "$type": "app.bsky.feed.post",
                            "text": message,
                            "createdAt": created_at,
                        },
                    },
                )
                record_response.raise_for_status()
                record_data = record_response.json()
                uri = record_data["uri"]
                rkey = uri.rstrip("/").split("/")[-1]
                public_url = f"https://bsky.app/profile/{authenticated_handle}/post/{rkey}"
                return PlatformResult(
                    platform=self.name,
                    status="success",
                    posted_url=public_url,
                    public_access=True,
                    date=now.date().isoformat(),
                    time=now.timetz().replace(microsecond=0).isoformat(),
                )
        except httpx.TimeoutException as exc:
            return PlatformResult(
                platform=self.name,
                status="failed",
                error=f"request timed out: {exc}",
            )
        except httpx.HTTPStatusError as exc:
            return PlatformResult(
                platform=self.name,
                status="failed",
                error=f"HTTP {exc.response.status_code}",
            )
        except httpx.HTTPError as exc:
            return PlatformResult(
                platform=self.name,
                status="failed",
                error=f"HTTP error: {exc}",
            )
        except (KeyError, ValueError, TypeError) as exc:
            return PlatformResult(
                platform=self.name,
                status="failed",
                error=f"malformed response: {exc}",
            )
