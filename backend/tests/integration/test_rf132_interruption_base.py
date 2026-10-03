"""La base de interrupciones y su exportación (RF-132, ARCERNNR-002/20).

Lo que este módulo **no** hace es lo que más se prueba: no calcula FMIK ni TTIK. Los dos índices
dividen por el kVA instalado de la unidad, que vive en los sistemas corporativos y no aquí, y
publicar un índice contra un denominador supuesto sería publicar un número que después hay que
defender ante el regulador. Se exportan la base y los dos numeradores, y se dice qué falta.

Lo otro que se prueba es que el umbral de «no computable» siga viniendo del parámetro (ADR-007), y
que el formato sea un archivo: la regulación renombra y reordena columnas cada pocos años, y eso
debería ser un archivo que se añade, no código que se cambia.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.interruptions import (
    UnknownFormatError,
    collect,
    load_format,
    render,
)
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.regulatory.service import set_parameter
from app.responses.service import save_answers
from app.workorders.models import WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

SUPERVISOR = Principal(
    subject="kc|supervisor.demo",
    username="supervisor.demo",
    roles=frozenset({Role.SUPERVISOR.value}),
    business_units=frozenset({"GYE"}),
)

TECHNICIAN = Principal(
    subject="kc|tecnico.demo",
    username="tecnico.demo",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
START = datetime(2026, 9, 19, 20, 0, tzinfo=UTC)


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
def threshold(session: Session):
    """El umbral en vigor, cargado como dato y verificado."""
    return set_parameter(
        session,
        code="interruption.non_computable_seconds",
        value=180,
        unit="s",
        norm_ref="ARCERNNR 002/20",
        article_ref="Art. 8",
        effective_from=date(2026, 1, 1),
        verified_by="kc|regulatorio.1",
    )


def an_interruption(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str,
    seconds: float | None = 3600,
    kva: float | None = 250,
    cause: str = "descarga_atmosferica",
    submitted: datetime | None = None,
    partials: list[dict] | None = None,
):
    order = create_work_order(
        session,
        unit,
        work_type="interrupcion",
        form_code="F-OP-03",
        asset_type_key="line_segment",
        longitude=-79.90,
        latitude=-2.17,
        zone="Urbano",
        planner_id="kc|planner.a",
    )
    order.state = WorkOrderState.SYNCED
    order.form_version = "1.0.0"
    order.code = code
    session.flush()

    answers: dict[str, object] = {
        "work_order_code": code,
        "work_type": "interrupcion",
        "priority": "alta",
        "feeder_code": "04BH070T11",
        "substation_code": "SE-NORTE",
        "interruption_kind": "no_programada",
        "interruption_origin": "interna",
        "started_at_interruption": START.isoformat(),
        "protection_operated": "RECONECTADOR-7",
        "transformers_affected": 12,
        "interruption_cause": cause,
    }
    if seconds is not None:
        answers["interruption_seconds"] = seconds
        answers["restored_at_interruption"] = (START + timedelta(seconds=seconds)).isoformat()
    if kva is not None:
        answers["kva_affected"] = kva
    if partials is not None:
        answers["partial_restorations"] = partials

    response = save_answers(session, unit, order, answers=answers, submit=True)
    response.submitted_at = submitted or NOW
    session.flush()
    return order


def client_as(session: Session, principal: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: principal
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with client_as(session, SUPERVISOR) as raw:
        yield raw


def base(client: TestClient, unit: BusinessUnit, **params: object) -> dict:
    answer = client.get(f"/api/v1/analytics/units/{unit.code}/interruptions", params=params)
    assert answer.status_code == 200, answer.text
    return answer.json()


class TestWhatItRefusesToCompute:
    def test_rf_132_no_publica_fmik_ni_ttik(
        self, client: TestClient, session: Session, unit: BusinessUnit, threshold
    ) -> None:
        """Los dos índices dividen por el kVA instalado, que la plataforma no conoce.

        Lo que no puede existir es un **campo** que se llame como un índice y traiga un número: eso
        es lo que alguien copiaría a un informe. Que la nota los nombre para explicar por qué no
        están es justo lo contrario.
        """
        an_interruption(session, unit, code="OT-I1")
        session.flush()

        body = base(client, unit)
        forbidden = {"fmik", "ttik"}
        assert forbidden.isdisjoint(body)
        assert forbidden.isdisjoint(body["numerators"])
        assert "denominador" in body["numerators"]["note"]
        assert "kVA instalado" in body["numerators"]["note"]

    def test_los_numeradores_sí_se_calculan(
        self, client: TestClient, session: Session, unit: BusinessUnit, threshold
    ) -> None:
        """Salen solo de las interrupciones, así que son de la plataforma."""
        an_interruption(session, unit, code="OT-N1", seconds=3600, kva=100)
        an_interruption(session, unit, code="OT-N2", seconds=7200, kva=50)
        session.flush()

        numbers = base(client, unit)["numerators"]
        assert numbers["kva_affected"] == pytest.approx(150.0)
        # 100 kVA por 1 h mas 50 kVA por 2 h.
        assert numbers["kva_hours"] == pytest.approx(200.0)

    def test_una_interrupción_sin_kva_se_cuenta_como_faltante(
        self, client: TestClient, session: Session, unit: BusinessUnit, threshold
    ) -> None:
        """Cada una deja los dos numeradores por debajo de la realidad, y eso hay que decirlo."""
        an_interruption(session, unit, code="OT-SK", kva=None)
        session.flush()
        assert base(client, unit)["numerators"]["missing_kva"] == 1


class TestTheThresholdComesFromTheParameter:
    def test_rf_132_el_umbral_no_está_en_el_código(
        self, client: TestClient, session: Session, unit: BusinessUnit, threshold
    ) -> None:
        """Se cambia el parámetro y la clasificación cambia con él (ADR-007)."""
        an_interruption(session, unit, code="OT-CORTA", seconds=120)
        session.flush()
        assert base(client, unit)["not_computable"] == 1

        set_parameter(
            session,
            code="interruption.non_computable_seconds",
            value=60,
            unit="s",
            norm_ref="ARCERNNR 002/20",
            effective_from=date(2026, 6, 1),
            verified_by="kc|regulatorio.1",
        )
        session.flush()
        # El mismo evento, ahora computable: la regla es la misma y el dato cambió.
        body = base(client, unit)
        assert body["computable"] == 1
        assert body["not_computable"] == 0

    def test_sin_umbral_cargado_no_se_clasifica_ni_se_supone(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Suponerla computable inflaría los índices; suponer lo contrario esconderían
        interrupciones que ocurrieron. Se cuenta como sin clasificar."""
        an_interruption(session, unit, code="OT-SU")
        session.flush()

        body = base(client, unit)
        assert body["unclassified"] == 1
        assert body["computable"] == 0
        assert body["numerators"]["kva_affected"] == pytest.approx(0.0)

    def test_una_interrupción_sin_duración_queda_sin_clasificar(
        self, client: TestClient, session: Session, unit: BusinessUnit, threshold
    ) -> None:
        an_interruption(session, unit, code="OT-SD", seconds=None)
        session.flush()
        assert base(client, unit)["unclassified"] == 1


class TestTheFormatIsAFile:
    def test_rf_132_el_formato_se_carga_de_disco(self) -> None:
        layout = load_format("arcernnr-002-20")
        assert layout.norm_ref == "ARCERNNR 002/20"
        assert layout.delimiter == ";"
        assert layout.decimal == ","
        headers = [column.header for column in layout.columns]
        assert "kVA afectados" in headers
        assert "Computable" in headers

    def test_un_formato_que_no_existe_no_cae_al_de_por_defecto(self) -> None:
        """Una exportación que usara otro formato en silencio produciría un archivo que el regulador
        rechaza por razones que nadie puede rastrear."""
        with pytest.raises(UnknownFormatError, match="disponibles"):
            load_format("el-de-la-otra-regulacion")

    def test_el_endpoint_devuelve_404_para_un_formato_desconocido(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        answer = client.get(
            f"/api/v1/analytics/units/{unit.code}/interruptions.csv",
            params={"format": "inventado"},
        )
        assert answer.status_code == 404

    def test_el_tablero_dice_qué_formatos_hay(self, client: TestClient, unit: BusinessUnit) -> None:
        assert "arcernnr-002-20" in base(client, unit)["formats"]


class TestTheExport:
    def test_rf_132_exporta_con_los_campos_de_f_op_03(
        self, client: TestClient, session: Session, unit: BusinessUnit, threshold
    ) -> None:
        an_interruption(session, unit, code="OT-EXP", seconds=5400, kva=250)
        session.flush()

        answer = client.get(f"/api/v1/analytics/units/{unit.code}/interruptions.csv")
        assert answer.status_code == 200
        assert "attachment" in answer.headers["content-disposition"]
        text = answer.content.decode("utf-8")
        assert text.startswith("﻿")

        header, row = text.lstrip("﻿").splitlines()[:2]
        columns = header.split(";")
        values = dict(zip(columns, row.split(";"), strict=True))
        assert values["Código OT"] == "OT-EXP"
        assert values["Subestación"] == "SE-NORTE"
        assert values["Alimentador"] == "04BH070T11"
        assert values["Tipo"] == "no_programada"
        assert values["kVA afectados"] == "250,00"
        # 5400 s son 1,5 h; 250 kVA por 1,5 h da 375 kVA hora.
        assert values["Duración (h)"] == "1,50"
        assert values["kVA·h"] == "375,00"
        assert values["Computable"] == "sí"
        assert values["Umbral (s)"] == "180,00"
        assert values["Umbral verificado"] == "sí"
        assert values["Norma del umbral"] == "ARCERNNR 002/20"

    def test_los_decimales_van_con_coma_y_no_con_punto(
        self, client: TestClient, session: Session, unit: BusinessUnit, threshold
    ) -> None:
        """Un Excel configurado para Ecuador lee «1.5» como quince."""
        an_interruption(session, unit, code="OT-DEC", seconds=5400, kva=250)
        session.flush()
        text = client.get(f"/api/v1/analytics/units/{unit.code}/interruptions.csv").content.decode()
        assert "1,50" in text
        assert "1.50" not in text

    def test_una_causa_con_punto_y_coma_no_desplaza_las_columnas(
        self, session: Session, unit: BusinessUnit, threshold
    ) -> None:
        an_interruption(session, unit, code="OT-SEMI", cause="viento; rama caída")
        session.flush()

        rows = collect(session, unit.id, since=NOW - timedelta(days=30), until=NOW)
        layout = load_format("arcernnr-002-20")
        text = render(rows, layout)
        header, row = text.lstrip("﻿").splitlines()[:2]
        assert len(row.split(";")) == len(header.split(";"))

    def test_las_reposiciones_parciales_se_cuentan(
        self, client: TestClient, session: Session, unit: BusinessUnit, threshold
    ) -> None:
        an_interruption(
            session,
            unit,
            code="OT-PAR",
            partials=[
                {"restored_at": START.isoformat(), "section": "T1", "kva_restored": 50},
                {"restored_at": START.isoformat(), "section": "T2", "kva_restored": 80},
            ],
        )
        session.flush()
        text = client.get(f"/api/v1/analytics/units/{unit.code}/interruptions.csv").content.decode()
        header, row = text.lstrip("﻿").splitlines()[:2]
        values = dict(zip(header.split(";"), row.split(";"), strict=True))
        assert values["Reposiciones parciales"] == "2,00"

    def test_sin_interrupciones_el_archivo_trae_la_cabecera(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        """Un archivo vacío haría dudar de si la consulta falló."""
        text = client.get(f"/api/v1/analytics/units/{unit.code}/interruptions.csv").content.decode()
        assert len(text.strip().splitlines()) == 1


class TestWhoMaySee:
    def test_un_técnico_no_exporta_la_base(self, session: Session, unit: BusinessUnit) -> None:
        with client_as(session, TECHNICIAN) as raw:
            answer = raw.get(f"/api/v1/analytics/units/{unit.code}/interruptions")
        assert answer.status_code == 403

    def test_adr_009_la_base_no_incluye_interrupciones_de_otra_unidad(
        self, client: TestClient, session: Session, unit: BusinessUnit, threshold
    ) -> None:
        org = session.query(Organization).one()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        ingest_metadata(session, other, build_metadata("cnel-gye"))
        an_interruption(session, other, code="OT-MAN")
        session.flush()
        assert base(client, unit)["interruptions"] == 0
