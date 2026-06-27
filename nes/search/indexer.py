"""Live-indexing adaptor used by the write path.

:class:`EntityIndexer` turns an entity into a document and upserts/deletes it in
the search backend. All operations are *best-effort*: the database write is the
source of truth and the index is always rebuildable via ``nes search reindex``,
so an indexing failure is logged but never propagated to the caller. This keeps
entity writes succeeding even when the search engine is down.
"""

import logging
from typing import Optional

from nes.core.models.entity import Entity
from nes.search.backend import SearchBackend
from nes.search.document import EntityDocumentBuilder

logger = logging.getLogger(__name__)


class EntityIndexer:
    """Best-effort bridge between entity writes and the search backend."""

    def __init__(
        self,
        backend: SearchBackend,
        builder: Optional[EntityDocumentBuilder] = None,
    ):
        self.backend = backend
        self.builder = builder or EntityDocumentBuilder()

    async def upsert_entity(self, entity: Entity) -> bool:
        """Index (create or replace) one entity. Returns True on success."""
        try:
            doc = self.builder.build(entity)
            await self.backend.index(doc)
            return True
        except Exception:
            logger.exception("search index upsert failed for %s", entity.id)
            return False

    async def remove_entity(self, entity_id: str) -> bool:
        """Remove one entity from the index. Returns True on success."""
        try:
            await self.backend.delete(entity_id)
            return True
        except Exception:
            logger.exception("search index delete failed for %s", entity_id)
            return False
