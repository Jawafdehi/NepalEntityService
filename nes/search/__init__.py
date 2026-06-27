"""Dedicated entity search module.

Provides a backend-agnostic search abstraction used by the API and CLI:

- :class:`SearchQuery` / :class:`SearchHit` / :class:`SearchResults` -- the
  request/response contract.
- :class:`SearchBackend` -- the interface implemented by the in-process
  fallback and the OpenSearch backend.
- :class:`EntityDocumentBuilder` -- converts an Entity into a searchable doc
  (multi-field, with index-time EN<->Devanagari transliteration).
- :class:`EntityIndexer` -- best-effort live indexing for the write path.
- :func:`get_search_backend` -- environment-driven backend selection.
"""

from nes.search.backend import SearchBackend
from nes.search.document import EntityDocumentBuilder
from nes.search.factory import get_search_backend
from nes.search.indexer import EntityIndexer
from nes.search.models import SearchHit, SearchQuery, SearchResults

__all__ = [
    "SearchBackend",
    "SearchQuery",
    "SearchHit",
    "SearchResults",
    "EntityDocumentBuilder",
    "EntityIndexer",
    "get_search_backend",
]
