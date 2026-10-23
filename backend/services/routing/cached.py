"""Caches routing responses so the analysis and the heatmap see the same routes."""
from django.core.cache import cache as default_cache

from domain.geo import LatLng

from .base import RouteOption, RoutingProvider

CACHE_TTL_S = 3600


class CachedRouting:
    def __init__(self, inner: RoutingProvider, cache=None, ttl: int = CACHE_TTL_S):
        self.inner = inner
        self.cache = cache if cache is not None else default_cache
        self.ttl = ttl

    @staticmethod
    def _key(waypoints: list[LatLng], alternatives: bool) -> str:
        coords = ";".join(f"{lat:.4f},{lng:.4f}" for lat, lng in waypoints)
        return f"route:{int(alternatives)}:{coords}"

    def route(self, waypoints: list[LatLng], alternatives: bool = False) -> list[RouteOption]:
        key = self._key(waypoints, alternatives)
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        routes = self.inner.route(waypoints, alternatives)
        if routes:  # never cache "no route": it may be a transient failure upstream
            self.cache.set(key, routes, self.ttl)
        return routes
