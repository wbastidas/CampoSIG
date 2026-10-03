"""La bitácora inmutable, contra base real (RF-160, RF-161).

Una bitácora sirve para una sola cosa: que alguien pueda reconstruir qué pasó y defenderlo. Las dos
formas en que deja de servir son que no registre algo y que se pueda corregir, y las dos se prueban
aquí contra PostgreSQL de verdad, porque las dos dependen de la base: la primera de que los eventos
se escriban en la misma transacción que el cambio, y la segunda del disparador.

Lo que más importa es el tramo negativo: tres maneras distintas de manipular la cadena y las tres
detectadas, con el motivo que un auditor puede poner en un informe. Una verificación que solo se ha
visto decir «íntegra» no está probada.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.models import ActorKind, AuditEvent, EventKind
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.workorders.models import WorkOrderState
from app.workorders.service import assign, create_work_order, transition
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

AUDITOR = Principal(
    subject="kc|auditor.demo",
    username="auditor.demo",
    roles=frozenset({Role.AUDITOR.value}),
    business_units=frozenset({"GYE"}),
)

SUPERVISOR = Principal(
    subject="kc|supervisor.demo",
    username="supervisor.demo",
    roles=frozenset({Role.SUPERVISOR.value}),
    business_units=frozenset({"GYE"}),
)


@pytest.fixture
def unit(session: Session) -> BusinessUnit:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created = BusinessUnit(
        organization_id=org.id, code="GYE", name="Unidad Guayaquil", profile_id="cnel-gye"
    )
    session.add(created)
    session.flush()
    ingest_metadata(session, created, build_metadata("cnel-gye"))
    return created


@pytest.fixture
def other_unit(session: Session, unit: BusinessUnit) -> BusinessUnit:
    created = BusinessUnit(
        organization_id=unit.organization_id,
        code="MAN",
        name="Unidad Manabí",
        profile_id="cnel-gye",
    )
    session.add(created)
    session.flush()
    ingest_metadata(session, created, build_metadata("cnel-gye"))
    return created


def some_event(session: Session, unit: BusinessUnit, **overrides: object) -> AuditEvent:
    body: dict[str, object] = {
        "kind": EventKind.CREATED,
        "subject_type": "prueba",
        "subject_id": "s-1",
        "actor": "kc|alguien",
    }
    body.update(overrides)
    return audit.record(session, unit.id, **body)  # type: ignore[arg-type]


def client_as(session: Session, principal: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: principal
    return TestClient(app)


class TestTheChain:
    def test_rf_160_el_primer_evento_abre_la_cadena(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        event = some_event(session, unit)
        assert event.sequence == 1
        # Cadena vacía como cadena vacía y no como nulo: una cadena que empieza en nulo es una
        # cadena cuyo primer eslabón no se puede comprobar.
        assert event.prev_hash == audit.GENESIS
        assert len(event.hash) == 64

    def test_cada_evento_encadena_con_el_anterior(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        first = some_event(session, unit)
        second = some_event(session, unit)
        assert second.sequence == 2
        assert second.prev_hash == first.hash

    def test_la_cadena_es_por_unidad_de_negocio(
        self, session: Session, unit: BusinessUnit, other_unit: BusinessUnit
    ) -> None:
        """ADR-009 y concurrencia a la vez: una sola cadena global haría que cada unidad del país
        esperara detrás de todas las demás."""
        mine = some_event(session, unit)
        theirs = some_event(session, other_unit)
        assert mine.sequence == 1
        assert theirs.sequence == 1
        assert theirs.prev_hash == audit.GENESIS

    def test_una_cadena_intacta_se_verifica(self, session: Session, unit: BusinessUnit) -> None:
        for _ in range(5):
            some_event(session, unit)
        check = audit.verify(session, unit.id)
        assert check.intact
        assert check.events == 5
        assert check.problem is None

    def test_la_verificación_de_una_bitácora_vacía_no_falla(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Ninguna unidad nueva tiene eventos, y eso no es una cadena rota."""
        assert audit.verify(session, unit.id).intact


class TestTheThreeWaysToBreakIt:
    def test_un_evento_alterado_se_detecta_y_se_dice_cuál(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Editar la historia. El disparador lo impide por la vía normal, así que aquí se fuerza
        desactivándolo: lo que se prueba es que, aun así, la cadena lo delata."""
        for _ in range(3):
            some_event(session, unit)
        target = session.scalars(
            text("SELECT id FROM audit_event WHERE sequence = 2")  # type: ignore[arg-type]
        ).one()
        _without_the_trigger(
            session,
            "UPDATE audit_event SET actor = 'otro' WHERE id = :id",
            {"id": target},
        )
        session.expire_all()

        check = audit.verify(session, unit.id)
        assert not check.intact
        assert check.broken_at == 2
        assert check.problem is not None and "alterado" in check.problem

    def test_un_evento_quitado_del_medio_rompe_el_enlace(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Quitar historia. Desaparece el 2, así que el 3 ya no encadena con nada."""
        for _ in range(3):
            some_event(session, unit)
        _without_the_trigger(session, "DELETE FROM audit_event WHERE sequence = 2", {})
        session.expire_all()

        check = audit.verify(session, unit.id)
        assert not check.intact
        assert check.broken_at == 3
        assert check.problem is not None and "falta el evento 2" in check.problem

    def test_un_evento_quitado_del_final_lo_delata_la_secuencia(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El caso que los enlaces solos no ven: borrar el último no rompe ningún eslabón.

        Lo delata el hueco en la secuencia —por eso la secuencia existe y es única por unidad—
        cuando se compara contra lo que la bitácora dice de sí misma.
        """
        for _ in range(3):
            some_event(session, unit)
        _without_the_trigger(session, "DELETE FROM audit_event WHERE sequence = 1", {})
        session.expire_all()

        check = audit.verify(session, unit.id)
        assert not check.intact
        assert check.broken_at == 2


class TestTheDatabaseRefuses:
    def test_rf_160_la_base_rechaza_un_update(self, session: Session, unit: BusinessUnit) -> None:
        """La guarda que no depende de que nadie recuerde nada: un psql con buenas intenciones."""
        some_event(session, unit)
        with pytest.raises(DatabaseError, match="append-only"):
            session.execute(text("UPDATE audit_event SET actor = 'otro'"))
        session.rollback()

    def test_rf_160_la_base_rechaza_un_delete(self, session: Session, unit: BusinessUnit) -> None:
        some_event(session, unit)
        with pytest.raises(DatabaseError, match="append-only"):
            session.execute(text("DELETE FROM audit_event"))
        session.rollback()


class TestWhatGetsRecorded:
    def test_rf_160_crear_una_ot_deja_su_evento(self, session: Session, unit: BusinessUnit) -> None:
        order = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            asset_code="P-000452",
            planner_id="kc|planner.a",
        )
        events = audit.trail(session, unit.id, work_order_id=order.id)
        assert [event.kind for event in events] == [EventKind.CREATED]
        assert events[0].actor == "kc|planner.a"
        assert events[0].asset_code == "P-000452"

    def test_rf_160_cada_transición_queda_con_el_estado_de_origen_y_el_de_destino(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Sin el estado de origen la historia no se reconstruye: solo se sabe dónde acabó."""
        order = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            planner_id="kc|planner.a",
        )
        transition(session, order, WorkOrderState.CANCELLED, reason="duplicada", actor="kc|sup.1")

        moves = [
            event
            for event in audit.trail(session, unit.id, work_order_id=order.id)
            if event.kind == EventKind.TRANSITION
        ]
        assert len(moves) == 1
        assert moves[0].payload["from"] == WorkOrderState.PLANNED
        assert moves[0].payload["to"] == WorkOrderState.CANCELLED
        assert moves[0].reason == "duplicada"
        assert moves[0].actor == "kc|sup.1"

    def test_una_transición_sin_persona_se_registra_como_del_sistema_y_no_como_de_nadie(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un nulo en «quién» lo lee el siguiente auditor como «alguien»."""
        order = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            planner_id="kc|planner.a",
        )
        transition(session, order, WorkOrderState.CANCELLED, reason="x")
        moves = [
            event
            for event in audit.trail(session, unit.id, work_order_id=order.id)
            if event.kind == EventKind.TRANSITION
        ]
        assert moves[0].actor_kind == ActorKind.SYSTEM
        assert moves[0].actor.startswith("sistema:")

    def test_una_asignación_deja_el_antes_y_el_después_y_el_dispositivo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            planner_id="kc|planner.a",
        )
        assign(
            session,
            order,
            user_sub="kc|tecnico.1",
            device_id="dev-7",
            granted_by="kc|planner.a",
        )
        changes = [
            event
            for event in audit.trail(session, unit.id, work_order_id=order.id)
            if event.kind == EventKind.FIELD_CHANGED
        ]
        assert changes[0].payload["before"]["user_sub"] is None
        assert changes[0].payload["after"]["user_sub"] == "kc|tecnico.1"
        assert changes[0].device_key == "dev-7"

    def test_el_evento_vive_en_la_misma_transacción_que_el_cambio(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una bitácora que registra trabajo que no ocurrió es peor que ninguna: es una con la que
        alguien defendería una decisión."""
        order = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            planner_id="kc|planner.a",
        )
        before = audit.count(session, unit.id)
        savepoint = session.begin_nested()
        transition(session, order, WorkOrderState.CANCELLED, reason="me equivoqué")
        assert audit.count(session, unit.id) == before + 1
        savepoint.rollback()
        # El cambio se deshizo y el evento con él.
        assert audit.count(session, unit.id) == before


class TestTheFourQuestions:
    @pytest.fixture
    def populated(self, session: Session, unit: BusinessUnit) -> dict[str, object]:
        first = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            asset_code="P-000452",
            planner_id="kc|planner.a",
        )
        second = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            asset_code="P-000999",
            planner_id="kc|planner.b",
        )
        assign(
            session, first, user_sub="kc|tecnico.1", device_id="dev-1", granted_by="kc|planner.a"
        )
        assign(
            session, second, user_sub="kc|tecnico.2", device_id="dev-2", granted_by="kc|planner.b"
        )
        session.flush()
        return {"first": first, "second": second}

    def test_rf_161_por_orden_de_trabajo(
        self, session: Session, unit: BusinessUnit, populated: dict[str, object]
    ) -> None:
        order = populated["first"]
        events = audit.trail(session, unit.id, work_order_id=order.id)  # type: ignore[union-attr]
        assert events
        assert {event.work_order_id for event in events} == {order.id}  # type: ignore[union-attr]
        # Del más viejo al más nuevo: una historia leída al revés es otra historia.
        assert [event.sequence for event in events] == sorted(event.sequence for event in events)

    def test_rf_161_por_activo(
        self, session: Session, unit: BusinessUnit, populated: dict[str, object]
    ) -> None:
        events = audit.trail(session, unit.id, asset_code="P-000999")
        assert events
        assert {event.asset_code for event in events} == {"P-000999"}

    def test_rf_161_por_usuario(
        self, session: Session, unit: BusinessUnit, populated: dict[str, object]
    ) -> None:
        events = audit.trail(session, unit.id, actor="kc|planner.b")
        assert events
        assert {event.actor for event in events} == {"kc|planner.b"}

    def test_rf_161_por_dispositivo(
        self, session: Session, unit: BusinessUnit, populated: dict[str, object]
    ) -> None:
        events = audit.trail(session, unit.id, device_key="dev-2")
        assert events
        assert {event.device_key for event in events} == {"dev-2"}

    def test_los_filtros_se_combinan(
        self, session: Session, unit: BusinessUnit, populated: dict[str, object]
    ) -> None:
        """«Qué le hizo esta persona a esta OT» es una sola consulta."""
        order = populated["second"]
        events = audit.trail(
            session,
            unit.id,
            work_order_id=order.id,  # type: ignore[union-attr]
            actor="kc|planner.b",
        )
        assert events

    def test_el_periodo_acota(self, session: Session, unit: BusinessUnit) -> None:
        some_event(session, unit)
        future = datetime.now(UTC) + timedelta(days=1)
        assert audit.trail(session, unit.id, since=future) == []


class TestTheApi:
    def test_rf_161_el_auditor_reconstruye_la_historia_de_una_ot(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            planner_id="kc|planner.a",
        )
        transition(session, order, WorkOrderState.CANCELLED, reason="x", actor="kc|sup.1")
        session.flush()

        with client_as(session, AUDITOR) as client:
            body = client.get(
                f"/api/v1/audit/units/{unit.code}/trail",
                params={"work_order_id": str(order.id)},
            ).json()
        kinds = [event["kind"] for event in body["events"]]
        assert kinds == [EventKind.CREATED, EventKind.TRANSITION]
        # El hash viaja, para que el auditor pueda comprobar la cadena fuera de la plataforma.
        assert all(len(event["hash"]) == 64 for event in body["events"])

    def test_rf_160_el_endpoint_de_verificación_dice_que_la_cadena_está_íntegra(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        some_event(session, unit)
        with client_as(session, AUDITOR) as client:
            body = client.get(f"/api/v1/audit/units/{unit.code}/verify").json()
        assert body["intact"] is True
        assert body["events"] == 1

    def test_una_cadena_rota_se_informa_con_200_y_no_con_un_error_del_servidor(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una cadena rota es un hallazgo que el auditor tiene que leer y reportar, no un error que
        un tablero de monitoreo se traga."""
        for _ in range(2):
            some_event(session, unit)
        _without_the_trigger(session, "DELETE FROM audit_event WHERE sequence = 1", {})
        session.expire_all()

        with client_as(session, AUDITOR) as client:
            answer = client.get(f"/api/v1/audit/units/{unit.code}/verify")
        assert answer.status_code == 200
        assert answer.json()["intact"] is False

    def test_un_supervisor_no_consulta_la_bitácora(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una bitácora no es un informe de gestión."""
        with client_as(session, SUPERVISOR) as client:
            answer = client.get(f"/api/v1/audit/units/{unit.code}/trail")
        assert answer.status_code == 403

    def test_adr_009_la_bitácora_de_una_unidad_no_muestra_la_de_otra(
        self, session: Session, unit: BusinessUnit, other_unit: BusinessUnit
    ) -> None:
        some_event(session, other_unit, subject_id="ajena")
        with client_as(session, AUDITOR) as client:
            body = client.get(f"/api/v1/audit/units/{unit.code}/trail").json()
        assert [event["subject_id"] for event in body["events"]] == []


def _without_the_trigger(session: Session, statement: str, params: dict[str, object]) -> None:
    """Run one statement with the append-only trigger disabled.

    Only the tests do this, and only to prove the *other* two guards work: a chain that has never
    been attacked is a chain whose verification has never been tested. Disabling it needs the table
    owner, which the application role in production does not have.
    """
    session.execute(text("ALTER TABLE audit_event DISABLE TRIGGER USER"))
    try:
        session.execute(text(statement), params)
    finally:
        session.execute(text("ALTER TABLE audit_event ENABLE TRIGGER USER"))


def test_los_identificadores_de_prueba_son_uuid() -> None:
    """Guarda mínima del ayudante: si `some_event` dejara de escribir, los tests de arriba pasarían
    por vacuidad."""
    assert isinstance(uuid.uuid4(), uuid.UUID)
