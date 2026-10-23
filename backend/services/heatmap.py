"""Forecast heatmap along the trip corridor: risk level per grid point per hour (0-48h)."""
import math
from datetime import datetime, timedelta, timezone

from domain.geo import LatLng, bearing_deg, cumulative_miles, destination_point, point_at_mile
from domain.models import RiskLevel
from domain.rules import classify
from services.analysis import forecast_days_needed
from services.weather.open_meteo import floor_hour

HOURS = 49
MAX_POINTS = 150
BASE_SPACING_MI = 25.0
LATERAL_OFFSET_MI = 15.0


def corridor_points(routes: list[list[LatLng]], max_points: int = MAX_POINTS) -> list[LatLng]:
    """Samples along every route plus lateral offsets, deduped on a ~0.2 degree grid."""
    spacing = BASE_SPACING_MI
    while True:
        seen: dict[tuple[int, int], LatLng] = {}
        for points in routes:
            cumulative = cumulative_miles(points)
            total = cumulative[-1]
            n = max(1, math.ceil(total / spacing))
            for i in range(n + 1):
                here = point_at_mile(points, cumulative, min(total, i * spacing))
                ahead = point_at_mile(points, cumulative, min(total, i * spacing + 1.0))
                behind = point_at_mile(points, cumulative, max(0.0, i * spacing - 1.0))
                heading = bearing_deg(behind, ahead) if behind != ahead else 0.0
                for offset_deg in (None, 90, -90):
                    p = here if offset_deg is None else destination_point(here, (heading + offset_deg) % 360, LATERAL_OFFSET_MI)
                    seen.setdefault((round(p[0] * 5), round(p[1] * 5)), p)
        if len(seen) <= max_points:
            return list(seen.values())
        spacing *= 1.25


def build_heatmap(route_points: list[list[LatLng]], departure: datetime, load_lb: float, weather,
                  now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    start = floor_hour(departure)
    hours = [start + timedelta(hours=h) for h in range(HOURS)]
    points = corridor_points(route_points)
    series = weather.fetch(points, forecast_days_needed(now, hours[-1]))
    levels = []
    for p in points:
        s = series.get(p) or {}
        row = []
        for hour in hours:
            wx = s.get(hour)
            row.append(int(classify(wx, load_lb).overall) if wx else -1)
        levels.append(row)
    return {
        "hours": [h.isoformat() for h in hours],
        "points": [[round(lat, 4), round(lng, 4)] for lat, lng in points],
        "levels": levels,
        "max_level": int(RiskLevel.NO_TRAVEL),
    }
