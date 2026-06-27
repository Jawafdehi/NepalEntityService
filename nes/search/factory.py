"""Select and construct a :class:`SearchBackend` from environment config.

Environment variables:

- ``SEARCH_BACKEND`` -- ``inprocess`` (default) or ``opensearch``.
- ``OPENSEARCH_URL`` -- OpenSearch endpoint. If set and ``SEARCH_BACKEND`` is
  unset, the OpenSearch backend is selected automatically.
- ``OPENSEARCH_INDEX`` -- override the default index/alias name.
- ``OPENSEARCH_USER`` / ``OPENSEARCH_PASSWORD`` -- optional basic auth.

The default is the in-process fallback so existing dev/test environments work
with no external engine running.
"""

import logging
import os
from typing import Optional

from nes.search.backend import SearchBackend
from nes.search.fallback import InProcessSearchBackend

logger = logging.getLogger(__name__)


def resolve_backend_kind(
    backend: Optional[str] = None, opensearch_url: Optional[str] = None
) -> Optional[str]:
    """Decide which backend to build from explicit args / environment.

    Returns ``None`` when nothing is configured, meaning "use the legacy
    database search" (no behavior change). The engine is fully opt-in.
    """
    backend = backend or os.getenv("SEARCH_BACKEND")
    opensearch_url = opensearch_url or os.getenv("OPENSEARCH_URL")

    if backend:
        return backend.strip().lower()
    if opensearch_url:
        return "opensearch"
    return None


def get_search_backend(
    backend: Optional[str] = None, opensearch_url: Optional[str] = None
) -> Optional[SearchBackend]:
    """Construct the configured search backend, or ``None`` if unconfigured.

    - Unconfigured (default): returns ``None`` -> callers use database search,
      preserving existing behavior with no external engine.
    - ``opensearch``: builds the OpenSearch backend; if its client/dependency
      is unavailable, returns ``None`` so the service degrades to database
      search rather than crashing.
    - ``inprocess``: builds the empty in-process backend (mainly for tests and
      explicit local experimentation; it must be populated to return results).
    """
    kind = resolve_backend_kind(backend, opensearch_url)

    if kind is None:
        return None

    if kind == "opensearch":
        try:
            from nes.search.opensearch.backend import OpenSearchBackend

            return OpenSearchBackend.from_env(
                url=opensearch_url or os.getenv("OPENSEARCH_URL"),
                index=os.getenv("OPENSEARCH_INDEX"),
            )
        except Exception:
            logger.exception(
                "Failed to construct OpenSearch backend; "
                "degrading to database search"
            )
            return None

    if kind == "inprocess":
        return InProcessSearchBackend()

    logger.warning("Unknown SEARCH_BACKEND=%r; degrading to database search", kind)
    return None
