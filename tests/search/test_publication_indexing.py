"""Live-indexing hook tests for PublicationService.

Verifies that create/update/delete operations keep the search backend in sync
when an indexer is configured, that nothing happens when it is not, and -- most
importantly -- that an indexing failure never breaks the entity write.
"""

import pytest

from nes.database.file_database import FileDatabase
from nes.search.document import EntityDocumentBuilder
from nes.search.fallback import InProcessSearchBackend
from nes.search.indexer import EntityIndexer
from nes.search.models import SearchQuery
from nes.services.publication import PublicationService


def _make_service(temp_db_path, backend=None):
    db = FileDatabase(base_path=str(temp_db_path))
    indexer = EntityIndexer(backend, EntityDocumentBuilder()) if backend else None
    return db, PublicationService(database=db, indexer=indexer)


PERSON = {
    "slug": "ram-chandra-poudel",
    "names": [{"kind": "PRIMARY", "en": {"full": "Ram Chandra Poudel"}}],
}


class TestPublicationIndexing:
    @pytest.mark.asyncio
    async def test_create_indexes_entity(self, temp_db_path):
        backend = InProcessSearchBackend()
        _, pub = _make_service(temp_db_path, backend)

        await pub.create_entity("person", dict(PERSON), "author:test", "create")

        res = await backend.search(SearchQuery.build(query="poudel"))
        assert res.total == 1
        assert res.hits[0].entity_id == "entity:person/ram-chandra-poudel"

    @pytest.mark.asyncio
    async def test_update_reindexes_entity(self, temp_db_path):
        backend = InProcessSearchBackend()
        _, pub = _make_service(temp_db_path, backend)

        entity = await pub.create_entity(
            "person", dict(PERSON), "author:test", "create"
        )
        # Rename and update.
        entity.names[0].en.full = "Ramchandra Poudel Updated"
        await pub.update_entity(entity, "author:test", "rename")

        res = await backend.search(SearchQuery.build(query="updated"))
        assert res.total == 1
        assert res.hits[0].entity_id == entity.id

    @pytest.mark.asyncio
    async def test_delete_removes_from_index(self, temp_db_path):
        backend = InProcessSearchBackend()
        _, pub = _make_service(temp_db_path, backend)

        entity = await pub.create_entity(
            "person", dict(PERSON), "author:test", "create"
        )
        await pub.delete_entity(entity.id, "author:test", "remove")

        res = await backend.search(SearchQuery.build(query="poudel"))
        assert res.total == 0

    @pytest.mark.asyncio
    async def test_no_indexer_still_works(self, temp_db_path):
        db, pub = _make_service(temp_db_path, backend=None)
        entity = await pub.create_entity(
            "person", dict(PERSON), "author:test", "create"
        )
        # Entity persisted normally.
        assert await db.get_entity(entity.id) is not None

    @pytest.mark.asyncio
    async def test_indexing_failure_does_not_break_write(self, temp_db_path):
        class BrokenBackend(InProcessSearchBackend):
            async def index(self, doc):
                raise RuntimeError("index down")

        db, pub = _make_service(temp_db_path, BrokenBackend())

        # Must not raise despite the indexer failing.
        entity = await pub.create_entity(
            "person", dict(PERSON), "author:test", "create"
        )
        # The write itself succeeded; DB is the source of truth.
        assert await db.get_entity(entity.id) is not None
