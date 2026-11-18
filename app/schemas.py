import re
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


def _extract_urls(message: str) -> List[str]:
    return URL_PATTERN.findall(message)


def _is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class PostingRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=200)

    @field_validator("message")
    @classmethod
    def exactly_one_valid_url(cls, value: str) -> str:
        urls = _extract_urls(value)
        if len(urls) == 0:
            raise ValueError("message must contain exactly one HTTP/HTTPS URL")
        if len(urls) > 1:
            raise ValueError("message must contain exactly one HTTP/HTTPS URL")
        if not _is_valid_url(urls[0]):
            raise ValueError("message contains a malformed URL")
        return value


class PlatformResult(BaseModel):
    platform: str
    status: str
    posted_url: Optional[str] = None
    public_access: Optional[bool] = None
    date: Optional[str] = None
    time: Optional[str] = None
    error: Optional[str] = None


class PostingResponse(BaseModel):
    results: List[PlatformResult] = Field(default_factory=list)
