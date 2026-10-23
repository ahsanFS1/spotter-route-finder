from dataclasses import dataclass
from typing import Protocol

from domain.geo import LatLng


@dataclass
class RouteOption:
    points: list[LatLng]
    distance_mi: float
    duration_s: float
    # (mile along `points`, elapsed seconds) pairs, monotonic
    profile: list[tuple[float, float]]


class RoutingProvider(Protocol):
    def route(self, waypoints: list[LatLng], alternatives: bool = False) -> list[RouteOption]:
        """Routes through the ordered waypoints; empty list if none found."""
