from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database.models import Base


def _default_data_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "aegis.db"


def resolve_database_url(database_url: str | None = None) -> str:
    if database_url:
        return database_url
    configured = get_settings().database_url
    if configured and configured.startswith("sqlite"):
        return configured
    sqlite_path = _default_data_path()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{sqlite_path}"


def initialize_database(database_url: str | None = None) -> Session:
    resolved_url = resolve_database_url(database_url)
    engine: Engine = create_engine(
        resolved_url,
        connect_args={"check_same_thread": False} if resolved_url.startswith("sqlite") else {},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return SessionLocal()
