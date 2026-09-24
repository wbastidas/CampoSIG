"""Outage requests: the consignación and its window (RF-024).

«Una OT que requiere corte se vincula con la solicitud de consignación y su ventana horaria», and
the acceptance is a refusal: «no se habilita el formulario F-TR-02 sin un N.º de consignación».

The number is the point. A consignación is granted by the Centro de Control and *its number is the
authority*: it is what the crew reads back over the radio before touching anything, and what an
investigation asks for afterwards. So the number is what the platform requires, and it requires it
from the granted request rather than from a box the crew fills — a number typed into the permit form
would be a number nobody granted.

Two decisions worth stating:

* **The window is data, not a suggestion.** A crew working before or after the approved window is
  working on a line that may be re-energised. The platform records that, loudly, and does **not**
  refuse the capture: refusing would lose the record of what actually happened, which is the one
  thing an investigation needs. Refuse what must not happen; record what did.
* **A request serves several work orders.** «Consignación del alimentador sur, sábado de 06:00 a
  12:00» covers every front working under it, and modelling one request per order would have the
  Centro de Control granting six descargos for one outage.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


class OutageState(StrEnum):
    """The life of a request, as the Centro de Control runs it."""

    REQUESTED = "solicitada"
    #: Granted, with a number. Only from here does the permit form open.
    APPROVED = "aprobada"
    REJECTED = "rechazada"
    #: The window passed without the work being done. Not «rejected»: nobody refused it.
    EXPIRED = "vencida"
    #: The crew handed the outage back and the equipment can be re-energised.
    RETURNED = "devuelta"


#: States in which the permit form may open. Only one, deliberately: a requested-but-not-granted
#: consignación is exactly the situation the rule exists to stop.
GRANTS_PERMIT = (OutageState.APPROVED,)


class OutageRequest(Base):
    """One consignación: what is de-energised, when, and by whose authority."""

    __tablename__ = "outage_request"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )

    #: The number the Centro de Control granted. Null while the request is only a request — and that
    #: is why the permit form checks the number and not merely the state: a row marked approved with
    #: no number is a row somebody edited, not a consignación anybody granted.
    number: Mapped[str | None] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(16), nullable=False, default=OutageState.REQUESTED)

    #: What is being de-energised, in the words the Centro de Control uses.
    equipment: Mapped[str] = mapped_column(String(255), nullable=False)
    feeder_code: Mapped[str | None] = mapped_column(String(32))
    substation_code: Mapped[str | None] = mapped_column(String(32))

    #: The approved window. Both ends required: an open-ended consignación is not a window, and the
    #: whole point of recording one is being able to say whether the work happened inside it.
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    #: Who asked, and who granted or refused. Two people, never one: a consignación somebody granted
    #: to themselves is the failure mode the whole procedure exists to prevent.
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String(255))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Why it was refused, or the note the Centro de Control attached when granting.
    note: Mapped[str | None] = mapped_column(Text)

    #: When the crew handed it back, and who did.
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_by: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        #: One number per unit. The Centro de Control owns the numbering, and two rows claiming the
        #: same descargo would make «¿bajo qué consignación trabajaron?» unanswerable.
        UniqueConstraint("business_unit_id", "number", name="uq_outage_request_number"),
        Index("ix_outage_request_state", "business_unit_id", "state"),
        Index("ix_outage_request_window", "business_unit_id", "window_start", "window_end"),
    )

    @property
    def grants_permit(self) -> bool:
        """Whether the permit form may open under this request.

        Both conditions, and the number is the stricter one: RF-024's criterion is «sin un N.º de
        consignación», not «sin una solicitud aprobada».
        """
        return self.state in GRANTS_PERMIT and bool(self.number)
