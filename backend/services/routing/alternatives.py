"""Build up to three distinct routes. OSRM often returns fewer than three, so
perpendicular via-points are the normal way to fill the remainder."""
from concurrent.futures import ThreadPoolExecutor

from domain.geo import LatLng, bearing_deg, destination_point, haversine_mi, point_at_mile, cumulative_miles

from .base import RouteOption, RoutingProvider

MAX_DISTANCE_RATIO = 1.5
MAX_OVERLAP = 0.9
VIA_OFFSET_FRACTIONS = (0.12, 0.25)
LABELS = ("Fastest", "Alternative 1", "Alternative 2")


def _cells(route: RouteOption, step_mi: float = 0.5) -> set[tuple[int, int]]:
    cumulative = cumulative_miles(route.points)
    total = cumulative[-1]
    count = max(2, int(total / step_mi))
    cells = set()
    for i in range(count + 1):
        lat, lng = point_at_mile(route.points, cumulative, total * i / count)
        cells.add((round(lat * 100), round(lng * 100)))  # ~0.7 mile cells
    return cells


def _overlap(a: set, b: set) -> float:
    return len(a & b) / max(1, min(len(a), len(b)))


def _via_points(origin: LatLng, dest: LatLng, fraction: float) -> list[LatLng]:
    mid = ((origin[0] + dest[0]) / 2, (origin[1] + dest[1]) / 2)
    offset = haversine_mi(origin, dest) * fraction
    heading = bearing_deg(origin, dest)
    return [destination_point(mid, (heading + 90) % 360, offset), destination_point(mid, (heading - 90) % 360, offset)]


def build_routes(provider: RoutingProvider, origin: LatLng, dest: LatLng, want: int = 3):
    """Returns (labelled routes sorted fastest first, warnings)."""
    warnings: list[str] = []
    candidates = list(provider.route([origin, dest], alternatives=True))
    if not candidates:
        return [], ["No drivable route was found between these locations."]

    for fraction in VIA_OFFSET_FRACTIONS:
        if len(_dedupe(candidates, candidates[0].distance_mi * MAX_DISTANCE_RATIO)) >= want:
            break
        vias = _via_points(origin, dest, fraction)
        with ThreadPoolExecutor(max_workers=len(vias)) as pool:
            results = list(pool.map(lambda v: _safe_route(provider, [origin, v, dest]), vias))
        for found in results:
            candidates.extend(found)

    fastest = min(c.duration_s for c in candidates)
    base = next(c for c in candidates if c.duration_s == fastest)
    kept = _dedupe(sorted(candidates, key=lambda c: c.duration_s), base.distance_mi * MAX_DISTANCE_RATIO)[:want]
    if len(kept) < want:
        warnings.append(f"Only {len(kept)} distinct route(s) could be found for this trip.")
    return list(zip(LABELS, kept)), warnings


def _safe_route(provider, waypoints):
    try:
        return provider.route(waypoints, alternatives=False)
    except Exception:  # a failed detour attempt is not fatal
        return []


def _dedupe(routes: list[RouteOption], max_distance_mi: float) -> list[RouteOption]:
    kept: list[RouteOption] = []
    kept_cells: list[set] = []
    for route in sorted(routes, key=lambda r: r.duration_s):
        if route.distance_mi > max_distance_mi:
            continue
        cells = _cells(route)
        if any(_overlap(cells, other) > MAX_OVERLAP for other in kept_cells):
            continue
        kept.append(route)
        kept_cells.append(cells)
    return kept
