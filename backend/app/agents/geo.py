"""Distance between two coordinates, for the coherence node.

The haversine formula rather than PostGIS, because the node is pure: a rule that needed a database
round trip could not be tested against a hundred synthetic captures, and the accuracy a great-circle
distance loses at neighbourhood scale is metres — far below the threshold a rule of this kind should
ever use.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

#: Mean Earth radius in metres.
EARTH_RADIUS_M = 6_371_008.8


def distance_m(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    """Great-circle distance in metres."""
    lat1, lon1, lat2, lon2 = map(
        radians, (first_latitude, first_longitude, second_latitude, second_longitude)
    )
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    inner = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(min(inner, 1.0)))


def format_distance(metres: float) -> str:
    """A distance as somebody in Ecuador reads it (rule 11).

    Python's `:,.0f` writes `6,480 m`, which in es-EC reads as six point four eight metres — the
    separators are the other way round. So there is no grouping at all below a kilometre, and above
    it the value becomes kilometres with a **comma** decimal, which is both correct and easier to
    judge: "6,5 km from the asset" lands immediately in a way "6480 m" does not.
    """
    if metres < 1_000:
        return f"{metres:.0f} m"
    return f"{metres / 1_000:.1f}".replace(".", ",") + " km"
