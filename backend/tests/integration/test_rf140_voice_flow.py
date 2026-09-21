"""Dictation end to end: proposal, gate, confirmation, answer (I7, RF-140, SRS rule 0.5).

The gate is the point. A technician can dictate a whole form and still not submit it,
because a value the machine heard is not an answer until a person says it is. These tests
walk that path against a real database, including the failure the rule exists to prevent.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.gis_gateway.ingest import ingest_metadata
from app.org.models import BusinessUnit, Organization
from app.responses.models import ResponseState, ValueOrigin
from app.responses.service import compose_for, save_answers, unconfirmed_ai_values
from app.review.service import approval_blockers
from app.voice.service import (
    UnknownProposalError,
    confirm,
    discard,
    lexicon_for_order,
    order_context,
    pending_proposals,
    propose_from_dictation,
)
from app.workorders.models import WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

FEEDER = "04BH070T11"


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
    created.asset_code = "P-000452"
    created.feeder_code = FEEDER
    created.zone = "Durán"
    session.flush()
    return created


@pytest.fixture
def response(session: Session, unit: BusinessUnit, order):
    return save_answers(session, unit, order, answers={"work_order_code": "OT-1"}, submit=False)


def dictate(session, unit, order, response, transcript: str):
    form = compose_for(session, unit, order)
    lexicon = lexicon_for_order(session, unit, order, form=form)
    return propose_from_dictation(
        session,
        response,
        form,
        lexicon,
        transcript,
        asr_model="zipformer-es",
        asr_version="2024.11",
    )


class TestTheLexiconFollowsTheWorkOrder:
    def test_rf_331_the_order_context_comes_from_the_order(self, order) -> None:
        context = order_context(order)
        assert context.asset_code == "P-000452"
        assert context.feeder_code == FEEDER
        assert context.address == "Durán"

    def test_rf_331_the_lexicon_knows_this_order_feeder(self, session, unit, order) -> None:
        lexicon = lexicon_for_order(session, unit, order)
        assert FEEDER in lexicon.codes_for("feeder_code")
        assert lexicon.content_hash


class TestDictationIsAProposal:
    def test_rf_140_a_dictation_writes_provenance_not_answers(
        self, session, unit, order, response
    ) -> None:
        result = dictate(
            session, unit, order, response, "el poste es de hormigón, la altura es once metros"
        )
        assert result.values["material"] == "concrete"

        session.refresh(response)
        # The answers are untouched: nobody has confirmed anything.
        assert "material" not in (response.answers or {})
        assert {entry.field_key for entry in pending_proposals(response)} >= {"material"}

    def test_rf_052_the_provenance_names_both_models(self, session, unit, order, response) -> None:
        """A bad proposal may be the transcript's fault; telling them apart needs both."""
        dictate(session, unit, order, response, "el poste es de hormigón")
        session.refresh(response)
        entry = next(e for e in response.provenance if e.field_key == "material")
        assert entry.origin == ValueOrigin.VOICE
        assert "zipformer-es" in (entry.model_name or "")
        assert "rule-based-es-ec" in (entry.model_name or "")
        assert entry.confidence and 0 < entry.confidence < 1
        assert entry.source_transcript

    def test_rule_05_an_unconfirmed_proposal_blocks_approval(
        self, session, unit, order, response
    ) -> None:
        dictate(session, unit, order, response, "el poste es de hormigón")
        session.refresh(response)
        assert unconfirmed_ai_values(session, response)
        blockers = approval_blockers(session, unit, order, response)
        assert any("sin confirmar" in reason for reason in blockers)


class TestConfirmation:
    def test_rf_140_confirming_writes_the_value_into_the_answers(
        self, session, unit, order, response
    ) -> None:
        dictate(session, unit, order, response, "el poste es de hormigón")
        entry = confirm(
            session,
            response,
            field_key="material",
            final_value="concrete",
            confirmed_by="tecnico.1",
        )
        assert entry.accepted_unchanged is True
        assert entry.confirmed_at is not None
        session.refresh(response)
        assert response.answers["material"] == "concrete"
        assert not pending_proposals(response)

    def test_rf_140_a_correction_is_recorded_as_a_correction(
        self, session, unit, order, response
    ) -> None:
        """The pair proposal/final value is what training consumes; it must survive."""
        dictate(session, unit, order, response, "el poste es de hormigón")
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
        assert entry.reviewer_level == "supervisor"
        session.refresh(response)
        assert response.answers["material"] == "steel"

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

    def test_rf_140_a_rejected_proposal_leaves_no_value_behind(
        self, session, unit, order, response
    ) -> None:
        dictate(session, unit, order, response, "el poste es de hormigón")
        discard(session, response, field_key="material", discarded_by="tecnico.1")
        session.refresh(response)
        assert not pending_proposals(response)
        assert "material" not in (response.answers or {})
        assert not approval_blockers(session, unit, order, response) or all(
            "sin confirmar" not in reason
            for reason in approval_blockers(session, unit, order, response)
        )


class TestTheWholeDictatedCapture:
    def test_rf_140_dictate_confirm_and_submit(self, session, unit, order, response) -> None:
        """A capture that started as speech reaches a submitted response — through a person."""
        result = dictate(
            session,
            unit,
            order,
            response,
            f"el poste es de hormigón, la altura es de once metros, el alimentador es {FEEDER}",
        )
        assert set(result.values) >= {"material", "height_m", "feeder_code"}

        for field_key, value in result.values.items():
            confirm(
                session,
                response,
                field_key=field_key,
                final_value=value,
                confirmed_by="tecnico.1",
            )

        session.refresh(response)
        assert not unconfirmed_ai_values(session, response)

        answers = dict(response.answers)
        answers.update(
            {
                "work_order_code": "OT-1",
                "work_type": "inspeccion_preventiva",
                "priority": "media",
                "gps": {"latitude": -2.17, "longitude": -79.9, "accuracy_m": 4.0},
                "general_condition": "regular",
                "code": "P-000452",
                "final_state": "resuelto",
                "photos_before": ["s3://a.jpg", "s3://b.jpg"],
                "photos_after": [],
            }
        )
        submitted = save_answers(session, unit, order, answers=answers, submit=True)
        assert submitted.state == ResponseState.SUBMITTED
        assert submitted.answers["material"] == "concrete"
        assert submitted.answers["height_m"] == 11
        assert submitted.answers["feeder_code"] == FEEDER
