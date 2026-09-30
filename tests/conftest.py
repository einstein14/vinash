"""Use a temporary database for each test."""

import pytest

import app.db as database
from app.config import settings
from app.models import Base


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setattr(settings, "database_url", database_url)
    monkeypatch.setattr(settings, "environment", "development")
    database.reset_engine(database_url)
    Base.metadata.drop_all(bind=database.engine)
    database.init_db()
