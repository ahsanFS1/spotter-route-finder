import pytest

from domain.geo import cumulative_miles, haversine_mi
from domain.models import Checkpoint, RiskLevel as L, RouteMetrics
from domain.ranking import rank_routes
from domain.sampling import sample_route, seconds_at_mile
from domain.scoring import summarize_route

LINE = [(40.0, -100.0), (40.0, -99.0), (40.0, -98.0), (40.0, -97.0)]  # ~159 mi


def test_haversine_known_distance():
    assert haversine_mi((0, 0), (0, 1)) == pytest.approx(69.09, abs=0.1)


@pytest.mark.parametrize("interval", [10, 25, 50])
def test_owned_miles_sum_to_route_length(interval):
    samples, total = sample_route(LINE, interval)
    assert sum(s.owned_miles for s in samples) == pytest.approx(total)
    assert total == pytest.approx(cumulative_miles(LINE)[-1])
    assert samples[0].mile == 0 and samples[-1].mile == pytest.approx(total)
    assert samples[-1].owned_miles == 0


def test_checkpoints_are_spaced_by_interval():
    samples, _ = sample_route(LINE, 25)
    gaps = [b.mile - a.mile for a, b in zip(samples, samples[1:])]
    assert all(g == pytest.approx(25) for g in gaps[:-1])
    assert 0 < gaps[-1] <= 25


def test_route_shorter_than_interval():
    short = [(40.0, -100.0), (40.0, -99.7)]  # ~15 mi
    samples, total = sample_route(short, 25)
    assert len(samples) == 2
    assert samples[0].owned_miles == pytest.approx(total)


def test_exact_multiple_does_not_duplicate_end():
    pts = [(0.0, 0.0), (0.0, 1.0)]
    total = haversine_mi(*pts)
    samples, _ = sample_route(pts, total / 2)
    assert len(samples) == 3


def test_sample_points_lie_on_route():
    samples, _ = sample_route(LINE, 50)
    assert all(s.lat == pytest.approx(40.0) for s in samples)


def test_seconds_at_mile_interpolates_and_clamps():
    profile = [(0, 0), (10, 600), (30, 1800)]
    assert seconds_at_mile(profile, 5) == 300
    assert seconds_at_mile(profile, 20) == 1200
    assert seconds_at_mile(profile, -1) == 0
    assert seconds_at_mile(profile, 99) == 1800


def _cp(level, owned):
    from domain.models import Levels
    levels = None if level is None else Levels(level, level, level, level)
    return Checkpoint(0, 0, 0, owned, 0, None, levels)


def test_summary_miles_and_average():
    cps = [_cp(L.LOW, 25), _cp(L.HIGH, 25), _cp(L.SEVERE, 50), _cp(L.LOW, 0)]
    m = summarize_route(cps, 100, 7200)
    assert m.miles_by_level[L.SEVERE] == 50 and m.miles_by_level[L.HIGH] == 25
    assert m.avg_risk == pytest.approx((0 * 25 + 2 * 25 + 3 * 50) / 100)
    assert m.max_level == L.SEVERE and not m.has_no_travel


def test_unscored_miles_excluded_from_average():
    m = summarize_route([_cp(L.HIGH, 50), _cp(None, 50)], 100, 100)
    assert m.scored_miles == 50 and m.unscored_miles == 50
    assert m.avg_risk == pytest.approx(2.0)


def test_no_travel_flag():
    m = summarize_route([_cp(L.NO_TRAVEL, 10)], 10, 10)
    assert m.has_no_travel


def metrics(severe=0.0, high=0.0, avg=0.0, dur=1000, no_travel=False):
    return RouteMetrics(
        miles_by_level={L.SEVERE: severe, L.HIGH: high, L.NO_TRAVEL: 0.0},
        avg_risk=avg, duration_s=dur, has_no_travel=no_travel,
    )


def test_fewest_severe_wins_over_everything():
    rec = rank_routes({"a": metrics(severe=10, dur=100), "b": metrics(severe=0, high=90, avg=2, dur=9000)})
    assert rec.recommended_id == "b" and "severe" in rec.reason


def test_high_miles_break_severe_tie():
    rec = rank_routes({"a": metrics(high=30), "b": metrics(high=10, dur=9999)})
    assert rec.recommended_id == "b" and "high" in rec.reason


def test_average_risk_then_duration():
    assert rank_routes({"a": metrics(avg=1.2), "b": metrics(avg=0.8, dur=9999)}).recommended_id == "b"
    rec = rank_routes({"a": metrics(avg=1.0, dur=2000), "b": metrics(avg=1.0, dur=1500)})
    assert rec.recommended_id == "b" and "time" in rec.reason


def test_rounding_lets_near_ties_fall_through():
    rec = rank_routes({"a": metrics(severe=10.01, dur=500), "b": metrics(severe=10.04, dur=900)})
    assert rec.recommended_id == "a" and "time" in rec.reason


def test_no_travel_routes_rank_last_and_all_blocked_gives_no_recommendation():
    rec = rank_routes({"a": metrics(no_travel=True), "b": metrics(severe=50)})
    assert rec.recommended_id == "b" and rec.ordered_ids == ["b", "a"]
    blocked = rank_routes({"a": metrics(no_travel=True), "b": metrics(no_travel=True)})
    assert blocked.recommended_id is None


def test_single_route():
    assert rank_routes({"a": metrics()}).recommended_id == "a"
    assert rank_routes({}).recommended_id is None
