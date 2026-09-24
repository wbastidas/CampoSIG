"""Who modified a regulatory parameter, and from what (RF-150).

The periods were already the history of the *values* a regulator published, and the date-based
lookup was already tested (RF-350). What this file covers is the half of RF-150 that was missing:
«usuario que modificó».

Three properties:

* **The author is recorded, and it is not the verifier.** Correcting a typo in a description is not
  certifying a figure against the official text, and one field standing for both would let a
  correction look like a verification.
* **A correction does not erase what the value was.** The one mutation the model allows is an edit
  to an existing period, so the revision log keeps the previous figure. «Who changed it» is only
  useful next to «from what».
* **Verification comes from the token, never from the payload.** A verification the caller could
  type is a verification nobody made.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.infra.database import get_session
from app.main import create_app
from app.regulatory.cli import main as cli_main
from app.regulatory.loader import apply_seed, load_seed
from app.regulatory.models import RegulatoryRevision, RevisionAction
from app.regulatory.service import (
    SYSTEM_ACTOR,
    UnknownParameterError,
    history,
    revisions,
    set_parameter,
    verify_parameter,
)

pytestmark = pytest.mark.integration

CODE = "prueba.limite_horas"
NORM = "Resolución de prueba"


def write(session: Session, **kwargs) -> object:
    defaults = {
        "code": CODE,
        "value": 24,
        "norm_ref": NORM,
        "effective_from": date(2026, 1, 1),
    }
    return set_parameter(session, **{**defaults, **kwargs})


class TestAuthorship:
    def test_a_new_period_records_who_loaded_it(self, session: Session):
        row = write(session, actor="maria.perez")
        assert row.created_by == "maria.perez"
        assert row.updated_by == "maria.perez"

    def test_a_load_with_no_actor_is_attributed_to_the_loader_and_not_to_a_person(
        self, session: Session
    ):
        """A generic name that is obviously a script beats a person who was not there."""
        assert write(session).created_by == SYSTEM_ACTOR

    def test_a_correction_changes_the_editor_and_not_the_loader(self, session: Session):
        write(session, actor="maria.perez")
        corrected = write(session, value=30, actor="jose.vera")
        assert corrected.created_by == "maria.perez"
        assert corrected.updated_by == "jose.vera"

    def test_the_author_is_not_the_verifier(self, session: Session):
        """Correcting a description is not certifying a figure."""
        row = write(session, actor="jose.vera")
        assert row.updated_by == "jose.vera"
        assert row.verified_by is None
        assert row.is_verified is False


class TestTheRevisionLog:
    def test_a_creation_is_logged(self, session: Session):
        write(session, actor="maria.perez")
        entries = revisions(session, CODE)
        assert [entry.action for entry in entries] == [RevisionAction.CREATED]
        assert entries[0].actor == "maria.perez"

    def test_a_correction_keeps_the_previous_value(self, session: Session):
        """The whole reason the log exists: the correction overwrites the figure in place."""
        write(session, value=24, actor="maria.perez")
        write(session, value=30, actor="jose.vera")
        last = revisions(session, CODE)[-1]
        assert last.action == RevisionAction.CORRECTED
        # Sin el envoltorio de almacenamiento: quien lee la revisión busca la cifra, no `{"v": …}`.
        assert last.changed["value"] == {"from": 24, "to": 30}

    def test_a_correction_that_changes_nothing_logs_no_field(self, session: Session):
        """Otherwise the log fills with «24 → 24» and buries the edits that mattered."""
        write(session, value=24, actor="maria.perez")
        write(session, value=24, actor="maria.perez")
        assert revisions(session, CODE)[-1].changed == {}

    def test_opening_a_new_period_logs_the_close_of_the_previous_one(self, session: Session):
        write(session, effective_from=date(2026, 1, 1), actor="maria.perez")
        write(session, effective_from=date(2026, 7, 1), value=18, actor="jose.vera")
        actions = [entry.action for entry in revisions(session, CODE)]
        assert actions == [
            RevisionAction.CREATED,
            RevisionAction.CLOSED,
            RevisionAction.CREATED,
        ]
        closed = next(entry for entry in revisions(session, CODE) if entry.action == "cerrado")
        assert closed.changed["effective_to"]["to"] == "2026-06-30"
        assert closed.actor == "jose.vera"

    def test_the_order_is_the_sequence_and_not_the_timestamp(self, session: Session):
        """Why the sequence column exists.

        `at` is the transaction clock, so every revision of one request shares it to the microsecond
        and the order is whatever the scan returns. Worse, a timestamp can be older than the row
        before it — a clock adjustment, a backdated insert. The sequence cannot. So a revision
        written last with an ancient `at` must still read last.
        """
        write(session, value=24, actor="maria.perez")
        write(session, value=30, actor="jose.vera")
        backdated = RegulatoryRevision(
            parameter_id=history(session, CODE)[0].id,
            code=CODE,
            action=RevisionAction.CORRECTED,
            actor="reloj.desajustado",
            changed={},
            at=datetime(2001, 1, 1, tzinfo=UTC),
        )
        session.add(backdated)
        session.flush()
        entries = revisions(session, CODE)
        assert [entry.actor for entry in entries][-1] == "reloj.desajustado"
        sequences = [entry.sequence for entry in entries]
        assert sequences == sorted(sequences)

    def test_the_note_travels_so_a_reader_knows_why(self, session: Session):
        write(session, actor="maria.perez", note="corrige el numeral citado")
        assert revisions(session, CODE)[0].note == "corrige el numeral citado"

    def test_the_log_is_oldest_first_because_the_answer_is_a_story(self, session: Session):
        write(session, effective_from=date(2026, 1, 1), actor="a")
        write(session, effective_from=date(2026, 7, 1), actor="b")
        entries = revisions(session, CODE)
        assert entries == sorted(entries, key=lambda entry: entry.at)

    def test_another_codes_revisions_are_not_mixed_in(self, session: Session):
        write(session, actor="a")
        write(session, code="otro.codigo", actor="b")
        assert [entry.code for entry in revisions(session, CODE)] == [CODE]


class TestVerification:
    def test_verifying_records_who_and_when(self, session: Session):
        write(session, actor="maria.perez")
        row = verify_parameter(session, CODE, effective_from=date(2026, 1, 1), actor="jose.vera")
        assert row.verified_by == "jose.vera"
        assert row.is_verified is True
        assert revisions(session, CODE)[-1].action == RevisionAction.VERIFIED

    def test_verifying_a_period_that_does_not_exist_says_so(self, session: Session):
        write(session, effective_from=date(2026, 1, 1), actor="a")
        with pytest.raises(UnknownParameterError):
            verify_parameter(session, CODE, effective_from=date(2020, 1, 1), actor="b")

    def test_verifying_one_period_leaves_the_others_alone(self, session: Session):
        """A figure certified for this year says nothing about last year's."""
        write(session, effective_from=date(2026, 1, 1), actor="a")
        write(session, effective_from=date(2026, 7, 1), value=18, actor="a")
        verify_parameter(session, CODE, effective_from=date(2026, 7, 1), actor="jose.vera")
        rows = {row.effective_from: row for row in history(session, CODE)}
        assert rows[date(2026, 7, 1)].is_verified is True
        assert rows[date(2026, 1, 1)].is_verified is False


class TestTheSeedCli:
    def test_a_dry_run_writes_nothing_and_lists_the_file(self, capsys):
        assert cli_main(["--dry-run"]) == 0
        out = capsys.readouterr().out
        assert "Simulación: no se escribió nada." in out
        assert "apg.max_restoration_hours" in out

    def test_a_missing_file_is_one_line_and_not_a_traceback(self, capsys):
        assert cli_main(["--path", "/no/existe.yaml"]) == 2
        assert "No se pudo leer" in capsys.readouterr().err

    def test_verified_by_with_nothing_verified_in_the_file_warns(self, capsys):
        """Whoever passed it believes they are certifying something."""
        cli_main(["--dry-run", "--verified-by", "maria.perez"])
        assert "no marca ninguna entrada como verificada" in capsys.readouterr().err

    def test_the_loader_attributes_the_load_to_whoever_ran_it(self, session: Session):
        written = apply_seed(session, load_seed(), actor="maria.perez")
        assert written
        assert all(row.created_by == "maria.perez" for row in written)

    def test_the_loader_without_an_actor_is_attributed_to_the_script(self, session: Session):
        written = apply_seed(session, load_seed())
        assert all(row.created_by == SYSTEM_ACTOR for row in written)


ADMIN = Principal(
    subject="kc|admin.funcional",
    username="admin.funcional",
    display_name="Administradora Funcional",
    roles=frozenset({Role.FUNCTIONAL_ADMIN.value}),
    business_units=frozenset({"GYE"}),
)

SUPERVISOR = Principal(
    subject="kc|supervisor.demo",
    username="supervisor.demo",
    display_name="Supervisor Demo",
    roles=frozenset({Role.SUPERVISOR.value}),
    business_units=frozenset({"GYE"}),
)


@pytest.fixture
def client(session: Session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: ADMIN
    with TestClient(app) as raw:
        yield raw


BODY = {
    "code": CODE,
    "value": 24,
    "norm_ref": NORM,
    "effective_from": "2026-01-01",
}


class TestApi:
    def test_the_author_comes_from_the_token(self, client, session: Session):
        body = client.post("/api/v1/regulatory/parameters", json=BODY).json()
        assert body["created_by"] == ADMIN.subject
        assert body["updated_by"] == ADMIN.subject

    def test_a_verified_by_in_the_payload_is_ignored(self, client):
        """A verification the caller could type is a verification nobody made."""
        body = client.post(
            "/api/v1/regulatory/parameters",
            json={**BODY, "verified_by": "quien.yo.diga"},
        ).json()
        assert body["verified"] is False
        assert body["verified_by"] is None

    def test_verifying_is_its_own_endpoint_and_signs_with_the_token(self, client):
        client.post("/api/v1/regulatory/parameters", json=BODY)
        response = client.post(
            f"/api/v1/regulatory/parameters/{CODE}/verify",
            json={"effective_from": "2026-01-01", "note": "leído el texto oficial"},
        )
        assert response.status_code == 200
        assert response.json()["verified_by"] == ADMIN.subject

    def test_verifying_a_period_that_does_not_exist_is_404(self, client):
        client.post("/api/v1/regulatory/parameters", json=BODY)
        response = client.post(
            f"/api/v1/regulatory/parameters/{CODE}/verify",
            json={"effective_from": "1999-01-01"},
        )
        assert response.status_code == 404

    def test_the_revisions_endpoint_tells_the_story(self, client):
        client.post("/api/v1/regulatory/parameters", json=BODY)
        client.post("/api/v1/regulatory/parameters", json={**BODY, "value": 30})
        rows = client.get(f"/api/v1/regulatory/parameters/{CODE}/revisions").json()
        assert [row["action"] for row in rows] == ["creado", "corregido"]
        assert rows[1]["changed"]["value"] == {"from": 24, "to": 30}

    def test_a_supervisor_may_read_and_may_not_write(self, session: Session):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: SUPERVISOR
        with TestClient(app) as supervisor:
            assert supervisor.get("/api/v1/regulatory/parameters").status_code == 200
            assert supervisor.post("/api/v1/regulatory/parameters", json=BODY).status_code == 403
            refused = supervisor.post(
                f"/api/v1/regulatory/parameters/{CODE}/verify",
                json={"effective_from": "2026-01-01"},
            )
            assert refused.status_code == 403

    def test_an_overlapping_period_is_409_and_not_resolved_by_guessing(self, client):
        client.post(
            "/api/v1/regulatory/parameters",
            json={**BODY, "effective_from": "2026-01-01", "effective_to": "2026-12-31"},
        )
        response = client.post(
            "/api/v1/regulatory/parameters", json={**BODY, "effective_from": "2026-06-01"}
        )
        assert response.status_code == 409
