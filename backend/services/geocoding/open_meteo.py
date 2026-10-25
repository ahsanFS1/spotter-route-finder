"""Open-Meteo geocoding: a second place-search source used when Photon is unavailable.
It matches place names (cities, towns), not street addresses."""
from services.http import build_session, get_json

from .photon import ALLOWED_COUNTRIES, TIMEOUT_S


class OpenMeteoGeocoder:
    def __init__(self, base_url: str = "https://geocoding-api.open-meteo.com/v1/search", session=None):
        self.base_url = base_url
        self.session = session or build_session(retries=1, backoff=0.5)

    def search(self, query: str, limit: int = 6) -> list[dict]:
        data = get_json(
            self.session, self.base_url,
            {"name": query, "count": 20, "language": "en", "format": "json"}, timeout=TIMEOUT_S,
        )
        results, seen = [], set()
        for item in data.get("results", []):
            if item.get("country_code") not in ALLOWED_COUNTRIES:
                continue
            label = ", ".join(
                dict.fromkeys(p for p in (item.get("name"), item.get("admin1"), item.get("country_code")) if p)
            )
            if label in seen:
                continue
            seen.add(label)
            results.append({"label": label, "lat": item["latitude"], "lng": item["longitude"]})
            if len(results) == limit:
                break
        return results
