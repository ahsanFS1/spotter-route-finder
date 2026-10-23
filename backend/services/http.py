"""Shared HTTP session with retries and a descriptive User-Agent."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "spotter-route-finder/1.0 (weather-aware truck routing)"
DEFAULT_TIMEOUT_S = 25


class ProviderError(Exception):
    """A third-party provider failed or returned something unusable."""


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.6,
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
    except (requests.RequestException, ValueError) as exc:
        raise ProviderError(f"{url.split('/')[2]} request failed: {exc}") from exc
