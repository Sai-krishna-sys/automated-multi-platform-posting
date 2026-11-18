from fastapi import FastAPI

from app import config  # noqa: F401
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.linkedin import LinkedInPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.x_twitter import XTwitterPlatform
from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import PostingService

app = FastAPI(title="Automated Multi-Platform Posting System")

_posting_service = PostingService([BlueskyPlatform(), TelegramPlatform(), MastodonPlatform(), XTwitterPlatform(), LinkedInPlatform()])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/posting", response_model=PostingResponse)
def posting(request: PostingRequest) -> PostingResponse:
    return _posting_service.post_to_all(request.message)
