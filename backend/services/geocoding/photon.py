"""Photon (OpenStreetMap) geocoder. GeoJSON coordinates are [lon, lat]."""
from services.http import build_session, get_json

ALLOWED_COUNTRIES = {"US", "CA", "MX"}


class PhotonGeocoder:
    def __init__(self, base_url: str = "https://photon.komoot.io", session=None):
        self.base_url = base_url.rstrip("/")
        self.session = session or build_session()

    def search(self, query: str, limit: int = 6) -> list[dict]:
        data = get_json(self.session, f"{self.base_url}/api/", {"q": query, "limit": limit * 2, "lang": "en"})
        results, seen = [], set()
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            if props.get("countrycode") not in ALLOWED_COUNTRIES:
                continue
            lng, lat = feature["geometry"]["coordinates"]
            label = ", ".join(
                dict.fromkeys(
                    p for p in (props.get("name"), props.get("city"), props.get("state"), props.get("countrycode")) if p
                )
            )
            if label in seen:
                continue
            seen.add(label)
            results.append({"label": label, "lat": lat, "lng": lng})
            if len(results) == limit:
                break
        return results
