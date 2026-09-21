"""Database engine and session management (PostgreSQL + PostGIS)."""

import importlib
import pkgutil
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.settings import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def import_all_models() -> list[str]:
    """Import every ``models`` module under ``app`` so ``Base.metadata`` is complete.

    Discovery rather than a hand-kept list, because the failure mode of forgetting an
    import is silent and expensive: Alembic's autogenerate would emit a migration missing
    those tables, and a foreign key pointing at an unimported table cannot even be
    rendered. Anything that relies on the full metadata calls this first.

    :returns: the module names imported, so callers can assert coverage.
    """
    app_root = Path(__file__).resolve().parents[1]
    imported: list[str] = []
    for module in pkgutil.walk_packages([str(app_root)], prefix="app."):
        if module.name.rsplit(".", 1)[-1] != "models":
            continue
        importlib.import_module(module.name)
        imported.append(module.name)
    return sorted(imported)


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a transactional session."""
    with get_session_factory()() as session:
        yield session
