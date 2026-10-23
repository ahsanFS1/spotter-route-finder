from services.routing.cached import CachedRouting

from .fakes import FakeRouting
from .test_providers import MemoryCache

A, B = (41.88, -87.63), (32.78, -96.80)


def test_second_identical_request_is_served_from_cache():
    inner = FakeRouting()
    routing = CachedRouting(inner, cache=MemoryCache())
    first = routing.route([A, B], alternatives=True)
    second = routing.route([A, B], alternatives=True)
    assert len(inner.calls) == 1 and first == second


def test_nearby_coordinates_share_an_entry_but_options_do_not():
    inner = FakeRouting()
    routing = CachedRouting(inner, cache=MemoryCache())
    routing.route([A, B], alternatives=True)
    routing.route([(41.88001, -87.63001), B], alternatives=True)
    routing.route([A, B], alternatives=False)
    assert len(inner.calls) == 2


def test_empty_results_are_not_cached():
    class Flaky(FakeRouting):
        def route(self, waypoints, alternatives=False):
            self.calls.append(waypoints)
            return [] if len(self.calls) == 1 else super().route(waypoints, alternatives)

    inner = Flaky()
    routing = CachedRouting(inner, cache=MemoryCache())
    assert routing.route([A, B]) == []
    assert routing.route([A, B]) != []
