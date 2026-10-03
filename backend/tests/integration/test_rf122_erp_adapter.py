"""El adaptador del ERP: materiales, existencias y movimientos (RF-122).

Lo que esto cierra no era una función que faltaba sino **una declaración que apuntaba a nada**: el
catálogo `material` se enviaba con `source: integracion` y la nota «vacío hasta el primer envío del
ERP», y no existía forma de hacer ese primer envío. Un teléfono que dibujaba la tabla de materiales
de B07 tenía un campo de código y ningún valor para elegir.

Los cuatro casos que más se prueban son los que cuestan dinero o inventario:

* un lote que **no** se declara completo no puede retirar códigos (si pudiera, una descarga que
  falló a medias vaciaría el selector en el campo: silencioso aquí, muy ruidoso en una subestación);
* las existencias se **reemplazan** por ubicación, porque una línea que desapareció significa que el
  material se acabó y dejarla tendría a alguien planificando contra algo que no está;
* el consumo y la devolución son **dos movimientos** y no una cantidad con signo: lo reutilizable va
  a bodega y la chatarra a disposición, y son asientos distintos en el ERP;
* y el movimiento se publica **dentro de la transacción de la aprobación**, así que una OT aprobada
  no puede dejar al ERP sin saber qué salió de bodega.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalogs import service as catalogs
from app.catalogs.models import Catalog, CatalogSource
from app.gis_gateway.ingest import ingest_metadata
from app.integrations import erp_adapter
from app.integrations.erp_models import StockLocationKind
from app.integrations.models import (
    Connector,
    Direction,
    EventKind,
    EventStatus,
    IntegrationEvent,
)
from app.integrations.transport import RecordingTransport, Response, TransportError
from app.org.models import BusinessUnit, Organization
from app.responses.models import EvidenceStage
from app.responses.service import register_evidence, save_answers
from app.workers.integration_delivery import deliver_one, run_once
from app.workorders.models import WorkOrder, WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

BASE = "http://erp.test"
ACTOR = "conector.erp"


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
        ingest_metadata(session, unit, build_metadata("cnel-gye"))
        created[code] = unit
    return created


@pytest.fixture
def unit(units: dict[str, BusinessUnit]) -> BusinessUnit:
    return units["GYE"]


@pytest.fixture
def material_catalog(session: Session) -> Catalog:
    """El catálogo como se envía: del ERP y vacío."""
    catalog = Catalog(
        code=erp_adapter.MATERIAL_CATALOG,
        title="Material",
        source=CatalogSource.INTEGRATION,
        note="Vacío hasta el primer envío del ERP.",
    )
    session.add(catalog)
    session.flush()
    return catalog


def materials_transport(
    items: list[dict[str, Any]], *, complete: bool = True
) -> RecordingTransport:
    transport = RecordingTransport()
    transport.script(
        "GET", f"{BASE}/materials", Response(200, {"items": items, "complete": complete})
    )
    return transport


def stock_transport(locations: list[dict[str, Any]]) -> RecordingTransport:
    transport = RecordingTransport()
    transport.script("GET", f"{BASE}/stock", Response(200, {"locations": locations}))
    return transport


def a_material(code: str, label: str | None = None, **extra: Any) -> dict[str, Any]:
    return {"code": code, "label": label or f"Material {code}", **extra}


def codes_in_catalogue(session: Session) -> list[str]:
    return sorted(
        entry.code for entry in catalogs.resolve(session, erp_adapter.MATERIAL_CATALOG).entries
    )


class TestTheCatalogueArrives:
    def test_rf_122_el_primer_envio_llena_el_catalogo_que_venia_vacio(
        self, session: Session, unit: BusinessUnit, material_catalog: Catalog
    ) -> None:
        """El hueco, en un test: el catálogo existía y nada podía llenarlo."""
        assert codes_in_catalogue(session) == []

        report = erp_adapter.import_materials(
            session,
            unit,
            materials_transport([a_material("MT-CRUCETA-2M", "Cruceta de madera 2 m")]),
            base_url=BASE,
            actor=ACTOR,
        )

        assert report["written"] == ["MT-CRUCETA-2M"]
        assert codes_in_catalogue(session) == ["MT-CRUCETA-2M"]

    def test_rf_122_el_catalogo_sigue_sin_poder_editarse_a_mano(
        self, session: Session, unit: BusinessUnit, material_catalog: Catalog
    ) -> None:
        """Escribirlo como el ERP no lo vuelve editable: el siguiente lote lo sobreescribiría."""
        erp_adapter.import_materials(
            session, unit, materials_transport([a_material("MT-X")]), base_url=BASE, actor=ACTOR
        )

        with pytest.raises(catalogs.NotEditableError):
            catalogs.upsert_entry(
                session,
                erp_adapter.MATERIAL_CATALOG,
                entry_code="MT-X",
                label="Editado a mano",
                actor="admin.funcional",
            )

    def test_rf_122_un_material_sin_descripcion_se_rechaza_con_su_codigo(
        self, session: Session, unit: BusinessUnit, material_catalog: Catalog
    ) -> None:
        """Un selector que muestra un código pelado es un selector que un técnico no puede usar."""
        report = erp_adapter.import_materials(
            session,
            unit,
            materials_transport([{"code": "MT-SIN-NOMBRE"}, a_material("MT-OK")]),
            base_url=BASE,
            actor=ACTOR,
        )

        assert report["written"] == ["MT-OK"]
        assert report["rejected"][0]["code"] == "MT-SIN-NOMBRE"
        assert "descripción" in report["rejected"][0]["reason"]

    def test_rf_122_un_material_sin_codigo_se_rechaza(
        self, session: Session, unit: BusinessUnit, material_catalog: Catalog
    ) -> None:
        report = erp_adapter.import_materials(
            session,
            unit,
            materials_transport([{"label": "Sin código"}]),
            base_url=BASE,
            actor=ACTOR,
        )

        assert report["written"] == []
        assert report["rejected"][0]["reason"].endswith("no trae código")

    def test_rf_122_el_lote_guarda_la_unidad_de_medida_y_la_uc(
        self, session: Session, unit: BusinessUnit, material_catalog: Catalog
    ) -> None:
        erp_adapter.import_materials(
            session,
            unit,
            materials_transport(
                [a_material("MT-CABLE", "Conductor ACSR 2 AWG", unit="m", uc_code="CO-AC-02")]
            ),
            base_url=BASE,
            actor=ACTOR,
        )

        entry = next(
            row
            for row in catalogs.resolve(session, erp_adapter.MATERIAL_CATALOG).entries
            if row.code == "MT-CABLE"
        )
        assert entry.attributes["unit"] == "m"
        assert entry.attributes["uc_code"] == "CO-AC-02"

    def test_rf_122_los_sinonimos_del_erp_llegan_al_catalogo_y_de_ahi_al_dictado(
        self, session: Session, unit: BusinessUnit, material_catalog: Catalog
    ) -> None:
        """RF-147: los sinónimos del catálogo alimentan el léxico del reconocedor."""
        erp_adapter.import_materials(
            session,
            unit,
            materials_transport(
                [
                    a_material(
                        "MT-CRUCETA-2M", "Cruceta de madera 2 m", synonyms=["cruceta 2 metros"]
                    )
                ]
            ),
            base_url=BASE,
            actor=ACTOR,
        )

        entry = next(
            row
            for row in catalogs.resolve(session, erp_adapter.MATERIAL_CATALOG).entries
            if row.code == "MT-CRUCETA-2M"
        )
        assert "cruceta 2 metros" in entry.synonyms

    def test_rf_122_volver_a_importar_actualiza_y_no_duplica(
        self, session: Session, unit: BusinessUnit, material_catalog: Catalog
    ) -> None:
        erp_adapter.import_materials(
            session,
            unit,
            materials_transport([a_material("MT-X", "Nombre viejo")]),
            base_url=BASE,
            actor=ACTOR,
        )
        erp_adapter.import_materials(
            session,
            unit,
            materials_transport([a_material("MT-X", "Nombre nuevo")]),
            base_url=BASE,
            actor=ACTOR,
        )

        entries = catalogs.resolve(session, erp_adapter.MATERIAL_CATALOG).entries
        assert [entry.code for entry in entries] == ["MT-X"]
        assert entries[0].label == "Nombre nuevo"


class TestAPartialBatchCannotEmptyThePicker:
    def test_rf_122_un_lote_completo_retira_lo_que_el_erp_dejo_de_enviar(
        self, session: Session, unit: BusinessUnit, material_catalog: Catalog
    ) -> None:
        erp_adapter.import_materials(
            session,
            unit,
            materials_transport([a_material("MT-A"), a_material("MT-B")]),
            base_url=BASE,
            actor=ACTOR,
        )

        report = erp_adapter.import_materials(
            session, unit, materials_transport([a_material("MT-A")]), base_url=BASE, actor=ACTOR
        )

        assert report["retired"] == ["MT-B"]
        assert codes_in_catalogue(session) == ["MT-A"]

    def test_rf_122_un_lote_parcial_no_retira_nada_y_lo_dice(
        self, session: Session, unit: BusinessUnit, material_catalog: Catalog
    ) -> None:
        """Una descarga que falló a medias no puede vaciar el selector de una cuadrilla."""
        erp_adapter.import_materials(
            session,
            unit,
            materials_transport([a_material("MT-A"), a_material("MT-B")]),
            base_url=BASE,
            actor=ACTOR,
        )

        report = erp_adapter.import_materials(
            session,
            unit,
            materials_transport([a_material("MT-A")], complete=False),
            base_url=BASE,
            actor=ACTOR,
        )

        assert report["retired"] == []
        assert report["complete"] is False
        assert report["note"] is not None and "parcial" in report["note"]
        assert codes_in_catalogue(session) == ["MT-A", "MT-B"]

    def test_rf_122_un_codigo_retirado_viaja_como_lapida_y_no_desaparece(
        self, session: Session, unit: BusinessUnit, material_catalog: Catalog
    ) -> None:
        """RF-034: el teléfono tiene que enterarse de que un valor se retiró."""
        erp_adapter.import_materials(
            session,
            unit,
            materials_transport([a_material("MT-A"), a_material("MT-B")]),
            base_url=BASE,
            actor=ACTOR,
        )
        erp_adapter.import_materials(
            session, unit, materials_transport([a_material("MT-A")]), base_url=BASE, actor=ACTOR
        )

        delta = catalogs.delta(session, since=0, unit=unit, codes=[erp_adapter.MATERIAL_CATALOG])
        tombstones = [row for row in delta.changes if not row["active"]]
        assert [entry["code"] for entry in tombstones] == ["MT-B"]


class TestStockIsASnapshot:
    def location(self, **overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "kind": StockLocationKind.WAREHOUSE.value,
            "code": "BOD-01",
            "name": "Bodega central",
            "as_of": "2026-09-24T04:00:00+00:00",
            "lines": [
                {"material_code": "MT-A", "quantity": 42, "unit": "u"},
                {"material_code": "MT-B", "quantity": 7, "unit": "u"},
            ],
        }
        base.update(overrides)
        return base

    def test_rf_122_las_existencias_llegan_por_bodega_y_por_vehiculo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El vehículo es el que decide si el trabajo de hoy se puede hacer."""
        report = erp_adapter.import_stock(
            session,
            unit,
            stock_transport(
                [
                    self.location(),
                    self.location(
                        kind=StockLocationKind.VEHICLE.value,
                        code="VEH-0142",
                        lines=[{"material_code": "MT-A", "quantity": 6, "unit": "u"}],
                    ),
                ]
            ),
            base_url=BASE,
        )

        assert report["lines"] == 3
        assert sorted(report["locations"]) == ["BOD-01", "VEH-0142"]
        vehicle = erp_adapter.stock_of(session, unit, location_kind=StockLocationKind.VEHICLE.value)
        assert [row.material_code for row in vehicle] == ["MT-A"]

    def test_rf_122_un_lote_nuevo_reemplaza_las_lineas_de_esa_ubicacion(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una línea que desapareció es material que se acabó, y dejarla es un fantasma."""
        erp_adapter.import_stock(session, unit, stock_transport([self.location()]), base_url=BASE)

        erp_adapter.import_stock(
            session,
            unit,
            stock_transport(
                [self.location(lines=[{"material_code": "MT-A", "quantity": 40, "unit": "u"}])]
            ),
            base_url=BASE,
        )

        rows = erp_adapter.stock_of(session, unit)
        assert [row.material_code for row in rows] == ["MT-A"]
        assert rows[0].quantity == Decimal("40.000")

    def test_rf_122_reemplazar_una_ubicacion_no_toca_las_otras(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        erp_adapter.import_stock(
            session,
            unit,
            stock_transport(
                [
                    self.location(),
                    self.location(
                        kind=StockLocationKind.VEHICLE.value,
                        code="VEH-1",
                        lines=[{"material_code": "MT-Z", "quantity": 3}],
                    ),
                ]
            ),
            base_url=BASE,
        )

        erp_adapter.import_stock(
            session, unit, stock_transport([self.location(lines=[])]), base_url=BASE
        )

        rows = erp_adapter.stock_of(session, unit)
        assert [row.location_code for row in rows] == ["VEH-1"]

    def test_rf_122_la_hora_del_erp_se_conserva_para_mostrarla(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una existencia de un lote nocturno tiene horas, y el número no puede parecer actual."""
        erp_adapter.import_stock(session, unit, stock_transport([self.location()]), base_url=BASE)

        row = erp_adapter.stock_of(session, unit)[0]
        assert row.as_of == datetime(2026, 9, 24, 4, 0, tzinfo=UTC)

    def test_rf_122_sin_hora_del_erp_se_usa_ahora_en_vez_de_nada(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Nulo se leería como «actual», que es justo la lectura que esta columna evita."""
        erp_adapter.import_stock(
            session, unit, stock_transport([self.location(as_of=None)]), base_url=BASE
        )

        assert erp_adapter.stock_of(session, unit)[0].as_of is not None

    def test_rf_122_una_ubicacion_de_tipo_desconocido_se_rechaza_con_su_motivo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        report = erp_adapter.import_stock(
            session, unit, stock_transport([self.location(kind="nube")]), base_url=BASE
        )

        assert report["locations"] == []
        assert "nube" in report["rejected"][0]["reason"]

    def test_rf_122_una_linea_con_cantidad_ilegible_se_rechaza_y_las_otras_entran(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        report = erp_adapter.import_stock(
            session,
            unit,
            stock_transport(
                [
                    self.location(
                        lines=[
                            {"material_code": "MT-A", "quantity": "muchos"},
                            {"material_code": "MT-B", "quantity": 5},
                        ]
                    )
                ]
            ),
            base_url=BASE,
        )

        assert report["lines"] == 1
        assert len(report["rejected"]) == 1

    def test_rf_122_las_existencias_no_cruzan_unidades_de_negocio(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        erp_adapter.import_stock(
            session, units["GYE"], stock_transport([self.location()]), base_url=BASE
        )

        assert erp_adapter.stock_of(session, units["MAN"]) == []

    def test_rf_122_importar_una_unidad_no_borra_las_lineas_de_otra(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        """El reemplazo por ubicación es una **escritura**, y tiene que ir acotada por unidad.

        Dos unidades pueden tener una bodega con el mismo código —«BOD-01» es un nombre que se
        repite— y un borrado sin el filtro de unidad vaciaría el inventario de la otra. Es la clase
        de defecto que ya costó caro una vez en esta plataforma (la tabla de staging as-built sin
        columna de unidad): no una fuga de lectura sino una escritura cruzada, más difícil de
        deshacer y contraria a ADR-009. Este test existe porque el sabotaje correspondiente pasó
        inadvertido: `stock_of` filtra por unidad, así que leer no lo detecta.
        """
        for code in ("GYE", "MAN"):
            erp_adapter.import_stock(
                session,
                units[code],
                stock_transport(
                    [self.location(lines=[{"material_code": f"MT-{code}", "quantity": 5}])]
                ),
                base_url=BASE,
            )

        erp_adapter.import_stock(
            session,
            units["GYE"],
            stock_transport([self.location(lines=[{"material_code": "MT-GYE", "quantity": 9}])]),
            base_url=BASE,
        )

        other = erp_adapter.stock_of(session, units["MAN"])
        assert [row.material_code for row in other] == ["MT-MAN"]
        assert other[0].quantity == Decimal("5.000")

    def test_rf_122_reporta_los_codigos_con_existencia_que_el_catalogo_no_conoce(
        self, session: Session, unit: BusinessUnit, material_catalog: Catalog
    ) -> None:
        """No es un error —los dos lotes llegan por separado— pero es la señal de que se desvían."""
        erp_adapter.import_materials(
            session, unit, materials_transport([a_material("MT-A")]), base_url=BASE, actor=ACTOR
        )

        report = erp_adapter.import_stock(
            session, unit, stock_transport([self.location()]), base_url=BASE
        )

        assert report["unknown_in_catalogue"] == ["MT-B"]

    def test_rf_122_un_fallo_de_transporte_queda_en_la_bitacora_de_integraciones(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        transport = RecordingTransport()
        transport.script("GET", f"{BASE}/stock", TransportError("503", retryable=True))

        with pytest.raises(TransportError):
            erp_adapter.import_stock(session, unit, transport, base_url=BASE)

        event = session.execute(
            select(IntegrationEvent).where(IntegrationEvent.kind == EventKind.MATERIAL_STOCK.value)
        ).scalar_one()
        # Un 503 es reintentable, así que el evento queda pendiente con su espera: lo que importa
        # es que el intento **quedó registrado** y que hay una próxima vez agendada.
        assert event.attempts == 1
        assert "503" in (event.last_error or "")
        assert event.status == EventStatus.PENDING
        assert event.next_attempt_at is not None


# --- salida: los movimientos ----------------------------------------------------------------


def an_order_with_materials(
    session: Session,
    unit: BusinessUnit,
    *,
    materials: list[dict[str, Any]] | None,
    code: str = "OT-AP-1",
) -> WorkOrder:
    """Una OT de atención de luminaria, que es uno de los formularios que llevan B07."""
    order = create_work_order(
        session,
        unit,
        work_type="luminaria_falla",
        form_code="F-AP-01",
        asset_type_key="street_light",
        asset_code="LUM-0099",
        planner_id="kc|planner.a",
    )
    order.state = WorkOrderState.SYNCED
    order.form_version = "1.1.0"
    order.code = code
    session.flush()

    answers: dict[str, Any] = {
        "work_order_code": code,
        "work_type": "luminaria_falla",
        "priority": "alta",
        "code": "LUM-0099",
        "technology": "led",
        "feeder_code": "04BH070T11",
        "ats_reference": "ATS-2026-0001",
        "reported_failure": "apagada_de_noche",
        "cause_found": "lampara_o_modulo",
        "operative_at_close": True,
        # B06 es obligatorio en este formulario: una atención de luminaria siempre hizo algo.
        "activities": [{"activity_code": "cambio_lampara", "quantity": 1}],
        "final_state": "resuelto",
        "photos_before": ["s3://a.jpg"],
        "photos_after": ["s3://b.jpg"],
    }
    if materials is not None:
        answers["materials"] = materials
    response = save_answers(session, unit, order, answers=answers, submit=True)
    response.submitted_at = datetime.now(UTC)
    # Las fotos tienen que ser evidencia real: la aprobación cuenta filas, no elementos del JSON.
    for stage, name in ((EvidenceStage.BEFORE, "antes"), (EvidenceStage.AFTER, "despues")):
        register_evidence(
            session,
            response,
            kind="foto",
            storage_key=f"s3://{name}-{code}.jpg",
            content_hash=hashlib.sha256(f"{name}{code}".encode()).hexdigest(),
            stage=stage,
        )
    session.flush()
    return order


def events_of(session: Session, kind: EventKind) -> list[IntegrationEvent]:
    return list(
        session.execute(
            select(IntegrationEvent).where(IntegrationEvent.kind == kind.value)
        ).scalars()
    )


class TestTheMovementsLeave:
    def test_rf_122_lo_instalado_y_lo_retirado_son_dos_movimientos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Caen en lugares distintos del ERP: uno es consumo, el otro una recepción."""
        order = an_order_with_materials(
            session,
            unit,
            materials=[
                {
                    "material_code": "MT-LUM-LED-100",
                    "installed_quantity": 1,
                    "removed_quantity": 1,
                    "removed_state": "chatarra",
                }
            ],
        )

        events = erp_adapter.enqueue_material_movements(session, unit, order)

        kinds = sorted(event.kind for event in events)
        assert kinds == [EventKind.MATERIAL_CONSUMED.value, EventKind.MATERIAL_RETURNED.value]
        assert all(event.connector == Connector.ERP for event in events)
        assert all(event.direction == Direction.OUTBOUND for event in events)

    def test_rf_122_el_destino_sale_del_estado_que_anoto_la_cuadrilla(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """«Reutilizable» es una recepción en bodega; «chatarra», una disposición."""
        order = an_order_with_materials(
            session,
            unit,
            materials=[
                {"material_code": "MT-A", "removed_quantity": 2, "removed_state": "reutilizable"},
                {"material_code": "MT-B", "removed_quantity": 1, "removed_state": "chatarra"},
            ],
        )

        erp_adapter.enqueue_material_movements(session, unit, order)

        returned = events_of(session, EventKind.MATERIAL_RETURNED)[0]
        destinations = {
            line["material_code"]: line["destination"] for line in returned.payload["lines"]
        }
        assert destinations == {"MT-A": "bodega", "MT-B": "chatarra"}

    def test_rf_122_sin_estado_anotado_el_destino_queda_por_clasificar(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """No se adivina «reutilizable»: meter chatarra a bodega es la dirección cara del error."""
        order = an_order_with_materials(
            session, unit, materials=[{"material_code": "MT-A", "removed_quantity": 1}]
        )

        erp_adapter.enqueue_material_movements(session, unit, order)

        line = events_of(session, EventKind.MATERIAL_RETURNED)[0].payload["lines"][0]
        assert line["destination"] == erp_adapter.UNKNOWN_DESTINATION
        assert line["recorded_state"] is None

    def test_rf_122_solo_instalado_no_publica_una_devolucion_vacia(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order_with_materials(
            session,
            unit,
            materials=[{"material_code": "MT-A", "installed_quantity": 3, "removed_quantity": 0}],
        )

        events = erp_adapter.enqueue_material_movements(session, unit, order)

        assert [event.kind for event in events] == [EventKind.MATERIAL_CONSUMED.value]

    def test_rf_122_una_ot_sin_materiales_no_publica_nada(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La mayoría del trabajo no consume nada, y un movimiento vacío ensucia el log del ERP."""
        order = an_order_with_materials(session, unit, materials=None)

        assert erp_adapter.enqueue_material_movements(session, unit, order) == []

    def test_rf_122_las_cantidades_decimales_sobreviven(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Metros de conductor: 0.1 más 0.2 tiene que dar 0.3 en un movimiento de inventario."""
        order = an_order_with_materials(
            session,
            unit,
            materials=[
                {"material_code": "MT-CABLE", "installed_quantity": 12.5, "unit": "m"},
            ],
        )

        erp_adapter.enqueue_material_movements(session, unit, order)

        line = events_of(session, EventKind.MATERIAL_CONSUMED)[0].payload["lines"][0]
        assert line["quantity"] == 12.5
        assert line["unit"] == "m"

    def test_rf_122_una_fila_sin_codigo_de_material_no_pasa_la_validacion(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El formulario la rechaza antes, que es más fuerte que ignorarla después.

        La primera versión de este test esperaba que el adaptador la descartara en silencio, y
        resultó que esa fila **no puede llegar**: B07 exige el código en cada fila. La guarda del
        adaptador se queda de todos modos, para una respuesta guardada antes de que el bloque
        existiera o escrita directo a la base, pero lo que el contrato afirma es esto.
        """
        from app.responses.service import AnswerValidationError

        with pytest.raises(AnswerValidationError, match="material_code"):
            an_order_with_materials(
                session, unit, materials=[{"installed_quantity": 1}], code="OT-AP-SIN"
            )

    def test_rf_122_reaprobar_no_duplica_el_movimiento(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La clave es la OT y el tipo: una corrección actualiza el asiento, no lo dobla."""
        order = an_order_with_materials(
            session, unit, materials=[{"material_code": "MT-A", "installed_quantity": 1}]
        )

        erp_adapter.enqueue_material_movements(session, unit, order)
        erp_adapter.enqueue_material_movements(session, unit, order)

        assert len(events_of(session, EventKind.MATERIAL_CONSUMED)) == 1


class TestDelivery:
    def test_rf_122_el_consumo_y_la_devolucion_van_a_endpoints_distintos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order_with_materials(
            session,
            unit,
            materials=[
                {
                    "material_code": "MT-A",
                    "installed_quantity": 1,
                    "removed_quantity": 1,
                    "removed_state": "chatarra",
                }
            ],
        )
        erp_adapter.enqueue_material_movements(session, unit, order)
        transport = RecordingTransport(default=Response(200, {"accepted": True}))

        for event in events_of(session, EventKind.MATERIAL_CONSUMED) + events_of(
            session, EventKind.MATERIAL_RETURNED
        ):
            deliver_one(session, event, transport=transport, base_url=BASE)

        urls = sorted(url for _method, url, _payload in transport.calls)
        assert urls == [f"{BASE}/movements/consumption", f"{BASE}/movements/return"]

    def test_rf_122_el_worker_entrega_los_eventos_del_erp(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order_with_materials(
            session, unit, materials=[{"material_code": "MT-A", "installed_quantity": 1}]
        )
        erp_adapter.enqueue_material_movements(session, unit, order)
        transport = RecordingTransport(default=Response(200, {"accepted": True}))

        report = run_once(session, unit, transport=transport, urls={Connector.ERP.value: BASE})

        assert report.delivered == 1
        assert events_of(session, EventKind.MATERIAL_CONSUMED)[0].status == EventStatus.DELIVERED

    def test_rf_122_sin_url_configurada_el_evento_se_omite_en_vez_de_gastar_reintentos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un conector que todavía no está desplegado no es un error."""
        order = an_order_with_materials(
            session, unit, materials=[{"material_code": "MT-A", "installed_quantity": 1}]
        )
        erp_adapter.enqueue_material_movements(session, unit, order)

        report = run_once(
            session, unit, transport=RecordingTransport(), urls={Connector.ERP.value: ""}
        )

        assert report.skipped == 1
        assert Connector.ERP.value in report.unconfigured

    def test_rf_122_un_tipo_que_el_adaptador_no_conoce_falla_sin_reintentos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un evento de entrada no tiene nada que entregar: es un error de programación."""
        from app.integrations.service import publish

        event = publish(
            session,
            unit,
            connector=Connector.ERP,
            direction=Direction.INBOUND,
            kind=EventKind.MATERIAL_CATALOGUE,
            idempotency_key="raro",
            payload={},
        )

        deliver_one(session, event, transport=RecordingTransport(), base_url=BASE)

        assert event.status == EventStatus.FAILED
        assert event.needs_attention is True


class TestApprovalPublishesTheMovement:
    def test_rf_122_aprobar_publica_el_consumo_en_su_propia_transaccion(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """«El consumo aprobado genera un movimiento en el ERP», y no como efecto secundario."""
        from app.review.service import Decision, decide
        from app.workorders.service import transition

        order = an_order_with_materials(
            session,
            unit,
            materials=[{"material_code": "MT-LUM-LED-100", "installed_quantity": 1}],
        )
        transition(session, order, WorkOrderState.IN_REVIEW)

        decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="kc|supervisor.demo")

        consumed = events_of(session, EventKind.MATERIAL_CONSUMED)
        assert len(consumed) == 1
        assert consumed[0].payload["lines"][0]["material_code"] == "MT-LUM-LED-100"
        assert consumed[0].work_order_id == order.id

    def test_rf_122_aprobar_una_ot_sin_materiales_no_publica_movimientos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        from app.review.service import Decision, decide
        from app.workorders.service import transition

        order = an_order_with_materials(session, unit, materials=None)
        transition(session, order, WorkOrderState.IN_REVIEW)

        decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="kc|supervisor.demo")

        assert events_of(session, EventKind.MATERIAL_CONSUMED) == []
