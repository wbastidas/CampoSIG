"""Rutas sugeridas para un conjunto de OT (RF-025).

El criterio es una comparación: «genera un orden de visita que reduce la distancia total frente al
orden aleatorio». Lo que se prueba es justamente eso —la sugerida nunca pesa más que la de entrada—,
más las tres cosas que hacen que el número sea honesto y no una promesa que la plataforma no puede
cumplir:

* **Nunca peor que el orden de entrada.** Un solucionador que a veces sugiere algo más largo que
  lo que ya había no es una sugerencia, es ruido con forma de número.
* **El aviso de línea recta viaja con el resultado.** La plataforma no tiene red vial; decirlo en la
  respuesta es lo que evita que alguien lea la distancia como minutos de manejo.
* **El inicio se fija cuando se pide, y solo entonces.** Sin punto de partida el problema tiene los
  dos extremos libres; con uno —explícito o desde la posición de un dispositivo (RF-020)— el primer
  tramo sale de ahí.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.dispatch import positions
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.routing import service as routing
from app.sync.service import enrol_device
from app.workorders.models import WorkOrder
from app.workorders.service import create_work_order

pytestmark = pytest.mark.integration

PLANNER = Principal(
    subject="kc|planificador.demo",
    username="planificador.demo",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE"}),
)
TECHNICIAN = Principal(
    subject="kc|tecnico.demo",
    username="tecnico.demo",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)


@pytest.fixture
def units(session: Session) -> dict[str, BusinessUnit]:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created: dict[str, BusinessUnit] = {}
    for code, name in (("GYE", "Unidad Guayaquil"), ("MAN", "Unidad Manabí")):
        unit = BusinessUnit(organization_id=org.id, code=code, name=name, profile_id="cnel-gye")
        session.add(unit)
        session.flush()
        created[code] = unit
    return created


@pytest.fixture
def unit(units: dict[str, BusinessUnit]) -> BusinessUnit:
    return units["GYE"]


def an_order(
    session: Session,
    unit: BusinessUnit,
    *,
    longitude: float,
    latitude: float,
    code: str,
) -> WorkOrder:
    order = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        longitude=longitude,
        latitude=latitude,
        planner_id=PLANNER.subject,
    )
    order.code = code
    session.flush()
    return order


def a_line_of_orders(session: Session, unit: BusinessUnit) -> list[WorkOrder]:
    """Cuatro OT sobre una línea recta: A, B, C, D, separadas por igual.

    El óptimo es trivial de verificar a mano —visitarlas en el orden de la línea, en cualquier
    dirección— así que sirve para probar que el solucionador encuentra lo obvio y no algo peor.
    """
    return [
        an_order(session, unit, longitude=lon, latitude=-2.17, code=f"OT-{letter}")
        for letter, lon in zip("ABCD", (-79.90, -79.85, -79.80, -79.75), strict=True)
    ]


def client_as(session: Session, who: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: who
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with client_as(session, PLANNER) as raw:
        yield raw


class TestNeverWorseThanTheInput:
    def test_rf_025_un_orden_desordenado_mejora_o_iguala(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """A, C, B, D obliga a un zigzag; la sugerida tiene que deshacerlo."""
        a, c, b, d = None, None, None, None
        orders = a_line_of_orders(session, unit)
        a, b, c, d = orders
        bad_order = [a.id, c.id, b.id, d.id]

        suggestion = routing.suggest_route(session, unit, bad_order)

        assert suggestion.total_distance_m <= suggestion.naive_distance_m
        assert suggestion.total_distance_m < suggestion.naive_distance_m

    def test_rf_025_un_orden_ya_optimo_no_empeora(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        orders = a_line_of_orders(session, unit)
        good_order = [order.id for order in orders]

        suggestion = routing.suggest_route(session, unit, good_order)

        assert suggestion.total_distance_m == pytest.approx(suggestion.naive_distance_m, rel=0.01)

    def test_rf_025_el_orden_sugerido_visita_las_mismas_ot(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        orders = a_line_of_orders(session, unit)
        ids = [order.id for order in orders]

        suggestion = routing.suggest_route(session, unit, [ids[3], ids[0], ids[2], ids[1]])

        assert {stop.work_order_id for stop in suggestion.stops} == set(ids)
        assert len(suggestion.stops) == len(ids)


class TestTheStartingPoint:
    def test_rf_025_sin_inicio_el_primer_tramo_no_cuenta_desde_ningun_lado(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        orders = a_line_of_orders(session, unit)
        suggestion = routing.suggest_route(session, unit, [order.id for order in orders])

        assert suggestion.stops[0].leg_distance_m == 0.0
        assert suggestion.start is None

    def test_rf_025_la_comparacion_de_entrada_cuenta_el_tramo_desde_el_inicio(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Si `naive_distance_m` no sumara el primer tramo, sería igual con o sin punto de
        partida — y ese es justo el número que le regalaría metros a la sugerencia sin reflejar
        lo que un planificador habría recorrido de verdad saliendo de donde está la cuadrilla."""
        orders = a_line_of_orders(session, unit)
        a, b, c, d = orders
        start = (-79.91, -2.17)

        with_start = routing.suggest_route(session, unit, [a.id, b.id, c.id, d.id], start=start)
        without_start = routing.suggest_route(session, unit, [a.id, b.id, c.id, d.id])

        from app.routing.service import _haversine_m

        manual_first_leg = _haversine_m(start, (-79.90, -2.17))
        assert manual_first_leg > 0
        assert with_start.naive_distance_m == pytest.approx(
            without_start.naive_distance_m + manual_first_leg
        )

    def test_rf_025_con_inicio_explicito_empieza_por_la_ot_mas_cercana(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        orders = a_line_of_orders(session, unit)
        a, b, c, d = orders
        # Justo al lado de D: el orden sugerido tiene que arrancar por D y no por A.
        start = (-79.751, -2.17)

        suggestion = routing.suggest_route(session, unit, [a.id, b.id, c.id, d.id], start=start)

        assert suggestion.stops[0].work_order_id == d.id
        assert suggestion.stops[0].leg_distance_m > 0
        assert suggestion.start == start

    def test_rf_025_la_posicion_de_un_dispositivo_sirve_de_inicio(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        """RF-020 alimenta a RF-025: la cuadrilla empieza donde está, no donde nació la OT."""
        device, _ = enrol_device(
            session, unit, device_key="phone-00000001", user_sub=TECHNICIAN.subject
        )
        positions.report(session, unit, device, latitude=-2.17, longitude=-79.751)
        orders = a_line_of_orders(session, unit)
        a, b, c, d = orders

        response = client.post(
            "/api/v1/routing/units/GYE/suggest",
            json={
                "work_order_ids": [str(a.id), str(b.id), str(c.id), str(d.id)],
                "start_device_key": "phone-00000001",
            },
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["stops"][0]["work_order_id"] == str(d.id)
        assert body["start"]["longitude"] == pytest.approx(-79.751)

    def test_rf_025_un_dispositivo_sin_posicion_se_rechaza_con_el_motivo(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        enrol_device(session, unit, device_key="phone-00000002", user_sub=TECHNICIAN.subject)
        orders = a_line_of_orders(session, unit)

        response = client.post(
            "/api/v1/routing/units/GYE/suggest",
            json={
                "work_order_ids": [str(order.id) for order in orders],
                "start_device_key": "phone-00000002",
            },
        )

        assert response.status_code == 422
        assert "no tiene una posición" in response.json()["detail"]

    def test_rf_025_no_se_puede_pedir_inicio_explicito_y_dispositivo_a_la_vez(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        orders = a_line_of_orders(session, unit)

        response = client.post(
            "/api/v1/routing/units/GYE/suggest",
            json={
                "work_order_ids": [str(order.id) for order in orders[:2]],
                "start_latitude": -2.17,
                "start_longitude": -79.9,
                "start_device_key": "phone-00000003",
            },
        )

        assert response.status_code == 422


class TestOpenPathIsNotAClosedLoop:
    """El caso que de verdad distingue «camino abierto» de «ciclo cerrado».

    Con puntos colineales o en un cuadrado, el orden óptimo del camino abierto y el del ciclo
    cerrado suelen coincidir por pura simetría — así fue como el primer pase de sabotaje pasó
    inadvertido: forzar un ciclo cerrado no cambiaba el orden que devolvía la geometría de las
    otras pruebas. Esta geometría se buscó por fuerza bruta precisamente para que no empate: el
    orden óptimo del camino abierto pesa unos 24 286 m en línea recta, y el orden óptimo del ciclo
    cerrado, evaluado como camino abierto, pesa unos 46 754 m — casi el doble.
    """

    def test_rf_025_el_inicio_fijo_no_se_resuelve_como_un_ciclo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        base_lon, base_lat = -79.9, -2.17
        start = (base_lon, base_lat)
        offsets = [(0.15, -0.15), (0.08, -0.06), (0.15, -0.14), (0.01, 0.0)]
        orders = [
            an_order(
                session,
                unit,
                longitude=base_lon + dlon,
                latitude=base_lat + dlat,
                code=f"OT-{index}",
            )
            for index, (dlon, dlat) in enumerate(offsets)
        ]

        suggestion = routing.suggest_route(
            session, unit, [order.id for order in orders], start=start
        )

        # El único orden que pesa ~24 286 m; el que resolvería un ciclo cerrado pesa ~46 754 m
        # como camino abierto — casi el doble, así que un umbral generoso sigue siendo decisivo.
        assert suggestion.total_distance_m < 30_000
        assert [stop.work_order_id for stop in suggestion.stops] == [
            orders[3].id,
            orders[1].id,
            orders[2].id,
            orders[0].id,
        ]

    def test_rf_025_el_orden_de_entrada_no_cambia_la_ruta_optima(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La misma geometría, entregada en otro orden, hace visible una fragilidad real.

        La primera versión de `_solve` probaba una sola estrategia de arranque, y con esta misma
        geometría —las mismas cuatro OT, el mismo punto de partida— el resultado dependía del
        orden en que llegaban en la lista: pedida como 0,1,2,3 resolvía el óptimo (~24 286 m);
        pedida como 0,1,3,2 se quedaba en un óptimo local de ~46 754 m, casi el doble, con las
        mismas coordenadas de por medio. El orden de entrada no tiene por qué importarle a la
        distancia de salida, y aquí importaba.
        """
        base_lon, base_lat = -79.9, -2.17
        start = (base_lon, base_lat)
        offsets = [(0.15, -0.15), (0.08, -0.06), (0.15, -0.14), (0.01, 0.0)]
        orders = [
            an_order(
                session,
                unit,
                longitude=base_lon + dlon,
                latitude=base_lat + dlat,
                code=f"OT-reorden-{index}",
            )
            for index, (dlon, dlat) in enumerate(offsets)
        ]
        # El orden que en el primer pase de esta prueba producía el óptimo local incorrecto.
        reordered_ids = [orders[0].id, orders[1].id, orders[3].id, orders[2].id]

        suggestion = routing.suggest_route(session, unit, reordered_ids, start=start)

        assert suggestion.total_distance_m < 30_000
        assert {stop.work_order_id for stop in suggestion.stops} == {o.id for o in orders}


class TestTheCaveat:
    def test_rf_025_el_aviso_de_linea_recta_viaja_con_el_resultado(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        orders = a_line_of_orders(session, unit)

        suggestion = routing.suggest_route(session, unit, [order.id for order in orders])

        assert any("línea recta" in caveat for caveat in suggestion.caveats)


class TestWhatIsRefused:
    def test_rf_025_una_sola_ot_no_es_una_ruta(self, session: Session, unit: BusinessUnit) -> None:
        order = an_order(session, unit, longitude=-79.9, latitude=-2.17, code="OT-1")

        with pytest.raises(routing.RoutingError, match="al menos dos OT"):
            routing.suggest_route(session, unit, [order.id])

    def test_rf_025_una_ot_sin_ubicacion_se_rechaza(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        located = an_order(session, unit, longitude=-79.9, latitude=-2.17, code="OT-1")
        unlocated = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            planner_id=PLANNER.subject,
        )
        unlocated.code = "OT-2"
        session.flush()

        with pytest.raises(routing.RoutingError, match="no tienen ubicación"):
            routing.suggest_route(session, unit, [located.id, unlocated.id])

    def test_rf_025_una_ot_de_otra_unidad_se_rechaza(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        mine = an_order(session, units["GYE"], longitude=-79.9, latitude=-2.17, code="OT-1")
        foreign = an_order(session, units["MAN"], longitude=-80.4, latitude=-1.05, code="OT-2")

        with pytest.raises(routing.RoutingError, match="no existen en la unidad"):
            routing.suggest_route(session, units["GYE"], [mine.id, foreign.id])

    def test_rf_025_una_ot_inexistente_se_rechaza(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit, longitude=-79.9, latitude=-2.17, code="OT-1")

        with pytest.raises(routing.RoutingError, match="no existen en la unidad"):
            routing.suggest_route(session, unit, [order.id, uuid.uuid4()])


class TestTheStopLimit:
    def test_rf_025_mas_del_maximo_de_paradas_se_rechaza(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """No hace falta que las OT existan: el límite se comprueba antes de tocar la base."""
        too_many = [uuid.uuid4() for _ in range(routing.MAX_STOPS + 1)]

        with pytest.raises(routing.RoutingError, match="como mucho"):
            routing.suggest_route(session, unit, too_many)


class TestApi:
    def test_rf_025_el_tecnico_no_pide_rutas(self, session: Session, unit: BusinessUnit) -> None:
        orders = a_line_of_orders(session, unit)

        with client_as(session, TECHNICIAN) as api:
            response = api.post(
                "/api/v1/routing/units/GYE/suggest",
                json={"work_order_ids": [str(order.id) for order in orders[:2]]},
            )

        assert response.status_code == 403

    def test_rf_025_nadie_pide_rutas_fuera_de_su_unidad(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        orders = [
            an_order(session, units["MAN"], longitude=-80.4, latitude=-1.05, code="OT-1"),
            an_order(session, units["MAN"], longitude=-80.3, latitude=-1.06, code="OT-2"),
        ]

        with client_as(session, PLANNER) as api:
            response = api.post(
                "/api/v1/routing/units/MAN/suggest",
                json={"work_order_ids": [str(order.id) for order in orders]},
            )

        assert response.status_code == 403

    def test_rf_025_devuelve_la_ruta_por_la_api(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        orders = a_line_of_orders(session, unit)

        response = client.post(
            "/api/v1/routing/units/GYE/suggest",
            json={"work_order_ids": [str(order.id) for order in orders]},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["stops"]) == 4
        assert body["total_distance_m"] <= body["naive_distance_m"]
        assert body["caveats"]

    def test_rf_025_latitud_sin_longitud_se_rechaza(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        orders = a_line_of_orders(session, unit)

        response = client.post(
            "/api/v1/routing/units/GYE/suggest",
            json={
                "work_order_ids": [str(order.id) for order in orders[:2]],
                "start_latitude": -2.17,
            },
        )

        assert response.status_code == 422

    def test_rf_025_una_sola_ot_responde_422_y_no_500(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        order = an_order(session, unit, longitude=-79.9, latitude=-2.17, code="OT-1")

        response = client.post(
            "/api/v1/routing/units/GYE/suggest", json={"work_order_ids": [str(order.id)]}
        )

        assert response.status_code == 422
