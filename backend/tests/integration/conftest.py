"""Fixtures for tests that need a real PostgreSQL with PostGIS.

The models use JSONB, UUID and geometry columns, so SQLite is not an option. These tests
skip when no database is reachable rather than failing: a developer without a local
database should still get a green run, while CI — which provisions PostGIS — executes them.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infra.database import Base, import_all_models
from app.settings import get_settings

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """A live engine, or a skip.

    SQLAlchemy imports the DBAPI lazily, so a missing driver surfaces on first connect
    rather than at create_engine — both live inside the try for that reason. Any failure
    here means skip, not fail: a developer without a local database still gets a green
    run, while CI provisions PostGIS and executes these for real.
    """
    url = get_settings().database_url
    candidate: Engine | None = None
    try:
        candidate = create_engine(url, pool_pre_ping=True, future=True)
        with candidate.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        if candidate is not None:
            candidate.dispose()
        pytest.skip(
            f"sin PostgreSQL disponible ({type(exc).__name__}); se omiten los tests de integración"
        )
    yield candidate
    candidate.dispose()


@pytest.fixture(scope="session")
def _schema(engine: Engine) -> Iterator[None]:
    """Create the schema once for the session.

    Uses metadata.create_all rather than Alembic on purpose: this verifies the ORM models
    themselves are coherent. Whether the migrations match is checked separately, by
    running `alembic upgrade head` in CI.
    """
    # Import every model module first, or create_all quietly builds a partial schema.
    import_all_models()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def session(engine: Engine, _schema: None) -> Iterator[Session]:
    """A session rolled back after each test, so tests cannot see each other's rows."""
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()
