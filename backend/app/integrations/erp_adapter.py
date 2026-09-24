"""Materials in, movements out (RF-122).

The gap this closes was, once again, a dangling declaration rather than a missing feature: the
`material` catalogue shipped with `source: integracion` and a note saying «vacío hasta el primer
envío del ERP», and **nothing could ever send that first batch**. A phone rendering B07's materials
table had a code field and no values to choose from.

Four decisions shape this module.

**The ERP owns the catalogue, so the platform writes it only as the ERP.** `upsert_entry` refuses a
hand edit on an integration-owned catalogue, and this adapter passes `from_integration=True`. That
is the whole point of the flag: a value typed over one tonight's batch will overwrite is a value
that disappears without explanation.

**A batch never retires what it does not mention, unless it says it is complete.** A paginated pull
that failed halfway would otherwise empty the picker in the field — silent on the server, very loud
in a substation. So the ERP has to declare `"complete": true` for the platform to withdraw the codes
it stopped sending, and the report says which mode ran.

**Stock is a snapshot, replaced per location.** Merging would leave a phantom line for the material
that ran out, and somebody plans against phantom lines.

**Consumption and return are two movements, not one signed quantity.** Installing three insulators
and taking two broken ones out is a consumption *and* a return, and they land in different places in
the ERP: the reusable one goes back to the warehouse, the scrap one to disposal. A single «used»
figure would lose half the inventory — and it is exactly the shape B07 was built to avoid.

Both movements are published inside the **approval's** transaction (like RF-124's claim closure),
so an approved job cannot leave the ERP unaware of what it consumed. Delivery happens afterwards
and may fail, retry or wait for a person; it cannot be lost.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.catalogs import service as catalogs
from app.integrations.erp_models import MaterialStock, StockLocationKind
from app.integrations.models import Connector, Direction, EventKind, IntegrationEvent
from app.integrations.service import mark_delivered, mark_failed, publish
from app.integrations.transport import Transport, TransportError
from app.org.models import BusinessUnit
from app.responses.models import FormResponse
from app.workorders.models import WorkOrder

#: The catalogue the ERP owns. Named here and in the seeds, nowhere else.
MATERIAL_CATALOG = "material"

#: The answer key B07 records materials under. One key, one place (SRS 4.2).
MATERIALS_KEY = "materials"

#: Where returned material goes, by the state the crew recorded. The ERP needs the destination, not
#: the adjective: «reutilizable» is a warehouse receipt and «chatarra» is a disposal.
RETURN_DESTINATION: dict[str, str] = {
    "reutilizable": "bodega",
    "chatarra": "chatarra",
}

#: What a movement says when the crew did not record the state of what they removed. Not guessed as
#: reusable — booking scrap into the warehouse is the expensive direction of this mistake.
UNKNOWN_DESTINATION = "por_clasificar"


# --- inbound: the catalogue -----------------------------------------------------------------


def import_materials(
    session: Session,
    unit: BusinessUnit,
    transport: Transport,
    *,
    base_url: str,
    actor: str = "conector.erp",
) -> dict[str, Any]:
    """Pull the ERP's material list into the catalogue (RF-122, RF-034).

    :returns: what was written, what was retired, and whether the batch was complete.
    """
    url = f"{base_url.rstrip('/')}/materials"
    event = publish(
        session,
        unit,
        connector=Connector.ERP,
        direction=Direction.INBOUND,
        kind=EventKind.MATERIAL_CATALOGUE,
        idempotency_key=f"materiales:{datetime.now(UTC).date().isoformat()}",
        payload={},
    )
    try:
        answer = transport.get(url)
    except TransportError as exc:
        mark_failed(session, event, exc)
        raise

    items = answer.body.get("items") or []
    complete = bool(answer.body.get("complete"))

    written: list[str] = []
    rejected: list[dict[str, str]] = []
    for item in items:
        code = str(item.get("code") or "").strip()
        label = str(item.get("label") or item.get("description") or "").strip()
        if not code:
            rejected.append({"code": "(sin código)", "reason": "el material no trae código"})
            continue
        if not label:
            # A picker showing a bare code is a picker a technician cannot use. Refused with the
            # code, so somebody can ask the ERP for the description rather than guessing one.
            rejected.append({"code": code, "reason": "el material no trae descripción"})
            continue
        catalogs.upsert_entry(
            session,
            MATERIAL_CATALOG,
            entry_code=code,
            label=label,
            synonyms=[str(word) for word in (item.get("synonyms") or [])],
            attributes=_material_attributes(item),
            actor=actor,
            from_integration=True,
        )
        written.append(code)

    retired: list[str] = []
    if complete:
        # Only on a batch the ERP calls complete. Withdrawing on a partial pull would empty the
        # picker in the field, which is silent here and very loud in a substation.
        known = {entry.code for entry in catalogs.resolve(session, MATERIAL_CATALOG).entries}
        for code in sorted(known - set(written)):
            catalogs.retire_entry(session, MATERIAL_CATALOG, code, actor=actor)
            retired.append(code)

    # En la respuesta del asiento y no en su payload: la bitácora de integraciones es
    # append-only (RF-160), y el payload es lo que se pidió, no lo que salió. La guarda de
    # RF-160 detectó la primera versión de esto, que reasignaba `event.payload`.
    mark_delivered(
        session,
        event,
        {
            "count": len(items),
            "complete": complete,
            "written": len(written),
            "retired": len(retired),
        },
    )
    session.flush()
    return {
        "written": written,
        "retired": retired,
        "rejected": rejected,
        "complete": complete,
        # Said out loud because it changes what the result means: an incomplete batch cannot
        # withdraw anything, so a code the ERP deleted is still on the phones.
        "note": None
        if complete
        else (
            "el ERP no declaró el lote como completo, así que no se retiró ningún código: un "
            "envío parcial que vaciara el selector sería invisible aquí y muy visible en el campo"
        ),
    }


def _material_attributes(item: dict[str, Any]) -> dict[str, Any]:
    """The attributes worth keeping from an ERP row.

    A deliberate subset: the unit of measure, whether it is serialised, and the construction unit it
    belongs to. Anything else the ERP sends is its business, and copying a whole row would make this
    platform a second (stale) inventory master.
    """
    attributes: dict[str, Any] = {}
    for source, target in (("unit", "unit"), ("uc_code", "uc_code"), ("family", "family")):
        value = item.get(source)
        if isinstance(value, str) and value.strip():
            attributes[target] = value.strip()
    if isinstance(item.get("serialised"), bool):
        attributes["serialised"] = item["serialised"]
    return attributes


# --- inbound: stock -------------------------------------------------------------------------


def import_stock(
    session: Session,
    unit: BusinessUnit,
    transport: Transport,
    *,
    base_url: str,
) -> dict[str, Any]:
    """Pull stock per warehouse or vehicle, replacing each location's lines (RF-122)."""
    url = f"{base_url.rstrip('/')}/stock"
    event = publish(
        session,
        unit,
        connector=Connector.ERP,
        direction=Direction.INBOUND,
        kind=EventKind.MATERIAL_STOCK,
        idempotency_key=f"existencias:{datetime.now(UTC).isoformat(timespec='hours')}",
        payload={},
    )
    try:
        answer = transport.get(url)
    except TransportError as exc:
        mark_failed(session, event, exc)
        raise

    locations = answer.body.get("locations") or []
    written = 0
    replaced: list[str] = []
    rejected: list[dict[str, str]] = []
    for location in locations:
        kind = str(location.get("kind") or "")
        code = str(location.get("code") or "").strip()
        if kind not in tuple(StockLocationKind) or not code:
            rejected.append(
                {
                    "location": code or "(sin código)",
                    "reason": f"ubicación de tipo «{kind}» desconocida o sin código",
                }
            )
            continue
        as_of = _timestamp(location.get("as_of"))
        # Replaced, not merged: a line that disappeared means the material ran out, and leaving it
        # would have somebody planning against stock that is not there.
        session.execute(
            delete(MaterialStock).where(
                MaterialStock.business_unit_id == unit.id,
                MaterialStock.location_kind == kind,
                MaterialStock.location_code == code,
            )
        )
        for line in location.get("lines") or []:
            quantity = _quantity(line.get("quantity"))
            material = str(line.get("material_code") or "").strip()
            if not material or quantity is None:
                rejected.append(
                    {
                        "location": code,
                        "reason": f"línea sin material o con cantidad ilegible: {line!r}",
                    }
                )
                continue
            session.add(
                MaterialStock(
                    business_unit_id=unit.id,
                    material_code=material,
                    location_kind=kind,
                    location_code=code,
                    location_name=location.get("name"),
                    quantity=quantity,
                    unit=line.get("unit"),
                    as_of=as_of,
                )
            )
            written += 1
        replaced.append(code)

    session.flush()
    unknown = unknown_codes(session, unit)
    mark_delivered(session, event, {"lines": written, "locations": len(replaced)})
    return {
        "locations": replaced,
        "lines": written,
        "rejected": rejected,
        # Codes the platform holds stock for and the catalogue does not know. Not an error — the
        # two batches arrive separately — but the drift is worth seeing before a técnico meets it.
        "unknown_in_catalogue": unknown,
    }


def unknown_codes(session: Session, unit: BusinessUnit) -> list[str]:
    """Stocked material codes the catalogue does not know."""
    stocked = set(
        session.execute(
            select(MaterialStock.material_code).where(MaterialStock.business_unit_id == unit.id)
        )
        .scalars()
        .all()
    )
    if not stocked:
        return []
    try:
        known = {entry.code for entry in catalogs.resolve(session, MATERIAL_CATALOG).entries}
    except catalogs.UnknownCatalogError:
        known = set()
    return sorted(stocked - known)


def stock_of(
    session: Session,
    unit: BusinessUnit,
    *,
    location_kind: str | None = None,
    location_code: str | None = None,
    material_code: str | None = None,
) -> list[MaterialStock]:
    query = select(MaterialStock).where(MaterialStock.business_unit_id == unit.id)
    if location_kind:
        query = query.where(MaterialStock.location_kind == location_kind)
    if location_code:
        query = query.where(MaterialStock.location_code == location_code)
    if material_code:
        query = query.where(MaterialStock.material_code == material_code)
    return list(
        session.execute(
            query.order_by(
                MaterialStock.location_kind,
                MaterialStock.location_code,
                MaterialStock.material_code,
            )
        ).scalars()
    )


# --- outbound: the movements ----------------------------------------------------------------


def enqueue_material_movements(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
) -> list[IntegrationEvent]:
    """Queue the consumption and the return of an approved order's materials (RF-122).

    «El consumo aprobado genera un movimiento en el ERP», and it is queued inside the approval's own
    transaction so the approval cannot succeed without it existing.

    Two events and not one: what was installed is a consumption, what was removed is a receipt into
    the warehouse or into scrap, and the ERP books them in different places. Returning them as one
    signed number would lose the destination.
    """
    response = (
        session.execute(select(FormResponse).where(FormResponse.work_order_id == order.id))
        .scalars()
        .first()
    )
    rows = (response.answers or {}).get(MATERIALS_KEY) if response else None
    if not isinstance(rows, list) or not rows:
        # Nothing to tell: most work consumes nothing, and an empty movement would make the ERP's
        # log unreadable for the ones that do.
        return []

    consumed: list[dict[str, Any]] = []
    returned: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("material_code") or "").strip()
        if not code:
            continue
        installed = _quantity(row.get("installed_quantity"))
        removed = _quantity(row.get("removed_quantity"))
        if installed is not None and installed > 0:
            consumed.append(
                {
                    "material_code": code,
                    "quantity": float(installed),
                    "unit": row.get("unit"),
                    "serial_number": row.get("serial_number"),
                }
            )
        if removed is not None and removed > 0:
            state = str(row.get("removed_state") or "")
            returned.append(
                {
                    "material_code": code,
                    "quantity": float(removed),
                    "unit": row.get("unit"),
                    "serial_number": row.get("serial_number"),
                    "destination": RETURN_DESTINATION.get(state, UNKNOWN_DESTINATION),
                    "recorded_state": state or None,
                }
            )

    events: list[IntegrationEvent] = []
    for kind, lines in (
        (EventKind.MATERIAL_CONSUMED, consumed),
        (EventKind.MATERIAL_RETURNED, returned),
    ):
        if not lines:
            continue
        events.append(
            publish(
                session,
                unit,
                connector=Connector.ERP,
                direction=Direction.OUTBOUND,
                kind=kind,
                # Keyed by the order and the kind: re-approving after a correction updates the
                # movement instead of booking it twice.
                idempotency_key=f"{kind.value}:{order.id}",
                payload={
                    "work_order_id": str(order.id),
                    "work_order_code": order.code,
                    "asset_code": order.asset_code,
                    "lines": lines,
                },
                order=order,
                external_ref=order.code,
            )
        )
    return events


def deliver(
    session: Session, event: IntegrationEvent, transport: Transport, *, base_url: str
) -> IntegrationEvent:
    """Send one queued ERP movement."""
    endpoint = {
        EventKind.MATERIAL_CONSUMED.value: "/movements/consumption",
        EventKind.MATERIAL_RETURNED.value: "/movements/return",
    }.get(event.kind)
    if endpoint is None:
        # An inbound event has nothing to deliver, and an unknown kind is a programming error
        # rather than a transport failure: retrying it forever would hide it.
        return mark_failed(
            session,
            event,
            TransportError(
                f"el adaptador del ERP no sabe entregar eventos de tipo '{event.kind}'",
                retryable=False,
            ),
        )
    try:
        answer = transport.post(f"{base_url.rstrip('/')}{endpoint}", event.payload)
    except TransportError as exc:
        return mark_failed(session, event, exc)
    return mark_delivered(session, event, answer)


# --- helpers --------------------------------------------------------------------------------


def _quantity(value: Any) -> Decimal | None:
    """A quantity, or None when it cannot be read.

    `Decimal` and not float: 0.1 metres of cable plus 0.2 has to be 0.3 in an inventory movement,
    and a boolean is never a quantity even though Python would let it be one.
    """
    if isinstance(value, bool) or value is None:
        return None
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return quantity if quantity >= 0 else None


def _timestamp(value: Any) -> datetime:
    """The ERP's `as_of`, or now when it did not say.

    Now rather than null, because the column is what the screen shows next to the number, and a
    missing timestamp would read as «current» — which is the reading this field exists to prevent.
    """
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(UTC)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return datetime.now(UTC)
