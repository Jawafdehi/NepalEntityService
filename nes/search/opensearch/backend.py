"""OpenSearch-backed :class:`SearchBackend` implementation.

Indexes entity documents and serves multi-field, fuzzy, transliteration-aware
search with accurate totals (``track_total_hits``) and bounded pagination.

The ``opensearch-py`` dependency is imported lazily (in the client module and
the bulk helper) so that importing this module does not require the optional
dependency to be installed; only constructing/using the backend does.
"""

import logging
import os
from typing import Any, Dict, Iterable, List, Optional

from nes.search.backend import SearchBackend
from nes.search.models import SearchHit, SearchQuery, SearchResults
from nes.search.opensearch.client import build_async_client
from nes.search.opensearch.mapping import (
    DEFAULT_INDEX,
    MAX_RESULT_WINDOW,
    build_query_body,
    index_mappings,
    index_settings,
)

logger = logging.getLogger(__name__)


class OpenSearchBackend(SearchBackend):
    """Search backend backed by an OpenSearch cluster."""

    def __init__(self, client, index: str = DEFAULT_INDEX, use_icu: bool = True):
        self.client = client
        self.index_name = index
        self.use_icu = use_icu

    @classmethod
    def from_env(
        cls,
        url: Optional[str] = None,
        index: Optional[str] = None,
        use_icu: Optional[bool] = None,
    ) -> "OpenSearchBackend":
        """Build a backend from explicit args / environment variables."""
        url = url or os.getenv("OPENSEARCH_URL", "http://localhost:9200")
        index = index or os.getenv("OPENSEARCH_INDEX", DEFAULT_INDEX)
        if use_icu is None:
            use_icu = os.getenv("OPENSEARCH_USE_ICU", "true").lower() != "false"
        client = build_async_client(
            url=url,
            user=os.getenv("OPENSEARCH_USER"),
            password=os.getenv("OPENSEARCH_PASSWORD"),
        )
        return cls(client=client, index=index, use_icu=use_icu)

    async def health(self) -> bool:
        try:
            return bool(await self.client.ping())
        except Exception:
            logger.warning("OpenSearch ping failed", exc_info=True)
            return False

    async def ensure_index(self) -> None:
        if await self.client.indices.exists(index=self.index_name):
            return
        body = {
            "settings": index_settings(use_icu=self.use_icu),
            "mappings": index_mappings(),
        }
        try:
            await self.client.indices.create(index=self.index_name, body=body)
        except Exception as e:
            # Retry without ICU only when the failure is the missing ICU
            # tokenizer; any other error (bad shards, auth, network) propagates
            # so it isn't masked as an "ICU fallback".
            if self.use_icu and _is_missing_icu_error(e):
                logger.info(
                    "Index create failed with ICU analyzer; retrying with the "
                    "standard Devanagari analyzer (install the analysis-icu "
                    "plugin for better Devanagari tokenization)"
                )
                self.use_icu = False
                body["settings"] = index_settings(use_icu=False)
                await self.client.indices.create(index=self.index_name, body=body)
            else:
                raise

    async def delete_index(self) -> None:
        """Delete the index if present (used by tests and full rebuilds)."""
        await self.client.indices.delete(index=self.index_name, ignore=[404])

    async def refresh(self) -> None:
        """Make recently-indexed documents visible to search immediately."""
        await self.client.indices.refresh(index=self.index_name)

    async def index(self, doc: Dict[str, Any]) -> None:
        entity_id = doc.get("id")
        if not entity_id:
            raise ValueError("document is missing required 'id' field")
        await self.client.index(index=self.index_name, id=entity_id, body=doc)

    async def index_bulk(self, docs: Iterable[Dict[str, Any]]) -> int:
        from opensearchpy.helpers import async_bulk  # lazy import

        actions = (
            {
                "_op_type": "index",
                "_index": self.index_name,
                "_id": doc["id"],
                "_source": doc,
            }
            for doc in docs
        )
        success, _ = await async_bulk(self.client, actions)
        return success

    async def delete(self, entity_id: str) -> bool:
        result = await self.client.delete(
            index=self.index_name, id=entity_id, ignore=[404]
        )
        return result.get("result") == "deleted"

    async def search(self, query: SearchQuery) -> SearchResults:
        # Guard deep pagination so callers get a clear error instead of an
        # opaque OpenSearch "Result window is too large" 500.
        if query.offset + query.limit > MAX_RESULT_WINDOW:
            raise ValueError(
                f"Pagination window too large: offset ({query.offset}) + limit "
                f"({query.limit}) exceeds {MAX_RESULT_WINDOW}. Narrow the query "
                f"or request an earlier page."
            )
        body = build_query_body(query)
        response = await self.client.search(index=self.index_name, body=body)
        return self._parse_response(response, query)

    @staticmethod
    def _parse_response(response: Dict[str, Any], query: SearchQuery) -> SearchResults:
        raw_hits = response.get("hits", {})
        total = raw_hits.get("total", {})
        total_value = total.get("value", 0) if isinstance(total, dict) else total

        hits: List[SearchHit] = []
        for h in raw_hits.get("hits", []):
            hits.append(
                SearchHit(
                    entity_id=h.get("_id"),
                    score=h.get("_score") or 0.0,
                    source=h.get("_source", {}),
                    highlights=h.get("highlight") if query.highlight else None,
                )
            )
        return SearchResults(hits=hits, total=int(total_value))

    async def close(self) -> None:
        try:
            await self.client.close()
        except Exception:
            logger.warning("Error closing OpenSearch client", exc_info=True)


def _is_missing_icu_error(exc: Exception) -> bool:
    """Return True if ``exc`` indicates the ICU tokenizer/plugin is unavailable.

    OpenSearch raises an illegal_argument_exception referencing the missing
    ``icu_tokenizer`` when the analysis-icu plugin is not installed.
    """
    message = str(exc).lower()
    return "icu" in message


__all__ = ["OpenSearchBackend"]
