"""OSRM client. The public demo server only offers a car profile, so travel times
are divided by a truck speed factor instead of being presented as truck-exact.
"""
from domain.geo import cumulative_miles
from services.http import ProviderError, build_session, get_json

from .base import RouteOption

METERS_PER_MILE = 1609.344


def decode_polyline6(encoded: str) -> list[tuple[float, float]]:
    """Decode an OSRM `polyline6` string into (lat, lng) pairs."""
    points, index, lat, lng = [], 0, 0, 0
    while index < len(encoded):
        for axis in (0, 1):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if axis == 0:
                lat += delta
            else:
                lng += delta
        points.append((lat / 1e6, lng / 1e6))
    return points


class OsrmProvider:
    def __init__(self, base_url: str, truck_speed_factor: float = 0.9, session=None):
        self.base_url = base_url.rstrip("/")
        self.truck_speed_factor = truck_speed_factor
        self.session = session or build_session()

    def route(self, waypoints, alternatives=False):
        coords = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in waypoints)
        params = {
            "overview": "full",
            # polyline6 without steps keeps a coast-to-coast response around 100 KB;
            # GeoJSON with steps is ~1.2 MB and takes the public server over a minute.
            "geometries": "polyline6",
            "steps": "false",
            "alternatives": "true" if alternatives else "false",
        }
        data = get_json(self.session, f"{self.base_url}/route/v1/driving/{coords}", params, timeout=45)
        code = data.get("code")
        if code == "NoRoute":
            return []
        if code != "Ok":
            raise ProviderError(f"routing failed: {code} {data.get('message', '')}".strip())
        return [self._parse(r) for r in data.get("routes", [])]

    def _parse(self, route: dict) -> RouteOption:
        points = decode_polyline6(route["geometry"])
        geom_total = cumulative_miles(points)[-1]
        osrm_total = route["distance"] / METERS_PER_MILE
        scale = geom_total / osrm_total if osrm_total else 1.0
        factor = self.truck_speed_factor

        profile = [(0.0, 0.0)]
        meters = seconds = 0.0
        for leg in route["legs"]:  # one leg per waypoint pair; time is spread evenly within a leg
            meters += leg["distance"]
            seconds += leg["duration"] / factor
            profile.append((meters / METERS_PER_MILE * scale, seconds))
        return RouteOption(
            points=points,
            distance_mi=osrm_total,
            duration_s=route["duration"] / factor,
            profile=profile,
        )
