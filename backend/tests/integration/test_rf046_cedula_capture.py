"""La cédula del cliente en una captura entregada (RF-046).

El bloque B12 declara `format: ec-cedula` en sus datos; el servidor lo hace cumplir al validar la
respuesta, con la misma regla que el teléfono y la web (`forms/contract/identification-cases.json`).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.org.models import BusinessUnit
from app.responses.service import compose_for
from app.sync.models import Device
from app.workorders.models import WorkOrderState
from tests.integration.test_rf102_sync_api import an_order, full_answers, operation, push
from tests.integration.test_rf102_sync_api import client as client
from tests.integration.test_rf102_sync_api import device as device
from tests.integration.test_rf102_sync_api import unit as unit
from tests.integration.test_rf102_sync_api import units as units

pytestmark = pytest.mark.integration


def deliver(client: TestClient, order, **answers) -> dict:  # type: ignore[no-untyped-def]
    return push(
        client, operation("form_response", order, answers=full_answers(**answers), submit=True)
    ).json()


class TestRf046:
    def test_a_valid_cedula_is_accepted(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        assert deliver(client, order, customer_id="0912345675")["accepted"] == 1

    def test_a_wrong_check_digit_is_parked_with_the_reason(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        body = deliver(client, order, customer_id="0912345676")
        assert body["rejected"] == 1
        reason = body["operations"][0]["rejection_reason"]
        assert "no es una cédula válida" in reason
        assert "0912345676" in reason

    def test_an_empty_optional_cedula_is_not_a_wrong_one(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        assert deliver(client, order, customer_id="")["accepted"] == 1

    def test_the_format_is_declared_in_the_block_data(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Rule 3: the field is a cédula because the block says so, not because of its name."""
        order = an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        schema = compose_for(session, unit, order).schema
        assert schema["properties"]["customer_id"]["format"] == "ec-cedula"
