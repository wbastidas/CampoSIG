"""The loop, end to end: capture, submit, review, approve, stage, dispatch (I5 + I6).

This is the path the whole platform exists to serve. Each step has its own tests elsewhere;
these assert that the steps connect, and that the gates between them actually hold.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.gis_gateway.asbuilt import (
    ProposalRejectedError,
    apply_results,
    batch_payload,
    build_proposal,
    create_batch,
    stage_from_work_order,
)
from app.gis_gateway.ingest import ingest_metadata
from app.gis_gateway.staging_table import asbuilt_proposal
from app.org.models import BusinessUnit, Organization
from app.org.service import resolver_for_unit
from app.responses.models import EvidenceStage, ResponseState, ValueOrigin
from app.responses.service import (
    AnswerValidationError,
    NotEditableError,
    compose_for,
    missing_photos,
    record_provenance,
    register_evidence,
    save_answers,
    unconfirmed_ai_values,
    verify_integrity,
)
from app.review.blind import assign as assign_blind
from app.review.models import Decision
from app.review.service import (
    ApprovalBlockedError,
    NotReviewableError,
    decide,
    decision_history,
    observations_for,
    queue_size,
    review_queue,
)
from app.workorders.models import WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration


@pytest.fixture
def unit(session: Session) -> BusinessUnit:
    """A business unit whose agent has already synced metadata.

    The sync matters: without a metadata snapshot the asset-derived sections of a form are
    empty and the form has no requirements, which is correct behaviour but not the situation
    these tests are about. A real deployment has run its agent before anyone captures work.
    """
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
        planner_id="planner.a",
    )
    created.state = WorkOrderState.SYNCED
    created.form_version = "1.0.0"
    session.flush()
    return created


def full_answers() -> dict:
    """Answers that satisfy F-MT-01, so tests can start from a valid baseline."""
    return {
        "work_order_code": "OT-1",
        "work_type": "inspeccion_preventiva",
        "priority": "media",
        "gps": {"latitude": -2.17, "longitude": -79.9, "accuracy_m": 4.0},
        "general_condition": "regular",
        "code": "P-000452",
        "material": "concrete",
        # Required because the capture manual marks the feeder CORE. Its catalogue is one of
        # the three that vary per business unit, so the value is a real GYE feeder code.
        "feeder_code": "04BH070T11",
        "height_m": 11.0,
        "final_state": "resuelto",
        # B04: el formulario exige ATS, así que la referencia es obligatoria.
        "ats_reference": "ATS-2026-0001",
        "photos_before": ["s3://a.jpg", "s3://b.jpg"],
        "photos_after": [],
    }


def add_photos(session: Session, response, before: int = 2, after: int = 0) -> None:
    for stage, count in ((EvidenceStage.BEFORE, before), (EvidenceStage.AFTER, after)):
        for index in range(count):
            register_evidence(
                session,
                response,
                kind="foto",
                storage_key=f"s3://{stage.value}-{index}.jpg",
                content_hash=hashlib.sha256(f"{stage}{index}".encode()).hexdigest(),
                stage=stage,
            )


class TestCaptureAndValidation:
    def test_a_draft_is_saved_without_full_validation(self, session, unit, order):
        """A technician halfway through must not be blocked by a field they have not reached."""
        response = save_answers(session, unit, order, answers={"code": "P-1"}, submit=False)
        assert response.state == ResponseState.DRAFT

    def test_submitting_incomplete_answers_is_refused(self, session, unit, order):
        with pytest.raises(AnswerValidationError):
            save_answers(session, unit, order, answers={"code": "P-1"}, submit=True)

    def test_submitting_valid_answers_succeeds(self, session, unit, order):
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        assert response.state == ResponseState.SUBMITTED
        assert response.submitted_at is not None

    def test_the_conditional_rule_is_enforced_on_the_server(self, session, unit, order):
        """The cause is required when the work was not resolved (block B12's rule)."""
        answers = full_answers() | {"final_state": "no_resuelto"}
        with pytest.raises(AnswerValidationError, match="causa"):
            save_answers(session, unit, order, answers=answers, submit=True)

        answers["unresolved_reason"] = "falta_material"
        response = save_answers(session, unit, order, answers=answers, submit=True)
        assert response.state == ResponseState.SUBMITTED

    def test_an_ats_form_is_refused_without_the_ats_reference(self, session, unit, order):
        """B04, y la razón de que el bloque exista.

        `requires_ats: true` viajaba al teléfono como `x-requires-ats` y nada lo miraba: no había
        campo donde anotar cuál, así que una OT «que exige ATS» se cerraba sin nombrar ninguno.
        """
        answers = {key: value for key, value in full_answers().items() if key != "ats_reference"}
        with pytest.raises(AnswerValidationError, match="ats_reference"):
            save_answers(session, unit, order, answers=answers, submit=True)

    def test_a_work_permit_without_its_ats_is_refused(self, session, unit, order):
        """La regla de B04, que además es el primer uso del operador «está contestado»."""
        answers = {key: value for key, value in full_answers().items() if key != "ats_reference"}
        answers["work_permit_reference"] = "PT-2026-77"
        with pytest.raises(AnswerValidationError, match="ATS"):
            save_answers(session, unit, order, answers=answers, submit=True)

    def test_a_form_without_b07_does_not_validate_materials(self, session, unit, order):
        """Una inspección preventiva no lleva B07, y por eso este test está escrito así.

        La primera versión mandaba `materials` a F-MT-01 y pasaba: el esquema no prohíbe
        propiedades extra, así que la tabla viajaba como dato desconocido y el test no probaba nada
        del bloque. Lo que sí se puede afirmar aquí es que el formulario **no** la declara; que la
        tabla funciona se prueba contra un formulario que la incluye, en los tests del compositor.
        """
        composed = compose_for(session, unit, order)
        assert "materials" not in composed.schema["properties"]

    def test_the_form_version_is_the_one_assigned(self, session, unit, order):
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        assert response.form_version == order.form_version

    def test_a_submitted_response_is_no_longer_the_devices_to_change(self, session, unit, order):
        save_answers(session, unit, order, answers=full_answers(), submit=True)
        with pytest.raises(NotEditableError):
            save_answers(session, unit, order, answers=full_answers(), submit=False)


class TestEvidence:
    def test_integrity_is_verified_against_the_devices_hash(self, session, unit, order):
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        content = b"contenido de la foto"
        evidence = register_evidence(
            session,
            response,
            kind="foto",
            storage_key="s3://x.jpg",
            content_hash=hashlib.sha256(content).hexdigest(),
            stage=EvidenceStage.BEFORE,
        )
        assert verify_integrity(evidence, content) is True
        assert evidence.integrity_verified is True

    def test_a_mismatched_file_is_not_evidence(self, session, unit, order):
        """A photograph whose hash does not match is not the photograph that was taken."""
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        evidence = register_evidence(
            session,
            response,
            kind="foto",
            storage_key="s3://x.jpg",
            content_hash=hashlib.sha256(b"original").hexdigest(),
            stage=EvidenceStage.BEFORE,
        )
        assert verify_integrity(evidence, b"otra cosa") is False
        assert evidence.integrity_verified is False

    def test_photo_minimums_are_reported(self, session, unit, order):
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        form = compose_for(session, unit, order)
        # F-MT-01 requires two "before" photographs.
        assert missing_photos(form, response)
        add_photos(session, response, before=2)
        session.refresh(response)
        assert missing_photos(form, response) == []


class TestProvenance:
    def test_an_accepted_proposal_is_marked_unchanged(self, session, unit, order):
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        entry = record_provenance(
            session,
            response,
            field_key="material",
            origin=ValueOrigin.VOICE,
            proposed_value="concrete",
            final_value="concrete",
            model_name="qwen2.5-1.5b",
            model_version="0.4.0",
            confidence=0.91,
            confirmed_by="tecnico.a",
        )
        assert entry.accepted_unchanged is True
        assert entry.confirmed_at is not None

    def test_a_correction_is_the_more_valuable_example(self, session, unit, order):
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        entry = record_provenance(
            session,
            response,
            field_key="material",
            origin=ValueOrigin.VOICE,
            proposed_value="wood",
            final_value="concrete",
            confirmed_by="tecnico.a",
        )
        assert entry.accepted_unchanged is False
        assert entry.proposed_value == {"v": "wood"}
        assert entry.final_value == {"v": "concrete"}

    def test_an_unconfirmed_ai_value_is_detected(self, session, unit, order):
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        record_provenance(
            session,
            response,
            field_key="material",
            origin=ValueOrigin.VISION,
            proposed_value="concrete",
            final_value="concrete",
        )
        session.refresh(response)
        assert [e.field_key for e in unconfirmed_ai_values(session, response)] == ["material"]

    def test_a_manual_value_needs_no_confirmation(self, session, unit, order):
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        record_provenance(
            session, response, field_key="code", origin=ValueOrigin.MANUAL, final_value="P-1"
        )
        session.refresh(response)
        assert unconfirmed_ai_values(session, response) == []


class TestReview:
    def test_the_queue_shows_synced_work(self, session, unit, order):
        assert [o.id for o in review_queue(session, unit)] == [order.id]
        assert queue_size(session, unit) == 1

    def test_the_queue_never_shows_another_units_work(self, session, unit, order):
        other_org = session.get(Organization, unit.organization_id)
        assert other_org is not None
        other = BusinessUnit(
            organization_id=other_org.id, code="MAN", name="Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        assert review_queue(session, other) == []

    def test_approving_without_a_response_is_blocked(self, session, unit, order):
        with pytest.raises(ApprovalBlockedError, match="no hay respuesta"):
            decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="sup.a")

    def test_approving_without_the_required_photos_is_blocked(self, session, unit, order):
        save_answers(session, unit, order, answers=full_answers(), submit=True)
        with pytest.raises(ApprovalBlockedError, match="fotos"):
            decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="sup.a")

    def test_approving_over_unconfirmed_ai_values_is_blocked(self, session, unit, order):
        """SRS rule 0.5: approving these would make the model the author of the record."""
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        add_photos(session, response, before=2)
        record_provenance(
            session,
            response,
            field_key="material",
            origin=ValueOrigin.VISION,
            proposed_value="concrete",
            final_value="concrete",
        )
        session.refresh(response)
        with pytest.raises(ApprovalBlockedError, match="sin confirmar"):
            decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="sup.a")

    def test_a_complete_work_order_is_approved(self, session, unit, order):
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        add_photos(session, response, before=2)
        session.refresh(response)
        row = decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="sup.a")
        assert row.decision == Decision.APPROVED
        assert order.state == WorkOrderState.APPROVED
        assert response.state == ResponseState.APPROVED

    def test_returning_attaches_observations_to_their_fields(self, session, unit, order):
        """RF-112: 'faltan datos' makes a technician guess, and guessing returns it twice."""
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        decide(
            session,
            unit,
            order,
            decision=Decision.RETURNED,
            reviewer_sub="sup.a",
            note="revisar altura",
            observations=[
                {"field_key": "height_m", "message": "La altura no coincide con la foto"},
            ],
        )
        assert order.state == WorkOrderState.RETURNED
        session.refresh(response)
        assert response.state == ResponseState.RETURNED
        observations = observations_for(session, order)
        assert [o.field_key for o in observations] == ["height_m"]

    def test_a_returned_response_is_editable_again(self, session, unit, order):
        save_answers(session, unit, order, answers=full_answers(), submit=True)
        decide(session, unit, order, decision=Decision.RETURNED, reviewer_sub="sup.a", note="x")
        # The technician must be able to act on the observations.
        updated = save_answers(session, unit, order, answers=full_answers(), submit=False)
        assert updated.state == ResponseState.RETURNED

    def test_deciding_on_work_that_is_not_in_review_is_refused(self, session, unit, order):
        order.state = WorkOrderState.IN_EXECUTION
        session.flush()
        with pytest.raises(NotReviewableError):
            decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="sup.a")

    def test_the_decision_history_is_kept(self, session, unit, order):
        save_answers(session, unit, order, answers=full_answers(), submit=True)
        decide(session, unit, order, decision=Decision.RETURNED, reviewer_sub="sup.a", note="1")
        assert len(decision_history(session, order)) == 1

    def test_rf_111a_el_sorteo_marca_la_decisión_y_no_la_marca_quien_la_toma(
        self, session, unit, order
    ):
        """RF-111a: el sesgo de anclaje se mide, no se supone resuelto.

        Y la marca sale del sorteo. Antes era un booleano que mandaba el navegador, es decir un
        campo que rellenaba lo que se está midiendo.
        """
        save_answers(session, unit, order, answers=full_answers(), submit=True)
        assign_blind(session, order.id, unit.id, rate=1.0)
        row = decide(
            session, unit, order, decision=Decision.RETURNED, reviewer_sub="sup.a", note="x"
        )
        assert row.blind_sample is True

    def test_rf_111a_una_ot_no_sorteada_no_queda_marcada_como_ciega(self, session, unit, order):
        """Si toda decisión se marcara ciega, el kappa se calcularía sobre la población entera."""
        save_answers(session, unit, order, answers=full_answers(), submit=True)
        row = decide(
            session, unit, order, decision=Decision.RETURNED, reviewer_sub="sup.a", note="x"
        )
        assert row.blind_sample is None


class TestAsBuiltStaging:
    @pytest.fixture
    def approved(self, session, unit, order):
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        add_photos(session, response, before=2)
        session.refresh(response)
        decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="sup.a")
        return order

    def test_a_proposal_is_validated_against_the_profile(self, unit):
        resolver = resolver_for_unit(unit)
        proposal = build_proposal(
            resolver,
            asset_type_key="support_structure",
            action="create",
            attributes={"code": "P-999", "material": "concrete"},
        )
        assert proposal["action"] == "create"

    def test_an_attribute_outside_the_profile_is_refused(self, unit):
        """The profile defines the write scope (D11)."""
        resolver = resolver_for_unit(unit)
        with pytest.raises(ProposalRejectedError, match="fuera del alcance"):
            build_proposal(
                resolver,
                asset_type_key="support_structure",
                action="create",
                attributes={"campo_inventado": 1},
            )

    def test_an_update_without_an_element_is_refused(self, unit):
        resolver = resolver_for_unit(unit)
        with pytest.raises(ProposalRejectedError, match="identificador"):
            build_proposal(
                resolver,
                asset_type_key="support_structure",
                action="update",
                attributes={"code": "P-1"},
            )

    def test_an_unknown_action_is_refused(self, unit):
        resolver = resolver_for_unit(unit)
        with pytest.raises(ProposalRejectedError, match="no válida"):
            build_proposal(
                resolver, asset_type_key="support_structure", action="borrar", attributes={}
            )

    def test_staging_requires_an_approved_work_order(self, session, unit, order):
        """Staging is the antechamber to the corporate geodatabase."""
        with pytest.raises(ProposalRejectedError, match="aprobada"):
            stage_from_work_order(
                session,
                unit,
                order,
                [
                    {
                        "proposal_id": str(uuid.uuid4()),
                        "asset_type_key": "support_structure",
                        "action": "create",
                        "attributes": {"code": "P-999"},
                    }
                ],
            )

    def test_approved_work_reaches_staging(self, session, unit, approved):
        staged = stage_from_work_order(
            session,
            unit,
            approved,
            [
                {
                    "proposal_id": str(uuid.uuid4()),
                    "asset_type_key": "support_structure",
                    "action": "create",
                    "attributes": {"code": "P-999", "material": "concrete"},
                }
            ],
        )
        assert len(staged) == 1

    def test_staging_is_idempotent(self, session, unit, approved):
        """Re-approving must not duplicate a pole in the geodatabase."""
        proposal_id = str(uuid.uuid4())
        payload = [
            {
                "proposal_id": proposal_id,
                "asset_type_key": "support_structure",
                "action": "create",
                "attributes": {"code": "P-999"},
            }
        ]
        first = stage_from_work_order(session, unit, approved, payload)
        second = stage_from_work_order(session, unit, approved, payload)
        assert first == second

        batch = create_batch(session, unit, asset_type_key="support_structure")
        assert batch is not None
        assert len(batch_payload(session, unit, batch)["proposals"]) == 1


class TestBatchDispatch:
    @pytest.fixture
    def staged(self, session, unit, order):
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        add_photos(session, response, before=2)
        session.refresh(response)
        decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="sup.a")
        proposal_id = str(uuid.uuid4())
        stage_from_work_order(
            session,
            unit,
            order,
            [
                {
                    "proposal_id": proposal_id,
                    "asset_type_key": "support_structure",
                    "action": "create",
                    "attributes": {"code": "P-999", "material": "concrete"},
                }
            ],
        )
        return proposal_id

    def test_nothing_staged_means_no_batch(self, session, unit):
        assert create_batch(session, unit, asset_type_key="street_light") is None

    def test_a_batch_carries_what_the_agent_needs(self, session, unit, staged):
        batch = create_batch(session, unit, asset_type_key="support_structure")
        assert batch is not None
        payload = batch_payload(session, unit, batch)
        assert payload["target_layer"]
        assert payload["field_map"]["code"]
        assert payload["spatial_reference"] == unit.spatial_reference
        assert len(payload["proposals"]) == 1

    def test_the_batch_carries_only_mapped_fields(self, session, unit, staged):
        """Nothing outside the profile can reach the geodatabase."""
        batch = create_batch(session, unit, asset_type_key="support_structure")
        assert batch is not None
        payload = batch_payload(session, unit, batch)
        resolver = resolver_for_unit(unit)
        assert set(payload["field_map"]) == set(resolver.fields("support_structure"))

    def test_a_network_class_is_marked_staging_only(self, session, unit):
        resolver = resolver_for_unit(unit)
        assert resolver.participates_in_geometric_network("distribution_transformer")
        assert resolver.write_path("distribution_transformer").value == "staging_only"

    def test_results_are_recorded_on_the_staging_rows(self, session, unit, staged):
        batch = create_batch(session, unit, asset_type_key="support_structure")
        assert batch is not None
        apply_results(session, batch, [{"proposal_id": staged, "status": "applied"}])
        # The proposal stays visible in the batch: the trail is the point, not a queue that
        # empties. An auditor asking what reached the geodatabase needs this row.
        assert len(batch_payload(session, unit, batch)["proposals"]) == 1

    def test_requires_arcfm_is_not_an_error(self, session, unit, staged):
        """The agent said all it can; the rest is the GIS team's call (D11).

        So the proposal stays dispatched rather than becoming an error: nothing went wrong,
        it simply needs ArcFM's auto-updaters, which the agent deliberately never runs.
        """
        batch = create_batch(session, unit, asset_type_key="support_structure")
        assert batch is not None
        apply_results(session, batch, [{"proposal_id": staged, "status": "requires_arcfm"}])

        row = session.execute(
            select(asbuilt_proposal.c.status, asbuilt_proposal.c.apply_result).where(
                asbuilt_proposal.c.proposal_id == uuid.UUID(staged)
            )
        ).one()
        assert row.status == "dispatched"
        assert row.apply_result["status"] == "requires_arcfm"

    def test_an_applied_proposal_is_recorded_as_applied(self, session, unit, staged):
        batch = create_batch(session, unit, asset_type_key="support_structure")
        assert batch is not None
        apply_results(session, batch, [{"proposal_id": staged, "status": "applied"}])
        status = session.execute(
            select(asbuilt_proposal.c.status).where(
                asbuilt_proposal.c.proposal_id == uuid.UUID(staged)
            )
        ).scalar_one()
        assert status == "applied"

    def test_an_agent_error_is_recorded_as_an_error(self, session, unit, staged):
        batch = create_batch(session, unit, asset_type_key="support_structure")
        assert batch is not None
        apply_results(
            session,
            batch,
            [{"proposal_id": staged, "status": "error", "message": "red bloqueada"}],
        )
        row = session.execute(
            select(asbuilt_proposal.c.status, asbuilt_proposal.c.apply_result).where(
                asbuilt_proposal.c.proposal_id == uuid.UUID(staged)
            )
        ).one()
        assert row.status == "error"
        # The agent's message survives, so a human can see why it failed.
        assert "red bloqueada" in row.apply_result["message"]


class TestTheWholeLoop:
    def test_capture_review_approve_stage_dispatch(self, session, unit, order):
        """The path the platform exists to serve, in one test."""
        # 1. The technician fills the form and closes it in the field.
        response = save_answers(
            session,
            unit,
            order,
            answers=full_answers(),
            device_key="phone-001",
            captured_by="tecnico.a",
            captured_at=datetime.now(UTC),
            submit=True,
        )
        add_photos(session, response, before=2)

        # 2. A vision proposal is confirmed by the technician.
        record_provenance(
            session,
            response,
            field_key="material",
            origin=ValueOrigin.VISION,
            proposed_value="concrete",
            final_value="concrete",
            confidence=0.88,
            confirmed_by="tecnico.a",
        )
        session.refresh(response)

        # 3. The supervisor approves.
        decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="sup.a")
        assert order.state == WorkOrderState.APPROVED

        # 4. The as-built proposal reaches staging.
        proposal_id = str(uuid.uuid4())
        stage_from_work_order(
            session,
            unit,
            order,
            [
                {
                    "proposal_id": proposal_id,
                    "asset_type_key": "support_structure",
                    "action": "create",
                    "attributes": {"code": "P-999", "material": "concrete"},
                }
            ],
        )

        # 5. A batch is dispatched to the unit's arcpy agent.
        batch = create_batch(session, unit, asset_type_key="support_structure")
        assert batch is not None
        assert batch.business_unit_id == unit.id
        payload = batch_payload(session, unit, batch)
        assert payload["proposals"][0]["proposal_id"] == proposal_id

        # 6. The agent reports back and the trail is complete.
        apply_results(session, batch, [{"proposal_id": proposal_id, "status": "applied"}])
