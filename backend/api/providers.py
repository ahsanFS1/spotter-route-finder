"""Provider instances built once from settings (shared HTTP sessions and caches)."""
from functools import lru_cache

from django.conf import settings

from services.geocoding.photon import PhotonGeocoder
from services.routing.osrm import OsrmProvider
from services.weather.open_meteo import OpenMeteoProvider


@lru_cache
def routing() -> OsrmProvider:
    return OsrmProvider(settings.OSRM_BASE_URL, settings.TRUCK_SPEED_FACTOR)


@lru_cache
def geocoder() -> PhotonGeocoder:
    return PhotonGeocoder(settings.PHOTON_BASE_URL)


@lru_cache
def weather() -> OpenMeteoProvider:
    return OpenMeteoProvider(settings.OPEN_METEO_URL)
