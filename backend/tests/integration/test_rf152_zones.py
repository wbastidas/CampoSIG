"""Zones as polygons: import, resolution, coverage and overlap (RF-152).

Need PostGIS, because every question here is a spatial one. The properties under test are the ones
that would hurt silently:

* an invalid ring is **rejected and named**, never repaired into a different boundary;
* one broken feature does not lose the file's other thirty-nine;
* a point in two zones comes back as two, not as the first row;
* a work order that already carries a zone keeps it when the polygons are backfilled;
* nothing crosses between business units (ADR-009).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.audit.service import verify
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.workorders.models import WorkOrder, WorkOrderState
from app.workorders.service import create_work_order, transition
from app.zones import service as zones
from app.zones.models import ZoneOrigin

pytestmark = pytest.mark.integration

ACTOR = "admin.funcional"


def square(west: float, south: float, size: float = 0.10) -> dict[str, object]:
    """A closed square ring as GeoJSON, in degrees. Small enough to be a city sector."""
    east, north = west + size, south + size
    return {
        "type": "Polygon",
        "coordinates": [
            [[west, south], [east, south], [east, north], [west, north], [west, south]]
        ],
    }


def feature(code: str, geometry: dict[str, object], **properties: object) -> dict[str, object]:
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {"code": code, **properties},
    }


def collection(*features: dict[str, object], name: str | None = None) -> dict[str, object]:
    document: dict[str, object] = {"type": "FeatureCollection", "features": list(features)}
    if name:
        document["name"] = name
    return document


@pytest.fixture
def units(session: Session) -> dict[str, BusinessUnit]:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created = {}
    for code, name in (("GYE", "Unidad Guayaquil"), ("MAN", "Unidad Manabí")):
        unit = BusinessUnit(organization_id=org.id, code=code, name=name, profile_id="cnel-gye")
        session.add(unit)
        created[code] = unit
    session.flush()
    return created


@pytest.fixture
def unit(units: dict[str, BusinessUnit]) -> BusinessUnit:
    return units["GYE"]


def make_order(
    session: Session,
    unit: BusinessUnit,
    *,
    lon: float | None = -79.95,
    lat: float | None = -2.15,
    state: str | None = None,
    zone: str | None = None,
) -> WorkOrder:
    order = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        longitude=lon,
        latitude=lat,
        planner_id="planner.a",
        zone=zone,
    )
    if state is not None:
        # Through the real transitions, so the state is one the machine allows.
        for step in ("asignada", "descargada", "en_camino", "en_sitio", "en_ejecucion"):
            if order.state == state:
                break
            transition(session, order, step, actor="tecnico.1")
        session.flush()
    return order


class TestImport:
    def test_a_feature_collection_becomes_zones(self, session: Session, unit: BusinessUnit):
        report = zones.import_geojson(
            session,
            unit,
            collection(
                feature("NORTE", square(-80.0, -2.10), name="Sector Norte"),
                feature("SUR", square(-80.0, -2.30), name="Sector Sur"),
                name="parroquias.geojson",
            ),
            actor=ACTOR,
        )
        assert report.created == ["NORTE", "SUR"]
        assert report.rejected == []
        saved = zones.list_zones(session, unit)
        assert [z.code for z in saved] == ["NORTE", "SUR"]
        assert saved[0].name == "Sector Norte"
        assert saved[0].origin == ZoneOrigin.IMPORTED
        assert saved[0].imported_from is not None
        assert saved[0].imported_from["file"] == "parroquias.geojson"
        assert saved[0].created_by == ACTOR

    def test_a_single_feature_is_accepted_too(self, session: Session, unit: BusinessUnit):
        """QGIS exports one selected polygon as a bare Feature, and a user will paste that."""
        report = zones.import_geojson(
            session, unit, feature("CENTRO", square(-79.95, -2.20)), actor=ACTOR
        )
        assert report.created == ["CENTRO"]

    def test_the_code_is_read_from_any_of_the_usual_property_names(
        self, session: Session, unit: BusinessUnit
    ):
        document = collection(
            {
                "type": "Feature",
                "geometry": square(-80.0, -2.10),
                "properties": {"ZONA": "ESTE", "nombre": "Sector Este"},
            }
        )
        report = zones.import_geojson(session, unit, document, actor=ACTOR)
        assert report.created == ["ESTE"]
        assert zones.get_zone(session, unit, "ESTE").name == "Sector Este"

    def test_an_explicit_property_name_wins_over_the_guesses(
        self, session: Session, unit: BusinessUnit
    ):
        document = collection(
            {
                "type": "Feature",
                "geometry": square(-80.0, -2.10),
                "properties": {"code": "NO", "sector": "SI"},
            }
        )
        report = zones.import_geojson(session, unit, document, actor=ACTOR, code_property="sector")
        assert report.created == ["SI"]

    def test_a_polygon_becomes_a_multipolygon_without_losing_a_part(
        self, session: Session, unit: BusinessUnit
    ):
        """A zone with an island: forcing POLYGON would make this unimportable."""
        multi = {
            "type": "MultiPolygon",
            "coordinates": [
                square(-80.0, -2.10)["coordinates"],
                square(-79.5, -2.60)["coordinates"],
            ],
        }
        zones.import_geojson(session, unit, collection(feature("INSULAR", multi)), actor=ACTOR)
        # Both parts answer: a point in the detached part is in the zone.
        assert zones.zones_at(session, unit, -79.45, -2.55) == ["INSULAR"]
        assert zones.zones_at(session, unit, -79.95, -2.05) == ["INSULAR"]


class TestImportRefusals:
    def test_an_invalid_ring_is_rejected_with_the_reason_and_never_repaired(
        self, session: Session, unit: BusinessUnit
    ):
        """A bow-tie. `ST_MakeValid` would import a *different* boundary and report success."""
        bowtie = {
            "type": "Polygon",
            "coordinates": [
                [[-80.0, -2.0], [-79.9, -2.1], [-80.0, -2.1], [-79.9, -2.0], [-80.0, -2.0]]
            ],
        }
        report = zones.import_geojson(
            session, unit, collection(feature("MALA", bowtie)), actor=ACTOR
        )
        assert report.created == []
        assert len(report.rejected) == 1
        assert report.rejected[0].code == "MALA"
        assert "inválida" in report.rejected[0].reason
        assert zones.list_zones(session, unit) == []

    def test_one_bad_feature_does_not_lose_the_good_ones(
        self, session: Session, unit: BusinessUnit
    ):
        """The reason rejections are per feature: a file of forty parishes imports thirty-nine."""
        bowtie = {
            "type": "Polygon",
            "coordinates": [
                [[-80.0, -2.0], [-79.9, -2.1], [-80.0, -2.1], [-79.9, -2.0], [-80.0, -2.0]]
            ],
        }
        report = zones.import_geojson(
            session,
            unit,
            collection(
                feature("BUENA-1", square(-80.5, -2.10)),
                feature("MALA", bowtie),
                feature("BUENA-2", square(-80.5, -2.40)),
            ),
            actor=ACTOR,
        )
        assert report.created == ["BUENA-1", "BUENA-2"]
        assert [item.code for item in report.rejected] == ["MALA"]

    def test_a_geometry_postgis_cannot_parse_does_not_lose_the_features_already_accepted(
        self, session: Session, unit: BusinessUnit
    ):
        """The reason the validity probe runs inside a SAVEPOINT.

        A ring PostGIS cannot even read aborts the transaction, so without the savepoint the
        rejection would take the zones already written with it — and the report would still say
        they were created. Hence the assertion is on the rows, not on the report.
        """
        unreadable = {"type": "MultiPolygon", "coordinates": square(-80.0, -2.1)["coordinates"]}
        report = zones.import_geojson(
            session,
            unit,
            collection(
                feature("ANTES", square(-80.5, -2.10)),
                feature("ILEGIBLE", unreadable),
                feature("DESPUES", square(-80.5, -2.40)),
            ),
            actor=ACTOR,
        )
        assert [item.code for item in report.rejected] == ["ILEGIBLE"]
        assert [zone.code for zone in zones.list_zones(session, unit)] == ["ANTES", "DESPUES"]

    def test_a_point_is_rejected_saying_a_zone_is_an_area(
        self, session: Session, unit: BusinessUnit
    ):
        document = collection(feature("PUNTO", {"type": "Point", "coordinates": [-79.9, -2.1]}))
        report = zones.import_geojson(session, unit, document, actor=ACTOR)
        assert "Point" in report.rejected[0].reason
        assert "área" in report.rejected[0].reason

    def test_a_feature_without_a_code_says_where_it_looked(
        self, session: Session, unit: BusinessUnit
    ):
        document = collection(
            {"type": "Feature", "geometry": square(-80.0, -2.1), "properties": {"otra": "cosa"}}
        )
        report = zones.import_geojson(session, unit, document, actor=ACTOR)
        assert "código" in report.rejected[0].reason
        assert "codigo" in report.rejected[0].reason  # the list it searched is in the message

    def test_a_repeated_code_in_the_same_file_is_rejected_once(
        self, session: Session, unit: BusinessUnit
    ):
        report = zones.import_geojson(
            session,
            unit,
            collection(
                feature("NORTE", square(-80.0, -2.10)),
                feature("NORTE", square(-80.5, -2.40)),
            ),
            actor=ACTOR,
        )
        assert report.created == ["NORTE"]
        assert "repetido" in report.rejected[0].reason

    def test_a_document_that_is_not_geojson_is_refused_whole(
        self, session: Session, unit: BusinessUnit
    ):
        with pytest.raises(zones.ZoneError):
            zones.import_geojson(session, unit, {"type": "Topology"}, actor=ACTOR)

    def test_an_empty_collection_is_refused_rather_than_reported_as_success(
        self, session: Session, unit: BusinessUnit
    ):
        with pytest.raises(zones.ZoneError):
            zones.import_geojson(session, unit, collection(), actor=ACTOR)

    def test_reimporting_replaces_the_boundary_and_records_who(
        self, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1))), actor=ACTOR
        )
        assert zones.zones_at(session, unit, -79.95, -2.05) == ["N"]
        report = zones.import_geojson(
            session, unit, collection(feature("N", square(-81.0, -3.1))), actor="otra.persona"
        )
        assert report.updated == ["N"]
        assert zones.zones_at(session, unit, -79.95, -2.05) == []
        assert zones.zones_at(session, unit, -80.95, -3.05) == ["N"]
        assert zones.get_zone(session, unit, "N").updated_by == "otra.persona"

    def test_an_existing_code_is_reported_when_replacement_was_not_asked_for(
        self, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1))), actor=ACTOR
        )
        report = zones.import_geojson(
            session,
            unit,
            collection(feature("N", square(-81.0, -3.1))),
            actor=ACTOR,
            replace_existing=False,
        )
        assert report.updated == []
        assert "ya existe" in report.rejected[0].reason
        # And the original boundary is untouched.
        assert zones.zones_at(session, unit, -79.95, -2.05) == ["N"]


class TestResolution:
    def test_a_point_outside_every_zone_resolves_to_nothing(
        self, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1))), actor=ACTOR
        )
        assert zones.zones_at(session, unit, -70.0, -10.0) == []

    def test_a_point_in_two_zones_returns_both(self, session: Session, unit: BusinessUnit):
        """Ambiguity is reported, not resolved by picking the first row."""
        zones.import_geojson(
            session,
            unit,
            collection(
                feature("A", square(-80.00, -2.10)),
                feature("B", square(-79.95, -2.05)),
            ),
            actor=ACTOR,
        )
        assert zones.zones_at(session, unit, -79.93, -2.03) == ["A", "B"]

    def test_an_inactive_zone_stops_answering(self, session: Session, unit: BusinessUnit):
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1))), actor=ACTOR
        )
        zones.set_active(session, unit, "N", active=False, actor=ACTOR)
        assert zones.zones_at(session, unit, -79.95, -2.05) == []
        # But it is still there, with its history.
        assert [z.code for z in zones.list_zones(session, unit, include_inactive=True)] == ["N"]

    def test_zones_do_not_cross_between_units(
        self, session: Session, units: dict[str, BusinessUnit]
    ):
        """ADR-009: two units may both operate a NORTE, and neither sees the other's."""
        for code in ("GYE", "MAN"):
            zones.import_geojson(
                session,
                units[code],
                collection(feature("NORTE", square(-80.0, -2.1))),
                actor=ACTOR,
            )
        assert zones.zones_at(session, units["GYE"], -79.95, -2.05) == ["NORTE"]
        gye_zone = zones.get_zone(session, units["GYE"], "NORTE")
        man_zone = zones.get_zone(session, units["MAN"], "NORTE")
        assert gye_zone.id != man_zone.id
        assert len(zones.list_zones(session, units["GYE"])) == 1

    def test_an_unknown_code_raises_rather_than_returning_none(
        self, session: Session, unit: BusinessUnit
    ):
        with pytest.raises(zones.UnknownZoneError):
            zones.get_zone(session, unit, "NO-EXISTE")


class TestOverlaps:
    def test_neighbours_that_only_share_a_border_are_not_an_overlap(
        self, session: Session, unit: BusinessUnit
    ):
        """Adjacency is the normal case. Reporting every neighbour would bury the real problem."""
        zones.import_geojson(
            session,
            unit,
            collection(
                feature("A", square(-80.0, -2.1)),
                feature("B", square(-79.9, -2.1)),  # shares the eastern edge exactly
            ),
            actor=ACTOR,
        )
        assert zones.overlaps(session, unit) == []

    def test_overlapping_interiors_are_reported_with_an_area_in_square_metres(
        self, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session,
            unit,
            collection(
                feature("A", square(-80.00, -2.10)),
                feature("B", square(-79.95, -2.05)),
            ),
            actor=ACTOR,
        )
        found = zones.overlaps(session, unit)
        assert [(item.left, item.right) for item in found] == [("A", "B")]
        # A 0.05° square near the equator is roughly 5.5 km on a side: tens of km², not degrees².
        assert 2e7 < found[0].area_m2 < 5e7
        assert "m²" in found[0].describe()

    def test_a_zone_contained_in_another_is_reported(self, session: Session, unit: BusinessUnit):
        """`ST_Overlaps` alone would miss this, and a zone inside another is a real problem."""
        zones.import_geojson(
            session,
            unit,
            collection(
                feature("GRANDE", square(-80.0, -2.2, size=0.4)),
                feature("CHICA", square(-79.9, -2.1, size=0.05)),
            ),
            actor=ACTOR,
        )
        assert [(i.left, i.right) for i in zones.overlaps(session, unit)] == [("CHICA", "GRANDE")]

    def test_an_inactive_zone_does_not_overlap_anything(self, session: Session, unit: BusinessUnit):
        zones.import_geojson(
            session,
            unit,
            collection(feature("A", square(-80.00, -2.10)), feature("B", square(-79.95, -2.05))),
            actor=ACTOR,
        )
        zones.set_active(session, unit, "B", active=False, actor=ACTOR)
        assert zones.overlaps(session, unit) == []


class TestCoverage:
    def test_coverage_separates_outside_from_without_location(
        self, session: Session, unit: BusinessUnit
    ):
        """The distinction matters: one is a zone problem, the other is a coordinates problem."""
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1))), actor=ACTOR
        )
        make_order(session, unit, lon=-79.95, lat=-2.05)  # inside
        make_order(session, unit, lon=-70.0, lat=-10.0)  # outside
        make_order(session, unit, lon=None, lat=None)  # no point
        found = zones.coverage(session, unit)
        assert (found.inside_one, found.outside, found.without_location) == (1, 1, 1)
        assert found.open_orders == 3

    def test_the_share_does_not_count_orders_without_a_point_against_the_zones(
        self, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1))), actor=ACTOR
        )
        make_order(session, unit, lon=-79.95, lat=-2.05)
        make_order(session, unit, lon=None, lat=None)
        assert zones.coverage(session, unit).covered_share == 1.0

    def test_the_share_is_none_when_nothing_is_locatable(
        self, session: Session, unit: BusinessUnit
    ):
        """A unit that captures no coordinates would otherwise read as 0 % zone coverage."""
        make_order(session, unit, lon=None, lat=None)
        assert zones.coverage(session, unit).covered_share is None

    def test_an_ambiguous_order_is_counted_apart_from_the_uncovered(
        self, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session,
            unit,
            collection(feature("A", square(-80.00, -2.10)), feature("B", square(-79.95, -2.05))),
            actor=ACTOR,
        )
        make_order(session, unit, lon=-79.93, lat=-2.03)
        found = zones.coverage(session, unit)
        assert (found.ambiguous, found.outside, found.inside_one) == (1, 0, 0)

    def test_closed_work_is_not_counted(self, session: Session, unit: BusinessUnit):
        """A closed order in no zone is history; an assigned one is a technician without a map."""
        order = make_order(session, unit, lon=-70.0, lat=-10.0)
        assert zones.coverage(session, unit).open_orders == 1
        transition(
            session,
            order,
            WorkOrderState.CANCELLED.value,
            actor="planner.a",
            reason="se anula para la prueba",
        )
        session.flush()
        assert zones.coverage(session, unit).open_orders == 0


class TestBackfill:
    def test_an_empty_zone_is_filled_from_the_polygon(self, session: Session, unit: BusinessUnit):
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1))), actor=ACTOR
        )
        order = make_order(session, unit, lon=-79.95, lat=-2.05)
        report = zones.backfill_zones(session, unit, actor=ACTOR)
        assert report.filled == {str(order.id): "N"}
        assert order.zone == "N"

    def test_an_existing_zone_is_never_overwritten(self, session: Session, unit: BusinessUnit):
        """The string may have come from the corporate system or from a planner who knows more."""
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1))), actor=ACTOR
        )
        order = make_order(session, unit, lon=-79.95, lat=-2.05, zone="LA-QUE-DIJO-EL-SISTEMA")
        report = zones.backfill_zones(session, unit, actor=ACTOR)
        assert report.filled == {}
        assert order.zone == "LA-QUE-DIJO-EL-SISTEMA"

    def test_an_ambiguous_order_is_returned_and_not_guessed(
        self, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session,
            unit,
            collection(feature("A", square(-80.00, -2.10)), feature("B", square(-79.95, -2.05))),
            actor=ACTOR,
        )
        order = make_order(session, unit, lon=-79.93, lat=-2.03)
        report = zones.backfill_zones(session, unit, actor=ACTOR)
        assert report.filled == {}
        assert report.ambiguous == {str(order.id): ["A", "B"]}
        assert order.zone is None

    def test_a_dry_run_reports_without_writing(self, session: Session, unit: BusinessUnit):
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1))), actor=ACTOR
        )
        order = make_order(session, unit, lon=-79.95, lat=-2.05)
        report = zones.backfill_zones(session, unit, actor=ACTOR, dry_run=True)
        assert report.filled == {str(order.id): "N"}
        assert order.zone is None


class TestTrail:
    def test_every_change_to_a_boundary_lands_in_the_trail_and_the_chain_holds(
        self, session: Session, unit: BusinessUnit
    ):
        """A zone decides which crew covers which street. Who moved it is an audit question."""
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1))), actor=ACTOR
        )
        zones.import_geojson(
            session, unit, collection(feature("N", square(-81.0, -3.1))), actor="otra.persona"
        )
        zones.set_active(session, unit, "N", active=False, actor="tercera.persona")
        events = [
            event
            for event in session.query(AuditEvent).order_by(AuditEvent.sequence)
            if event.subject_type == "zone"
        ]
        assert [event.actor for event in events] == [ACTOR, "otra.persona", "tercera.persona"]
        assert verify(session, unit.id).intact


#: The administrator these endpoint tests act as. Identity comes from the token in production;
#: here the dependency is overridden, because what this section tests is the endpoints.
ADMIN = Principal(
    subject="kc|admin.funcional",
    username="admin.funcional",
    display_name="Administradora Funcional",
    roles=frozenset({Role.FUNCTIONAL_ADMIN.value}),
    business_units=frozenset({"GYE", "MAN"}),
)

PLANNER = Principal(
    subject="kc|planner.a",
    username="planner.a",
    display_name="Planificador",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE"}),
)


@pytest.fixture
def client(session: Session):
    """A client sharing the test's transaction, so nothing it writes escapes the rollback."""
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: ADMIN
    with TestClient(app) as raw:
        yield raw


class TestApi:
    def test_the_list_comes_back_as_a_feature_collection_maplibre_can_draw(
        self, client, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1), name="Norte")), actor=ACTOR
        )
        body = client.get("/api/v1/zones/units/GYE").json()
        assert body["type"] == "FeatureCollection"
        assert body["features"][0]["properties"]["code"] == "N"
        assert body["features"][0]["geometry"]["type"] == "MultiPolygon"

    def test_a_drawn_polygon_is_saved_with_the_author_from_the_token(
        self, client, session: Session, unit: BusinessUnit
    ):
        response = client.put(
            "/api/v1/zones/units/GYE/CENTRO",
            json={"code": "CENTRO", "name": "Centro", "geometry": square(-79.95, -2.20)},
        )
        assert response.status_code == 200
        assert zones.get_zone(session, unit, "CENTRO").created_by == ADMIN.subject

    def test_an_invalid_polygon_comes_back_as_422_with_the_reason(self, client, unit: BusinessUnit):
        bowtie = {
            "type": "Polygon",
            "coordinates": [
                [[-80.0, -2.0], [-79.9, -2.1], [-80.0, -2.1], [-79.9, -2.0], [-80.0, -2.0]]
            ],
        }
        response = client.put(
            "/api/v1/zones/units/GYE/MALA",
            json={"code": "MALA", "name": "Mala", "geometry": bowtie},
        )
        assert response.status_code == 422
        assert "inválida" in response.json()["detail"]

    def test_a_code_mismatch_between_route_and_body_is_refused(self, client, unit: BusinessUnit):
        """Otherwise a mistyped URL would quietly create a second zone under the other name."""
        response = client.put(
            "/api/v1/zones/units/GYE/UNA",
            json={"code": "OTRA", "name": "Otra", "geometry": square(-79.95, -2.20)},
        )
        assert response.status_code == 422

    def test_coverage_reports_the_overlaps_alongside_the_counts(
        self, client, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session,
            unit,
            collection(feature("A", square(-80.00, -2.10)), feature("B", square(-79.95, -2.05))),
            actor=ACTOR,
        )
        body = client.get("/api/v1/zones/units/GYE/coverage").json()
        assert body["overlaps"][0]["left"] == "A"
        assert "m²" in body["overlaps"][0]["text"]
        assert body["coverage"]["open_orders"] == 0

    def test_a_planner_may_look_and_may_not_move_a_boundary(
        self, session: Session, unit: BusinessUnit
    ):
        """A boundary decides which crew covers which street, so moving one is administrative."""
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: PLANNER
        with TestClient(app) as planner_client:
            assert planner_client.get("/api/v1/zones/units/GYE").status_code == 200
            forbidden = planner_client.put(
                "/api/v1/zones/units/GYE/CENTRO",
                json={"code": "CENTRO", "name": "Centro", "geometry": square(-79.95, -2.20)},
            )
            assert forbidden.status_code == 403

    def test_an_unknown_unit_is_404(self, client):
        response = client.get("/api/v1/zones/units/XX")
        assert response.status_code in (403, 404)

    def test_the_dry_run_of_the_backfill_writes_nothing(
        self, client, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session, unit, collection(feature("N", square(-80.0, -2.1))), actor=ACTOR
        )
        order = make_order(session, unit, lon=-79.95, lat=-2.05)
        session.flush()
        body = client.post("/api/v1/zones/units/GYE/backfill?dry_run=true").json()
        assert body["dry_run"] is True
        assert body["filled"] == {str(order.id): "N"}
        assert order.zone is None
