"""Database engine and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


engine = create_engine(
    settings.database_url,
    **_engine_kwargs(settings.database_url),
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def reset_engine(database_url: str) -> None:
    """Point the app at a different database (used in tests)."""
    global engine, SessionLocal
    engine.dispose()
    engine = create_engine(database_url, **_engine_kwargs(database_url))
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def init_db() -> None:
    """Create tables when they do not exist (local/tests). Production should run Alembic."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Provide one database session per request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
