import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from app import config  # noqa: F401 - loads .env via python-dotenv
from app.platforms.base import Platform
from app.schemas import PlatformResult


class TelegramPlatform(Platform):
    @property
    def name(self) -> str:
        return "telegram"

    def _credentials(self) -> tuple[Optional[str], Optional[str]]:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        return token, chat_id

    def _http_error(self, exc: httpx.HTTPStatusError) -> str:
        description = None
        try:
            description = exc.response.json().get("description")
        except (ValueError, TypeError, AttributeError):
            description = None
        if exc.response.status_code == 404:
            return "invalid or incorrectly loaded bot token (HTTP 404)"
        if description:
            return f"HTTP {exc.response.status_code}: {description}"
        return f"HTTP {exc.response.status_code}"

    def post(self, message: str) -> PlatformResult:
        token, chat_id = self._credentials()
        if not token or not chat_id:
            return PlatformResult(
                platform=self.name,
                status="not_configured",
                error="missing Telegram credentials",
            )

        base_url = f"https://api.telegram.org/bot{token}"
        try:
            with httpx.Client(timeout=10.0) as client:
                me_response = client.get(f"{base_url}/getMe")
                me_response.raise_for_status()
                me_data = me_response.json()
                if not me_data.get("ok"):
                    return PlatformResult(
                        platform=self.name,
                        status="failed",
                        error=me_data.get("description", "invalid bot token"),
                    )

                response = client.post(
                    f"{base_url}/sendMessage",
                    json={"chat_id": chat_id, "text": message},
                )
                response.raise_for_status()
                data = response.json()
                if not data.get("ok"):
                    return PlatformResult(
                        platform=self.name,
                        status="failed",
                        error=data.get("description", "Telegram API returned ok=false"),
                    )

                result = data["result"]
                message_id = result["message_id"]
                message_date = datetime.fromtimestamp(result["date"], tz=timezone.utc)
                chat = result.get("chat", {})
                username = chat.get("username")

                if username:
                    posted_url = f"https://t.me/{username}/{message_id}"
                    public_access = True
                else:
                    posted_url = None
                    public_access = False

                return PlatformResult(
                    platform=self.name,
                    status="success",
                    posted_url=posted_url,
                    public_access=public_access,
                    date=message_date.date().isoformat(),
                    time=message_date.timetz().replace(microsecond=0).isoformat(),
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
                error=self._http_error(exc),
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
