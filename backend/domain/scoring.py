"""Route-level metrics computed from scored checkpoints."""
from .models import Checkpoint, RiskLevel, RouteMetrics


def summarize_route(checkpoints: list[Checkpoint], distance_mi: float, duration_s: float) -> RouteMetrics:
    miles_by_level = {level: 0.0 for level in RiskLevel}
    scored = 0.0
    unscored = 0.0
    weighted = 0.0
    max_level: RiskLevel | None = None
    has_no_travel = False
    for cp in checkpoints:
        level = cp.level
        if level is None:
            unscored += cp.owned_miles
            continue
        miles_by_level[level] += cp.owned_miles
        scored += cp.owned_miles
        weighted += int(level) * cp.owned_miles
        max_level = level if max_level is None else max(max_level, level)
        has_no_travel = has_no_travel or level == RiskLevel.NO_TRAVEL
    return RouteMetrics(
        miles_by_level=miles_by_level,
        scored_miles=scored,
        unscored_miles=unscored,
        avg_risk=weighted / scored if scored else 0.0,
        max_level=max_level,
        has_no_travel=has_no_travel,
        distance_mi=distance_mi,
        duration_s=duration_s,
    )
