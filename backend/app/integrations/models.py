"""The integration ledger (RF-125).

Every exchange with a corporate system is a row here before it is an HTTP request. That
ordering is the whole design: an outbound event is written **in the same transaction as the
business change that caused it**, so a work order cannot be approved without the "close the
claim" event existing. The delivery happens afterwards and may fail, retry, or wait for a
person — but it can never be silently lost, which is the failure mode of calling an API
inside a business transaction.

Inbound exchanges are logged too, with the payload as it arrived. When an import turns out to
have been wrong, the only way to know what the other system actually sent is to have kept it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


class Direction(StrEnum):
    #: The corporate system spoke to us.
    INBOUND = "entrada"
    #: We have something to tell the corporate system.
    OUTBOUND = "salida"


class Connector(StrEnum):
    """The corporate systems the platform talks to."""

    WORK_ORDER_SYSTEM = "sistema_ot"
    CALL_CENTRE = "call_center"
    GIS = "arcgis"
    #: Materials, stock and movements (RF-122). The ERP owns the material catalogue, so the
    #: platform refuses to edit those values by hand (RF-034).
    ERP = "erp"


class EventStatus(StrEnum):
    PENDING = "pendiente"
    DELIVERED = "entregado"
    #: Retries are exhausted. Waiting for a person to press retry (RF-125).
    FAILED = "fallido"
    #: Deliberately given up on, with a reason. Never a silent disappearance.
    ABANDONED = "descartado"


class EventKind(StrEnum):
    WORK_ORDER_IMPORTED = "ot_importada"
    WORK_ORDER_STATUS = "estado_ot"
    WORK_ORDER_RESULT = "resultado_ot"
    CLAIM_RECEIVED = "reclamo_recibido"
    CLAIM_CLOSED = "reclamo_cerrado"
    #: The ERP handed over its material list (RF-122).
    MATERIAL_CATALOGUE = "catalogo_materiales"
    #: The ERP handed over stock for one warehouse or vehicle.
    MATERIAL_STOCK = "existencias"
    #: Material installed on approved work: a consumption the ERP has to book.
    MATERIAL_CONSUMED = "consumo_material"
    #: Material removed and returned: to the warehouse if reusable, to scrap otherwise. A second
    #: movement and not a negative consumption, because the two land in different places.
    MATERIAL_RETURNED = "devolucion_material"


class IntegrationEvent(Base):
    """One exchange, with its payload, its outcome and its retries."""

    __tablename__ = "integration_event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )

    connector: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=EventStatus.PENDING)

    #: The key that makes an exchange happen once. For an import it is the external work-order
    #: reference; for an outbound status it is the order and the state it reports.
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)

    #: What was sent, or what arrived. Kept verbatim.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    #: What the other side answered, when it answered.
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    work_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="SET NULL")
    )
    external_ref: Mapped[str | None] = mapped_column(String(64))

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    #: When the next automatic attempt is due. Null once delivered or given up on.
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # One exchange per key and direction: re-importing the same work order, or
        # re-reporting the same status, updates the row instead of duplicating the call.
        UniqueConstraint(
            "connector", "direction", "idempotency_key", name="uq_integration_identity"
        ),
        Index("ix_integration_unit_status", "business_unit_id", "status"),
        # The worker's query: what is due for another attempt.
        Index("ix_integration_due", "status", "next_attempt_at"),
        Index("ix_integration_order", "work_order_id"),
    )

    @property
    def needs_attention(self) -> bool:
        """What the integrations screen lists first."""
        return self.status == EventStatus.FAILED
