from datetime import datetime, timedelta, timezone

import pytest

from domain.models import Weather
from services.analysis import TripError, TripRequest, analyze_trip
from services.heatmap import HOURS, MAX_POINTS, build_heatmap, corridor_points
from services.routing.alternatives import build_routes

from .fakes import FakeRouting, FakeWeather, straight_route

CHICAGO = (41.88, -87.63)
DALLAS = (32.78, -96.80)  # ~800 mi
NOW = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
DEPART = NOW + timedelta(hours=3)


def trip(load=20_000, interval=50, dest=DALLAS):
    return TripRequest(CHICAGO, dest, DEPART, load, interval)


def test_three_alternatives_need_no_via_requests():
    routing = FakeRouting(alternatives=3)
    routes, warnings = build_routes(routing, CHICAGO, DALLAS)
    assert [label for label, _ in routes] == ["Fastest", "Alternative 1", "Alternative 2"]
    assert warnings == [] and len(routing.calls) == 1


def test_missing_alternatives_are_filled_with_via_routes():
    routing = FakeRouting(alternatives=1)
    routes, warnings = build_routes(routing, CHICAGO, DALLAS)
    assert len(routes) == 3 and warnings == []
    assert any(len(w) == 3 for w, _ in routing.calls)
    durations = [r.duration_s for _, r in routes]
    assert durations == sorted(durations)


def test_identical_routes_are_not_counted_twice():
    class Same(FakeRouting):
        def route(self, waypoints, alternatives=False):
            return [straight_route(waypoints[0], waypoints[-1])] * 2

    routes, warnings = build_routes(Same(), CHICAGO, DALLAS)
    assert len(routes) == 1 and "1 distinct" in warnings[0]


def test_no_route_found():
    class Empty(FakeRouting):
        def route(self, *a, **k):
            return []

    routes, warnings = build_routes(Empty(), CHICAGO, DALLAS)
    assert routes == [] and warnings


def test_analysis_structure_and_checkpoints():
    result = analyze_trip(trip(), FakeRouting(), FakeWeather(), now=NOW)
    assert len(result["routes"]) == 3
    route = result["routes"][0]
    cps = route["checkpoints"]
    assert cps[0]["mile"] == 0 and cps[-1]["mile"] == pytest.approx(route["distance_mi"], rel=0.02)
    assert all(b["mile"] - a["mile"] <= 50.01 for a, b in zip(cps, cps[1:]))
    etas = [datetime.fromisoformat(c["eta"]) for c in cps]
    assert etas == sorted(etas) and etas[0] == DEPART
    assert sum(route["metrics"]["miles_by_level"].values()) == pytest.approx(route["metrics"]["scored_miles"], abs=0.5)
    assert len(route["segments"]) == len(cps) - 1


def test_checkpoint_weather_is_looked_up_at_the_eta_hour():
    # severe wind only from 18:00 UTC onwards; a later checkpoint ETA must pick it up
    storm_from = datetime(2026, 10, 23, 18, tzinfo=timezone.utc)

    class Timed(FakeWeather):
        def fetch(self, points, forecast_days):
            base = super().fetch(points, forecast_days)
            for series in base.values():
                for hour in series:
                    if hour >= storm_from:
                        series[hour] = Weather(48, 0, 0)
            return base

    result = analyze_trip(trip(), FakeRouting(), Timed(), now=NOW)
    cps = result["routes"][0]["checkpoints"]
    for cp in cps:
        eta = datetime.fromisoformat(cp["eta"])
        stormy = eta.replace(minute=0) + timedelta(hours=1 if eta.minute >= 30 else 0) >= storm_from
        assert cp["level"] == (3 if stormy else 0)
    assert {c["level"] for c in cps} == {0, 3}


def test_heavy_load_raises_wind_risk():
    wind = FakeWeather(Weather(40, 0, 0))
    light = analyze_trip(trip(load=20_000), FakeRouting(), wind, now=NOW)["routes"][0]["metrics"]
    heavy = analyze_trip(trip(load=45_000), FakeRouting(), wind, now=NOW)["routes"][0]["metrics"]
    assert light["max_level"] == 2 and heavy["max_level"] == 3


def test_recommends_the_route_that_avoids_the_storm():
    # the northern bulge (alt 1) is in a storm; the fastest and southern routes are clear
    def by_point(p):
        line_lat = CHICAGO[0] + (DALLAS[0] - CHICAGO[0]) * (p[1] - CHICAGO[1]) / (DALLAS[1] - CHICAGO[1])
        return Weather(48, 0, 0) if p[0] - line_lat > 0.3 else Weather(5, 0, 0)  # north of the corridor

    result = analyze_trip(trip(interval=25), FakeRouting(), FakeWeather(by_point=by_point), now=NOW)
    rec = next(r for r in result["routes"] if r["recommended"])
    assert rec["metrics"]["miles_by_level"]["severe"] == 0
    assert result["recommended_route_id"] == rec["id"]
    assert [r["rank"] for r in result["routes"] if r["id"] == rec["id"]] == [1]


def test_no_travel_everywhere_means_no_recommendation():
    result = analyze_trip(trip(), FakeRouting(), FakeWeather(Weather(60, 0, 0)), now=NOW)
    assert result["recommended_route_id"] is None
    assert "do not depart" in result["reason"].lower()
    assert all(r["metrics"]["has_no_travel"] for r in result["routes"])


def test_checkpoints_past_the_forecast_are_unscored_and_reported():
    result = analyze_trip(trip(), FakeRouting(), FakeWeather(until=DEPART + timedelta(hours=3)), now=NOW)
    metrics = result["routes"][0]["metrics"]
    assert metrics["unscored_miles"] > 0
    assert any(cp["level"] is None for cp in result["routes"][0]["checkpoints"])
    assert any("no forecast" in w for w in result["warnings"])


def test_too_many_checkpoints_is_a_clear_error():
    far = (47.6, -122.3)  # Seattle, ~1,700 mi; 10-mile interval -> 170 only, so use a huge pair
    asia_scale = (-33.9, 151.2)
    with pytest.raises(TripError, match="Choose a larger interval"):
        analyze_trip(TripRequest(far, asia_scale, DEPART, 1000, 10), FakeRouting(), FakeWeather(), now=NOW)


def test_weather_is_requested_once_for_all_routes():
    weather = FakeWeather()
    analyze_trip(trip(), FakeRouting(), weather, now=NOW)
    assert len(weather.requests) == 1


def test_heatmap_shape_and_levels():
    routes = [straight_route(CHICAGO, DALLAS).points]
    weather = FakeWeather(Weather(40, 0, 0))
    data = build_heatmap(routes, DEPART, 45_000, weather, now=NOW)
    assert len(data["hours"]) == HOURS == 49
    assert len(data["points"]) == len(data["levels"]) <= MAX_POINTS
    assert all(len(row) == HOURS for row in data["levels"])
    assert {lvl for row in data["levels"] for lvl in row} == {3}  # wind 40 mph + heavy load


def test_heatmap_matches_checkpoint_scoring_for_the_same_hour():
    route = straight_route(CHICAGO, DALLAS)
    weather = FakeWeather(Weather(40, 0, 0))
    heat = build_heatmap([route.points], DEPART, 20_000, weather, now=NOW)
    result = analyze_trip(trip(load=20_000), FakeRouting(), weather, now=NOW)
    assert {lvl for row in heat["levels"] for lvl in row} == {c["level"] for c in result["routes"][0]["checkpoints"]} == {2}


def test_heatmap_marks_hours_without_forecast():
    weather = FakeWeather(until=DEPART + timedelta(hours=5))
    data = build_heatmap([straight_route(CHICAGO, DALLAS).points], DEPART, 0, weather, now=NOW)
    assert data["levels"][0][0] >= 0 and data["levels"][0][-1] == -1


def test_corridor_is_capped_and_deduped():
    long_route = straight_route((47.0, -122.0), (25.8, -80.2), steps=200).points
    pts = corridor_points([long_route])
    assert len(pts) <= MAX_POINTS
    assert len(set((round(a * 5), round(b * 5)) for a, b in pts)) == len(pts)


def test_routes_that_double_back_are_rejected():
    from domain.geo import destination_point
    from services.routing.base import RouteOption

    straight = straight_route(CHICAGO, DALLAS)
    # out along the line, up a 30-mile spur, back down the same spur, then on to the end
    pts = straight.points
    half = len(pts) // 2
    spur = [destination_point(pts[half], 0, d) for d in range(1, 31)]
    spiky_pts = pts[: half + 1] + spur + spur[::-1] + pts[half + 1 :]
    spiky = RouteOption(spiky_pts, straight.distance_mi + 60, straight.duration_s + 4000, [(0, 0), (straight.distance_mi + 60, straight.duration_s + 4000)])

    class Spiky(FakeRouting):
        def route(self, waypoints, alternatives=False):
            return [straight, spiky] if alternatives else [straight_route(waypoints[0], waypoints[-1])]

    routes, _ = build_routes(Spiky(), CHICAGO, DALLAS)
    assert spiky not in [r for _, r in routes]
