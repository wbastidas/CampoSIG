"""El borde HTTP del teléfono: enrolar, pedir y entregar (RF-004, RF-101 a RF-106).

El servicio de sincronización existía y estaba probado, y **no tenía router**: el teléfono no tenía
a qué llamar. Estas pruebas son ese contrato, por donde se ejercita de verdad — por HTTP, con token,
con rol y con la clave del dispositivo.

Lo que se prueba, en el orden en que importa:

* **Entregar aplica algo.** `push_operation` solo escribía el asiento de idempotencia; una captura
  entregada quedaba registrada y las respuestas no se guardaban en ninguna parte. Aquí una captura
  entregada tiene que poder leerse después como respuesta del formulario, con sus evidencias.
* **Un reenvío no aplica dos veces** y devuelve el resultado guardado (RF-105).
* **Lo que no se puede aplicar se rechaza con su motivo**, nunca con un 500: el teléfono aparca esa
  operación y se la muestra a una persona. Un error de servidor la reintentaría para siempre.
* **Un dispositivo no lleva una OT a «aprobada»**: eso lo decide la oficina, y la tabla de
  transiciones sola lo aceptaría de un teléfono.
* **Nada cruza entre unidades de negocio** (ADR-009), y una clave de dispositivo no sirve para
  traerse el trabajo de otra persona: la clave se puede copiar, el token no.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.outages import service as outages
from app.responses.models import Evidence, FormResponse, ResponseState
from app.sync.models import Device, DeviceStatus, SyncOperationLog
from app.sync.service import block_device, enrol_device
from app.workorders.models import WorkOrder, WorkOrderState
from app.workorders.service import create_work_order

pytestmark = pytest.mark.integration

DEVICE_KEY = "phone-00000001"

TECHNICIAN = Principal(
    subject="kc|tecnico.demo",
    username="tecnico.demo",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)
OTHER_TECHNICIAN = Principal(
    subject="kc|tecnico.otro",
    username="tecnico.otro",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)
PLANNER = Principal(
    subject="kc|planificador.demo",
    username="planificador.demo",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE"}),
)
CONTROL = Principal(
    subject="kc|centro.control",
    username="centro.control",
    roles=frozenset({Role.SUPERVISOR.value}),
    business_units=frozenset({"GYE"}),
)
IT = Principal(
    subject="kc|soporte.ti",
    username="soporte.ti",
    roles=frozenset({Role.IT_ADMIN.value}),
    business_units=frozenset({"GYE", "MAN"}),
)


@pytest.fixture
def units(session: Session) -> dict[str, BusinessUnit]:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created: dict[str, BusinessUnit] = {}
    for code, name in (("GYE", "Unidad Guayaquil"), ("MAN", "Unidad Manabí")):
        unit = BusinessUnit(organization_id=org.id, code=code, name=name, profile_id="cnel-gye")
        session.add(unit)
        session.flush()
        created[code] = unit
    return created


@pytest.fixture
def unit(units: dict[str, BusinessUnit]) -> BusinessUnit:
    return units["GYE"]


@pytest.fixture
def device(session: Session, unit: BusinessUnit) -> Device:
    created, _ = enrol_device(
        session,
        unit,
        device_key=DEVICE_KEY,
        user_sub=TECHNICIAN.subject,
        model="Pixel 8a",
    )
    return created


def an_order(
    session: Session,
    unit: BusinessUnit,
    *,
    state: str = WorkOrderState.ASSIGNED,
    user_sub: str | None = TECHNICIAN.subject,
    code: str = "OT-2026-0001",
) -> WorkOrder:
    order = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        longitude=-79.9,
        latitude=-2.17,
        zone="norte",
        planner_id=PLANNER.subject,
    )
    order.state = state
    order.form_version = "1.1.0"
    order.assigned_user_sub = user_sub
    order.code = code
    session.flush()
    return order


def full_answers(**overrides: Any) -> dict[str, Any]:
    """Respuestas que satisfacen F-MT-01, para partir de una captura válida."""
    answers: dict[str, Any] = {
        "work_order_code": "OT-2026-0001",
        "work_type": "inspeccion_preventiva",
        "priority": "media",
        "gps": {"latitude": -2.17, "longitude": -79.9, "accuracy_m": 4.0},
        "general_condition": "regular",
        "code": "P-000452",
        "material": "concrete",
        "feeder_code": "04BH070T11",
        "height_m": 11.0,
        "final_state": "resuelto",
        "ats_reference": "ATS-2026-0001",
        "photos_before": ["s3://a.jpg", "s3://b.jpg"],
        "photos_after": [],
    }
    answers.update(overrides)
    return answers


def client_as(session: Session, who: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: who
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with client_as(session, TECHNICIAN) as raw:
        yield raw


def push(client: TestClient, *operations: dict[str, Any], unit_code: str = "GYE") -> Any:
    return client.post(
        f"/api/v1/sync/units/{unit_code}/push",
        json={"device_key": DEVICE_KEY, "operations": list(operations)},
    )


def operation(op_kind: str, order: WorkOrder | None = None, **payload: Any) -> dict[str, Any]:
    """Una operación como la manda el teléfono.

    El primer parámetro se llama `op_kind` y no `kind` porque una evidencia lleva su propio `kind`
    en el payload, y los dos nombres chocaban.
    """
    return {
        "operation_id": payload.pop("operation_id", f"op-{uuid.uuid4().hex[:8]}"),
        "kind": op_kind,
        "work_order_id": str(order.id) if order else None,
        "payload": payload,
    }


class TestEnrolment:
    def test_rf_004_el_titular_del_dispositivo_sale_del_token(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        """Un dispositivo cuyo titular pudiera escribir el llamante haría decorativa la dueñez."""
        response = client.post(
            "/api/v1/sync/units/GYE/devices",
            json={"device_key": DEVICE_KEY, "model": "Pixel 8a", "user_sub": "kc|otra.persona"},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["user_sub"] == TECHNICIAN.subject
        assert body["created"] is True
        assert body["business_unit"] == "GYE"

    def test_rf_004_enrolar_dos_veces_no_crea_dos_dispositivos(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        """La app se reenrola en cada actualización y tras una reinstalación."""
        first = client.post(
            "/api/v1/sync/units/GYE/devices", json={"device_key": DEVICE_KEY, "app_version": "1.0"}
        )
        second = client.post(
            "/api/v1/sync/units/GYE/devices", json={"device_key": DEVICE_KEY, "app_version": "1.1"}
        )

        assert first.json()["created"] is True
        assert second.json()["created"] is False
        assert second.json()["device_id"] == first.json()["device_id"]
        rows = session.execute(select(Device).where(Device.device_key == DEVICE_KEY)).scalars()
        assert len(list(rows)) == 1

    def test_rf_004_un_dispositivo_no_se_muda_de_unidad_de_negocio(
        self, session: Session, units: dict[str, BusinessUnit], device: Device
    ) -> None:
        """Reenrolarlo en otra unidad movería de geodatabase lo capturado (ADR-009)."""
        with client_as(session, IT) as api:
            response = api.post("/api/v1/sync/units/MAN/devices", json={"device_key": DEVICE_KEY})

        assert response.status_code == 409
        assert session.get(Device, device.id).business_unit_id == units["GYE"].id

    def test_rf_004_quien_no_lleva_un_telefono_no_enrola(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        with client_as(session, PLANNER) as api:
            response = api.post("/api/v1/sync/units/GYE/devices", json={"device_key": DEVICE_KEY})

        assert response.status_code == 403


class TestPull:
    def test_rf_102_el_telefono_recibe_su_ot_con_ubicacion_y_version_de_formulario(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit)

        response = client.get(f"/api/v1/sync/units/GYE/pull?device_key={DEVICE_KEY}")

        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["work_orders"]) == 1
        row = body["work_orders"][0]
        assert row["work_order_id"] == str(order.id)
        assert row["longitude"] == pytest.approx(-79.9)
        assert row["latitude"] == pytest.approx(-2.17)
        # La versión congelada al asignar, no la vigente hoy (RF-032).
        assert row["form_version"] == "1.1.0"
        assert body["next_cursor"]
        assert body["form_versions"]["F-MT-01"]

    def test_rf_102_el_cursor_no_devuelve_dos_veces_lo_mismo(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        an_order(session, unit)
        first = client.get(f"/api/v1/sync/units/GYE/pull?device_key={DEVICE_KEY}").json()

        second = client.get(
            f"/api/v1/sync/units/GYE/pull?device_key={DEVICE_KEY}&cursor={first['next_cursor']}"
        ).json()

        assert second["work_orders"] == []
        # Nulo y no el mismo cursor: el teléfono conserva el que ya tenía.
        assert second["next_cursor"] is None

    def test_rf_102_el_telefono_no_recibe_el_trabajo_de_otra_persona(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        an_order(session, unit, user_sub="kc|tecnico.otro", code="OT-2026-0002")

        body = client.get(f"/api/v1/sync/units/GYE/pull?device_key={DEVICE_KEY}").json()

        assert body["work_orders"] == []

    def test_rf_024_la_consignacion_viaja_con_la_ot(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """El F-TR-02 se llena en una subestación sin cobertura: el número tiene que ir dentro."""
        order = an_order(session, unit)
        request = outages.request_outage(
            session,
            unit,
            equipment="Alimentador 04BH070T11, tramo sur",
            window_start=datetime(2026, 9, 26, 11, tzinfo=UTC),
            window_end=datetime(2026, 9, 26, 17, tzinfo=UTC),
            requested_by=PLANNER.subject,
        )
        outages.approve(session, unit, request, number="DESC-2026-0771", decided_by=CONTROL.subject)
        outages.link(session, unit, order, request, actor=PLANNER.subject)

        body = client.get(f"/api/v1/sync/units/GYE/pull?device_key={DEVICE_KEY}").json()

        outage = body["work_orders"][0]["outage"]
        assert outage["number"] == "DESC-2026-0771"
        assert outage["grants_permit"] is True

    def test_rf_004_un_dispositivo_bloqueado_recibe_la_orden_de_borrarse(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        block_device(session, device, reason="teléfono perdido en Milagro")

        response = client.get(f"/api/v1/sync/units/GYE/pull?device_key={DEVICE_KEY}")

        assert response.status_code == 403
        assert response.json()["detail"]["wipe"] is True

    def test_rf_004_el_borrado_se_confirma_y_queda_con_su_hora(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """Sin esto, quien bloqueó un teléfono perdido no sabe si el borrado ocurrió."""
        block_device(session, device, reason="teléfono perdido")

        response = client.post(f"/api/v1/sync/units/GYE/wipe-acknowledged?device_key={DEVICE_KEY}")

        assert response.status_code == 200
        assert response.json()["wipe_acknowledged_at"]
        assert session.get(Device, device.id).wipe_acknowledged_at is not None
        assert session.get(Device, device.id).status == DeviceStatus.BLOCKED

    def test_rf_102_una_clave_de_dispositivo_no_trae_el_trabajo_de_su_dueno(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        """La clave viaja en un QR y se puede copiar; el token no."""
        an_order(session, unit)

        with client_as(session, OTHER_TECHNICIAN) as api:
            response = api.get(f"/api/v1/sync/units/GYE/pull?device_key={DEVICE_KEY}")

        assert response.status_code == 403
        assert "otra persona" in response.json()["detail"]

    def test_rf_102_un_dispositivo_de_otra_unidad_no_existe_para_esta(
        self, session: Session, units: dict[str, BusinessUnit], device: Device
    ) -> None:
        with client_as(session, IT) as api:
            response = api.get(f"/api/v1/sync/units/MAN/pull?device_key={DEVICE_KEY}")

        assert response.status_code == 404

    def test_rf_102_un_dispositivo_sin_enrolar_no_sincroniza(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        response = client.get("/api/v1/sync/units/GYE/pull?device_key=phone-desconocido")

        assert response.status_code == 404


class TestPushApplies:
    def test_rf_101_una_captura_entregada_se_guarda_de_verdad(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """La prueba que faltaba: el asiento de idempotencia no es guardar la captura."""
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)

        response = push(
            client, operation("form_response", order, answers=full_answers(), submit=False)
        )

        assert response.status_code == 200, response.text
        outcome = response.json()["operations"][0]
        assert outcome["accepted"] is True
        assert outcome["replay"] is False
        saved = session.execute(
            select(FormResponse).where(FormResponse.work_order_id == order.id)
        ).scalar_one()
        assert saved.answers["code"] == "P-000452"
        assert outcome["result"]["response_id"] == str(saved.id)

    def test_rf_101_una_evidencia_entregada_queda_contra_su_respuesta(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        digest = hashlib.sha256(b"foto-antes").hexdigest()

        response = push(
            client,
            operation("form_response", order, answers=full_answers()),
            operation(
                "evidence",
                order,
                kind="foto",
                storage_key="s3://antes-1.jpg",
                content_hash=digest,
                stage="antes",
                latitude=-2.17,
                longitude=-79.9,
            ),
        )

        assert response.json()["accepted"] == 2
        evidence = session.execute(select(Evidence)).scalars().all()
        assert [item.content_hash for item in evidence] == [digest]
        assert evidence[0].stage == "antes"

    def test_rf_101_una_evidencia_sin_su_respuesta_se_rechaza_diciendo_el_orden(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """El orden es parte del contrato: la evidencia cuelga de una respuesta."""
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)

        response = push(
            client,
            operation(
                "evidence",
                order,
                kind="foto",
                storage_key="s3://antes-1.jpg",
                content_hash=hashlib.sha256(b"x").hexdigest(),
            ),
        )

        outcome = response.json()["operations"][0]
        assert outcome["accepted"] is False
        assert "antes que sus evidencias" in outcome["rejection_reason"]

    def test_rf_101_una_evidencia_sin_hash_se_aparca(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """Una evidencia sin hash es una foto que nadie puede verificar después.

        El hash es lo que sostiene la cadena de custodia: sin él la revisión no puede decir que la
        foto que mira es la que se tomó. `register_evidence` acepta la cadena vacía sin protestar,
        así que el borde es el que tiene que negarse.
        """
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)

        response = push(
            client,
            operation("form_response", order, answers=full_answers()),
            operation("evidence", order, kind="foto", storage_key="s3://antes-1.jpg"),
        )

        outcome = response.json()["operations"][1]
        assert outcome["accepted"] is False
        assert "hash" in outcome["rejection_reason"]
        assert session.execute(select(Evidence)).first() is None

    def test_rf_016_un_cambio_de_estado_entregado_mueve_la_ot(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.DOWNLOADED)

        response = push(client, operation("transition", order, target="en_camino"))

        assert response.json()["operations"][0]["result"] == {
            "from": "descargada",
            "to": "en_camino",
        }
        assert session.get(WorkOrder, order.id).state == WorkOrderState.EN_ROUTE

    def test_rf_016_un_dispositivo_no_aprueba_una_ot(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """Aprobar es de la oficina. La tabla de transiciones sola lo aceptaría del teléfono."""
        order = an_order(session, unit, state=WorkOrderState.IN_REVIEW)

        response = push(client, operation("transition", order, target="aprobada"))

        outcome = response.json()["operations"][0]
        assert outcome["accepted"] is False
        assert "decisión de la oficina" in outcome["rejection_reason"]
        assert session.get(WorkOrder, order.id).state == WorkOrderState.IN_REVIEW

    def test_rf_016_una_transicion_imposible_se_rechaza_con_los_permitidos(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.ASSIGNED)

        response = push(client, operation("transition", order, target="cerrada_campo"))

        outcome = response.json()["operations"][0]
        assert outcome["accepted"] is False
        assert "no se puede pasar" in outcome["rejection_reason"]

    def test_rf_016_suspender_sin_motivo_se_rechaza(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.ON_SITE)

        response = push(client, operation("transition", order, target="suspendida"))

        assert "exige un motivo" in response.json()["operations"][0]["rejection_reason"]
        assert session.get(WorkOrder, order.id).state == WorkOrderState.ON_SITE

    def test_rf_103_una_captura_invalida_se_rechaza_con_el_motivo_y_no_con_un_500(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """Un 500 haría que la bandeja de salida la reintentara para siempre."""
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)

        response = push(
            client,
            operation(
                "form_response", order, answers=full_answers(general_condition=None), submit=True
            ),
        )

        assert response.status_code == 200
        outcome = response.json()["operations"][0]
        assert outcome["accepted"] is False
        assert outcome["rejection_reason"]
        assert (
            session.execute(
                select(FormResponse).where(FormResponse.work_order_id == order.id)
            ).scalar_one_or_none()
            is None
        )

    def test_rf_103_un_tipo_de_operacion_desconocido_se_aparca_con_los_admitidos(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """Un teléfono con una versión que el servidor no conoce: adivinar pierde capturas."""
        order = an_order(session, unit)

        response = push(client, operation("telemetria_de_bateria", order, level=12))

        outcome = response.json()["operations"][0]
        assert outcome["accepted"] is False
        assert "no conoce operaciones" in outcome["rejection_reason"]

    def test_rf_103_una_operacion_sin_ot_se_aparca(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        response = push(client, operation("transition", None, target="en_camino"))

        assert "necesita la OT" in response.json()["operations"][0]["rejection_reason"]

    def test_rf_105_una_ot_que_no_existe_se_aparca_sin_reventar(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        payload = {
            "operation_id": "op-huerfana",
            "kind": "transition",
            "work_order_id": str(uuid.uuid4()),
            "payload": {"target": "en_camino"},
        }

        response = push(client, payload)

        outcome = response.json()["operations"][0]
        assert outcome["accepted"] is False
        assert outcome["rejection_reason"] == "la OT no existe"


class TestIdempotency:
    def test_rf_105_reenviar_no_aplica_dos_veces_y_devuelve_lo_guardado(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.DOWNLOADED)
        step = operation("transition", order, target="en_camino", operation_id="op-fija")

        first = push(client, step).json()["operations"][0]
        second = push(client, step).json()["operations"][0]

        assert first["replay"] is False
        assert second["replay"] is True
        # El mismo resultado, sin volver a mover nada: la OT no pasó de en_camino a lo siguiente.
        assert second["result"] == first["result"]
        assert session.get(WorkOrder, order.id).state == WorkOrderState.EN_ROUTE
        rows = session.execute(
            select(SyncOperationLog).where(SyncOperationLog.operation_id == "op-fija")
        ).scalars()
        assert len(list(rows)) == 1

    def test_rf_105_reenviar_una_captura_no_duplica_la_respuesta(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        step = operation("form_response", order, answers=full_answers(), operation_id="op-captura")

        push(client, step)
        push(client, step)

        rows = session.execute(
            select(FormResponse).where(FormResponse.work_order_id == order.id)
        ).scalars()
        assert len(list(rows)) == 1

    def test_rf_105_el_reenvio_de_un_rechazo_devuelve_el_mismo_rechazo(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """Si el reenvío volviera a intentarlo, la bandeja de salida nunca podría cerrar la fila."""
        order = an_order(session, unit, state=WorkOrderState.ASSIGNED)
        step = operation("transition", order, target="cerrada_campo", operation_id="op-mala")

        first = push(client, step).json()["operations"][0]
        second = push(client, step).json()["operations"][0]

        assert first["accepted"] is False
        assert second["accepted"] is False
        assert second["replay"] is True
        assert second["rejection_reason"] == first["rejection_reason"]

    def test_rf_105_dos_dispositivos_pueden_usar_el_mismo_id_de_operacion(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        """Los ids los genera cada teléfono: la clave de idempotencia es (dispositivo, id)."""
        other, _ = enrol_device(
            session, unit, device_key="phone-00000002", user_sub=OTHER_TECHNICIAN.subject
        )
        mine = an_order(session, unit, state=WorkOrderState.DOWNLOADED)
        theirs = an_order(
            session,
            unit,
            state=WorkOrderState.DOWNLOADED,
            user_sub=OTHER_TECHNICIAN.subject,
            code="OT-2026-0002",
        )

        with client_as(session, TECHNICIAN) as api:
            first = api.post(
                "/api/v1/sync/units/GYE/push",
                json={
                    "device_key": DEVICE_KEY,
                    "operations": [
                        operation("transition", mine, target="en_camino", operation_id="op-1")
                    ],
                },
            )
        with client_as(session, OTHER_TECHNICIAN) as api:
            second = api.post(
                "/api/v1/sync/units/GYE/push",
                json={
                    "device_key": other.device_key,
                    "operations": [
                        operation("transition", theirs, target="en_camino", operation_id="op-1")
                    ],
                },
            )

        assert first.json()["operations"][0]["replay"] is False
        assert second.json()["operations"][0]["replay"] is False


class TestUnitIsolation:
    def test_rf_102_una_operacion_sobre_otra_unidad_aborta_el_lote(
        self, session: Session, units: dict[str, BusinessUnit], device: Device, client: TestClient
    ) -> None:
        """Un dispositivo que manda trabajo de otra unidad es una anomalía, no un dato malo."""
        mine = an_order(session, units["GYE"], state=WorkOrderState.DOWNLOADED)
        foreign = an_order(session, units["MAN"], state=WorkOrderState.DOWNLOADED, code="OT-MAN-1")

        response = push(
            client,
            operation("transition", mine, target="en_camino"),
            operation("transition", foreign, target="en_camino"),
        )

        assert response.status_code == 403
        # Y no se aplicó nada, ni lo que era legítimo: el lote se revisa antes de aplicar.
        assert session.get(WorkOrder, mine.id).state == WorkOrderState.DOWNLOADED
        assert (
            session.execute(
                select(SyncOperationLog).where(SyncOperationLog.device_id == device.id)
            ).first()
            is None
        )

    def test_rf_102_el_planificador_no_entrega_capturas(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.DOWNLOADED)

        with client_as(session, PLANNER) as api:
            response = api.post(
                "/api/v1/sync/units/GYE/push",
                json={
                    "device_key": DEVICE_KEY,
                    "operations": [operation("transition", order, target="en_camino")],
                },
            )

        assert response.status_code == 403

    def test_rf_102_nadie_sincroniza_en_una_unidad_fuera_de_su_alcance(
        self, session: Session, units: dict[str, BusinessUnit], device: Device, client: TestClient
    ) -> None:
        """ADR-009 desde el borde: el token del técnico solo alcanza a GYE."""
        response = client.get(f"/api/v1/sync/units/MAN/pull?device_key={DEVICE_KEY}")

        assert response.status_code == 403


class TestDelivery:
    def test_rf_104_lo_entregado_al_telefono_queda_registrado_al_bajarlo(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """«Asignada» y «de verdad en el teléfono» son los dos números del despacho."""
        from app.dispatch.models import WorkOrderDelivery

        order = an_order(session, unit)

        client.get(f"/api/v1/sync/units/GYE/pull?device_key={DEVICE_KEY}")

        deliveries = session.execute(
            select(WorkOrderDelivery).where(WorkOrderDelivery.work_order_id == order.id)
        ).scalars()
        assert len(list(deliveries)) == 1

    def test_rf_106_el_pull_dice_la_hora_del_servidor(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """El reloj del teléfono deriva offline; el que manda para el delta es el del servidor."""
        before = datetime.now(UTC) - timedelta(seconds=5)

        body = client.get(f"/api/v1/sync/units/GYE/pull?device_key={DEVICE_KEY}").json()

        assert datetime.fromisoformat(body["server_time"]) >= before


class TestSubmitClosesTheForm:
    def test_rf_101_enviar_la_captura_la_deja_fuera_del_alcance_del_telefono(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        """Una respuesta enviada deja de ser del dispositivo: el siguiente cambio se rechaza."""
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        from app.responses.service import register_evidence

        sent = push(client, operation("form_response", order, answers=full_answers(), submit=False))
        assert sent.json()["accepted"] == 1
        response = session.execute(
            select(FormResponse).where(FormResponse.work_order_id == order.id)
        ).scalar_one()
        for index in range(2):
            register_evidence(
                session,
                response,
                kind="foto",
                storage_key=f"s3://antes-{index}.jpg",
                content_hash=hashlib.sha256(f"antes{index}".encode()).hexdigest(),
                stage="antes",
            )
        session.flush()

        submitted = push(
            client, operation("form_response", order, answers=full_answers(), submit=True)
        )
        assert submitted.json()["operations"][0]["accepted"] is True
        assert (
            session.execute(select(FormResponse).where(FormResponse.work_order_id == order.id))
            .scalar_one()
            .state
            == ResponseState.SUBMITTED
        )

        again = push(
            client, operation("form_response", order, answers=full_answers(), submit=False)
        )
        outcome = again.json()["operations"][0]
        assert outcome["accepted"] is False
        assert "no se puede modificar" in outcome["rejection_reason"]
