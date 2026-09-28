"""Where the crews are, according to the last GPS their phones reported (RF-020).

The dispatcher's question at ten in the morning is «who is closest to this fault?», and until this
module existed the platform could not answer it: nothing stored a position at all.

Four decisions, and the first two are the ones that matter:

* **Only the last position exists.** The table's primary key is the device, so there is nowhere to
  keep a movement history. The platform answers «where is this crew now» and is structurally unable
  to answer «where did this technician go on Tuesday» — a question nobody asked and that a works
  council would be right to object to.
* **A position is always reported with its age, and stale is a state.** It is captured when the
  phone syncs, so it is as old as the last sync; drawing a confident dot for a fix from four hours
  ago is worse than drawing nothing, because a dispatcher sends a crew on it.
* **A crew's position is derived from its phones**, through the work those phones actually hold —
  the same derivation the dispatch board already uses, because a device belongs to a person and
  people move between crews.
* **A fix the phone itself does not trust is refused.** Out-of-range coordinates and the null island
  at (0, 0) are the two classic bad fixes, and both would put a crew in the Gulf of Guinea.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dispatch.models import DevicePosition, WorkOrderDelivery
from app.org.models import BusinessUnit
from app.sync.models import SYNCABLE_STATES, Device
from app.workorders.models import STORAGE_SRID, Crew, WorkOrder

#: Beyond this, a position is shown as stale rather than as a location. Two hours: a crew that has
#: not synced in two hours may have driven across the whole concession, and a dot that old sends
#: somebody to the wrong parish.
STALE_AFTER = timedelta(hours=2)

#: Beyond this, the position is deleted. The platform keeps the last position to dispatch with, not
#: a record of where people were: a fix from yesterday answers no operational question and is
#: exactly the data that should not accumulate.
RETENTION = timedelta(hours=24)

#: An accuracy worse than this is reported as a doubtful fix. 200 m is about the point where a dot
#: on a distribution map stops telling you which street the crew is on.
DOUBTFUL_ACCURACY_M = 200.0


class PositionError(Exception):
    pass


def report(
    session: Session,
    unit: BusinessUnit,
    device: Device,
    *,
    latitude: float,
    longitude: float,
    accuracy_m: float | None = None,
    reported_at: datetime | None = None,
) -> DevicePosition:
    """Record where this phone says it is, replacing whatever it said before.

    :raises PositionError: for a fix that cannot be a position in Ecuador's neighbourhood.
    """
    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        raise PositionError("la posición está fuera de rango")
    if latitude == 0.0 and longitude == 0.0:
        # The null island. A GPS that reports it has no fix, and drawing it would put the crew in
        # the Gulf of Guinea — which is funny once and then somebody dispatches on it.
        raise PositionError("una posición en (0, 0) es un GPS sin señal, no una ubicación")
    if accuracy_m is not None and accuracy_m < 0:
        raise PositionError("la precisión no puede ser negativa")
    if device.business_unit_id != unit.id:
        raise PositionError("el dispositivo no es de esta unidad de negocio")

    when = reported_at or datetime.now(UTC)
    existing = session.get(DevicePosition, device.id)
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), STORAGE_SRID)
    if existing is None:
        existing = DevicePosition(
            device_id=device.id,
            business_unit_id=unit.id,
            location=point,
            accuracy_m=accuracy_m,
            reported_at=when,
        )
        session.add(existing)
    elif when < existing.reported_at:
        # An out-of-order delivery: the phone retried an old fix after a newer one arrived. Keeping
        # the newer one is the whole point of storing only one.
        return existing
    else:
        existing.location = point
        existing.accuracy_m = accuracy_m
        existing.reported_at = when
        existing.received_at = datetime.now(UTC)
    session.flush()
    return existing


@dataclass
class CrewPosition:
    """One phone's position, and the crews it is carrying work for."""

    device_key: str
    user_sub: str | None
    longitude: float
    latitude: float
    accuracy_m: float | None
    reported_at: datetime
    minutes_old: int
    stale: bool
    doubtful: bool
    crews: list[dict[str, str]] = field(default_factory=list)

    def as_feature(self) -> dict[str, Any]:
        return {
            "type": "Feature",
            "id": self.device_key,
            "geometry": {"type": "Point", "coordinates": [self.longitude, self.latitude]},
            "properties": {
                "device_key": self.device_key,
                "user_sub": self.user_sub,
                "accuracy_m": self.accuracy_m,
                "reported_at": self.reported_at.isoformat(),
                # La edad en minutos, dicha por el servidor: el reloj del navegador tampoco es el
                # que manda, y una posición sin su edad miente.
                "minutes_old": self.minutes_old,
                "stale": self.stale,
                "doubtful": self.doubtful,
                "crews": self.crews,
            },
        }


def crew_positions(
    session: Session,
    unit: BusinessUnit,
    *,
    now: datetime | None = None,
    zone: str | None = None,
) -> list[CrewPosition]:
    """The last position of every phone in this unit, with the crews it serves.

    :param zone: keep only phones carrying work in this zone, which is how a dispatcher narrows a
        map to the area they are responsible for.
    """
    moment = now or datetime.now(UTC)
    rows = session.execute(
        select(
            Device.device_key,
            Device.user_sub,
            Device.id,
            ST_X(DevicePosition.location),
            ST_Y(DevicePosition.location),
            DevicePosition.accuracy_m,
            DevicePosition.reported_at,
        )
        .join(DevicePosition, DevicePosition.device_id == Device.id)
        .where(DevicePosition.business_unit_id == unit.id)
        .order_by(Device.device_key)
    ).all()
    if not rows:
        return []

    crews = _crews_of([row[2] for row in rows], session, unit, zone=zone)
    positions: list[CrewPosition] = []
    for device_key, user_sub, device_id, longitude, latitude, accuracy, reported_at in rows:
        if zone is not None and not crews.get(device_id):
            # Filtering by zone means «phones working in this zone»; one with no work there is not
            # a phone the dispatcher of that zone is looking for.
            continue
        age = moment - reported_at
        positions.append(
            CrewPosition(
                device_key=device_key,
                user_sub=user_sub,
                longitude=float(longitude),
                latitude=float(latitude),
                accuracy_m=float(accuracy) if accuracy is not None else None,
                reported_at=reported_at,
                minutes_old=max(int(age.total_seconds() // 60), 0),
                stale=age > STALE_AFTER,
                doubtful=accuracy is not None and float(accuracy) > DOUBTFUL_ACCURACY_M,
                crews=crews.get(device_id, []),
            )
        )
    return positions


def purge(session: Session, *, now: datetime | None = None) -> int:
    """Delete positions older than the retention window. Returns how many went.

    Run nightly. The platform keeps the last position to dispatch with, not a record of where people
    were, and a table that only ever grows would quietly become the second thing.
    """
    moment = now or datetime.now(UTC)
    stale = list(
        session.scalars(
            select(DevicePosition).where(DevicePosition.reported_at < moment - RETENTION)
        )
    )
    for row in stale:
        session.delete(row)
    session.flush()
    return len(stale)


def _crews_of(
    device_ids: list[uuid.UUID],
    session: Session,
    unit: BusinessUnit,
    *,
    zone: str | None = None,
) -> dict[uuid.UUID, list[dict[str, str]]]:
    """Which crews each device is carrying work for, through what was delivered to it.

    The same derivation the dispatch board uses: a device belongs to a person, not to a crew, and
    people move between crews. What matters to a dispatcher is which phone has the work.
    """
    statement = (
        select(WorkOrderDelivery.device_id, Crew.id, Crew.code, Crew.name)
        .join(WorkOrder, WorkOrder.id == WorkOrderDelivery.work_order_id)
        .join(Crew, Crew.id == WorkOrder.assigned_crew_id)
        .where(
            WorkOrderDelivery.device_id.in_(device_ids),
            WorkOrder.business_unit_id == unit.id,
            WorkOrder.state.in_(SYNCABLE_STATES),
        )
        .distinct()
    )
    if zone is not None:
        statement = statement.where(WorkOrder.zone == zone)
    found: dict[uuid.UUID, list[dict[str, str]]] = {}
    for device_id, crew_id, code, name in session.execute(statement).all():
        entry = {"crew_id": str(crew_id), "code": code, "name": name}
        rows = found.setdefault(device_id, [])
        if entry not in rows:
            rows.append(entry)
    for rows in found.values():
        rows.sort(key=lambda item: item["code"])
    return found
