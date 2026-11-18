from typing import List

from app.platforms.base import Platform
from app.schemas import PlatformResult, PostingResponse


class PostingService:
    def __init__(self, platforms: List[Platform] | None = None) -> None:
        self._platforms: List[Platform] = list(platforms or [])

    def post_to_all(self, message: str) -> PostingResponse:
        results: List[PlatformResult] = []
        for platform in self._platforms:
            try:
                result = platform.post(message)
            except Exception as exc:  # noqa: BLE001 - isolate platform failures
                result = PlatformResult(
                    platform=platform.name,
                    status="failed",
                    error=str(exc),
                )
            results.append(result)
        return PostingResponse(results=results)
