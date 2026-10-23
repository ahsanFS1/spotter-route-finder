"""Checkpoint sampling along a route and ETA lookup."""
import bisect

from .geo import LatLng, cumulative_miles, point_at_mile
from .models import SamplePoint

SUPPORTED_INTERVALS_MI = (10, 25, 50)


def sample_route(points: list[LatLng], interval_mi: float) -> tuple[list[SamplePoint], float]:
    """Return checkpoints at the start, every `interval_mi`, and the end.

    Each checkpoint owns the miles from itself up to the next one, so the owned
    miles sum to the route length. The destination owns none.
    """
    if len(points) < 2:
        raise ValueError("a route needs at least two points")
    if interval_mi <= 0:
        raise ValueError("interval must be positive")
    cumulative = cumulative_miles(points)
    total = cumulative[-1]
    miles = [0.0]
    step = 1
    while step * interval_mi < total - 1e-6:
        miles.append(step * interval_mi)
        step += 1
    miles.append(total)
    samples = []
    for i, mile in enumerate(miles):
        lat, lng = point_at_mile(points, cumulative, mile)
        owned = miles[i + 1] - mile if i + 1 < len(miles) else 0.0
        samples.append(SamplePoint(lat=lat, lng=lng, mile=mile, owned_miles=owned))
    return samples, total


def seconds_at_mile(profile: list[tuple[float, float]], mile: float) -> float:
    """Interpolate elapsed seconds at `mile` from a monotonic (mile, seconds) profile."""
    if not profile:
        raise ValueError("empty profile")
    if mile <= profile[0][0]:
        return profile[0][1]
    if mile >= profile[-1][0]:
        return profile[-1][1]
    idx = bisect.bisect_right([p[0] for p in profile], mile)
    (m0, s0), (m1, s1) = profile[idx - 1], profile[idx]
    t = 0.0 if m1 == m0 else (mile - m0) / (m1 - m0)
    return s0 + (s1 - s0) * t
