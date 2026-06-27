"""Abstract search backend interface.

A :class:`SearchBackend` is the single seam between the application and a
concrete search engine. The in-process fallback and the OpenSearch backend
both implement this contract, and the same contract test-suite runs against
each.

Backends operate on opaque "documents" (plain dicts produced by
:class:`nes.search.document.EntityDocumentBuilder`). The document's ``id``
field is the canonical entity ID and serves as the document key, so repeated
``index`` calls upsert rather than duplicate.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable

from nes.search.models import SearchQuery, SearchResults


class SearchBackend(ABC):
    """Storage-agnostic interface for indexing and querying entity documents."""

    @abstractmethod
    async def search(self, query: SearchQuery) -> SearchResults:
        """Execute a search and return ranked hits plus an accurate total."""
        raise NotImplementedError

    @abstractmethod
    async def index(self, doc: Dict[str, Any]) -> None:
        """Upsert a single document, keyed by ``doc['id']``."""
        raise NotImplementedError

    @abstractmethod
    async def index_bulk(self, docs: Iterable[Dict[str, Any]]) -> int:
        """Upsert many documents. Returns the number indexed."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Remove a document by entity ID. Returns True if one was removed."""
        raise NotImplementedError

    @abstractmethod
    async def ensure_index(self) -> None:
        """Create the index/schema if it does not already exist (idempotent)."""
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> bool:
        """Return True if the backend is reachable and ready to serve."""
        raise NotImplementedError

    async def close(self) -> None:
        """Release any resources held by the backend. Default: no-op."""
        return None
