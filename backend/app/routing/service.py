"""Rutas sugeridas para un conjunto de OT (RF-025).

El criterio es una comparación: «genera un orden de visita que reduce la distancia total frente al
orden aleatorio». No hay tabla nueva — la ruta no se guarda, se calcula al pedirla, sobre las OT que
el planificador ya tiene seleccionadas en el mapa.

Cuatro decisiones:

* **Distancia en línea recta, dicha como lo que es.** La plataforma no tiene red vial ni tiempos de
  viaje reales — eso vive en ArcGIS Network Analyst, que este incremento no toca — así que la
  distancia es geodésica (`haversine`), una aproximación honesta y no una promesa de minutos de
  manejo. El resultado lleva el aviso en sus propias palabras, como toda aproximación en esta
  plataforma.
* **Inicio libre, salvo que alguien lo fije.** Sin un punto de partida, el problema es «visitar N
  OT en el orden que menos sume», con inicio y fin libres — no un ciclo que vuelve al principio,
  porque una cuadrilla no necesariamente regresa a donde empezó. Con un punto de partida —la
  posición de un dispositivo, reportada por RF-020, o coordenadas explícitas— el inicio se fija ahí
  y el final queda libre igual.
* **El truco es un nodo fantasma, no un algoritmo propio.** Un nodo a distancia cero de todos los
  demás hace que «terminar en cualquier parte» no cueste nada: el vehículo puede insertarlo justo
  antes de cerrar el ciclo, así que cerrar el ciclo por el depósito sale gratis desde cualquier
  última parada real. Por eso un solo depósito —el punto de partida cuando lo hay, o el propio nodo
  fantasma cuando no— basta para las dos formas del problema: no hace falta una segunda variante que
  fije el nodo fantasma como destino explícito, porque el fantasma ya absorbe el costo de cerrar el
  ciclo se declare o no como destino. (Esto se comprobó, no se supuso: una versión con destino
  explícito y otra con depósito único devolvían siempre el mismo orden en las pruebas de sabotaje —
  la diferencia era forma, no comportamiento — así que se dejó una sola, más simple.) Es la técnica
  estándar para un TSP de camino abierto, y evita escribir un optimizador propio para un problema
  que ya resuelve una biblioteca con licencia Apache 2.0 (la que nombra el SRS para esto).
* **La comparación va en la respuesta, no queda para que alguien la calcule.** El criterio de
  aceptación es explícitamente contra el orden aleatorio, así que la distancia del orden **en que
  llegaron las OT** viaja junto a la sugerida —incluido el tramo desde el punto de partida, si lo
  hay—: es la que un planificador habría recorrido sin esto.
* **Una sola arrancada no basta, y esto se descubrió probando, no leyendo la documentación de
  OR-Tools.** Con una única estrategia de primera solución, el mismo conjunto de cuatro OT —las
  mismas coordenadas— resolvía el óptimo real o se quedaba en uno casi el doble de largo según el
  **orden en que llegaban en la lista de entrada**, algo que no debería importar y que importaba.
  Por eso `_solve` corre varias estrategias y se queda con la de menor distancia real, no con la
  que cada solucionador cree que ganó: son contabilidades internas distintas, y solo la geodésica
  final es comparable entre ellas.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any

from geoalchemy2.functions import ST_X, ST_Y
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.principal import Principal
from app.auth.scope import work_order_scope
from app.dispatch.models import DevicePosition
from app.org.models import BusinessUnit
from app.sync.models import Device
from app.workorders.models import WorkOrder

EARTH_RADIUS_M = 6_371_000.0

#: Menos de dos puntos no es una ruta, es una OT. Más de esto y el problema deja de ser lo que
#: RF-025 pide —una ruta del día de una cuadrilla— y empieza a ser una redistritación completa, que
#: es un problema distinto y uno que un solucionador con límite de tiempo corto no resuelve bien.
MIN_STOPS = 2
MAX_STOPS = 60

#: Cuánto tiempo, como mucho, se le da a cada intento del solucionador. Se prueban varias
#: estrategias de primera solución y se corre esto por cada una (ver `_CANDIDATE_STRATEGIES`); para
#: el tamaño de una ruta diaria esto converge casi de inmediato, y más tiempo no es gratis cuando
#: alguien está esperando la respuesta en el mapa.
SOLVER_TIME_LIMIT_S = 1

#: Varias estrategias de arranque, no una. Se encontró por las malas: con una sola —incluso con
#: búsqueda local guiada corriendo después— el resultado dependía del orden en que llegaban las OT
#: de entrada, y para el mismo conjunto geométrico una lista podía resolver el óptimo verdadero y
#: otra quedarse en un óptimo local casi el doble de largo. Cada estrategia parte de un extremo
#: distinto del espacio de soluciones, y quedarse con la mejor de todas —comparada por la distancia
#: real, no por lo que cada solucionador cree haber logrado— es la manera barata de dejar de
#: apostarle a una sola arrancada.
_CANDIDATE_STRATEGIES = (
    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
    routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
    routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
    routing_enums_pb2.FirstSolutionStrategy.CHRISTOFIDES,
)


class RoutingError(Exception):
    pass


@dataclass
class RouteStop:
    """Una parada, en el orden sugerido."""

    work_order_id: uuid.UUID
    code: str | None
    longitude: float
    latitude: float
    #: Metros desde la parada anterior (o desde el punto de partida, si lo hay).
    leg_distance_m: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": str(self.work_order_id),
            "code": self.code,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "leg_distance_m": round(self.leg_distance_m),
        }


@dataclass
class RouteSuggestion:
    stops: list[RouteStop]
    total_distance_m: float
    #: La distancia del orden en que llegaron las OT: el punto de comparación del criterio de
    #: aceptación, no una decoración.
    naive_distance_m: float
    start: tuple[float, float] | None
    caveats: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "stops": [stop.as_dict() for stop in self.stops],
            "total_distance_m": round(self.total_distance_m),
            "naive_distance_m": round(self.naive_distance_m),
            "start": (
                {"longitude": self.start[0], "latitude": self.start[1]}
                if self.start is not None
                else None
            ),
            "caveats": self.caveats,
        }


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distancia geodésica entre dos puntos (lon, lat) en grados, en metros."""
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(min(1.0, h)))


def _path_distance_m(points: list[tuple[float, float]]) -> float:
    return sum(_haversine_m(points[i], points[i + 1]) for i in range(len(points) - 1))


def device_position(session: Session, unit: BusinessUnit, device_key: str) -> tuple[float, float]:
    """El último punto reportado por un dispositivo (RF-020), como (longitud, latitud).

    :raises RoutingError: si el dispositivo no existe en la unidad o nunca reportó posición.
    """
    row = session.execute(
        select(ST_X(DevicePosition.location), ST_Y(DevicePosition.location))
        .join(Device, Device.id == DevicePosition.device_id)
        .where(Device.device_key == device_key, Device.business_unit_id == unit.id)
    ).first()
    if row is None or row[0] is None:
        raise RoutingError(
            f"el dispositivo «{device_key}» no tiene una posición reportada en esta unidad"
        )
    return float(row[0]), float(row[1])


def suggest_route(
    session: Session,
    unit: BusinessUnit,
    order_ids: list[uuid.UUID],
    *,
    start: tuple[float, float] | None = None,
    principal: Principal | None = None,
) -> RouteSuggestion:
    """Sugerir el orden de visita que menos distancia recta suma (RF-025).

    :param start: (longitud, latitud) desde donde empieza la cuadrilla. Si no se da, el problema es
        de inicio y fin libres.
    :param principal: quien pide la ruta. Una OT fuera de su ámbito (RF-002) cuenta como una que
        no existe: la ruta lleva sus coordenadas, y una ruta no es una vía para leerlas.
    :raises RoutingError: menos de dos OT, más del máximo, alguna fuera de la unidad (ADR-009) o
        del ámbito, o alguna sin ubicación registrada.
    """
    if len(order_ids) < MIN_STOPS:
        raise RoutingError("una ruta necesita al menos dos OT")
    if len(order_ids) > MAX_STOPS:
        raise RoutingError(f"como mucho {MAX_STOPS} OT por ruta sugerida")

    statement = select(
        WorkOrder.id, WorkOrder.code, ST_X(WorkOrder.location), ST_Y(WorkOrder.location)
    ).where(WorkOrder.business_unit_id == unit.id, WorkOrder.id.in_(order_ids))
    scope = work_order_scope(principal) if principal is not None else None
    if scope is not None:
        statement = statement.where(scope)
    rows = session.execute(statement).all()
    found = {row[0]: row for row in rows}
    missing = [str(oid) for oid in order_ids if oid not in found]
    if missing:
        raise RoutingError(f"estas OT no existen en la unidad de negocio: {', '.join(missing)}")
    unlocated = [str(oid) for oid in order_ids if found[oid][2] is None or found[oid][3] is None]
    if unlocated:
        raise RoutingError(
            f"estas OT no tienen ubicación registrada, así que no se pueden ordenar: "
            f"{', '.join(unlocated)}"
        )

    # El orden de entrada es el punto de comparación del criterio de aceptación: la distancia que
    # un planificador habría recorrido sin pedir la sugerencia. El tramo desde el punto de partida
    # cuenta igual que cualquier otro: omitirlo le regalaría metros a la comparación.
    ordered = [found[oid] for oid in order_ids]
    points = [(float(row[2]), float(row[3])) for row in ordered]
    naive_distance = _path_distance_m(([start] if start is not None else []) + points)

    sequence = _solve(points, start=start)
    stops: list[RouteStop] = []
    previous = start
    for index in sequence:
        row = ordered[index]
        lon, lat = points[index]
        leg = _haversine_m(previous, (lon, lat)) if previous is not None else 0.0
        stops.append(
            RouteStop(
                work_order_id=row[0], code=row[1], longitude=lon, latitude=lat, leg_distance_m=leg
            )
        )
        previous = (lon, lat)

    return RouteSuggestion(
        stops=stops,
        total_distance_m=sum(stop.leg_distance_m for stop in stops),
        naive_distance_m=naive_distance,
        start=start,
        caveats=[
            "La distancia es en línea recta, no por la red vial: sirve para ordenar la visita, no "
            "para prometer minutos de manejo."
        ],
    )


def _solve(points: list[tuple[float, float]], *, start: tuple[float, float] | None) -> list[int]:
    """El truco del nodo fantasma, resuelto varias veces y quedándose con la mejor (ver arriba).

    Nodos: `[start?] + points + [fantasma]`. El fantasma está a distancia cero de todos, así que
    cerrar el ciclo por él —desde cualquier parada real— no cuesta nada: el vehículo lo inserta
    justo antes de volver al depósito, y esa vuelta también sale gratis porque el fantasma también
    está a distancia cero del depósito. Por eso un único depósito basta para las dos formas del
    problema: con `start`, el depósito es el punto de partida real y el resto del ciclo —incluida
    la vuelta— es gratis; sin `start`, el depósito es el propio fantasma, y tanto el primer como el
    último tramo real quedan libres.
    """
    n = len(points)
    has_start = start is not None
    #: Índice del nodo fantasma: el último de la lista.
    ghost = n + (1 if has_start else 0)
    #: Índice del depósito: el punto de partida real si lo hay, o el propio fantasma si no.
    depot = 0 if has_start else ghost

    def node_point(index: int) -> tuple[float, float] | None:
        if index == ghost:
            return None
        if has_start and index == 0:
            return start
        offset = index - (1 if has_start else 0)
        return points[offset]

    total_nodes = ghost + 1

    def attempt(strategy: int) -> list[int] | None:
        manager = pywrapcp.RoutingIndexManager(total_nodes, 1, depot)
        model = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            a, b = node_point(from_node), node_point(to_node)
            if a is None or b is None:
                return 0
            return round(_haversine_m(a, b))

        transit_index = model.RegisterTransitCallback(distance_callback)
        model.SetArcCostEvaluatorOfAllVehicles(transit_index)

        parameters = pywrapcp.DefaultRoutingSearchParameters()
        parameters.first_solution_strategy = strategy
        parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        parameters.time_limit.FromSeconds(SOLVER_TIME_LIMIT_S)

        solution = model.SolveWithParameters(parameters)
        if solution is None:
            return None

        order: list[int] = []
        index = model.Start(0)
        while not model.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != depot and node != ghost:
                order.append(node - (1 if has_start else 0))
            index = solution.Value(model.NextVar(index))
        return order

    best: list[int] | None = None
    best_cost = math.inf
    for strategy in _CANDIDATE_STRATEGIES:
        order = attempt(strategy)
        if order is None:
            continue
        # La distancia real, no lo que cada solucionador cree haber logrado: son estrategias
        # distintas con contabilidades internas distintas, y solo la geodésica de verdad es
        # comparable entre ellas.
        legs: list[tuple[float, float]] = ([start] if start is not None else []) + [
            points[i] for i in order
        ]
        cost = _path_distance_m(legs)
        if cost < best_cost:
            best, best_cost = order, cost

    if best is None:
        # No debería pasar para un problema de este tamaño y este tipo, pero un solucionador que
        # no encuentra nada no puede devolver silenciosamente el orden de entrada: eso simularía
        # una sugerencia que nunca se calculó.
        raise RoutingError("no se pudo calcular una ruta para este conjunto de OT")
    return best
