"""OpenSearch async client construction.

Isolated from the backend so the dependency (``opensearch-py``) is imported
lazily: importing :mod:`nes.search.opensearch.backend` must not fail when the
optional dependency is absent (the factory catches construction errors and
falls back to the in-process backend).
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse


@dataclass(frozen=True)
class ConnectionParams:
    """Resolved connection settings for an OpenSearch client."""

    host: str
    port: int
    use_ssl: bool
    http_auth: Optional[Tuple[str, str]]


def resolve_connection_params(
    url: str,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> ConnectionParams:
    """Resolve host/port/ssl/auth from a URL and optional explicit credentials.

    Explicit ``user``/``password`` take precedence; otherwise credentials
    embedded in the URL (``user:pass@host``) are used, so standard URL-based
    auth works. Pure and side-effect free for easy testing.
    """
    parsed = urlparse(url)
    use_ssl = parsed.scheme == "https"
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if use_ssl else 9200)

    user = user or parsed.username
    password = password or parsed.password

    http_auth: Optional[Tuple[str, str]] = None
    if user and password:
        http_auth = (user, password)

    return ConnectionParams(host=host, port=port, use_ssl=use_ssl, http_auth=http_auth)


def build_async_client(
    url: str,
    user: Optional[str] = None,
    password: Optional[str] = None,
    timeout: int = 30,
):
    """Construct an ``AsyncOpenSearch`` client for ``url``.

    Raises ImportError if ``opensearch-py`` is not installed.
    """
    from opensearchpy import AsyncOpenSearch  # lazy import

    params = resolve_connection_params(url, user=user, password=password)

    return AsyncOpenSearch(
        hosts=[{"host": params.host, "port": params.port}],
        http_auth=params.http_auth,
        use_ssl=params.use_ssl,
        verify_certs=params.use_ssl,
        timeout=timeout,
        max_retries=3,
        retry_on_timeout=True,
    )
