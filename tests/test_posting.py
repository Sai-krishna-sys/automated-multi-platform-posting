from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_message() -> None:
    message = "Hello world https://example.com"
    response = client.post("/posting", json={"message": message})
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert isinstance(body["results"], list)


def test_message_too_long() -> None:
    message = "a" * 201 + " https://example.com"
    response = client.post("/posting", json={"message": message})
    assert response.status_code == 422


def test_missing_url() -> None:
    response = client.post("/posting", json={"message": "Hello world without link"})
    assert response.status_code == 422


def test_multiple_urls() -> None:
    message = "https://a.com and https://b.com"
    response = client.post("/posting", json={"message": message})
    assert response.status_code == 422


def test_malformed_url() -> None:
    response = client.post("/posting", json={"message": "Visit http://"})
    assert response.status_code == 422


def test_endpoint_field_names() -> None:
    response = client.post("/posting", json={"message": "Hi https://example.com"})
    assert response.status_code == 200
    assert set(response.json().keys()) == {"results"}
from app.schemas import PlatformResult
from app.services.posting_service import PostingService


class _FakePlatform:
    def __init__(self, name, behavior="success"):
        self._name = name
        self._behavior = behavior

    @property
    def name(self) -> str:
        return self._name

    def post(self, message: str) -> PlatformResult:
        if self._behavior == "raise":
            raise RuntimeError("platform failure")
        return PlatformResult(platform=self._name, status="success")


def test_one_platform_failure_does_not_stop_others() -> None:
    platforms = [
        _FakePlatform("bluesky", "raise"),
        _FakePlatform("telegram"),
        _FakePlatform("mastodon"),
        _FakePlatform("x"),
        _FakePlatform("linkedin"),
    ]
    service = PostingService(platforms)
    response = service.post_to_all("hello https://example.com")
    assert len(response.results) == 5
    assert response.results[0].platform == "bluesky"
    assert response.results[0].status == "failed"
    assert all(result.status == "success" for result in response.results[1:])


def test_all_five_platforms_in_posting_response() -> None:
    response = client.post("/posting", json={"message": "Hi https://example.com"})
    assert response.status_code == 200
    platforms = {result["platform"] for result in response.json()["results"]}
    assert platforms == {"bluesky", "telegram", "mastodon", "x", "linkedin"}
