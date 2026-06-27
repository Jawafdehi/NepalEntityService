"""OpenSearch async client construction.

Isolated from the backend so the dependency (``opensearch-py``) is imported
lazily: importing :mod:`nes.search.opensearch.backend` must not fail when the
optional dependency is absent (the factory catches construction errors and
falls back to the in-process backend).
"""

from typing import Optional, Tuple
from urllib.parse import urlparse


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

    parsed = urlparse(url)
    use_ssl = parsed.scheme == "https"
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if use_ssl else 9200)

    http_auth: Optional[Tuple[str, str]] = None
    if user and password:
        http_auth = (user, password)

    return AsyncOpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=http_auth,
        use_ssl=use_ssl,
        verify_certs=use_ssl,
        timeout=timeout,
        max_retries=3,
        retry_on_timeout=True,
    )
