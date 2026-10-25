from datetime import datetime, timezone

import pytest

from domain.models import Weather
from services.geocoding.photon import PhotonGeocoder
from services.routing.osrm import METERS_PER_MILE, OsrmProvider
from services.weather.open_meteo import OpenMeteoProvider, nearest_hour, weather_at


class StubSession:
    """Mimics requests.Session.get for one canned JSON payload."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        payload = self.payload

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return payload

        return Resp()


def hourly(n=3, wind=10.0, rain=0.0, showers=0.0, snow=0.0):
    return {
        "time": [f"2026-10-24T{h:02d}:00" for h in range(n)],
        "wind_speed_10m": [wind] * n,
        "rain": [rain] * n,
        "showers": [showers] * n,
        "snowfall": [snow] * n,
    }


class MemoryCache(dict):
    def get_many(self, keys):
        return {k: self[k] for k in keys if k in self}

    def set(self, key, value, ttl=None):
        self[key] = value


def test_open_meteo_requests_explicit_units_and_utc():
    session = StubSession({"hourly": hourly()})
    OpenMeteoProvider(session=session, cache=MemoryCache()).fetch([(41.88, -87.63)], 2)
    params = session.calls[0][1]
    assert params["wind_speed_unit"] == "mph"
    assert params["precipitation_unit"] == "inch"
    assert params["timezone"] == "UTC"


def test_open_meteo_single_location_object_and_list_are_equivalent():
    one = OpenMeteoProvider(session=StubSession({"hourly": hourly()}), cache=MemoryCache())
    many = OpenMeteoProvider(session=StubSession([{"hourly": hourly()}, {"hourly": hourly(wind=50)}]), cache=MemoryCache())
    a = one.fetch([(41.88, -87.63)], 1)
    b = many.fetch([(41.88, -87.63), (29.76, -95.37)], 1)
    assert len(a) == 1 and len(b) == 2
    hour = datetime(2026, 10, 24, 1, tzinfo=timezone.utc)
    assert weather_at(b[(29.76, -95.37)], hour).wind_mph == 50


def test_rain_is_rain_plus_showers():
    provider = OpenMeteoProvider(session=StubSession({"hourly": hourly(rain=0.1, showers=0.05)}), cache=MemoryCache())
    series = provider.fetch([(40.0, -90.0)], 1)[(40.0, -90.0)]
    assert weather_at(series, datetime(2026, 10, 24, 0, tzinfo=timezone.utc)).rain_in_hr == pytest.approx(0.15)


def test_missing_values_leave_hours_unavailable():
    bad = hourly()
    bad["wind_speed_10m"][1] = None
    provider = OpenMeteoProvider(session=StubSession({"hourly": bad}), cache=MemoryCache())
    series = provider.fetch([(40.0, -90.0)], 1)[(40.0, -90.0)]
    assert weather_at(series, datetime(2026, 10, 24, 1, tzinfo=timezone.utc)) is None
    assert weather_at(series, datetime(2026, 10, 24, 2, tzinfo=timezone.utc)) is not None


def test_results_are_cached_by_rounded_coordinates():
    session = StubSession({"hourly": hourly()})
    provider = OpenMeteoProvider(session=session, cache=MemoryCache())
    provider.fetch([(40.001, -90.002)], 1)
    provider.fetch([(40.004, -90.001)], 1)  # same 0.01 degree cell
    assert len(session.calls) == 1


def test_large_batches_are_chunked():
    session = StubSession({"hourly": hourly()})

    def get(url, params=None, timeout=None):
        n = len(params["latitude"].split(","))
        session.calls.append(n)
        payload = [{"hourly": hourly()} for _ in range(n)]
        return type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: payload})()

    session.get = get
    points = [(30 + i * 0.05, -90.0) for i in range(120)]
    OpenMeteoProvider(session=session, cache=MemoryCache()).fetch(points, 1)
    assert sorted(session.calls) == [20, 50, 50]


@pytest.mark.parametrize("minute,expected_hour", [(0, 5), (29, 5), (30, 6), (59, 6)])
def test_nearest_hour(minute, expected_hour):
    dt = datetime(2026, 10, 24, 5, minute, tzinfo=timezone.utc)
    assert nearest_hour(dt).hour == expected_hour


def test_weather_at_without_series():
    assert weather_at(None, datetime.now(timezone.utc)) is None


def encode_polyline6(points):
    out, prev_lat, prev_lng = [], 0, 0
    for lat, lng in points:
        for value, prev in ((round(lat * 1e6), prev_lat), (round(lng * 1e6), prev_lng)):
            delta = value - prev
            delta = ~(delta << 1) if delta < 0 else delta << 1
            while delta >= 0x20:
                out.append(chr((0x20 | (delta & 0x1F)) + 63))
                delta >>= 5
            out.append(chr(delta + 63))
        prev_lat, prev_lng = round(lat * 1e6), round(lng * 1e6)
    return "".join(out)


def osrm_route(distance_m=160934.0, duration=7200.0):
    return {
        "code": "Ok",
        "routes": [{
            "distance": distance_m,
            "duration": duration,
            "geometry": encode_polyline6([(40.0, -100.0), (40.0, -99.0), (40.0, -98.0)]),
            "legs": [
                {"distance": distance_m / 2, "duration": duration / 2},
                {"distance": distance_m / 2, "duration": duration / 2},
            ],
        }],
    }


def test_osrm_applies_truck_speed_factor_and_flips_coordinates():
    provider = OsrmProvider("http://x", truck_speed_factor=0.8, session=StubSession(osrm_route()))
    route = provider.route([(40.0, -100.0), (40.0, -98.0)])[0]
    assert route.points[0] == (40.0, -100.0)
    assert route.duration_s == pytest.approx(7200 / 0.8)
    assert route.distance_mi == pytest.approx(160934 / METERS_PER_MILE)
    assert route.profile[-1][1] == pytest.approx(7200 / 0.8)
    assert route.profile[0] == (0.0, 0.0)


def test_osrm_profile_miles_follow_the_geometry():
    route = OsrmProvider("http://x", session=StubSession(osrm_route())).route([(40.0, -100.0), (40.0, -98.0)])[0]
    from domain.geo import cumulative_miles
    assert route.profile[-1][0] == pytest.approx(cumulative_miles(route.points)[-1])


def test_osrm_no_route_is_empty_and_errors_raise():
    from services.http import ProviderError
    assert OsrmProvider("http://x", session=StubSession({"code": "NoRoute"})).route([(0, 0), (1, 1)]) == []
    with pytest.raises(ProviderError):
        OsrmProvider("http://x", session=StubSession({"code": "InvalidQuery", "message": "bad"})).route([(0, 0), (1, 1)])


def test_photon_filters_countries_flips_coordinates_and_dedupes():
    feature = lambda name, cc, lon, lat, city=None: {
        "geometry": {"coordinates": [lon, lat]},
        "properties": {"name": name, "countrycode": cc, "state": "Illinois", "city": city},
    }
    payload = {"features": [
        feature("Chicago", "US", -87.63, 41.88),
        feature("Chicago", "US", -87.7, 41.9),  # duplicate label
        feature("Chicago", "FR", 2.3, 48.8),
        feature("Springfield", "US", -89.6, 39.8),
    ]}
    results = PhotonGeocoder(session=StubSession(payload)).search("chi")
    assert [r["label"] for r in results] == ["Chicago, Illinois, US", "Springfield, Illinois, US"]
    assert results[0]["lat"] == 41.88 and results[0]["lng"] == -87.63


def test_nearby_points_share_one_grid_cell_and_request():
    session = StubSession([{"hourly": hourly()}])
    provider = OpenMeteoProvider(session=session, cache=MemoryCache())
    result = provider.fetch([(40.011, -90.012), (40.024, -89.987)], 1)  # both snap to (40.0, -90.0)
    assert len(session.calls) == 1 and session.calls[0][1]["latitude"] == "40.00"
    assert result[(40.011, -90.012)] is result[(40.024, -89.987)]


def test_forecast_length_is_bucketed_for_cache_reuse():
    session = StubSession({"hourly": hourly()})
    provider = OpenMeteoProvider(session=session, cache=MemoryCache())
    provider.fetch([(40.0, -90.0)], 2)
    provider.fetch([(40.0, -90.0)], 4)
    assert len(session.calls) == 1 and session.calls[0][1]["forecast_days"] == 4


def test_provider_errors_are_user_safe(monkeypatch):
    import requests

    from services.http import ProviderError, get_json

    class Down:
        def get(self, url, params=None, timeout=None):
            raise requests.exceptions.RetryError("too many 429 error responses ... secret-url?x=1")

    with pytest.raises(ProviderError) as info:
        get_json(Down(), "https://api.open-meteo.com/v1/forecast", {})
    message = str(info.value)
    assert "weather service" in message and "busy" in message and "http" not in message


def test_open_meteo_geocoder_filters_countries_and_labels():
    from services.geocoding.open_meteo import OpenMeteoGeocoder
    payload = {"results": [
        {"name": "Chicago", "admin1": "Illinois", "country_code": "US", "latitude": 41.88, "longitude": -87.63},
        {"name": "Chicago", "admin1": "Illinois", "country_code": "US", "latitude": 41.9, "longitude": -87.7},
        {"name": "Chicago", "country_code": "FR", "latitude": 48.8, "longitude": 2.3},
    ]}
    assert OpenMeteoGeocoder(session=StubSession(payload)).search("chi") == [
        {"label": "Chicago, Illinois, US", "lat": 41.88, "lng": -87.63}
    ]
    assert OpenMeteoGeocoder(session=StubSession({})).search("zzz") == []


class _Geo:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result or [], error, 0

    def search(self, query, limit=6):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def _resilient(primary, fallback):
    from uuid import uuid4

    from django.core.cache.backends.locmem import LocMemCache
    from services.geocoding.resilient import ResilientGeocoder
    return ResilientGeocoder(primary, fallback, cache=LocMemCache(uuid4().hex, {}))  # named caches are shared


def test_geocoder_falls_back_when_primary_fails_and_caches():
    from services.http import ProviderError
    primary, fallback = _Geo(error=ProviderError("down")), _Geo([{"label": "A", "lat": 1, "lng": 2}])
    geo = _resilient(primary, fallback)
    assert geo.search("Chicago")[0]["label"] == "A"
    assert geo.search("  chicago ")[0]["label"] == "A"  # same normalised query is served from the cache
    assert primary.calls == 1 and fallback.calls == 1


def test_geocoder_raises_primary_error_when_both_fail():
    from services.http import ProviderError
    geo = _resilient(_Geo(error=ProviderError("primary down")), _Geo(error=ProviderError("fallback down")))
    with pytest.raises(ProviderError, match="primary down"):
        geo.search("Chicago")


def test_geocoder_tries_fallback_on_empty_primary_but_does_not_cache_empty():
    primary, fallback = _Geo([]), _Geo([])
    geo = _resilient(primary, fallback)
    assert geo.search("nowhere") == [] and geo.search("nowhere") == []
    assert primary.calls == 2 and fallback.calls == 2
