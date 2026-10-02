"""El mapa de despacho: OT filtradas y cuadrillas donde su teléfono dijo estar (RF-020).

«El mapa muestra OT y cuadrillas con filtros por área, zona y prioridad», y de las dos mitades la
segunda **no existía**: nada guardaba una posición, así que «la ubicación de cuadrillas según el
último GPS reportado» no se podía contestar de ninguna forma.

Lo que se prueba, en el orden en que importa:

* **Solo existe la última posición.** La clave primaria es el dispositivo: no hay dónde guardar un
  historial de por dónde anduvo un técnico, y ese es el diseño, no una nota de política.
* **Una posición sin su edad miente.** Se captura cuando el teléfono sincroniza, así que es tan
  vieja como el último sync; un punto de hace cuatro horas no se dibuja igual que uno de hace uno.
* **Un GPS sin señal no es una ubicación.** (0, 0) está en el golfo de Guinea y un despachador
  despacharía sobre él.
* **El filtro por área se resuelve por el formulario**, no por el nombre del tipo de trabajo. El que
  había —`work_type.startswith(area)`— no devolvía nada para casi ninguna área, y una bandeja que no
  devuelve nada se lee como «no hay trabajo».
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.dispatch import positions
from app.dispatch.models import DevicePosition
from app.dispatch.service import record_delivery
from app.forms.catalog import codes_for_area
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.sync.models import Device
from app.sync.service import enrol_device
from app.workorders.models import Crew, WorkOrder, WorkOrderState
from app.workorders.service import create_work_order, in_bounding_box

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 24, 15, 0, tzinfo=UTC)
DEVICE_KEY = "phone-00000001"

TECHNICIAN = Principal(
    subject="kc|tecnico.demo",
    username="tecnico.demo",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)
SUPERVISOR = Principal(
    subject="kc|supervisor.demo",
    username="supervisor.demo",
    roles=frozenset({Role.SUPERVISOR.value}),
    business_units=frozenset({"GYE"}),
)
PLANNER = Principal(
    subject="kc|planificador.demo",
    username="planificador.demo",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE"}),
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
        session, unit, device_key=DEVICE_KEY, user_sub=TECHNICIAN.subject, model="Pixel 8a"
    )
    # RF-107: without the person's consent nothing is stored. These tests are about what is done
    # with a position once it may be stored; whether it may is `test_rf107_position_policy.py`'s.
    positions.set_consent(session, unit, created, subject=TECHNICIAN.subject, granted=True)
    return created


@pytest.fixture
def crew(session: Session, unit: BusinessUnit) -> Crew:
    row = Crew(
        business_unit_id=unit.id,
        code="C-01",
        name="Cuadrilla norte",
        competencies=["MT"],
        zone="norte",
    )
    session.add(row)
    session.flush()
    return row


def an_order(
    session: Session,
    unit: BusinessUnit,
    *,
    form_code: str = "F-MT-01",
    work_type: str = "inspeccion_preventiva",
    asset_type_key: str = "support_structure",
    priority: str = "media",
    zone: str | None = "norte",
    crew: Crew | None = None,
    state: str = WorkOrderState.ASSIGNED,
    code: str = "OT-2026-0001",
) -> WorkOrder:
    order = create_work_order(
        session,
        unit,
        work_type=work_type,
        form_code=form_code,
        asset_type_key=asset_type_key,
        priority=priority,
        longitude=-79.9,
        latitude=-2.17,
        zone=zone,
        planner_id=PLANNER.subject,
    )
    order.state = state
    order.code = code
    if crew is not None:
        order.assigned_crew_id = crew.id
    order.assigned_user_sub = TECHNICIAN.subject
    session.flush()
    return order


def client_as(session: Session, who: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: who
    return TestClient(app)


def report(
    client: TestClient,
    *,
    latitude: float = -2.17,
    longitude: float = -79.9,
    accuracy_m: float | None = 8.0,
    reported_at: datetime | None = NOW,
) -> object:
    payload: dict[str, object] = {
        "device_key": DEVICE_KEY,
        "latitude": latitude,
        "longitude": longitude,
    }
    if accuracy_m is not None:
        payload["accuracy_m"] = accuracy_m
    if reported_at is not None:
        payload["reported_at"] = reported_at.isoformat()
    return client.post("/api/v1/sync/units/GYE/position", json=payload)


class TestOnlyTheLastPosition:
    def test_rf_020_el_telefono_reporta_su_posicion(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        with client_as(session, TECHNICIAN) as api:
            response = report(api)

        assert response.status_code == 200, response.text
        stored = session.get(DevicePosition, device.id)
        assert stored is not None
        assert stored.accuracy_m == pytest.approx(8.0)

    def test_rf_020_no_hay_donde_guardar_un_historial_de_movimientos(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        """La clave primaria es el dispositivo: el diseño de privacidad está en el esquema."""
        with client_as(session, TECHNICIAN) as api:
            report(api, latitude=-2.10, reported_at=NOW)
            report(api, latitude=-2.20, reported_at=NOW + timedelta(minutes=5))

        rows = session.execute(select(func.count()).select_from(DevicePosition)).scalar_one()
        assert rows == 1
        found = positions.crew_positions(session, unit, now=NOW + timedelta(minutes=6))
        assert found[0].latitude == pytest.approx(-2.20)

    def test_rf_020_un_reporte_atrasado_no_pisa_al_mas_nuevo(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        """La bandeja de salida reintenta: un punto viejo puede llegar después de uno nuevo."""
        with client_as(session, TECHNICIAN) as api:
            report(api, latitude=-2.20, reported_at=NOW)
            report(api, latitude=-2.10, reported_at=NOW - timedelta(hours=1))

        found = positions.crew_positions(session, unit, now=NOW)
        assert found[0].latitude == pytest.approx(-2.20)

    def test_rf_020_un_gps_sin_senal_no_es_una_ubicacion(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        """(0, 0) está en el golfo de Guinea y alguien despacharía sobre él."""
        with client_as(session, TECHNICIAN) as api:
            response = report(api, latitude=0.0, longitude=0.0)

        assert response.status_code == 422
        assert "sin señal" in response.json()["detail"]
        assert session.get(DevicePosition, device.id) is None

    def test_rf_020_una_posicion_fuera_de_rango_se_rechaza(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        with client_as(session, TECHNICIAN) as api:
            response = report(api, latitude=95.0)

        # Pydantic la para antes del servicio; el servicio la para igual si la llaman directo.
        assert response.status_code == 422
        with pytest.raises(positions.PositionError, match="fuera de rango"):
            positions.report(session, unit, device, latitude=95.0, longitude=-79.9)

    def test_rf_020_una_precision_negativa_se_rechaza(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        with pytest.raises(positions.PositionError, match="precisión"):
            positions.report(
                session, unit, device, latitude=-2.17, longitude=-79.9, accuracy_m=-1.0
            )

    def test_rf_020_el_dispositivo_de_otra_unidad_no_reporta_aqui(
        self, session: Session, units: dict[str, BusinessUnit], device: Device
    ) -> None:
        with pytest.raises(positions.PositionError, match="unidad de negocio"):
            positions.report(session, units["MAN"], device, latitude=-2.17, longitude=-79.9)


class TestAgeAndDoubt:
    def test_rf_020_la_posicion_lleva_su_edad_en_minutos(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        positions.report(
            session,
            unit,
            device,
            latitude=-2.17,
            longitude=-79.9,
            reported_at=NOW - timedelta(minutes=25),
        )

        found = positions.crew_positions(session, unit, now=NOW)

        assert found[0].minutes_old == 25
        assert found[0].stale is False

    def test_rf_020_una_posicion_vieja_se_marca_vieja(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        """Una cuadrilla que no sincroniza en dos horas pudo cruzar toda la concesión."""
        positions.report(
            session,
            unit,
            device,
            latitude=-2.17,
            longitude=-79.9,
            reported_at=NOW - timedelta(hours=3),
        )

        found = positions.crew_positions(session, unit, now=NOW)

        assert found[0].stale is True

    def test_rf_020_una_precision_mala_se_marca_dudosa(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        """Un punto con 900 m de precisión no dice en qué calle está la cuadrilla."""
        positions.report(session, unit, device, latitude=-2.17, longitude=-79.9, accuracy_m=900.0)

        found = positions.crew_positions(session, unit, now=NOW)

        assert found[0].doubtful is True

    def test_rf_020_una_precision_buena_no_es_dudosa(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        positions.report(session, unit, device, latitude=-2.17, longitude=-79.9, accuracy_m=6.0)

        assert positions.crew_positions(session, unit, now=NOW)[0].doubtful is False


class TestCrewsOnTheMap:
    def test_rf_020_el_punto_dice_para_qué_cuadrilla_trabaja_ese_telefono(
        self, session: Session, unit: BusinessUnit, device: Device, crew: Crew
    ) -> None:
        """Un dispositivo es de una persona, no de una cuadrilla: el vínculo sale del trabajo."""
        order = an_order(session, unit, crew=crew)
        record_delivery(session, device, [order])
        positions.report(session, unit, device, latitude=-2.17, longitude=-79.9)

        found = positions.crew_positions(session, unit, now=NOW)

        assert [item["code"] for item in found[0].crews] == ["C-01"]

    def test_rf_020_el_filtro_por_zona_deja_solo_los_telefonos_que_trabajan_ahi(
        self, session: Session, unit: BusinessUnit, device: Device, crew: Crew
    ) -> None:
        order = an_order(session, unit, crew=crew, zone="sur")
        record_delivery(session, device, [order])
        positions.report(session, unit, device, latitude=-2.17, longitude=-79.9)

        assert positions.crew_positions(session, unit, now=NOW, zone="sur")
        assert positions.crew_positions(session, unit, now=NOW, zone="norte") == []

    def test_rf_020_el_geojson_del_mapa_lleva_los_umbrales_del_servidor(
        self, session: Session, unit: BusinessUnit, device: Device, crew: Crew
    ) -> None:
        """Si la web repitiera los umbrales, cambiarlos aquí la dejaría pintando «reciente»."""
        order = an_order(session, unit, crew=crew)
        record_delivery(session, device, [order])
        positions.report(session, unit, device, latitude=-2.17, longitude=-79.9)

        with client_as(session, SUPERVISOR) as api:
            response = api.get("/api/v1/dispatch/units/GYE/crews.geojson")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["type"] == "FeatureCollection"
        assert body["stale_after_minutes"] == 120
        assert body["doubtful_accuracy_m"] == pytest.approx(200.0)
        feature = body["features"][0]
        assert feature["geometry"]["coordinates"] == [pytest.approx(-79.9), pytest.approx(-2.17)]
        assert feature["properties"]["device_key"] == DEVICE_KEY

    def test_rf_020_el_mapa_de_una_unidad_no_muestra_los_telefonos_de_otra(
        self, session: Session, units: dict[str, BusinessUnit], device: Device
    ) -> None:
        positions.report(session, units["GYE"], device, latitude=-2.17, longitude=-79.9)
        other, _ = enrol_device(
            session, units["MAN"], device_key="phone-00000002", user_sub="kc|tecnico.manabi"
        )
        positions.report(session, units["MAN"], other, latitude=-1.05, longitude=-80.45)

        found = positions.crew_positions(session, units["GYE"], now=NOW)

        assert [row.device_key for row in found] == [DEVICE_KEY]

    def test_rf_020_sin_posiciones_el_mapa_no_inventa_puntos(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        with client_as(session, SUPERVISOR) as api:
            body = api.get("/api/v1/dispatch/units/GYE/crews.geojson").json()

        assert body["features"] == []


class TestRetention:
    def test_rf_020_la_purga_borra_lo_de_ayer_y_deja_lo_de_hoy(
        self, session: Session, units: dict[str, BusinessUnit], device: Device
    ) -> None:
        """La plataforma guarda la última posición para despachar, no un registro histórico."""
        other, _ = enrol_device(
            session, units["GYE"], device_key="phone-00000002", user_sub="kc|tecnico.b"
        )
        positions.report(
            session,
            units["GYE"],
            device,
            latitude=-2.17,
            longitude=-79.9,
            reported_at=NOW - timedelta(hours=30),
        )
        positions.report(
            session, units["GYE"], other, latitude=-2.18, longitude=-79.91, reported_at=NOW
        )

        deleted = positions.purge(session, now=NOW)

        assert deleted == 1
        assert [
            row.device_key for row in positions.crew_positions(session, units["GYE"], now=NOW)
        ] == ["phone-00000002"]


class TestMapFilters:
    def test_rf_020_el_area_se_resuelve_por_el_formulario_y_no_por_el_tipo_de_trabajo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """`work_type.startswith('apg')` no encuentra «atencion_luminaria», que es de APG."""
        assert codes_for_area("apg") == ["F-AP-01"]
        assert codes_for_area("mantenimiento") == ["F-MT-01"]
        # Un área que no existe no es «sin filtro»: es «nada coincide».
        assert codes_for_area("no_existe") == []

    def test_rf_020_el_mapa_filtra_por_area(self, session: Session, unit: BusinessUnit) -> None:
        an_order(session, unit)
        an_order(
            session,
            unit,
            form_code="F-AP-01",
            work_type="atencion_luminaria",
            asset_type_key="street_light",
            code="OT-2026-0002",
        )

        alumbrado = in_bounding_box(
            session, unit, west=-80.5, south=-3.0, east=-79.0, north=-1.5, area="apg"
        )

        assert [order.form_code for order in alumbrado] == ["F-AP-01"]

    def test_rf_020_el_mapa_filtra_por_prioridad_y_por_zona(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        an_order(session, unit, priority="critica", zone="norte")
        an_order(session, unit, priority="baja", zone="sur", code="OT-2026-0002")

        criticas = in_bounding_box(
            session,
            unit,
            west=-80.5,
            south=-3.0,
            east=-79.0,
            north=-1.5,
            priorities=["critica", "alta"],
        )
        del_sur = in_bounding_box(
            session, unit, west=-80.5, south=-3.0, east=-79.0, north=-1.5, zone="sur"
        )

        assert [order.priority for order in criticas] == ["critica"]
        assert [order.zone for order in del_sur] == ["sur"]

    def test_rf_020_los_filtros_llegan_por_la_api_del_mapa(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        an_order(session, unit, priority="critica")
        an_order(
            session,
            unit,
            form_code="F-AP-01",
            work_type="atencion_luminaria",
            asset_type_key="street_light",
            priority="baja",
            code="OT-2026-0002",
        )

        with client_as(session, PLANNER) as api:
            body = api.get(
                "/api/v1/planning/work-orders.geojson"
                "?business_unit=GYE&west=-80.5&south=-3.0&east=-79.0&north=-1.5"
                "&area=apg"
            ).json()

        assert [row["properties"]["form_code"] for row in body["features"]] == ["F-AP-01"]
        assert body["features"][0]["properties"]["zone"] == "norte"


class TestWhoMaySee:
    def test_rf_020_el_tecnico_no_ve_el_mapa_de_las_cuadrillas(
        self, session: Session, unit: BusinessUnit, device: Device
    ) -> None:
        """Saber dónde está cada compañero no es parte del trabajo de campo."""
        positions.report(session, unit, device, latitude=-2.17, longitude=-79.9)

        with client_as(session, TECHNICIAN) as api:
            response = api.get("/api/v1/dispatch/units/GYE/crews.geojson")

        assert response.status_code == 403

    def test_rf_020_nadie_ve_el_mapa_de_una_unidad_fuera_de_su_alcance(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        with client_as(session, SUPERVISOR) as api:
            response = api.get("/api/v1/dispatch/units/MAN/crews.geojson")

        assert response.status_code == 403

    def test_rf_020_el_planificador_no_reporta_posiciones(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Reportar posición es del teléfono que la tiene, no de quien planifica desde la oficina.

        El dispositivo se enrola **a nombre del planificador** a propósito: con el del técnico, la
        llamada fallaba por ser el dispositivo de otra persona y el test pasaba sin comprobar el
        rol. El sabotaje que abría el endpoint al planificador seguía en verde.
        """
        own, _ = enrol_device(
            session, unit, device_key=DEVICE_KEY, user_sub=PLANNER.subject, model="Pixel 8a"
        )
        assert own.user_sub == PLANNER.subject

        with client_as(session, PLANNER) as api:
            response = report(api)

        assert response.status_code == 403
        assert "roles" in response.json()["detail"]
