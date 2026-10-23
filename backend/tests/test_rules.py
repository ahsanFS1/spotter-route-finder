import pytest

from domain.models import RiskLevel as L, Weather
from domain.rules import apply_load_rules, classify, rain_level, snow_level, wind_level


@pytest.mark.parametrize("mph,expected", [
    (0, L.LOW), (24.9, L.LOW), (25, L.MODERATE), (34.9, L.MODERATE),
    (35, L.HIGH), (44.9, L.HIGH), (45, L.SEVERE), (54.9, L.SEVERE),
    (55, L.NO_TRAVEL), (80, L.NO_TRAVEL),
])
def test_wind_bands(mph, expected):
    assert wind_level(mph) == expected


@pytest.mark.parametrize("v,expected", [
    (0, L.LOW), (0.099, L.LOW), (0.10, L.MODERATE), (0.249, L.MODERATE),
    (0.25, L.HIGH), (0.499, L.HIGH), (0.50, L.SEVERE), (1.00, L.SEVERE),
    (1.001, L.NO_TRAVEL),
])
def test_rain_bands(v, expected):
    assert rain_level(v) == expected


@pytest.mark.parametrize("v,expected", [
    (0, L.LOW), (0.49, L.LOW), (0.5, L.MODERATE), (0.99, L.MODERATE),
    (1.0, L.HIGH), (1.99, L.HIGH), (2.0, L.SEVERE), (3.0, L.SEVERE),
    (3.01, L.NO_TRAVEL),
])
def test_snow_bands(v, expected):
    assert snow_level(v) == expected


@pytest.mark.parametrize("wind,load,base,expected", [
    (55, 0, L.NO_TRAVEL, L.NO_TRAVEL),
    (60, 1_000, L.NO_TRAVEL, L.NO_TRAVEL),
    (45, 30_000, L.SEVERE, L.SEVERE),        # exactly 30,000 lb is not "over"
    (45, 30_001, L.SEVERE, L.NO_TRAVEL),
    (54.9, 50_000, L.SEVERE, L.NO_TRAVEL),
    (44.9, 30_001, L.HIGH, L.HIGH),          # 30k rule only applies from 45 mph
    (35, 40_000, L.HIGH, L.HIGH),            # exactly 40,000 lb is not "over"
    (35, 40_001, L.HIGH, L.SEVERE),
    (44.9, 80_000, L.HIGH, L.SEVERE),
    (34.9, 80_000, L.MODERATE, L.MODERATE),
])
def test_load_rules(wind, load, base, expected):
    assert apply_load_rules(wind, load, base) == expected


def test_load_rule_never_lowers_level():
    assert apply_load_rules(40, 50_000, L.NO_TRAVEL) == L.NO_TRAVEL


def test_overall_is_worst_of_conditions():
    levels = classify(Weather(wind_mph=10, rain_in_hr=0.3, snow_in_hr=2.5), load_lb=10_000)
    assert (levels.wind, levels.rain, levels.snow) == (L.LOW, L.HIGH, L.SEVERE)
    assert levels.overall == L.SEVERE


def test_heavy_load_wind_drives_overall():
    levels = classify(Weather(wind_mph=40, rain_in_hr=0.0, snow_in_hr=0.0), load_lb=45_000)
    assert levels.wind == L.SEVERE and levels.overall == L.SEVERE
    light = classify(Weather(wind_mph=40, rain_in_hr=0.0, snow_in_hr=0.0), load_lb=20_000)
    assert light.overall == L.HIGH
