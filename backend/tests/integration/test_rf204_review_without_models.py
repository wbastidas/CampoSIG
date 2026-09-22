"""El supervisor revisa y aprueba con el servicio de modelos detenido (RF-204, regla 17).

El criterio de aceptación de RF-204, literal: «Con el servicio de modelos detenido, el supervisor
puede revisar y aprobar OT (sin informe de agente, con aviso)». Es la propiedad que decide si la
capa de IA es una ayuda o un punto único de fallo, y no se puede comprobar en una prueba unitaria
de la política: hay que pedir el detalle y aprobar de verdad, por HTTP, con la pasarela apagada.

Se prueba en los tres perfiles porque los tres tienen que funcionar (regla 17), y el aviso cambia
entre ellos: en el perfil A el VLM está desactivado y no vuelve; en el B y el C espera la noche.
"""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.responses.models import EvidenceStage
from app.responses.service import register_evidence, save_answers
from app.settings import get_settings
from app.workorders.models import WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

SUPERVISOR = Principal(
    subject="kc|supervisor.demo",
    username="supervisor.demo",
    display_name="Supervisor Demo",
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
def order(session: Session, unit: BusinessUnit):
    created = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        longitude=-79.9,
        latitude=-2.17,
        zone="Urbano",
        planner_id="planner.a",
    )
    created.state = WorkOrderState.SYNCED
    created.form_version = "1.0.0"
    session.flush()
    response = save_answers(
        session,
        unit,
        created,
        answers={
            "work_order_code": "OT-1",
            "work_type": "inspeccion_preventiva",
            "priority": "media",
            "general_condition": "regular",
            "code": "P-000452",
            "material": "concrete",
            "feeder_code": "04BH070T11",
            "final_state": "resuelto",
        },
        submit=True,
    )
    # Con las fotos que el formulario exige, para que la aprobación sea alcanzable: lo que este
    # archivo prueba es que la decisión se puede tomar sin modelos, no la compuerta de evidencia
    # de I6, que tiene sus propios tests.
    for index in range(2):
        register_evidence(
            session,
            response,
            kind="foto",
            storage_key=f"s3://antes-{index}.jpg",
            content_hash=hashlib.sha256(f"antes{index}".encode()).hexdigest(),
            stage=EvidenceStage.BEFORE,
        )
    session.flush()
    return created


@pytest.fixture
def client(session: Session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: SUPERVISOR
    with TestClient(app) as raw:
        yield raw
    app.dependency_overrides.clear()


@pytest.fixture
def no_gateway(monkeypatch: pytest.MonkeyPatch):
    """The model service, stopped. Which on this deployment means: never configured."""
    settings = get_settings()
    monkeypatch.setattr(settings, "model_gateway_url", "")
    return settings


def detail_url(unit_code: str, order_id: object) -> str:
    return f"/api/v1/review/units/{unit_code}/work-orders/{order_id}"


@pytest.mark.parametrize("profile", ["A", "B", "C"])
def test_rf_204_el_detalle_llega_con_aviso_y_sin_informe(
    client: TestClient, unit: BusinessUnit, order, no_gateway, monkeypatch, profile: str
) -> None:
    """El detalle de la revisión se arma igual, y dice qué no va a estar."""
    monkeypatch.setattr(no_gateway, "inference_profile", profile)

    answer = client.get(detail_url(unit.code, order.id))
    assert answer.status_code == 200
    body = answer.json()

    # Todo lo determinista sigue ahí: es lo que sostiene la decisión.
    assert body["response"]["answers"]["material"] == "concrete"
    assert body["compliance"]
    assert "blockers" in body

    # Y el aviso está, con su motivo, en vez de una sección ausente que parecería completa.
    degradations = {entry["alias"]: entry for entry in body["degradations"]}
    assert "llm-judge" in degradations
    assert degradations["llm-judge"]["reason"]
    assert "pasarela de modelos no está configurada" in degradations["llm-judge"]["reason"]


def test_rf_204_el_aviso_distingue_lo_que_espera_de_lo_que_no_vuelve(
    client: TestClient, unit: BusinessUnit, order, no_gateway, monkeypatch
) -> None:
    """«No disponible» sin decir cuál de las dos invita a seguir recargando la pantalla."""
    monkeypatch.setattr(no_gateway, "inference_profile", "A")
    on_cpu = {
        entry["alias"]: entry["placement"]
        for entry in client.get(detail_url(unit.code, order.id)).json()["degradations"]
    }
    # En el perfil A el VLM está desactivado: se omite, no espera.
    assert on_cpu["vlm-audit"] == "unavailable"
    assert on_cpu["llm-judge"] == "night_batch"

    monkeypatch.setattr(no_gateway, "inference_profile", "C")
    with_a_gpu = {
        entry["alias"]: entry["placement"]
        for entry in client.get(detail_url(unit.code, order.id)).json()["degradations"]
    }
    # Con GPU, la misma auditoría espera la ventana nocturna.
    assert with_a_gpu["vlm-audit"] == "night_batch"


def test_rf_204_aprobar_funciona_con_el_servicio_de_modelos_detenido(
    client: TestClient, session: Session, unit: BusinessUnit, order, no_gateway
) -> None:
    """La mitad del criterio que de verdad importa: la decisión se puede tomar."""
    # Primero se comprueba lo que de verdad importa: ningún impedimento menciona un modelo. Un
    # impedimento por IA sería exactamente el bloqueo que RF-204 prohíbe, y se vería aquí.
    blockers = client.get(detail_url(unit.code, order.id)).json()["blockers"]
    text = " ".join(blockers).lower()
    assert "modelo" not in text
    assert "pasarela" not in text
    assert "agente" not in text

    answer = client.post(
        f"{detail_url(unit.code, order.id)}/decision",
        json={"decision": "aprobada", "note": "Evidencia suficiente."},
    )
    assert blockers == [], f"la OT no debería tener impedimentos deterministas: {blockers}"
    assert answer.status_code == 200, answer.text
    session.refresh(order)
    assert order.state == WorkOrderState.APPROVED


def test_rf_204_con_la_pasarela_configurada_y_perfil_c_no_hay_avisos(
    client: TestClient, unit: BusinessUnit, order, monkeypatch
) -> None:
    """La otra mitad del contrato: el aviso aparece cuando falta algo, no siempre.

    Sin esto, un aviso permanente se vuelve parte del decorado y nadie lo lee el día que significa
    algo.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "model_gateway_url", "http://pasarela.interna:4000")
    monkeypatch.setattr(settings, "inference_profile", "C")

    body = client.get(detail_url(unit.code, order.id)).json()
    assert body["degradations"] == []
