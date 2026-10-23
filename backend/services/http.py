"""Shared HTTP session with retries and a descriptive User-Agent."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import logging

USER_AGENT = "spotter-route-finder/1.0 (weather-aware truck routing)"
DEFAULT_TIMEOUT_S = 25

logger = logging.getLogger(__name__)

SERVICE_NAMES = {
    "open-meteo.com": "The weather service",
    "project-osrm.org": "The routing service",
    "komoot.io": "The place search service",
}


class ProviderError(Exception):
    """A third-party provider failed or returned something unusable.

    `str(exc)` is safe to show to a user; technical detail goes to the log.
    """


def _service_name(url: str) -> str:
    host = url.split("/")[2]
    return next((name for domain, name in SERVICE_NAMES.items() if host.endswith(domain)), "A data service")


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=2.0,  # 0s, 4s, 8s between attempts; Retry-After is honoured when sent
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=16)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers["User-Agent"] = USER_AGENT
    return session


def get_json(session: requests.Session, url: str, params: dict, timeout: float = DEFAULT_TIMEOUT_S):
    try:
        resp = session.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RetryError as exc:
        logger.warning("rate limited by %s: %s", url, exc)
        raise ProviderError(f"{_service_name(url)} is busy right now. Please try again in a minute.") from exc
    except (requests.RequestException, ValueError) as exc:
        logger.warning("request to %s failed: %s", url, exc)
        raise ProviderError(f"{_service_name(url)} is not responding. Please try again in a moment.") from exc
