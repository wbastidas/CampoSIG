"""Evidence integrity, metadata, gallery and watermark (RF-071 to RF-074).

Before this module the hash travelled with every photograph and nobody checked it:
`verify_integrity` existed and nothing called it, so `integrity_verified` was false for every
photograph ever captured — which made the reviewer's «hash does not match» warning permanent, and
therefore meaningless. The criteria, literally:

* RF-073 — «el backend verifica el hash al recibir; si no coincide, marca la evidencia como
  alterada», and the hash is «registrado en la cadena de auditoría».
* RF-074 — «una foto de galería no cuenta como evidencia ANTES/DESPUÉS».
* RF-071 — altitude, heading, the person and the device model with the capture.
* RF-072 — the watermarked copy is kept beside the original.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.audit.service import verify
from app.org.models import BusinessUnit
from app.responses.models import Evidence, FormResponse, IntegrityStatus
from app.responses.service import (
    EvidenceError,
    counts_as_evidence,
    photo_counts,
    register_evidence,
)
from app.storage import service as storage
from app.sync.models import Device
from app.workorders.models import WorkOrderState
from tests.integration.test_rf102_sync_api import (
    TECHNICIAN,
    an_order,
    full_answers,
    operation,
    push,
)
from tests.integration.test_rf102_sync_api import client as client
from tests.integration.test_rf102_sync_api import device as device
from tests.integration.test_rf102_sync_api import unit as unit
from tests.integration.test_rf102_sync_api import units as units

pytestmark = pytest.mark.integration

ORIGINAL = b"foto-antes-original"
DIGEST = hashlib.sha256(ORIGINAL).hexdigest()


@pytest.fixture
def bucket(monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    """The object store, as a dict: what the phone uploaded under each key."""
    stored: dict[str, bytes] = {}

    def read(key: str) -> bytes:
        if key not in stored:
            raise storage.StorageError(f"el archivo «{key}» no está en el almacenamiento")
        return stored[key]

    monkeypatch.setattr(storage, "read_object", read)
    return stored


def capture(order: Any, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": "foto",
        "storage_key": "GYE/evidencia/foto/antes-1.jpg",
        "content_hash": DIGEST,
        "stage": "antes",
        "latitude": -2.17,
        "longitude": -79.9,
        "source": "camara",
    }
    payload.update(extra)
    return operation("evidence", order, **payload)


def the_evidence(session: Session) -> Evidence:
    return session.execute(select(Evidence)).scalars().one()


class TestRf073Integrity:
    def test_the_hash_is_on_the_audit_trail_from_registration(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        push(client, operation("form_response", order, answers=full_answers()), capture(order))

        event = session.scalars(
            select(AuditEvent).where(
                AuditEvent.subject_type == "evidencia", AuditEvent.kind == "creacion"
            )
        ).one()
        assert event.payload["content_hash"] == DIGEST
        assert event.actor == TECHNICIAN.subject
        assert verify(session, unit.id).intact is True

    def test_a_registered_evidence_starts_pending(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        push(client, operation("form_response", order, answers=full_answers()), capture(order))
        assert the_evidence(session).integrity_status == IntegrityStatus.PENDING

    def test_an_upload_that_matches_is_verified(
        self,
        session: Session,
        unit: BusinessUnit,
        device: Device,
        client: TestClient,
        bucket: dict[str, bytes],
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        push(client, operation("form_response", order, answers=full_answers()), capture(order))
        bucket["GYE/evidencia/foto/antes-1.jpg"] = ORIGINAL

        body = push(client, operation("evidence_uploaded", order, content_hash=DIGEST)).json()

        assert body["accepted"] == 1
        assert body["operations"][0]["result"]["integrity_status"] == "verificada"
        evidence = the_evidence(session)
        assert evidence.integrity_verified is True
        assert evidence.uploaded_at is not None

    def test_an_upload_that_does_not_match_is_marked_altered_not_refused(
        self,
        session: Session,
        unit: BusinessUnit,
        device: Device,
        client: TestClient,
        bucket: dict[str, bytes],
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        push(client, operation("form_response", order, answers=full_answers()), capture(order))
        bucket["GYE/evidencia/foto/antes-1.jpg"] = b"otra-foto"

        body = push(client, operation("evidence_uploaded", order, content_hash=DIGEST)).json()

        assert body["accepted"] == 1
        evidence = the_evidence(session)
        assert evidence.integrity_status == IntegrityStatus.ALTERED
        assert evidence.integrity_verified is False
        event = session.scalars(
            select(AuditEvent).where(
                AuditEvent.subject_type == "evidencia", AuditEvent.kind == "cambio_campo"
            )
        ).one()
        assert event.payload["to"] == "alterada"
        assert event.payload["expected_hash"] == DIGEST
        assert event.payload["actual_hash"] == hashlib.sha256(b"otra-foto").hexdigest()

    def test_an_altered_photo_does_not_count(self, session: Session, unit, device, client, bucket):
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        push(client, operation("form_response", order, answers=full_answers()), capture(order))
        bucket["GYE/evidencia/foto/antes-1.jpg"] = b"otra-foto"
        push(client, operation("evidence_uploaded", order, content_hash=DIGEST))
        response = session.scalars(select(FormResponse)).one()
        assert photo_counts(response)["antes"] == 0

    def test_the_confirmation_checks_the_evidence_it_names(
        self, session: Session, unit, device, client, bucket
    ):
        """Two photographs on one order: confirming the second must not verify the first."""
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        second = b"foto-despues"
        second_digest = hashlib.sha256(second).hexdigest()
        push(
            client,
            operation("form_response", order, answers=full_answers()),
            capture(order),
            capture(
                order,
                storage_key="GYE/evidencia/foto/despues-1.jpg",
                content_hash=second_digest,
                stage="despues",
            ),
        )
        bucket["GYE/evidencia/foto/despues-1.jpg"] = second
        body = push(client, operation("evidence_uploaded", order, content_hash=second_digest))
        assert body.json()["accepted"] == 1
        statuses = {
            item.content_hash: item.integrity_status
            for item in session.execute(select(Evidence)).scalars()
        }
        assert statuses == {DIGEST: "pendiente", second_digest: "verificada"}

    def test_a_confirmation_before_the_file_arrives_is_parked(
        self, session: Session, unit, device, client, bucket
    ):
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        push(client, operation("form_response", order, answers=full_answers()), capture(order))
        body = push(client, operation("evidence_uploaded", order, content_hash=DIGEST)).json()
        assert body["rejected"] == 1
        assert "no está en el almacenamiento" in body["operations"][0]["rejection_reason"]
        assert the_evidence(session).integrity_status == IntegrityStatus.PENDING

    def test_a_confirmation_for_an_unknown_evidence_is_parked(
        self, session: Session, unit, device, client, bucket
    ):
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        push(client, operation("form_response", order, answers=full_answers()))
        body = push(client, operation("evidence_uploaded", order, content_hash=DIGEST)).json()
        assert body["rejected"] == 1
        assert "registrar la evidencia" in body["operations"][0]["rejection_reason"]


class TestRf074Gallery:
    def test_a_gallery_photo_is_attached_but_does_not_count(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        body = push(
            client,
            operation("form_response", order, answers=full_answers()),
            capture(order, source="galeria"),
        ).json()

        assert body["accepted"] == 2
        assert body["operations"][1]["result"]["counts_as_evidence"] is False
        response = session.scalars(select(FormResponse)).one()
        assert photo_counts(response)["antes"] == 0

    def test_a_camera_photo_counts(self, session: Session, unit, device, client):
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        body = push(
            client, operation("form_response", order, answers=full_answers()), capture(order)
        ).json()
        assert body["operations"][1]["result"]["counts_as_evidence"] is True
        assert photo_counts(session.scalars(select(FormResponse)).one())["antes"] == 1

    def test_a_capture_without_source_counts_as_camera(self, session: Session, unit, device):
        """Phones from before the field had no gallery option."""
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        response = FormResponse(
            business_unit_id=unit.id,
            work_order_id=order.id,
            form_code=order.form_code,
            form_version="1.1.0",
        )
        session.add(response)
        session.flush()
        evidence = register_evidence(
            session, response, kind="foto", storage_key="k", content_hash="a" * 64, stage="antes"
        )
        assert counts_as_evidence(evidence) is True

    def test_an_unknown_source_is_parked(self, session: Session, unit, device, client):
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        body = push(
            client,
            operation("form_response", order, answers=full_answers()),
            capture(order, source="captura_de_pantalla"),
        ).json()
        assert body["rejected"] == 1
        assert "origen" in body["operations"][1]["rejection_reason"]

    def test_the_service_refuses_an_unknown_source(self, session: Session, unit, device):
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        response = FormResponse(
            business_unit_id=unit.id,
            work_order_id=order.id,
            form_code=order.form_code,
            form_version="1.1.0",
        )
        session.add(response)
        session.flush()
        with pytest.raises(EvidenceError):
            register_evidence(
                session, response, kind="foto", storage_key="k", content_hash="a" * 64, source="x"
            )


class TestRf071Metadata:
    def test_altitude_heading_person_and_model_are_kept(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        push(
            client,
            operation("form_response", order, answers=full_answers()),
            capture(order, altitude_m=12.5, heading_deg=270.0),
        )
        evidence = the_evidence(session)
        assert evidence.altitude_m == pytest.approx(12.5)
        assert evidence.heading_deg == pytest.approx(270.0)
        assert evidence.captured_by == TECHNICIAN.subject
        assert evidence.device_model == "Pixel 8a"

    def test_the_person_is_never_taken_from_the_payload(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        push(
            client,
            operation("form_response", order, answers=full_answers()),
            capture(order, captured_by="kc|otra.persona", device_model="iPhone"),
        )
        evidence = the_evidence(session)
        assert evidence.captured_by == TECHNICIAN.subject
        assert evidence.device_model == "Pixel 8a"


class TestRf072Watermark:
    def test_the_watermarked_copy_is_kept_beside_the_original(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        push(
            client,
            operation("form_response", order, answers=full_answers()),
            capture(order, watermarked_storage_key="GYE/evidencia/foto/antes-1-marca.jpg"),
        )
        evidence = the_evidence(session)
        assert evidence.watermarked_storage_key == "GYE/evidencia/foto/antes-1-marca.jpg"
        # The original is the one hashed: the watermark is for people, the hash for evidence.
        assert evidence.storage_key == "GYE/evidencia/foto/antes-1.jpg"
        assert evidence.content_hash == DIGEST


class TestReviewShowsIt:
    def test_the_review_detail_carries_status_source_and_metadata(
        self, session: Session, unit, device, client
    ):
        from app.auth.dependencies import current_principal
        from app.auth.principal import Principal, Role
        from app.infra.database import get_session
        from app.main import create_app

        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        push(
            client,
            operation("form_response", order, answers=full_answers()),
            capture(order, source="galeria", altitude_m=3.0),
        )
        supervisor = Principal(
            subject="kc|supervisor",
            username="supervisor",
            roles=frozenset({Role.SUPERVISOR.value}),
            business_units=frozenset({"GYE"}),
        )
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: supervisor
        with TestClient(app) as raw:
            body = raw.get(f"/api/v1/review/units/GYE/work-orders/{order.id}").json()
        item = body["evidence"][0]
        assert item["integrity_status"] == "pendiente"
        assert item["source"] == "galeria"
        assert item["counts_as_evidence"] is False
        assert item["captured_by"] == TECHNICIAN.subject
        assert item["altitude_m"] == pytest.approx(3.0)
