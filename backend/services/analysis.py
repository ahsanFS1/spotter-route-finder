"""Trip analysis: routes -> checkpoints -> weather at ETA -> risk -> recommendation."""
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from domain.geo import LatLng, cumulative_miles, point_at_mile, slice_polyline, thin_polyline
from domain.models import Checkpoint, RiskLevel
from domain.ranking import rank_routes
from domain.rules import classify
from domain.sampling import sample_route, seconds_at_mile
from domain.scoring import summarize_route
from services.routing.alternatives import build_routes
from services.weather.open_meteo import MAX_FORECAST_DAYS, weather_at

MAX_CHECKPOINTS_PER_ROUTE = 150  # keeps one trip within the free weather API's per-minute allowance
GEOMETRY_GAP_MI = 0.2


class TripError(ValueError):
    """The request cannot be analyzed as asked (surfaces as a 400)."""


@dataclass
class TripRequest:
    origin: LatLng
    destination: LatLng
    departure: datetime  # timezone-aware
    load_lb: float
    interval_mi: int


def forecast_days_needed(now: datetime, end: datetime) -> int:
    start_of_today = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, math.ceil((end.astimezone(timezone.utc) - start_of_today).total_seconds() / 86400))


def analyze_trip(trip: TripRequest, routing, weather, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    routes, warnings = build_routes(routing, trip.origin, trip.destination)
    if not routes:
        raise TripError(warnings[0])

    prepared = []
    for label, option in routes:
        points = thin_polyline(option.points, GEOMETRY_GAP_MI)
        samples, total = sample_route(points, trip.interval_mi)
        if len(samples) > MAX_CHECKPOINTS_PER_ROUTE:
            raise TripError(
                f"A {trip.interval_mi}-mile interval gives {len(samples)} checkpoints on a {total:.0f}-mile "
                f"route (limit {MAX_CHECKPOINTS_PER_ROUTE}). Choose a larger interval."
            )
        prepared.append((label, option, points, samples, total))

    longest_s = max(opt.duration_s for _, opt, *_ in prepared)
    days = forecast_days_needed(now, trip.departure + timedelta(seconds=longest_s))
    if days > MAX_FORECAST_DAYS:
        warnings.append("Part of this trip is beyond the forecast horizon; those checkpoints are unscored.")
    series = weather.fetch(
        list({(s.lat, s.lng) for *_, samples, _ in prepared for s in samples}), days
    )

    results, metrics = [], {}
    for index, (label, option, points, samples, total) in enumerate(prepared):
        route_id = f"route-{index + 1}"
        checkpoints = []
        for s in samples:
            eta_s = seconds_at_mile(option.profile, s.mile)
            eta = trip.departure + timedelta(seconds=eta_s)
            wx = weather_at(series.get((s.lat, s.lng)), eta)
            levels = classify(wx, trip.load_lb) if wx else None
            checkpoints.append(Checkpoint(s.lat, s.lng, s.mile, s.owned_miles, eta_s, wx, levels))
        m = summarize_route(checkpoints, option.distance_mi, option.duration_s)
        metrics[route_id] = m
        if m.unscored_miles > 0:
            warnings.append(f"{label}: {m.unscored_miles:.0f} mi have no forecast and are not scored.")
        results.append(_route_payload(route_id, label, option, points, checkpoints, m, trip.departure))

    rec = rank_routes(metrics)
    order = {rid: i for i, rid in enumerate(rec.ordered_ids)}
    for r in results:
        r["rank"] = order[r["id"]] + 1
        r["recommended"] = r["id"] == rec.recommended_id
    return {
        "routes": results,
        "recommended_route_id": rec.recommended_id,
        "reason": rec.reason,
        "warnings": list(dict.fromkeys(warnings)),
        "departure": trip.departure.astimezone(timezone.utc).isoformat(),
        "load_lb": trip.load_lb,
        "interval_mi": trip.interval_mi,
    }


def _midpoint(points, cumulative) -> list[float]:
    lat, lng = point_at_mile(points, cumulative, cumulative[-1] / 2)
    return [lng, lat]


def _route_payload(route_id, label, option, points, checkpoints, m, departure) -> dict:
    cumulative = cumulative_miles(points)
    segments = []
    for cp, nxt in zip(checkpoints, checkpoints[1:]):
        line = slice_polyline(points, cumulative, cp.mile, nxt.mile)
        segments.append({"level": int(cp.level) if cp.level is not None else None,
                         "coordinates": [[lng, lat] for lat, lng in line]})
    return {
        "id": route_id,
        "label": label,
        "distance_mi": round(option.distance_mi, 1),
        "duration_s": round(option.duration_s),
        "arrival": (departure + timedelta(seconds=option.duration_s)).astimezone(timezone.utc).isoformat(),
        "label_at": _midpoint(points, cumulative),
        "start": [points[0][1], points[0][0]],
        "end": [points[-1][1], points[-1][0]],
        "bounds": [
            min(p[1] for p in points), min(p[0] for p in points),
            max(p[1] for p in points), max(p[0] for p in points),
        ],
        "segments": segments,
        "metrics": {
            "miles_by_level": {lvl.name.lower(): round(m.miles_by_level[lvl], 1) for lvl in RiskLevel},
            "scored_miles": round(m.scored_miles, 1),
            "unscored_miles": round(m.unscored_miles, 1),
            "avg_risk": round(m.avg_risk, 2),
            "max_level": int(m.max_level) if m.max_level is not None else None,
            "has_no_travel": m.has_no_travel,
        },
        "checkpoints": [
            {
                "lat": cp.lat, "lng": cp.lng, "mile": round(cp.mile, 1),
                "eta": (departure + timedelta(seconds=cp.eta_s)).astimezone(timezone.utc).isoformat(),
                "level": int(cp.level) if cp.level is not None else None,
                "weather": None if cp.weather is None else {
                    "wind_mph": round(cp.weather.wind_mph, 1),
                    "rain_in_hr": round(cp.weather.rain_in_hr, 2),
                    "snow_in_hr": round(cp.weather.snow_in_hr, 2),
                },
                "levels": None if cp.levels is None else {
                    "wind": int(cp.levels.wind), "rain": int(cp.levels.rain), "snow": int(cp.levels.snow),
                },
            }
            for cp in checkpoints
        ],
    }
