"""Route recommendation: fewest Severe miles, fewest High miles, lowest average
risk, then shortest time. Routes with a No Travel checkpoint rank after all others.
"""
from dataclasses import dataclass

from .models import RiskLevel, RouteMetrics

_CRITERIA = (
    "no travel segments",
    "severe miles",
    "high miles",
    "average risk",
    "travel time",
)


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
    for name, x, y in zip(_CRITERIA, a, b):
        if x != y:
            return Recommendation(ordered, best, f"Best on {name} compared with the next route.")
    return Recommendation(ordered, best, "Routes are equivalent; chose the first.")
