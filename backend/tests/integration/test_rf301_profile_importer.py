"""El importador de perfiles, de punta a punta (RF-301, RF-302, ADR-009).

Lo que se prueba aquí es el criterio de aceptación de I2 tal como lo vive un administrador
funcional: sincronizar metadatos, abrir un borrador, ver los huecos, decidir, publicar, y que
**la unidad adopte el perfil sin desplegar nada**.

Y tres cosas que tienen que fallar:

* publicar un perfil incompleto;
* abrir dos borradores en paralelo del mismo perfil;
* tocar el borrador de otra unidad de negocio.

Necesita PostgreSQL real: los índices parciales que impiden dos borradores abiertos son
PostgreSQL, no SQLAlchemy, y probarlos sin base sería probar la intención.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.model_profile.drafts import (
    DraftError,
    open_draft,
    publish_draft,
    published_profile,
    save_decisions,
    start_draft,
)
from app.model_profile.matching import (
    ProfileDecisions,
)
from app.model_profile.metadata import GisMetadata
from app.model_profile.models import STATUS_PUBLISHED, STATUS_SUPERSEDED, ProfileDraft
from app.model_profile.profile import ProfileHeader
from app.org.models import BusinessUnit, Organization
from app.org.service import resolver_for_unit
from app.settings import get_settings
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

ADMIN = "admin.funcional:admin_funcional|GYE,MAN"
PLANNER = "planificador.demo:planificador|GYE"


@pytest.fixture
def units(session: Session) -> dict[str, BusinessUnit]:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created: dict[str, BusinessUnit] = {}
    for code, name in (("GYE", "Unidad Guayaquil"), ("MAN", "Unidad Manabí")):
        unit = BusinessUnit(organization_id=org.id, code=code, name=name, profile_id="cnel-gye")
        session.add(unit)
        created[code] = unit
    session.flush()
    for unit in created.values():
        ingest_metadata(session, unit, build_metadata("cnel-gye"))
    session.flush()
    return created


@pytest.fixture
def unit(units: dict[str, BusinessUnit]) -> BusinessUnit:
    return units["GYE"]


@pytest.fixture
def metadata() -> GisMetadata:
    return build_metadata("cnel-gye")


@pytest.fixture
def client(session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    settings = get_settings()
    monkeypatch.setattr(settings, "allow_dev_identity", True)
    monkeypatch.setattr(settings, "environment", "development")
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as raw:
        yield raw
    app.dependency_overrides.clear()


def _header(profile_id: str = "gye-importado") -> ProfileHeader:
    return ProfileHeader(id=profile_id, provider="arcpy-agent", spatial_reference=32717)


def _start(session: Session, unit: BusinessUnit, metadata: GisMetadata) -> ProfileDraft:
    return start_draft(
        session,
        unit_id=unit.id,
        profile_id="gye-importado",
        header=_header(),
        metadata=metadata,
        snapshot_id=None,
        created_by="dev:admin",
    )


class TestTheDraftLifecycle:
    def test_rf_301_un_borrador_nuevo_llega_prellenado_y_sin_huecos(
        self, session: Session, unit: BusinessUnit, metadata: GisMetadata
    ) -> None:
        """Con metadatos coherentes, la coincidencia asistida no deja nada que decidir."""
        draft = _start(session, unit, metadata)
        assert draft.version == 1
        assert draft.problems == []
        assert draft.ready
        assert draft.document is not None

    def test_rf_301_publicar_hace_que_la_unidad_adopte_el_perfil_sin_desplegar(
        self, session: Session, unit: BusinessUnit, metadata: GisMetadata
    ) -> None:
        """La afirmación entera de RF-301, y la única forma de comprobarla: el resolver.

        Antes de publicar, la unidad resuelve con el archivo de `profiles/`. Después,
        con lo que el administrador aprobó — sin reiniciar nada.
        """
        assert published_profile(session, unit.id, "gye-importado") is None

        draft = _start(session, unit, metadata)
        publish_draft(session, draft, published_by="dev:admin")
        session.flush()

        unit.profile_id = "gye-importado"
        adopted = resolver_for_unit(unit, session)
        assert adopted.profile.id == "gye-importado"
        # Y resuelve lo mismo que el perfil de archivo del que salieron los metadatos.
        from_file = resolver_for_unit(units_copy(unit, "cnel-gye"))
        assert adopted.binding("support_structure").layer == (
            from_file.binding("support_structure").layer
        )

    def test_rf_301_publicar_supersede_la_version_anterior_en_vez_de_editarla(
        self, session: Session, unit: BusinessUnit, metadata: GisMetadata
    ) -> None:
        """Un formulario generado en marzo tiene que seguir explicándose en septiembre."""
        first = _start(session, unit, metadata)
        publish_draft(session, first, published_by="dev:admin")
        session.flush()

        second = _start(session, unit, metadata)
        assert second.version == 2
        publish_draft(session, second, published_by="dev:otro")
        session.flush()
        session.refresh(first)

        assert first.status == STATUS_SUPERSEDED
        assert second.status == STATUS_PUBLISHED
        assert first.document is not None, "la versión superada conserva su documento"

    def test_rf_301_un_perfil_incompleto_no_se_puede_publicar(
        self, session: Session, unit: BusinessUnit, metadata: GisMetadata
    ) -> None:
        """La compuerta es `validate_against_amd`, y se aplica al publicar, no solo al editar."""
        draft = _start(session, unit, metadata)
        decisions = ProfileDecisions.model_validate(draft.decisions)
        # Quitar el atributo obligatorio de un tipo es exactamente el hueco que RF-302
        # reporta y que no debe llegar a producción.
        del decisions.assets["support_structure"].attributes["code"]
        save_decisions(session, draft, metadata, decisions, updated_by="dev:admin")

        assert draft.problems
        with pytest.raises(DraftError, match="no está completo"):
            publish_draft(session, draft, published_by="dev:admin")
        assert draft.status != STATUS_PUBLISHED

    def test_rf_301_dos_borradores_abiertos_del_mismo_perfil_los_rechaza_la_base(
        self, session: Session, unit: BusinessUnit, metadata: GisMetadata
    ) -> None:
        """Dos administradores en paralelo es cómo se pierde la mitad del trabajo de uno."""
        _start(session, unit, metadata)
        session.flush()
        with pytest.raises(DraftError, match="borrador abierto"):
            _start(session, unit, metadata)

        # Y si alguien se salta el servicio, el índice parcial lo impide igual.
        session.rollback()
        session.add(
            ProfileDraft(
                business_unit_id=unit.id,
                profile_id="gye-importado",
                version=1,
                status="draft",
                created_by="dev:uno",
            )
        )
        session.add(
            ProfileDraft(
                business_unit_id=unit.id,
                profile_id="gye-importado",
                version=2,
                status="draft",
                created_by="dev:dos",
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()

    def test_rf_301_reimportar_conserva_las_decisiones_de_la_persona(
        self, session: Session, unit: BusinessUnit, metadata: GisMetadata
    ) -> None:
        """Si re-sincronizar perdiera las anulaciones, nadie volvería a re-sincronizar."""
        first = _start(session, unit, metadata)
        decisions = ProfileDecisions.model_validate(first.decisions)
        # Una anulación deliberada: el administrador sabe algo que la propuesta no.
        chosen = decisions.assets["support_structure"]
        alternative = next(
            field.name
            for field in metadata.layers[0].fields
            if field.name != chosen.attributes["code"] and field.type == "String"
        )
        chosen.attributes["code"] = alternative
        save_decisions(session, first, metadata, decisions, updated_by="dev:admin")
        publish_draft(session, first, published_by="dev:admin")
        session.flush()

        second = _start(session, unit, metadata)
        carried = ProfileDecisions.model_validate(second.decisions)
        assert carried.assets["support_structure"].attributes["code"] == alternative

    def test_una_version_publicada_ya_no_se_edita(
        self, session: Session, unit: BusinessUnit, metadata: GisMetadata
    ) -> None:
        draft = _start(session, unit, metadata)
        publish_draft(session, draft, published_by="dev:admin")
        session.flush()
        with pytest.raises(DraftError, match="published"):
            save_decisions(
                session,
                draft,
                metadata,
                ProfileDecisions.model_validate(draft.decisions),
                updated_by="dev:admin",
            )


class TestIsolationBetweenUnits:
    def test_adr_009_publicar_en_una_unidad_no_afecta_a_la_otra(
        self, session: Session, units: dict[str, BusinessUnit], metadata: GisMetadata
    ) -> None:
        gye, man = units["GYE"], units["MAN"]
        publish_draft(session, _start(session, gye, metadata), published_by="dev:admin")
        session.flush()

        assert published_profile(session, gye.id, "gye-importado") is not None
        assert published_profile(session, man.id, "gye-importado") is None
        # Y cada unidad puede tener su propio borrador abierto del mismo perfil.
        assert open_draft(session, man.id, "gye-importado") is None
        _start(session, man, metadata)
        session.flush()
        assert open_draft(session, man.id, "gye-importado") is not None


class TestTheApi:
    def test_rf_301_la_propuesta_llega_con_evidencia_y_con_las_clases_disponibles(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        answer = client.get(
            "/api/v1/model-profile/proposal",
            params={"business_unit": "GYE"},
            headers={"X-SIGEC-Dev-Identity": ADMIN},
        )
        assert answer.status_code == 200
        body = answer.json()
        assert body["gaps"] == []
        assert body["layer_names"]
        first = body["proposal"]["assets"][0]
        assert first["candidates"][0]["evidence"], "una propuesta sin evidencia no es revisable"

    def test_rf_002_un_planificador_no_puede_tocar_el_perfil(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        """El perfil decide dónde aterrizan los datos de campo; no es de un planificador."""
        answer = client.get(
            "/api/v1/model-profile/proposal",
            params={"business_unit": "GYE"},
            headers={"X-SIGEC-Dev-Identity": PLANNER},
        )
        assert answer.status_code == 403

    def test_rf_002_un_editor_gis_tampoco_puede_tocar_el_perfil(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        """Ni siquiera quien aplica los cambios en el GIS: aplicar y mapear son cosas distintas."""
        answer = client.get(
            "/api/v1/model-profile/proposal",
            params={"business_unit": "GYE"},
            headers={"X-SIGEC-Dev-Identity": "editor:editor_gis|GYE"},
        )
        assert answer.status_code == 403

    def test_adr_009_un_administrador_funcional_atraviesa_las_unidades_a_proposito(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        """Se fija aquí porque sorprende, y porque es una decisión, no un descuido.

        `admin_funcional` es un rol corporativo: `Principal.is_corporate` lo dice, y su cuenta
        no está atada a una unidad. Así que un administrador cuyo token nombra MAN puede
        trabajar el perfil de GYE — que es el caso de uso real, un equipo funcional central
        configurando unidad por unidad. Si esto alguna vez tiene que dejar de ser cierto, será
        en `Principal`, para toda la API a la vez, y este test lo notará.
        """
        answer = client.get(
            "/api/v1/model-profile/proposal",
            params={"business_unit": "GYE"},
            headers={"X-SIGEC-Dev-Identity": "central:admin_funcional|MAN"},
        )
        assert answer.status_code == 200

    def test_rf_301_el_ciclo_completo_por_http(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        headers = {"X-SIGEC-Dev-Identity": ADMIN}
        created = client.post(
            "/api/v1/model-profile/drafts",
            params={"business_unit": "GYE"},
            json={"profile_id": "gye-importado", "label": "GYE importado"},
            headers=headers,
        )
        assert created.status_code == 201, created.text
        draft_id = created.json()["draft_id"]
        assert created.json()["problems"] == []
        # La identidad sale del token, nunca del cuerpo (ADR-013).
        assert created.json()["created_by"].startswith("dev:")

        published = client.post(
            f"/api/v1/model-profile/drafts/{draft_id}/publish",
            params={"business_unit": "GYE"},
            headers=headers,
        )
        assert published.status_code == 200, published.text
        assert published.json()["status"] == "published"

        exported = client.get(
            f"/api/v1/model-profile/drafts/{draft_id}/yaml",
            params={"business_unit": "GYE"},
            headers=headers,
        )
        assert exported.status_code == 200
        assert exported.headers["content-type"].startswith("application/yaml")
        assert "bindings:" in exported.text

        listed = client.get(
            "/api/v1/model-profile/history",
            params={"business_unit": "GYE", "profile_id": "gye-importado"},
            headers=headers,
        )
        assert [entry["status"] for entry in listed.json()] == ["published"]

    def test_rf_301_publicar_un_borrador_incompleto_devuelve_la_lista_de_huecos(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        headers = {"X-SIGEC-Dev-Identity": ADMIN}
        created = client.post(
            "/api/v1/model-profile/drafts",
            params={"business_unit": "GYE"},
            json={"profile_id": "gye-importado"},
            headers=headers,
        )
        draft_id = created.json()["draft_id"]
        decisions = created.json()["decisions"]
        del decisions["assets"]["support_structure"]["attributes"]["code"]

        saved = client.put(
            f"/api/v1/model-profile/drafts/{draft_id}",
            params={"business_unit": "GYE"},
            json={"decisions": decisions},
            headers=headers,
        )
        assert saved.status_code == 200
        assert saved.json()["problems"]
        assert saved.json()["ready"] is False

        refused = client.post(
            f"/api/v1/model-profile/drafts/{draft_id}/publish",
            params={"business_unit": "GYE"},
            headers=headers,
        )
        assert refused.status_code == 422
        assert "code" in refused.json()["detail"]

    def test_adr_009_el_borrador_de_otra_unidad_da_404_y_no_403(
        self, client: TestClient, units: dict[str, BusinessUnit], session: Session
    ) -> None:
        """404 a propósito: sondear ids no debería enseñar que existe algo en otra unidad."""
        other = _start(session, units["MAN"], build_metadata("cnel-gye"))
        session.flush()
        answer = client.get(
            f"/api/v1/model-profile/drafts/{other.id}/yaml",
            params={"business_unit": "GYE"},
            headers={"X-SIGEC-Dev-Identity": ADMIN},
        )
        assert answer.status_code == 404

    def test_sin_metadatos_sincronizados_la_respuesta_lo_dice(
        self, client: TestClient, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        """Y lo dice con 409, porque no falta el recurso: falta que el agente haya corrido."""
        from app.gis_gateway.models import MetadataSnapshot

        session.query(MetadataSnapshot).delete()
        session.flush()
        answer = client.get(
            "/api/v1/model-profile/proposal",
            params={"business_unit": "GYE"},
            headers={"X-SIGEC-Dev-Identity": ADMIN},
        )
        assert answer.status_code == 409
        assert "agente" in answer.json()["detail"]

    def test_reevaluar_contra_otra_clase_llega_por_http(
        self, client: TestClient, unit: BusinessUnit, metadata: GisMetadata
    ) -> None:
        other = metadata.layers[-1].name
        answer = client.get(
            "/api/v1/model-profile/proposal/support_structure",
            params={"business_unit": "GYE", "layer": other},
            headers={"X-SIGEC-Dev-Identity": ADMIN},
        )
        assert answer.status_code == 200
        assert answer.json()["candidates"][0]["layer"] == other


def units_copy(unit: BusinessUnit, profile_id: str) -> BusinessUnit:
    """A detached twin pointing at a different profile, for comparing resolutions."""
    return BusinessUnit(
        organization_id=unit.organization_id,
        code=unit.code,
        name=unit.name,
        profile_id=profile_id,
        spatial_reference=unit.spatial_reference,
    )
