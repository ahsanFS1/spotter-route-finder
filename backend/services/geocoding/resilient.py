"""Place search that caches answers and falls back to a second source when the first fails."""
import logging

from django.core.cache import cache as default_cache

from services.http import ProviderError

CACHE_TTL_S = 24 * 3600

logger = logging.getLogger(__name__)


class ResilientGeocoder:
    def __init__(self, primary, fallback, cache=None, ttl: int = CACHE_TTL_S):
        self.primary = primary
        self.fallback = fallback
        self.cache = cache if cache is not None else default_cache
        self.ttl = ttl

    def search(self, query: str, limit: int = 6) -> list[dict]:
        key = f"geocode:{limit}:{' '.join(query.lower().split())}"
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        try:
            results = self.primary.search(query, limit)
            if not results:  # the primary may simply lack this name
                results = self._fallback(query, limit, None)
        except ProviderError as exc:
            results = self._fallback(query, limit, exc)
        if results:  # an empty list may be a transient miss, so it is not cached
            self.cache.set(key, results, self.ttl)
        return results

    def _fallback(self, query: str, limit: int, original: ProviderError | None) -> list[dict]:
        try:
            return self.fallback.search(query, limit)
        except ProviderError:
            if original is not None:
                raise original
            return []
