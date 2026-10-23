"""Small geodesy helpers (spherical earth, miles)."""
import math

EARTH_RADIUS_MI = 3958.7613

LatLng = tuple[float, float]


def haversine_mi(a: LatLng, b: LatLng) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MI * math.asin(min(1.0, math.sqrt(h)))


def bearing_deg(a: LatLng, b: LatLng) -> float:
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlng = math.radians(b[1] - a[1])
    y = math.sin(dlng) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def destination_point(origin: LatLng, bearing: float, distance_mi: float) -> LatLng:
    lat1, lng1 = math.radians(origin[0]), math.radians(origin[1])
    brg = math.radians(bearing)
    d = distance_mi / EARTH_RADIUS_MI
    lat2 = math.asin(math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(brg))
    lng2 = lng1 + math.atan2(
        math.sin(brg) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), (math.degrees(lng2) + 540) % 360 - 180


def cumulative_miles(points: list[LatLng]) -> list[float]:
    out = [0.0]
    for prev, cur in zip(points, points[1:]):
        out.append(out[-1] + haversine_mi(prev, cur))
    return out


def point_at_mile(points: list[LatLng], cumulative: list[float], mile: float) -> LatLng:
    """Linear interpolation along a polyline at a distance from its start."""
    if mile <= 0:
        return points[0]
    if mile >= cumulative[-1]:
        return points[-1]
    lo, hi = 0, len(cumulative) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cumulative[mid] <= mile:
            lo = mid
        else:
            hi = mid
    span = cumulative[hi] - cumulative[lo]
    t = 0.0 if span == 0 else (mile - cumulative[lo]) / span
    return (
        points[lo][0] + (points[hi][0] - points[lo][0]) * t,
        points[lo][1] + (points[hi][1] - points[lo][1]) * t,
    )


def thin_polyline(points: list[LatLng], min_gap_mi: float) -> list[LatLng]:
    """Drop vertices closer than `min_gap_mi` to the previous kept one (keeps the end)."""
    if len(points) <= 2:
        return list(points)
    kept = [points[0]]
    for p in points[1:-1]:
        if haversine_mi(kept[-1], p) >= min_gap_mi:
            kept.append(p)
    kept.append(points[-1])
    return kept


def slice_polyline(points: list[LatLng], cumulative: list[float], start: float, end: float) -> list[LatLng]:
    """The part of a polyline between two distances from its start."""
    out = [point_at_mile(points, cumulative, start)]
    out.extend(p for p, m in zip(points, cumulative) if start < m < end)
    out.append(point_at_mile(points, cumulative, end))
    return out
