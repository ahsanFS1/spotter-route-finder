"""Open-Meteo hourly forecast client. Units are requested explicitly (mph, inches)
and times are UTC, so an ETA maps to the matching hour without timezone guessing."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from django.core.cache import cache as default_cache

from domain.geo import LatLng
from domain.models import Weather
from services.http import ProviderError, build_session, get_json

MAX_FORECAST_DAYS = 16
CHUNK_SIZE = 50
CACHE_TTL_S = 1800
GRID_DEG = 0.05  # ~3.5 miles; nearby checkpoints share one forecast request and cache entry
DAY_BUCKETS = (4, 8, MAX_FORECAST_DAYS)  # fixed horizons so cached series are reused across trips
HOURLY = "wind_speed_10m,rain,showers,snowfall"
# hour (UTC, floored) -> Weather
Series = dict[datetime, Weather]


def floor_hour(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def nearest_hour(dt: datetime) -> datetime:
    dt = dt.astimezone(timezone.utc)
    base = floor_hour(dt)
    return base + timedelta(hours=1) if dt.minute >= 30 else base


class OpenMeteoProvider:
    def __init__(self, base_url: str = "https://api.open-meteo.com/v1/forecast", session=None, cache=None):
        self.base_url = base_url
        self.session = session or build_session()
        self.cache = cache if cache is not None else default_cache

    @staticmethod
    def _key(point: LatLng, days: int) -> str:
        return f"wx:{point[0]:.2f}:{point[1]:.2f}:{days}"

    def fetch(self, points: list[LatLng], forecast_days: int) -> dict[LatLng, Series | None]:
        """Hourly series per point. A point whose data is missing maps to None."""
        days = next((b for b in DAY_BUCKETS if forecast_days <= b), MAX_FORECAST_DAYS)
        rounded = {p: (round(round(p[0] / GRID_DEG) * GRID_DEG, 2), round(round(p[1] / GRID_DEG) * GRID_DEG, 2)) for p in points}
        unique = list(dict.fromkeys(rounded.values()))
        cached = self.cache.get_many([self._key(p, days) for p in unique])
        missing = [p for p in unique if self._key(p, days) not in cached]

        chunks = [missing[i : i + CHUNK_SIZE] for i in range(0, len(missing), CHUNK_SIZE)]
        if chunks:
            with ThreadPoolExecutor(max_workers=min(2, len(chunks))) as pool:
                for chunk, series_list in zip(chunks, pool.map(lambda c: self._fetch_chunk(c, days), chunks)):
                    for point, series in zip(chunk, series_list):
                        cached[self._key(point, days)] = series
                        self.cache.set(self._key(point, days), series, CACHE_TTL_S)
        return {p: cached.get(self._key(r, days)) for p, r in rounded.items()}

    def _fetch_chunk(self, chunk: list[LatLng], days: int) -> list[Series | None]:
        params = {
            "latitude": ",".join(f"{lat:.2f}" for lat, _ in chunk),
            "longitude": ",".join(f"{lng:.2f}" for _, lng in chunk),
            "hourly": HOURLY,
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "UTC",
            "timeformat": "iso8601",
            "forecast_days": days,
        }
        data = get_json(self.session, self.base_url, params, timeout=40)
        payloads = data if isinstance(data, list) else [data]  # one location returns an object
        if len(payloads) != len(chunk):
            raise ProviderError("weather response did not match the requested locations")
        return [self._parse(p) for p in payloads]

    @staticmethod
    def _parse(payload: dict) -> Series | None:
        hourly = payload.get("hourly")
        if not hourly:
            return None
        series: Series = {}
        for i, stamp in enumerate(hourly["time"]):
            wind = hourly["wind_speed_10m"][i]
            rain, showers, snow = hourly["rain"][i], hourly["showers"][i], hourly["snowfall"][i]
            if wind is None or rain is None or snow is None:
                continue
            series[datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)] = Weather(
                wind_mph=wind, rain_in_hr=rain + (showers or 0.0), snow_in_hr=snow
            )
        return series


def weather_at(series: Series | None, when: datetime) -> Weather | None:
    """Weather for the hour nearest `when`, or None when the forecast does not cover it."""
    if not series:
        return None
    return series.get(nearest_hour(when))
