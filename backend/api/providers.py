"""Provider instances built once from settings (shared HTTP sessions and caches)."""
from functools import lru_cache

from django.conf import settings

from services.geocoding.open_meteo import OpenMeteoGeocoder
from services.geocoding.photon import PhotonGeocoder
from services.geocoding.resilient import ResilientGeocoder
from services.routing.cached import CachedRouting
from services.routing.osrm import OsrmProvider
from services.weather.open_meteo import OpenMeteoProvider


@lru_cache
def routing() -> CachedRouting:
    return CachedRouting(OsrmProvider(settings.OSRM_BASE_URL, settings.TRUCK_SPEED_FACTOR))


@lru_cache
def geocoder() -> ResilientGeocoder:
    return ResilientGeocoder(PhotonGeocoder(settings.PHOTON_BASE_URL), OpenMeteoGeocoder())


@lru_cache
def weather() -> OpenMeteoProvider:
    return OpenMeteoProvider(settings.OPEN_METEO_URL)
