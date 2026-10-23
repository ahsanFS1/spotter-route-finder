"""Route recommendation: fewest Severe miles, fewest High miles, lowest average
risk, then shortest time. Routes with a No Travel checkpoint rank after all others.
"""
from dataclasses import dataclass

from .models import RiskLevel, RouteMetrics

def _describe(index: int, winner, other) -> str:
    """e.g. 'Fewest Severe miles (0 vs 25)', with the winner's value first."""
    if index == 0:
        return "Avoids the No Travel conditions on the other route"
    if index == 3:
        return f"Lowest average risk ({winner:.2f} vs {other:.2f})"
    if index == 4:
        return f"Shortest travel time ({winner / 3600:.1f} h vs {other / 3600:.1f} h)"
    name = "Severe" if index == 1 else "High"
    return f"Fewest {name} miles ({winner:g} vs {other:g})"


def sort_key(m: RouteMetrics) -> tuple:
    """Rounded so near-equal values fall through to the next criterion."""
    severe_or_worse = m.miles_by_level.get(RiskLevel.SEVERE, 0.0) + m.miles_by_level.get(
        RiskLevel.NO_TRAVEL, 0.0
    )
    return (
        m.has_no_travel,
        round(severe_or_worse, 1),
        round(m.miles_by_level.get(RiskLevel.HIGH, 0.0), 1),
        round(m.avg_risk, 2),
        round(m.duration_s),
    )


@dataclass(frozen=True)
class Recommendation:
    ordered_ids: list[str]
    recommended_id: str | None
    reason: str


def rank_routes(routes: dict[str, RouteMetrics]) -> Recommendation:
    if not routes:
        return Recommendation([], None, "No routes available.")
    ordered = sorted(routes, key=lambda rid: sort_key(routes[rid]))
    best = ordered[0]
    if routes[best].has_no_travel:
        return Recommendation(ordered, None, "Every route has a No Travel segment; do not depart.")
    if len(ordered) == 1:
        return Recommendation(ordered, best, "Only one route was available.")
    runner_up = ordered[1]
    a, b = sort_key(routes[best]), sort_key(routes[runner_up])
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return Recommendation(ordered, best, f"{_describe(i, x, y)} compared with the next route.")
    return Recommendation(ordered, best, "Routes are equivalent; chose the first.")
