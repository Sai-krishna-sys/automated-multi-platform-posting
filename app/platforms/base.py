from abc import ABC, abstractmethod

from app.schemas import PlatformResult


class Platform(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def post(self, message: str) -> PlatformResult:
        """Publish ``message`` to this platform and return an honest result."""
