"""The Alembic migrations and the ORM models must describe the same schema.

Without this, the two can drift apart invisibly: the integration tests build the schema
with `Base.metadata.create_all`, while production builds it with `alembic upgrade head`.
A column present in one and absent from the other would pass every test and fail in
production.

Both sides are rendered offline, so this needs no database.

The comparison is deliberately one-directional: every ORM table must exist in the
migrations, but not the reverse. Migration 0001 creates tables that have no ORM model yet
(`audit_event`, `asbuilt_proposal`, `network_asset_cache`); their models arrive with the
increments that use them. The direction checked is the one that breaks production.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.infra.database import Base, import_all_models

BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Tables PostGIS and Alembic manage themselves; neither side should declare them.
INFRASTRUCTURE_TABLES = {"spatial_ref_sys", "alembic_version", "geometry_columns"}


def _import_models() -> list[str]:
    """Import every module that defines a model, so Base.metadata is complete.

    Uses the shared discovery helper rather than a list here: a guard that silently covers
    less than it claims is worse than no guard.
    """
    return import_all_models()


@pytest.fixture(scope="module")
def migration_sql() -> str:
    """The SQL Alembic would run, rendered without connecting to anything."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "PYTHONPATH": str(BACKEND_ROOT),
            # Offline mode still needs a URL to pick the dialect; it never connects.
            "SIGEC_DATABASE_URL": "postgresql+psycopg://u:p@localhost/db",
        },
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"alembic upgrade --sql falló:\n{result.stderr}")
    return result.stdout


def _tables_in_sql(sql: str) -> dict[str, set[str]]:
    """Table name -> column names, as the migrations leave the schema.

    Migrations are cumulative, so this replays them in order: CREATE TABLE establishes a
    table, and later ALTER TABLE ADD/DROP COLUMN change it. Reading only the creates would
    miss every column a later revision adds — which is most of them, once a schema starts
    evolving.
    """
    tables: dict[str, set[str]] = {}

    # Statements in source order, so an ALTER always follows the CREATE it modifies.
    statement_pattern = re.compile(
        r"CREATE TABLE (?P<create>\w+) \((?P<body>.*?)\n\);"
        r"|ALTER TABLE (?P<alter>\w+) ADD COLUMN (?P<added>\w+)"
        r"|ALTER TABLE (?P<dropped_from>\w+) DROP COLUMN (?P<dropped>\w+)",
        flags=re.DOTALL | re.IGNORECASE,
    )

    for match in statement_pattern.finditer(sql):
        if match.group("create"):
            columns: set[str] = set()
            for line in match.group("body").splitlines():
                stripped = line.strip().rstrip(",")
                if not stripped:
                    continue
                first = stripped.split()[0].upper()
                # Skip table-level constraint clauses; keep column definitions.
                if first in {"PRIMARY", "FOREIGN", "UNIQUE", "CONSTRAINT", "CHECK"}:
                    continue
                columns.add(stripped.split()[0].lower())
            tables[match.group("create").lower()] = columns
        elif match.group("alter"):
            tables.setdefault(match.group("alter").lower(), set()).add(match.group("added").lower())
        elif match.group("dropped_from"):
            tables.setdefault(match.group("dropped_from").lower(), set()).discard(
                match.group("dropped").lower()
            )

    return tables


def _tables_in_models() -> dict[str, set[str]]:
    _import_models()
    dialect = postgresql.dialect()
    tables: dict[str, set[str]] = {}
    for table in Base.metadata.sorted_tables:
        if table.name in INFRASTRUCTURE_TABLES:
            continue
        # Rendering proves the model is expressible in PostgreSQL, not only that it parses.
        str(CreateTable(table).compile(dialect=dialect))
        tables[table.name.lower()] = {c.name.lower() for c in table.columns}
    return tables


class TestModelDiscovery:
    """The guard must actually see every model module, or it proves nothing."""

    def test_discovery_finds_the_known_model_modules(self):
        found = set(_import_models())
        assert {"app.gis_gateway.models", "app.org.models"} <= found

    def test_discovery_populates_metadata_with_their_tables(self):
        _import_models()
        tables = set(Base.metadata.tables)
        assert {"business_unit", "organization", "gis_metadata_snapshot"} <= tables


class TestSchemaParity:
    def test_migrations_render(self, migration_sql: str):
        assert "CREATE TABLE" in migration_sql

    def test_every_model_table_exists_in_the_migrations(self, migration_sql: str):
        in_sql = _tables_in_sql(migration_sql)
        missing = sorted(set(_tables_in_models()) - set(in_sql))
        assert not missing, (
            f"tablas declaradas en los modelos y ausentes de las migraciones: {missing}. "
            "Producción no las tendría."
        )

    def test_columns_match_for_every_shared_table(self, migration_sql: str):
        in_sql = _tables_in_sql(migration_sql)
        in_models = _tables_in_models()
        problems: list[str] = []
        for table, model_columns in in_models.items():
            sql_columns = in_sql.get(table)
            if sql_columns is None:
                continue  # reported by the test above
            only_in_models = sorted(model_columns - sql_columns)
            only_in_sql = sorted(sql_columns - model_columns)
            if only_in_models:
                problems.append(f"{table}: solo en los modelos {only_in_models}")
            if only_in_sql:
                problems.append(f"{table}: solo en las migraciones {only_in_sql}")
        assert not problems, "modelos y migraciones divergen:\n" + "\n".join(problems)

    def test_geometry_column_is_created_by_the_migration(self, migration_sql: str):
        """PostGIS geometry is added with AddGeometryColumn, not a plain column.

        Asserted explicitly because the parity check above cannot see it: it is a function
        call, not part of the CREATE TABLE.
        """
        assert "AddGeometryColumn" in migration_sql
