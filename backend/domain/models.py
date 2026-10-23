"""Plain data types shared across the domain package. No framework imports."""
from dataclasses import dataclass, field
from enum import IntEnum


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


@dataclass(frozen=True)
class Weather:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True)
class Levels:
    wind: RiskLevel
    rain: RiskLevel
    snow: RiskLevel
    overall: RiskLevel


@dataclass(frozen=True)
class SamplePoint:
    lat: float
    lng: float
    mile: float
    owned_miles: float


@dataclass
class Checkpoint:
    lat: float
    lng: float
    mile: float
    owned_miles: float
    eta_s: float  # seconds after departure
    weather: Weather | None = None
    levels: Levels | None = None

    @property
    def level(self) -> RiskLevel | None:
        return self.levels.overall if self.levels else None


@dataclass
class RouteMetrics:
    miles_by_level: dict[RiskLevel, float] = field(default_factory=dict)
    scored_miles: float = 0.0
    unscored_miles: float = 0.0
    avg_risk: float = 0.0
    max_level: RiskLevel | None = None
    has_no_travel: bool = False
    distance_mi: float = 0.0
    duration_s: float = 0.0
