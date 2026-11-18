from pathlib import Path

from app import config


def test_project_root_is_repository_root() -> None:
    assert config.PROJECT_ROOT.name == "automated-posting"
    assert (config.PROJECT_ROOT / ".env").name == ".env"


def test_dotenv_path_is_absolute_and_in_project_root() -> None:
    assert isinstance(config.PROJECT_ROOT, Path)
    assert config.PROJECT_ROOT.is_absolute()
