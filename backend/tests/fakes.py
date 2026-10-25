"""In-memory providers so service and API tests never touch the network."""
from datetime import datetime, timedelta, timezone

from domain.geo import cumulative_miles, destination_point
from domain.models import Weather
from services.routing.base import RouteOption


def straight_route(origin, dest, bulge_mi: float = 0.0, steps: int = 60, mph: float = 60.0) -> RouteOption:
    """A route from origin to dest; `bulge_mi` bends it sideways so routes differ."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        lat = origin[0] + (dest[0] - origin[0]) * t
        lng = origin[1] + (dest[1] - origin[1]) * t
        if bulge_mi:
            lat, lng = destination_point((lat, lng), 0, bulge_mi * 4 * t * (1 - t))
        pts.append((lat, lng))
    miles = cumulative_miles(pts)
    profile = [(m, m / mph * 3600) for m in miles]
    return RouteOption(points=pts, distance_mi=miles[-1], duration_s=profile[-1][1], profile=profile)


class FakeRouting:
    """Returns `alternatives` routes for a direct request, and one route per via request."""

    def __init__(self, alternatives: int = 3):
        self.alternatives = alternatives
        self.calls = []

    def route(self, waypoints, alternatives=False):
        self.calls.append((list(waypoints), alternatives))
        origin, dest = waypoints[0], waypoints[-1]
        if len(waypoints) == 3:  # via-point request
            via = waypoints[1]
            mid = ((origin[0] + dest[0]) / 2, (origin[1] + dest[1]) / 2)
            side = 1 if via[0] > mid[0] else -1
            return [straight_route(origin, dest, bulge_mi=side * 40, mph=58)]
        if not alternatives:
            return [straight_route(origin, dest)]
        return [straight_route(origin, dest, bulge_mi=b, mph=60 - i * 2) for i, b in zip(range(self.alternatives), (0, 35, -35))]


# Fixed so tests do not depend on today's date; matches NOW in test_analysis.
FORECAST_START = datetime(2026, 10, 23, tzinfo=timezone.utc)


class FakeWeather:
    """Constant weather, optionally varying by point and with an end to the forecast."""

    def __init__(self, weather=None, by_point=None, until: datetime | None = None):
        self.weather = weather or Weather(10, 0, 0)
        self.by_point = by_point or (lambda point: self.weather)
        self.until = until
        self.requests = []

    def fetch(self, points, forecast_days):
        self.requests.append((len(points), forecast_days))
        start = FORECAST_START
        out = {}
        for p in points:
            series = {}
            for h in range(forecast_days * 24):
                hour = start + timedelta(hours=h)
                if self.until and hour > self.until:
                    break
                series[hour] = self.by_point(p)
            out[p] = series
        return out
