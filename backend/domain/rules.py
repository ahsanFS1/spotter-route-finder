"""Risk thresholds and load rules. The single source of truth for classification.

Bands are lower-bound inclusive and upper-bound exclusive, except the Severe rain
and snow bands, whose upper edges (1.00 in/hr, 3.0 in/hr) are inclusive; No Travel
is strictly above them.
"""
from .models import Levels, RiskLevel, Weather

WIND_NO_TRAVEL_MPH = 55.0
HEAVY_LOAD_NO_TRAVEL_WIND_MPH = 45.0
HEAVY_LOAD_NO_TRAVEL_LB = 30_000
LOAD_SEVERE_WIND_MPH = 35.0
LOAD_SEVERE_LB = 40_000

# (exclusive upper bound, level) in ascending order
_WIND_BANDS = (
    (25.0, RiskLevel.LOW),
    (35.0, RiskLevel.MODERATE),
    (45.0, RiskLevel.HIGH),
    (WIND_NO_TRAVEL_MPH, RiskLevel.SEVERE),
)
_RAIN_BANDS = (
    (0.10, RiskLevel.LOW),
    (0.25, RiskLevel.MODERATE),
    (0.50, RiskLevel.HIGH),
)
_RAIN_SEVERE_MAX = 1.00
_SNOW_BANDS = (
    (0.5, RiskLevel.LOW),
    (1.0, RiskLevel.MODERATE),
    (2.0, RiskLevel.HIGH),
)
_SNOW_SEVERE_MAX = 3.0


def _classify(value: float, bands, severe_max: float) -> RiskLevel:
    for upper, level in bands:
        if value < upper:
            return level
    return RiskLevel.SEVERE if value <= severe_max else RiskLevel.NO_TRAVEL


def wind_level(mph: float) -> RiskLevel:
    for upper, level in _WIND_BANDS:
        if mph < upper:
            return level
    return RiskLevel.NO_TRAVEL


def rain_level(in_hr: float) -> RiskLevel:
    return _classify(in_hr, _RAIN_BANDS, _RAIN_SEVERE_MAX)


def snow_level(in_hr: float) -> RiskLevel:
    return _classify(in_hr, _SNOW_BANDS, _SNOW_SEVERE_MAX)


def apply_load_rules(wind_mph: float, load_lb: float, level: RiskLevel) -> RiskLevel:
    """Load rules can only raise a level."""
    if wind_mph >= WIND_NO_TRAVEL_MPH:
        return RiskLevel.NO_TRAVEL
    if wind_mph >= HEAVY_LOAD_NO_TRAVEL_WIND_MPH and load_lb > HEAVY_LOAD_NO_TRAVEL_LB:
        return RiskLevel.NO_TRAVEL
    if wind_mph >= LOAD_SEVERE_WIND_MPH and load_lb > LOAD_SEVERE_LB:
        return max(level, RiskLevel.SEVERE)
    return level


def classify(weather: Weather, load_lb: float) -> Levels:
    wind = apply_load_rules(weather.wind_mph, load_lb, wind_level(weather.wind_mph))
    rain = rain_level(weather.rain_in_hr)
    snow = snow_level(weather.snow_in_hr)
    return Levels(wind=wind, rain=rain, snow=snow, overall=max(wind, rain, snow))
