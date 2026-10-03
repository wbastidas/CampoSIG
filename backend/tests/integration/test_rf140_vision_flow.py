"""Vision proposals meet the approval gate (I11, RF-140, SRS rule 0.5).

The same rule as voice, and the reason it is tested again rather than assumed: the gate must
hold for every origin, and the way it breaks is that a new origin is added and nobody checks.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.gis_gateway.ingest import ingest_metadata
from app.org.models import BusinessUnit, Organization
from app.responses.models import ValueOrigin
from app.responses.service import compose_for, save_answers, unconfirmed_ai_values
from app.review.service import approval_blockers
from app.vision.contracts import BoundingBox, ImageAnalysis, Prediction
from app.vision.service import confirm, pending_proposals, propose_from_photograph
from app.voice.service import UnknownProposalError
from app.workorders.models import WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration


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
        planner_id="planner.a",
    )
    created.state = WorkOrderState.SYNCED
    created.form_version = "1.0.0"
    session.flush()
    return created


@pytest.fixture
def response(session: Session, unit: BusinessUnit, order):
    return save_answers(session, unit, order, answers={"work_order_code": "OT-1"}, submit=False)


def analyse(session, unit, order, response, predictions):
    form = compose_for(session, unit, order)
    return propose_from_photograph(
        session, response, form, ImageAnalysis("ev-antes-1", tuple(predictions))
    )


MATERIAL = Prediction(
    class_key="concrete",
    classifier_key="pole_material",
    confidence=0.92,
    box=BoundingBox(0.3, 0.2, 0.2, 0.6),
    model_name="mobilenetv3-pole",
    model_version="2026.09",
)


class TestAPhotographIsAProposal:
    def test_rf_140_analysis_writes_provenance_not_answers(
        self, session, unit, order, response
    ) -> None:
        result = analyse(session, unit, order, response, [MATERIAL])
        assert result.values == {"material": "concrete"}

        session.refresh(response)
        assert "material" not in (response.answers or {})
        assert [entry.field_key for entry in pending_proposals(response)] == ["material"]

    def test_rf_052_the_provenance_points_at_the_crop_the_model_looked_at(
        self, session, unit, order, response
    ) -> None:
        analyse(session, unit, order, response, [MATERIAL])
        session.refresh(response)
        entry = next(e for e in response.provenance if e.field_key == "material")
        assert entry.origin == ValueOrigin.VISION
        assert entry.model_name == "mobilenetv3-pole"
        assert entry.model_version == "2026.09"
        assert entry.source_transcript.startswith("evidencia:ev-antes-1@")

    def test_rule_05_an_unconfirmed_vision_value_blocks_approval(
        self, session, unit, order, response
    ) -> None:
        analyse(session, unit, order, response, [MATERIAL])
        session.refresh(response)
        assert unconfirmed_ai_values(session, response)
        assert any(
            "sin confirmar" in reason
            for reason in approval_blockers(session, unit, order, response)
        )

    def test_rf_140_a_finding_is_not_a_field_value(self, session, unit, order, response) -> None:
        """A leaning pole is something to report, not a value of any inventory field."""
        result = analyse(
            session,
            unit,
            order,
            response,
            [Prediction(class_key="leaning_pole", confidence=0.88)],
        )
        assert result.proposals == []
        assert [finding.key for finding in result.findings] == ["leaning_pole"]
        session.refresh(response)
        assert pending_proposals(response) == []


class TestConfirmation:
    def test_rf_140_confirming_writes_the_value(self, session, unit, order, response) -> None:
        analyse(session, unit, order, response, [MATERIAL])
        entry = confirm(
            session,
            response,
            field_key="material",
            final_value="concrete",
            confirmed_by="tecnico.1",
        )
        assert entry.accepted_unchanged is True
        session.refresh(response)
        assert response.answers["material"] == "concrete"
        assert not unconfirmed_ai_values(session, response)

    def test_rf_140_a_correction_keeps_the_training_pair(
        self, session, unit, order, response
    ) -> None:
        analyse(session, unit, order, response, [MATERIAL])
        entry = confirm(
            session,
            response,
            field_key="material",
            final_value="steel",
            confirmed_by="supervisor.1",
            reviewer_level="supervisor",
        )
        assert entry.accepted_unchanged is False
        assert entry.proposed_value == {"v": "concrete"}
        assert entry.final_value == {"v": "steel"}

    def test_rf_140_confirming_something_nobody_proposed_is_refused(
        self, session, unit, order, response
    ) -> None:
        with pytest.raises(UnknownProposalError):
            confirm(
                session,
                response,
                field_key="material",
                final_value="steel",
                confirmed_by="tecnico.1",
            )
