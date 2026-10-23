from datetime import datetime, timedelta, timezone

import pytest
from rest_framework.test import APIClient

from api import providers
from services.http import ProviderError

from .fakes import FakeRouting, FakeWeather


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(providers, "routing", lambda: FakeRouting())
    monkeypatch.setattr(providers, "weather", lambda: FakeWeather())
    return APIClient()


def payload(**overrides):
    body = {
        "origin": {"label": "Chicago", "lat": 41.88, "lng": -87.63},
        "destination": {"label": "Dallas", "lat": 32.78, "lng": -96.80},
        "departure": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "load_lb": 42000,
        "interval_mi": 50,
    }
    body.update(overrides)
    return body


def test_health(client):
    assert client.get("/api/health/").json() == {"status": "ok"}


def test_analyze_happy_path(client):
    res = client.post("/api/routes/analyze/", payload(), format="json")
    assert res.status_code == 200
    data = res.json()
    assert len(data["routes"]) == 3 and data["recommended_route_id"]
    assert {"id", "label", "start", "end", "bounds", "segments", "metrics", "checkpoints", "rank"} <= set(data["routes"][0])


def test_heatmap_happy_path(client):
    res = client.post("/api/heatmap/", payload(), format="json")
    assert res.status_code == 200
    body = res.json()
    assert len(body["hours"]) == 49 and len(body["points"]) == len(body["levels"])


@pytest.mark.parametrize("field,value", [
    ("load_lb", -1),
    ("load_lb", 999_999),
    ("interval_mi", 30),
    ("departure", "not a date"),
    ("departure", (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()),
    ("departure", (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()),
    ("origin", {"lat": 120, "lng": 0}),
])
def test_validation_errors_use_one_shape(client, field, value):
    res = client.post("/api/routes/analyze/", payload(**{field: value}), format="json")
    assert res.status_code == 400
    error = res.json()["error"]
    assert error["code"] == "validation_error" and field in error["fields"]


def test_same_origin_and_destination_is_rejected(client):
    same = payload(destination={"label": "x", "lat": 41.88, "lng": -87.63})
    res = client.post("/api/routes/analyze/", same, format="json")
    assert res.status_code == 400 and "destination" in res.json()["error"]["fields"]


def test_missing_fields(client):
    res = client.post("/api/routes/analyze/", {}, format="json")
    assert res.status_code == 400
    assert {"origin", "destination", "departure", "load_lb"} <= set(res.json()["error"]["fields"])


def test_unroutable_trip_is_a_400(client, monkeypatch):
    class Empty(FakeRouting):
        def route(self, *a, **k):
            return []

    monkeypatch.setattr(providers, "routing", lambda: Empty())
    res = client.post("/api/routes/analyze/", payload(), format="json")
    assert res.status_code == 400 and res.json()["error"]["code"] == "invalid_trip"


def test_provider_outage_is_a_502_not_a_500(client, monkeypatch):
    class Down:
        def fetch(self, *a, **k):
            raise ProviderError("open-meteo.com request failed: timeout")

    monkeypatch.setattr(providers, "weather", lambda: Down())
    res = client.post("/api/routes/analyze/", payload(), format="json")
    assert res.status_code == 502 and res.json()["error"]["code"] == "provider_unavailable"


def test_geocode_validates_and_returns_results(client, monkeypatch):
    class Geo:
        def search(self, q):
            return [{"label": q, "lat": 1.0, "lng": 2.0}]

    monkeypatch.setattr(providers, "geocoder", lambda: Geo())
    assert client.get("/api/geocode/?q=ab").status_code == 400
    assert client.get("/api/geocode/?q=Chicago").json()["results"][0]["label"] == "Chicago"
