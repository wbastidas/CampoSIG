"""Fire the preventive plans by hand (RF-012).

    python -m app.plans.cli [--on 2026-10-05] [--unit GYE] [--dry-run]

For the first load, for catching up a period the worker missed, and for seeing what a plan *would*
issue before letting it. `--dry-run` rolls back, so it is safe against production.
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from sqlalchemy import select

from app.infra.database import get_session_factory
from app.org.models import BusinessUnit
from app.plans import service as plans


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispara los planes preventivos vencidos")
    parser.add_argument("--on", help="La fecha a evaluar (por omisión, hoy)")
    parser.add_argument("--unit", help="Solo esta unidad de negocio")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra lo que emitiría y revierte, sin crear ninguna OT",
    )
    args = parser.parse_args()
    on = date.fromisoformat(args.on) if args.on else None

    with get_session_factory()() as session:
        query = select(BusinessUnit).order_by(BusinessUnit.code)
        if args.unit:
            query = query.where(BusinessUnit.code == args.unit)
        reports = {}
        for unit in session.execute(query).scalars():
            reports[unit.code] = plans.run_due(session, unit, on=on).as_dict()
        if args.dry_run:
            session.rollback()
        else:
            session.commit()
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
