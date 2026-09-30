"""Environment-based configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _default_database_url() -> str:
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir / 'vinash.db'}"


class Settings:
    database_url: str
    environment: str
    cookie_name: str
    cookie_max_age: int
    max_thought_chars: int
    max_action_chars: int

    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", _default_database_url())
        self.environment = os.getenv("VINASH_ENV", "development").lower()
        self.cookie_name = os.getenv("VINASH_COOKIE_NAME", "vinash_anon")
        self.cookie_max_age = int(os.getenv("VINASH_COOKIE_MAX_AGE", str(365 * 24 * 60 * 60)))
        self.max_thought_chars = int(os.getenv("VINASH_MAX_THOUGHT_CHARS", "20000"))
        self.max_action_chars = int(os.getenv("VINASH_MAX_ACTION_CHARS", "2000"))

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cookie_secure(self) -> bool:
        return self.is_production


settings = Settings()
