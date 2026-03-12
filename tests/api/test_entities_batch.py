"""Tests for batch entity lookup endpoint (TDD - Red Phase).

This test module covers the batch entity lookup functionality:
- Batch lookup with comma-separated IDs
- Partial success (some entities not found)
- Batch size validation (max 25)
- Parameter exclusivity validation
- URL encoding handling
- Empty/whitespace handling
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from nes.api.app import app
from nes.database.file_database import FileDatabase
from nes.services.publication import PublicationService
from tests.fixtures.nepali_data import get_party_entity, get_politician_entity


@pytest_asyncio.fixture
async def test_database(tmp_path):
    """Create a test database with sample data for batch lookup tests."""
    db_path = tmp_path / "test-db"
    db = FileDatabase(base_path=str(db_path))

    pub_service = PublicationService(database=db)

    from nes.core.models.entity import EntitySubType, EntityType

    # Create 5 test entities for batch lookup
    politicians = [
        "ram-chandra-poudel",
        "sher-bahadur-deuba",
        "khadga-prasad-oli",
    ]

    for slug in politicians:
        entity_data = get_politician_entity(slug)
        entity_data.pop("sub_type", None)
        await pub_service.create_entity(
            entity_prefix="person",
            entity_data=entity_data,
            author_id="author:test-setup",
            change_description="Test data setup",
        )

    # Create political parties
    parties = ["nepali-congress", "cpn-uml"]

    for slug in parties:
        entity_data = get_party_entity(slug)
        await pub_service.create_entity(
            entity_prefix="organization/political_party",
            entity_data=entity_data,
            author_id="author:test-setup",
            change_description="Test data setup",
        )

    return db


@pytest_asyncio.fixture
async def client(test_database):
    """Create an async HTTP client for testing."""
    from nes.config import Config

    db = test_database

    original_db = Config._database
    Config._database = db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    Config._database = original_db
    app.dependency_overrides.clear()


# ============================================================================
# Batch Lookup Tests
# ============================================================================


class TestBatchEntityLookup:
    """Tests for batch entity lookup with 'ids' parameter."""

    @pytest.mark.asyncio
    async def test_batch_lookup_two_entities(self, client):
        """Test batch lookup with two entity IDs."""
        ids = "entity:person/ram-chandra-poudel,entity:person/sher-bahadur-deuba"

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 200
        data = response.json()

        assert "entities" in data
        assert "total" in data
        assert "requested" in data

        assert data["total"] == 2
        assert data["requested"] == 2
        assert len(data["entities"]) == 2

        # Verify correct entities returned
        entity_ids = [e["id"] for e in data["entities"]]
        assert "entity:person/ram-chandra-poudel" in entity_ids
        assert "entity:person/sher-bahadur-deuba" in entity_ids

        # Should not have not_found field when all entities exist
        assert "not_found" not in data

    @pytest.mark.asyncio
    async def test_batch_lookup_all_five_entities(self, client):
        """Test batch lookup with all five test entities."""
        ids = ",".join(
            [
                "entity:person/ram-chandra-poudel",
                "entity:person/sher-bahadur-deuba",
                "entity:person/khadga-prasad-oli",
                "entity:organization/political_party/nepali-congress",
                "entity:organization/political_party/cpn-uml",
            ]
        )

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert data["requested"] == 5
        assert len(data["entities"]) == 5

    @pytest.mark.asyncio
    async def test_batch_lookup_single_entity(self, client):
        """Test batch lookup with single entity ID."""
        ids = "entity:person/ram-chandra-poudel"

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["requested"] == 1
        assert data["entities"][0]["id"] == "entity:person/ram-chandra-poudel"

    @pytest.mark.asyncio
    async def test_batch_lookup_with_not_found(self, client):
        """Test batch lookup when some entities don't exist."""
        ids = ",".join(
            [
                "entity:person/ram-chandra-poudel",
                "entity:person/nonexistent-person",
                "entity:person/sher-bahadur-deuba",
                "entity:person/another-missing",
            ]
        )

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2  # Only 2 found
        assert data["requested"] == 4  # 4 requested
        assert len(data["entities"]) == 2

        # Check not_found field
        assert "not_found" in data
        assert len(data["not_found"]) == 2
        assert "entity:person/nonexistent-person" in data["not_found"]
        assert "entity:person/another-missing" in data["not_found"]

        # Verify found entities are correct
        entity_ids = [e["id"] for e in data["entities"]]
        assert "entity:person/ram-chandra-poudel" in entity_ids
        assert "entity:person/sher-bahadur-deuba" in entity_ids

    @pytest.mark.asyncio
    async def test_batch_lookup_all_not_found(self, client):
        """Test batch lookup when no entities exist."""
        ids = "entity:person/fake1,entity:person/fake2,entity:person/fake3"

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["requested"] == 3
        assert len(data["entities"]) == 0
        assert len(data["not_found"]) == 3

    @pytest.mark.asyncio
    async def test_batch_lookup_with_whitespace(self, client):
        """Test batch lookup handles whitespace in comma-separated list."""
        ids = "entity:person/ram-chandra-poudel , entity:person/sher-bahadur-deuba , entity:person/khadga-prasad-oli"

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert data["requested"] == 3

    @pytest.mark.asyncio
    async def test_batch_lookup_empty_ids(self, client):
        """Test batch lookup with empty ids parameter."""
        response = await client.get("/api/entities?ids=")

        assert response.status_code == 400
        data = response.json()

        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_batch_lookup_only_commas(self, client):
        """Test batch lookup with only commas (no valid IDs)."""
        response = await client.get("/api/entities?ids=,,,")

        assert response.status_code == 400
        data = response.json()

        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "INVALID_REQUEST"


# ============================================================================
# Batch Size Validation Tests
# ============================================================================


class TestBatchSizeValidation:
    """Tests for batch size limit enforcement (max 25)."""

    @pytest.mark.asyncio
    async def test_batch_lookup_at_max_limit(self, client):
        """Test batch lookup with exactly 25 entities (max allowed)."""
        # Create 25 entity IDs
        ids = ",".join([f"entity:person/test-person-{i}" for i in range(25)])

        response = await client.get(f"/api/entities?ids={ids}")

        # Should succeed (even though entities don't exist)
        assert response.status_code == 200
        data = response.json()

        assert data["requested"] == 25
        # All will be in not_found since they don't exist
        assert data["total"] == 0
        assert len(data["not_found"]) == 25

    @pytest.mark.asyncio
    async def test_batch_lookup_exceeds_limit(self, client):
        """Test batch lookup with 26 entities (exceeds max)."""
        # Create 26 entity IDs
        ids = ",".join([f"entity:person/test-person-{i}" for i in range(26)])

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 400
        data = response.json()

        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "BATCH_SIZE_EXCEEDED"
        assert "25" in data["detail"]["error"]["message"]

    @pytest.mark.asyncio
    async def test_batch_lookup_far_exceeds_limit(self, client):
        """Test batch lookup with 100 entities (far exceeds max)."""
        ids = ",".join([f"entity:person/test-person-{i}" for i in range(100)])

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 400
        data = response.json()

        assert data["detail"]["error"]["code"] == "BATCH_SIZE_EXCEEDED"


# ============================================================================
# Parameter Exclusivity Tests
# ============================================================================


class TestParameterExclusivity:
    """Tests that 'ids' parameter cannot be combined with other parameters."""

    @pytest.mark.asyncio
    async def test_batch_lookup_with_query_fails(self, client):
        """Test that batch lookup cannot be combined with query parameter."""
        response = await client.get(
            "/api/entities?ids=entity:person/ram-chandra-poudel&query=poudel"
        )

        assert response.status_code == 400
        data = response.json()

        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "INVALID_REQUEST"
        assert "cannot be combined" in data["detail"]["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_batch_lookup_with_entity_type_fails(self, client):
        """Test that batch lookup cannot be combined with entity_type parameter."""
        response = await client.get(
            "/api/entities?ids=entity:person/ram-chandra-poudel&entity_type=person"
        )

        assert response.status_code == 400
        data = response.json()

        assert data["detail"]["error"]["code"] == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_batch_lookup_with_sub_type_fails(self, client):
        """Test that batch lookup cannot be combined with sub_type parameter."""
        response = await client.get(
            "/api/entities?ids=entity:organization/political_party/nepali-congress&sub_type=political_party"
        )

        assert response.status_code == 400
        data = response.json()

        assert data["detail"]["error"]["code"] == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_batch_lookup_with_attributes_fails(self, client):
        """Test that batch lookup cannot be combined with attributes parameter."""
        response = await client.get(
            '/api/entities?ids=entity:person/ram-chandra-poudel&attributes={"party":"nepali-congress"}'
        )

        assert response.status_code == 400
        data = response.json()

        assert data["detail"]["error"]["code"] == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_batch_lookup_with_limit_fails(self, client):
        """Test that batch lookup cannot be combined with limit parameter."""
        response = await client.get(
            "/api/entities?ids=entity:person/ram-chandra-poudel&limit=50"
        )

        assert response.status_code == 400
        data = response.json()

        assert data["detail"]["error"]["code"] == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_batch_lookup_with_offset_fails(self, client):
        """Test that batch lookup cannot be combined with offset parameter."""
        response = await client.get(
            "/api/entities?ids=entity:person/ram-chandra-poudel&offset=10"
        )

        assert response.status_code == 400
        data = response.json()

        assert data["detail"]["error"]["code"] == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_batch_lookup_with_multiple_params_fails(self, client):
        """Test that batch lookup fails with multiple other parameters."""
        response = await client.get(
            "/api/entities?ids=entity:person/ram-chandra-poudel&query=test&entity_type=person&limit=10"
        )

        assert response.status_code == 400
        data = response.json()

        assert data["detail"]["error"]["code"] == "INVALID_REQUEST"


# ============================================================================
# Response Format Tests
# ============================================================================


class TestBatchResponseFormat:
    """Tests for batch lookup response format."""

    @pytest.mark.asyncio
    async def test_batch_response_has_required_fields(self, client):
        """Test that batch response includes all required fields."""
        ids = "entity:person/ram-chandra-poudel"

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "entities" in data
        assert "total" in data
        assert "requested" in data

        # Optional fields (not present for search mode)
        assert "limit" not in data or data.get("limit") is None
        assert "offset" not in data or data.get("offset") is None

    @pytest.mark.asyncio
    async def test_batch_response_entity_structure(self, client):
        """Test that returned entities have correct structure."""
        ids = "entity:person/ram-chandra-poudel"

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 200
        data = response.json()

        entity = data["entities"][0]

        # Check entity structure
        assert "id" in entity
        assert "slug" in entity
        assert "type" in entity
        assert "names" in entity
        assert "attributes" in entity
        assert "created_at" in entity

    @pytest.mark.asyncio
    async def test_batch_response_not_found_optional(self, client):
        """Test that not_found field is optional when all entities exist."""
        ids = "entity:person/ram-chandra-poudel,entity:person/sher-bahadur-deuba"

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 200
        data = response.json()

        # not_found should be absent when all entities found
        assert "not_found" not in data


# ============================================================================
# Integration Tests
# ============================================================================


class TestBatchLookupIntegration:
    """Integration tests for batch lookup with real scenarios."""

    @pytest.mark.asyncio
    async def test_batch_lookup_mixed_entity_types(self, client):
        """Test batch lookup with different entity types."""
        ids = ",".join(
            [
                "entity:person/ram-chandra-poudel",
                "entity:organization/political_party/nepali-congress",
                "entity:person/sher-bahadur-deuba",
            ]
        )

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert data["requested"] == 3

        # Verify mixed types
        entity_types = [e["type"] for e in data["entities"]]
        assert "person" in entity_types
        assert "organization" in entity_types

    @pytest.mark.asyncio
    async def test_batch_lookup_preserves_entity_data(self, client):
        """Test that batch lookup returns complete entity data."""
        ids = "entity:person/ram-chandra-poudel"

        response = await client.get(f"/api/entities?ids={ids}")

        assert response.status_code == 200
        data = response.json()

        entity = data["entities"][0]

        # Verify complete data is returned
        assert entity["id"] == "entity:person/ram-chandra-poudel"
        assert entity["slug"] == "ram-chandra-poudel"
        assert entity["type"] == "person"
        assert len(entity["names"]) > 0
        assert entity["names"][0]["en"]["full"] == "Ram Chandra Poudel"

    @pytest.mark.asyncio
    async def test_regular_search_still_works(self, client):
        """Test that regular search endpoint still works after batch implementation."""
        response = await client.get("/api/entities?query=poudel")

        assert response.status_code == 200
        data = response.json()

        # Should have search response format
        assert "entities" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        # Batch-specific fields should not be present (or be None if present)
        # Note: Pydantic exclude_none may not work perfectly, so we check both
        if "requested" in data:
            assert data["requested"] is None
        if "not_found" in data:
            assert data["not_found"] is None
