"""Integration tests for tag filtering with InMemoryCachedReadDatabase.

These tests verify that tag filtering works correctly with the production
database configuration (file+memcached://) using the Config system.

This mirrors the actual production setup used by nes.jawafdehi.org API.
"""

import os
from datetime import date

import pytest
import pytest_asyncio

from nes.config import Config
from nes.core.models.entity import EntitySubType, EntityType
from nes.database.file_database import FileDatabase
from nes.services.publication import PublicationService


class TestTagFilteringIntegrationWithMemCached:
    """Integration tests for tag filtering with file+memcached:// configuration.

    These tests use the actual Config system with NES_DB_URL=file+memcached://
    to verify production-like behavior with InMemoryCachedReadDatabase.

    Requirements: 19.1, 19.2, 19.3, 19.4, 19.5
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, tmp_path, monkeypatch):
        """Set up test environment with file+memcached database configuration."""
        # Set up temporary database path
        db_path = tmp_path / "test-integration-db"
        db_path.mkdir(parents=True, exist_ok=True)

        # Set NES_DB_URL to use file+memcached protocol
        db_url = f"file+memcached:///{db_path}"
        monkeypatch.setenv("NES_DB_URL", db_url)

        # Initialize Config with the memcached database
        Config.cleanup()  # Clean up any existing instances
        Config.initialize_database(base_path=str(db_path))

        yield

        # Cleanup
        Config.cleanup()

    @pytest_asyncio.fixture
    async def file_db_for_writes(self, tmp_path):
        """Provide a FileDatabase instance for write operations.

        Since InMemoryCachedReadDatabase is read-only, we need a separate
        FileDatabase for creating test data.
        """
        db_path = tmp_path / "test-integration-db"
        return FileDatabase(base_path=str(db_path))

    @pytest.mark.asyncio
    async def test_tag_filtering_via_config_single_tag(self, file_db_for_writes):
        """Test tag filtering with single tag via Config system.

        Requirement 19.1: THE Search_Service SHALL support filtering entities by one or more tags
        """
        # Arrange: Create test data using FileDatabase for writes
        pub_service = PublicationService(database=file_db_for_writes)

        await pub_service.create_entity(
            "person",
            {
                "slug": "ram-chandra-poudel",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Ram Chandra Poudel"}}],
                "tags": ["president", "senior-leader"],
            },
            "author:test",
            "Integration test",
        )
        await pub_service.create_entity(
            "person",
            {
                "slug": "sher-bahadur-deuba",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Sher Bahadur Deuba"}}],
                "tags": ["prime-minister", "senior-leader"],
            },
            "author:test",
            "Integration test",
        )

        # Act: Use SearchService from Config (which uses InMemoryCachedReadDatabase)
        search_service = Config.get_search_service()
        results = await search_service.search_entities(tags=["president"])

        # Assert
        assert len(results) == 1
        assert results[0].slug == "ram-chandra-poudel"
        assert "president" in results[0].tags

    @pytest.mark.asyncio
    async def test_tag_filtering_via_config_multiple_tags_and_logic(
        self, file_db_for_writes
    ):
        """Test tag filtering with multiple tags (AND logic) via Config system.

        Requirement 19.2: WHEN multiple tags are provided, THE Search_Service SHALL apply AND logic
        """
        # Arrange
        pub_service = PublicationService(database=file_db_for_writes)

        await pub_service.create_entity(
            "person",
            {
                "slug": "person-a",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Person A"}}],
                "tags": ["politician", "senior-leader", "congress"],
            },
            "author:test",
            "Integration test",
        )
        await pub_service.create_entity(
            "person",
            {
                "slug": "person-b",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Person B"}}],
                "tags": ["politician", "congress"],  # Missing "senior-leader"
            },
            "author:test",
            "Integration test",
        )
        await pub_service.create_entity(
            "person",
            {
                "slug": "person-c",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Person C"}}],
                "tags": [
                    "politician",
                    "senior-leader",
                    "uml",
                ],  # Has "uml" not "congress"
            },
            "author:test",
            "Integration test",
        )

        # Act: Search via Config system
        search_service = Config.get_search_service()
        results = await search_service.search_entities(
            tags=["senior-leader", "congress"]
        )

        # Assert: Only person-a has BOTH tags
        assert len(results) == 1
        assert results[0].slug == "person-a"

    @pytest.mark.asyncio
    async def test_tag_filtering_via_config_combined_with_filters(
        self, file_db_for_writes
    ):
        """Test combining tag filter with other filters via Config system.

        Requirement 19.3: THE Search_Service SHALL allow combining tag filters with existing filters
        """
        # Arrange
        pub_service = PublicationService(database=file_db_for_writes)

        # Create person and organization with same tag
        await pub_service.create_entity(
            "person",
            {
                "slug": "tagged-person",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Tagged Person"}}],
                "tags": ["featured"],
            },
            "author:test",
            "Integration test",
        )
        await pub_service.create_entity(
            "organization",
            {
                "slug": "tagged-org",
                "type": "organization",
                "sub_type": "political_party",
                "names": [{"kind": "PRIMARY", "en": {"full": "Tagged Organization"}}],
                "tags": ["featured"],
            },
            "author:test",
            "Integration test",
        )

        # Act: Search via Config system with tag + type filter
        search_service = Config.get_search_service()
        results = await search_service.search_entities(
            tags=["featured"], entity_type="person"
        )

        # Assert: Only person should be returned
        assert len(results) == 1
        assert results[0].slug == "tagged-person"

    @pytest.mark.asyncio
    async def test_tag_filtering_via_config_with_text_query(self, file_db_for_writes):
        """Test combining tag filter with text query via Config system.

        Requirement 19.3: THE Search_Service SHALL allow combining tag filters with existing filters
        """
        # Arrange
        pub_service = PublicationService(database=file_db_for_writes)

        await pub_service.create_entity(
            "person",
            {
                "slug": "ram-sharma",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Ram Sharma"}}],
                "tags": ["congress"],
            },
            "author:test",
            "Integration test",
        )
        await pub_service.create_entity(
            "person",
            {
                "slug": "ram-thapa",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Ram Thapa"}}],
                "tags": ["uml"],
            },
            "author:test",
            "Integration test",
        )

        # Act: Search via Config system with text query + tag filter
        search_service = Config.get_search_service()
        results = await search_service.search_entities(query="Ram", tags=["congress"])

        # Assert
        assert len(results) == 1
        assert results[0].slug == "ram-sharma"

    @pytest.mark.asyncio
    async def test_tag_filtering_via_config_cache_warming(self, file_db_for_writes):
        """Test that cache warming works correctly for tagged entities.

        This test verifies that InMemoryCachedReadDatabase properly loads
        entities with tags into its cache during initialization.
        """
        # Arrange
        pub_service = PublicationService(database=file_db_for_writes)

        # Create entities with various tag combinations
        await pub_service.create_entity(
            "person",
            {
                "slug": "person-1",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Person 1"}}],
                "tags": ["tag-a", "tag-b"],
            },
            "author:test",
            "Integration test",
        )
        await pub_service.create_entity(
            "person",
            {
                "slug": "person-2",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Person 2"}}],
                "tags": ["tag-c"],
            },
            "author:test",
            "Integration test",
        )

        # Act: Get database from Config (should be InMemoryCachedReadDatabase)
        db = Config.get_database()

        # Verify it's the cached database
        from nes.database.in_memory_cached_read_database import (
            InMemoryCachedReadDatabase,
        )

        assert isinstance(db, InMemoryCachedReadDatabase)

        # Search via cached database
        search_service = Config.get_search_service()
        results_a = await search_service.search_entities(tags=["tag-a"])
        results_c = await search_service.search_entities(tags=["tag-c"])

        # Assert: Cache should have all entities with correct tags
        assert len(results_a) == 1
        assert results_a[0].slug == "person-1"
        assert len(results_c) == 1
        assert results_c[0].slug == "person-2"

    @pytest.mark.asyncio
    async def test_tag_filtering_via_config_verifies_production_setup(
        self, file_db_for_writes
    ):
        """Test that verifies the production setup with NES_DB_URL environment variable.

        This test confirms that:
        1. NES_DB_URL=file+memcached:// is correctly parsed
        2. InMemoryCachedReadDatabase is created
        3. Tag filtering works in production configuration
        """
        # Arrange
        pub_service = PublicationService(database=file_db_for_writes)

        await pub_service.create_entity(
            "person",
            {
                "slug": "production-test",
                "type": "person",
                "names": [{"kind": "PRIMARY", "en": {"full": "Production Test"}}],
                "tags": ["production", "verified"],
            },
            "author:test",
            "Integration test - production config",
        )

        # Act & Assert: Verify Config detects file+memcached protocol
        protocol = Config.get_db_protocol()
        assert protocol == "file+memcached"

        # Verify database is InMemoryCachedReadDatabase
        db = Config.get_database()
        from nes.database.in_memory_cached_read_database import (
            InMemoryCachedReadDatabase,
        )

        assert isinstance(db, InMemoryCachedReadDatabase)

        # Verify tag filtering works through Config
        search_service = Config.get_search_service()
        results = await search_service.search_entities(tags=["production", "verified"])

        assert len(results) == 1
        assert results[0].slug == "production-test"
        assert set(results[0].tags) == {"production", "verified"}
