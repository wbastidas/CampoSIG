"""El tablero de alumbrado público, contra base real (RF-131, ADR-007).

El plazo máximo de reposición **no está en el código**: vive en `regulatory_parameter` con su
vigencia y su referencia a la norma, y este tablero pregunta la misma regla que la compuerta de
aprobación. Eso es lo que se prueba con más cuidado, porque es la propiedad que hace que el número
se pueda defender:

* si alguien cambia el parámetro, el porcentaje cambia con él —sin tocar una línea—;
* si el parámetro tiene vigencias distintas, un periodo de marzo se juzga con el plazo de marzo;
* si el límite no está verificado contra el texto oficial, el tablero lo dice en vez de presentar el
  porcentaje como si citara la regulación.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.apg import as_csv, build
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.regulatory.service import set_parameter
from app.responses.models import EvidenceStage, FormResponse
from app.responses.service import register_evidence, save_answers
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
CLAIM = datetime(2026, 9, 18, 8, 0, tzinfo=UTC)


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
def deadline(session: Session):
    """El plazo en vigor, cargado como dato. Verificado contra el texto oficial."""
    return set_parameter(
        session,
        code="apg.max_restoration_hours",
        value=48,
        unit="h",
        norm_ref="ARCERNNR 007/23",
        article_ref="Art. 21",
        effective_from=date(2026, 1, 1),
        verified_by="kc|regulatorio.1",
    )


def an_attention(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str,
    luminaire: str = "LUM-0001",
    technology: str | None = "led",
    cause: str = "lampara_o_modulo",
    restored_after: timedelta = timedelta(hours=10),
    submitted: datetime | None = None,
    claim_at: datetime | None = CLAIM,
):
    """Una atención de luminaria en falla, capturada y enviada."""
    order = create_work_order(
        session,
        unit,
        work_type="luminaria_falla",
        form_code="F-AP-01",
        asset_type_key="street_light",
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
        "work_type": "luminaria_falla",
        "priority": "alta",
        "general_condition": "malo",
        "code": luminaire,
        "feeder_code": "04BH070T11",
        "reported_failure": "apagada_de_noche",
        "cause_found": cause,
        "operative_at_close": True,
        "final_state": "resuelto",
        # B04: el formulario exige ATS, así que la referencia es obligatoria.
        "ats_reference": "ATS-2026-0001",
        "activities": [{"activity_code": "REEMPLAZO_LUMINARIA", "quantity": 1}],
    }
    if technology is not None:
        answers["technology"] = technology
    if claim_at is not None:
        answers["claim_at"] = claim_at.isoformat()
        answers["restored_at"] = (claim_at + restored_after).isoformat()

    response = save_answers(session, unit, order, answers=answers, submit=True)
    response.submitted_at = submitted or NOW
    register_evidence(
        session,
        response,
        kind="foto",
        storage_key=f"s3://{code}.jpg",
        content_hash=hashlib.sha256(code.encode()).hexdigest(),
        stage=EvidenceStage.BEFORE,
    )
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


def apg(client: TestClient, unit: BusinessUnit, **params: object) -> dict:
    answer = client.get(f"/api/v1/analytics/units/{unit.code}/apg", params=params)
    assert answer.status_code == 200, answer.text
    return answer.json()


class TestTheDeadlineComesFromTheParameter:
    def test_rf_131_el_plazo_no_está_en_el_código(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        """Se cambia el parámetro y el veredicto cambia con él, sin tocar una línea (ADR-007)."""
        for index in range(5):
            an_attention(session, unit, code=f"OT-A{index}", restored_after=timedelta(hours=60))
        session.flush()
        # Con 48 h de plazo, 60 h incumplen.
        assert apg(client, unit)["restoration"]["breached"] == 5

        set_parameter(
            session,
            code="apg.max_restoration_hours",
            value=72,
            unit="h",
            norm_ref="ARCERNNR 007/23",
            effective_from=date(2026, 6, 1),
            verified_by="kc|regulatorio.1",
        )
        session.flush()
        # Con 72 h, las mismas atenciones cumplen. La regla es la misma; el dato cambió.
        body = apg(client, unit)
        assert body["restoration"]["breached"] == 0
        assert body["restoration"]["within"] == 5

    def test_la_cita_de_la_norma_viaja_con_el_incumplimiento(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        an_attention(session, unit, code="OT-CITA", restored_after=timedelta(hours=100))
        session.flush()

        breach = apg(client, unit)["breaches"][0]
        assert breach["norm_ref"] == "ARCERNNR 007/23"
        assert breach["article_ref"] == "Art. 21"
        assert breach["limit_hours"] == pytest.approx(48.0)
        assert breach["limit_verified"] is True

    def test_adr_007_un_límite_sin_verificar_se_cuenta_como_tal(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Un porcentaje calculado contra un número que alguien escribió de memoria, presentado como
        si citara la regulación, es peor que no tener porcentaje: invita a dejar de comprobar."""
        set_parameter(
            session,
            code="apg.max_restoration_hours",
            value=48,
            unit="h",
            norm_ref="Regulación de APG — por confirmar",
            effective_from=date(2026, 1, 1),
        )
        for index in range(5):
            an_attention(session, unit, code=f"OT-NV{index}", restored_after=timedelta(hours=60))
        session.flush()

        body = apg(client, unit)
        assert body["restoration"]["against_unverified_limit"] == 5
        assert body["breaches"][0]["limit_verified"] is False

    def test_sin_parámetro_cargado_no_se_inventa_un_plazo(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """La omisión es de la oficina, y la plataforma la reporta como no medible en vez de
        aprobar o incumplir por su cuenta."""
        an_attention(session, unit, code="OT-SP", restored_after=timedelta(hours=200))
        session.flush()

        body = apg(client, unit)
        assert body["restoration"]["not_measurable"] == 1
        assert body["restoration"]["judged"] == 0
        assert body["restoration"]["compliance"] is None

    def test_una_captura_sin_hora_de_reclamo_no_es_medible(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        an_attention(session, unit, code="OT-SH", claim_at=None)
        session.flush()
        assert apg(client, unit)["restoration"]["not_measurable"] == 1


class TestTheNumbers:
    def test_rf_131_el_cumplimiento_sale_con_la_mediana_y_la_cola(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        for index in range(4):
            an_attention(session, unit, code=f"OT-OK{index}", restored_after=timedelta(hours=10))
        an_attention(session, unit, code="OT-MAL", restored_after=timedelta(hours=90))
        session.flush()

        rows = apg(client, unit)["restoration"]
        assert rows["within"] == 4
        assert rows["breached"] == 1
        assert rows["compliance"] == pytest.approx(0.8)
        assert rows["median_hours"] == pytest.approx(10.0)
        assert rows["worst_hours"] == pytest.approx(90.0)

    def test_con_pocas_atenciones_no_se_reporta_un_porcentaje(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        an_attention(session, unit, code="OT-UNA")
        session.flush()
        rows = apg(client, unit)["restoration"]
        assert rows["judged"] == 1
        assert rows["compliance"] is None

    def test_rf_131_las_luminarias_se_cuentan_por_tecnología(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        """El campo lo inyecta el generador desde el perfil (regla 3): no está escrito a mano en el
        formulario, viene del modelo de datos de la unidad."""
        for index in range(3):
            an_attention(session, unit, code=f"OT-LED{index}", technology="led")
        an_attention(session, unit, code="OT-SODIO", technology="sodium_hp")
        session.flush()

        fleet = apg(client, unit)["fleet"]
        assert fleet["by_technology"]["led"] == 3
        assert fleet["by_technology"]["sodium_hp"] == 1

    def test_el_formulario_ya_no_permite_enviar_sin_tecnología(
        self, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        """Mejor que contarlas: que no ocurran.

        El bloque de atributos del activo llegó con el generador, y el atributo es obligatorio en el
        perfil, así que una captura nueva sin tecnología no se puede enviar. La comprobación está
        aquí porque de eso depende que el panel de flota signifique algo.
        """
        from app.responses.service import AnswerValidationError

        with pytest.raises(AnswerValidationError, match="technology"):
            an_attention(session, unit, code="OT-ST", technology=None)

    def test_las_capturas_antiguas_sin_tecnología_se_cuentan_aparte(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        """Las de antes de que el formulario lo pidiera.

        Una composición de flota calculada solo sobre las capturas que registraron tecnología
        informa la forma de los formularios bien llenados, no la de la flota.
        """
        order = an_attention(session, unit, code="OT-VIEJA-ST")
        response = session.scalars(
            select(FormResponse).where(FormResponse.work_order_id == order.id)
        ).one()
        # Así se ve una fila capturada antes de que el bloque B05 entrara en F-AP-01.
        response.answers = {
            key: value for key, value in response.answers.items() if key != "technology"
        }
        session.flush()

        fleet = apg(client, unit)["fleet"]
        assert fleet["without_technology"] == 1
        assert fleet["by_technology"] == {}

    def test_rf_131_la_tasa_de_falla_dice_cuál_es_su_denominador(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        """No es la tasa de la flota: el inventario vive en el SIG, y dividir por un total que la
        plataforma no conoce sería inventarlo."""
        an_attention(session, unit, code="OT-R1", luminaire="LUM-A")
        an_attention(session, unit, code="OT-R2", luminaire="LUM-A")
        an_attention(session, unit, code="OT-R3", luminaire="LUM-B")
        session.flush()

        failures = apg(client, unit)["failures"]
        assert failures["distinct_luminaires"] == 2
        assert failures["failures_per_luminaire"] == pytest.approx(1.5)
        assert "no el total instalado" in failures["denominator"]

    def test_una_luminaria_que_vuelve_a_fallar_se_destaca(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        """La reincidencia es la señal de que el reemplazo no arregló el problema."""
        an_attention(session, unit, code="OT-X1", luminaire="LUM-TERCA")
        an_attention(session, unit, code="OT-X2", luminaire="LUM-TERCA")
        an_attention(session, unit, code="OT-X3", luminaire="LUM-SANA")
        session.flush()

        repeats = apg(client, unit)["failures"]["repeat_offenders"]
        assert repeats == [{"asset_code": "LUM-TERCA", "failures": 2}]

    def test_las_causas_se_cuentan_para_saber_qué_comprar(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        an_attention(session, unit, code="OT-C1", cause="fotocontrol")
        an_attention(session, unit, code="OT-C2", cause="fotocontrol")
        an_attention(session, unit, code="OT-C3", cause="vandalismo")
        session.flush()
        assert apg(client, unit)["failures"]["by_cause"]["fotocontrol"] == 2


class TestThePeriod:
    def test_una_atención_anterior_al_periodo_no_entra(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        an_attention(session, unit, code="OT-VIEJA", submitted=NOW - timedelta(days=90))
        an_attention(session, unit, code="OT-NUEVA", submitted=NOW)
        session.flush()
        assert apg(client, unit, since=(NOW - timedelta(days=7)).isoformat())["attentions"] == 1


class TestTheExport:
    def test_rf_131_el_csv_abre_bien_en_un_excel_en_español(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        """Punto y coma, decimales con coma y marca de orden de bytes.

        No es una preferencia: un Excel configurado para Ecuador lee un archivo separado por comas
        como una sola columna y «1.5» como quince. «Exportable a Excel» significa esto.
        """
        an_attention(session, unit, code="OT-CSV", restored_after=timedelta(hours=60))
        session.flush()

        answer = client.get(f"/api/v1/analytics/units/{unit.code}/apg.csv")
        assert answer.status_code == 200
        assert "text/csv" in answer.headers["content-type"]
        assert "attachment" in answer.headers["content-disposition"]

        text = answer.content.decode("utf-8")
        assert text.startswith("﻿")
        header = text.splitlines()[0].lstrip("﻿")
        assert header.split(";")[0] == "ot"
        row = text.splitlines()[1]
        assert "OT-CSV" in row
        # 60,00 con coma decimal, no 60.00.
        assert "60,00" in row
        assert "60.00" not in row

    def test_un_mensaje_con_punto_y_coma_no_desplaza_las_columnas(
        self, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        """Un error de escape que corre una fila entera es más difícil de notar que un mensaje al
        que le falta un punto y coma."""
        an_attention(session, unit, code="OT-SEMI", restored_after=timedelta(hours=60))
        session.flush()

        board = build(session, unit.id, since=NOW - timedelta(days=30), until=NOW, now=NOW)
        board.breaches[0].as_dict()  # sanity: el veredicto existe
        board.breaches = [
            type(board.breaches[0])(
                **{**board.breaches[0].as_dict(), "message": "a;b;c", "hours": 60.0}
            )
        ]
        row = as_csv(board).splitlines()[1]
        assert len(row.split(";")) == 9

    def test_sin_incumplimientos_el_csv_trae_solo_la_cabecera(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        """Un archivo vacío haría dudar de si la consulta falló."""
        an_attention(session, unit, code="OT-BIEN", restored_after=timedelta(hours=5))
        session.flush()
        text = client.get(f"/api/v1/analytics/units/{unit.code}/apg.csv").content.decode("utf-8")
        assert len(text.strip().splitlines()) == 1


class TestWhoMaySee:
    def test_un_técnico_no_ve_el_tablero_de_apg(self, session: Session, unit: BusinessUnit) -> None:
        with client_as(session, TECHNICIAN) as raw:
            answer = raw.get(f"/api/v1/analytics/units/{unit.code}/apg")
        assert answer.status_code == 403

    def test_adr_009_el_tablero_no_cuenta_atenciones_de_otra_unidad(
        self, client: TestClient, session: Session, unit: BusinessUnit, deadline
    ) -> None:
        org = session.query(Organization).one()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        ingest_metadata(session, other, build_metadata("cnel-gye"))
        an_attention(session, other, code="OT-MAN")
        session.flush()
        assert apg(client, unit)["attentions"] == 0
