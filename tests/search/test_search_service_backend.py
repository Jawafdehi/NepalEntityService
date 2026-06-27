"""SearchService integration with a search backend.

Verifies that when a backend is configured, SearchService delegates to it,
hydrates real Entity objects from the database, returns accurate totals via
search_entities_full, and degrades gracefully when the backend errors.
"""

import pytest

from nes.database.file_database import FileDatabase
from nes.search.document import EntityDocumentBuilder
from nes.search.fallback import InProcessSearchBackend
from nes.search.models import SearchQuery
from nes.services.publication import PublicationService
from nes.services.search import SearchService


async def _seed(temp_db_path):
    """Create entities in the DB and a backend indexed with the same docs."""
    db = FileDatabase(base_path=str(temp_db_path))
    pub = PublicationService(database=db)
    backend = InProcessSearchBackend()
    builder = EntityDocumentBuilder()

    specs = [
        (
            "person",
            {
                "slug": "ram-chandra-poudel",
                "names": [{"kind": "PRIMARY", "en": {"full": "Ram Chandra Poudel"}}],
                "tags": ["politician"],
            },
        ),
        (
            "person",
            {
                "slug": "sher-bahadur-deuba",
                "names": [{"kind": "PRIMARY", "en": {"full": "Sher Bahadur Deuba"}}],
                "tags": ["politician"],
            },
        ),
    ]
    for prefix, data in specs:
        entity = await pub.create_entity(prefix, data, "author:test", "seed")
        await backend.index(builder.build(entity))
    return db, backend


class TestSearchServiceWithBackend:
    @pytest.mark.asyncio
    async def test_search_entities_hydrates_real_entities(self, temp_db_path):
        db, backend = await _seed(temp_db_path)
        service = SearchService(database=db, backend=backend)

        results = await service.search_entities(query="poudel")

        assert len(results) == 1
        # Hydrated from the DB -> a real Entity, not the raw doc.
        assert results[0].id == "entity:person/ram-chandra-poudel"
        assert results[0].names[0].en.full == "Ram Chandra Poudel"

    @pytest.mark.asyncio
    async def test_search_entities_full_reports_accurate_total(self, temp_db_path):
        db, backend = await _seed(temp_db_path)
        service = SearchService(database=db, backend=backend)

        results = await service.search_entities_full(
            SearchQuery.build(tags=["politician"], limit=1)
        )

        # total counts ALL matches even though only one fits on the page.
        assert results.total == 2
        assert len(results.hits) == 1

    @pytest.mark.asyncio
    async def test_no_backend_uses_database(self, temp_db_path):
        db, _ = await _seed(temp_db_path)
        service = SearchService(database=db)  # no backend

        results = await service.search_entities(query="poudel")
        assert len(results) == 1
        assert results[0].id == "entity:person/ram-chandra-poudel"

    @pytest.mark.asyncio
    async def test_backend_failure_falls_back_to_database(self, temp_db_path):
        db, _ = await _seed(temp_db_path)

        class BrokenBackend(InProcessSearchBackend):
            async def search(self, query):
                raise RuntimeError("backend down")

        service = SearchService(database=db, backend=BrokenBackend())

        # Should not raise; should fall back to the database search.
        results = await service.search_entities(query="poudel")
        assert len(results) == 1
        assert results[0].id == "entity:person/ram-chandra-poudel"

    @pytest.mark.asyncio
    async def test_search_entities_page_returns_entities_and_total(self, temp_db_path):
        db, backend = await _seed(temp_db_path)
        service = SearchService(database=db, backend=backend)

        entities, total = await service.search_entities_page(
            SearchQuery.build(tags=["politician"], limit=1)
        )
        assert total == 2  # accurate total across all matches
        assert len(entities) == 1  # page size
        assert entities[0].id.startswith("entity:person/")

    @pytest.mark.asyncio
    async def test_no_backend_page_single_db_fetch(self, temp_db_path):
        """No-backend path returns entities directly without a second fetch."""
        db, _ = await _seed(temp_db_path)
        service = SearchService(database=db)

        # Spy: get_entities_batch must NOT be called in the no-backend path
        # (the database search already returned full entities).
        called = {"batch": 0}
        orig_batch = service.get_entities_batch

        async def spy_batch(ids):
            called["batch"] += 1
            return await orig_batch(ids)

        service.get_entities_batch = spy_batch

        entities, total = await service.search_entities_page(
            SearchQuery.build(query="poudel")
        )
        assert len(entities) == 1
        assert total == 1
        assert called["batch"] == 0

    @pytest.mark.asyncio
    async def test_value_error_from_backend_propagates(self, temp_db_path):
        """Query errors (e.g. pagination window) surface, not silently degrade."""
        db, _ = await _seed(temp_db_path)

        class PaginationGuardBackend(InProcessSearchBackend):
            async def search(self, query):
                raise ValueError("Pagination window too large")

        service = SearchService(database=db, backend=PaginationGuardBackend())

        with pytest.raises(ValueError, match="Pagination window"):
            await service.search_entities_page(SearchQuery.build(query="x"))
