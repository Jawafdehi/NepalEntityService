"""API tests for entity_prefix query parameter — Task 14.16 (Red phase).

Requirement 21.11: GET /api/entities must accept an entity_prefix query parameter,
validate it against ALLOWED_ENTITY_PREFIXES (HTTP 400 on invalid), and pass it
through to search_entities. Old entity_type/sub_type params remain functional.

Test Coverage:
- GET /api/entities?entity_prefix=<exact> returns only matching entities
- GET /api/entities?entity_prefix=<partial> returns all children (startswith)
- GET /api/entities?entity_prefix=<invalid> returns HTTP 400
- GET /api/entities?entity_type=...&sub_type=... still works (backward compat regression)
- entity_prefix combined with text query
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from nes.api.app import app
from nes.config import Config
from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES
from nes.database.file_database import FileDatabase
from nes.services.publication import PublicationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_db_with_prefix_entities(tmp_path):
    """Database populated with entities at 1-, 2-, and 3-level prefix depths."""
    ALLOWED_ENTITY_PREFIXES.add("organization/nepal_govt")
    ALLOWED_ENTITY_PREFIXES.add("organization/nepal_govt/moha")
    ALLOWED_ENTITY_PREFIXES.add("organization/nepal_govt/mol")

    db = FileDatabase(base_path=str(tmp_path / "test-db"))
    pub = PublicationService(database=db)

    from nes.core.models.entity import EntitySubType, EntityType

    # 1-level: person
    await pub.create_entity(
        entity_type=EntityType.PERSON,
        entity_data={
            "slug": "rabi-lamichhane",
            "names": [{"kind": "PRIMARY", "en": {"full": "Rabi Lamichhane"}}],
        },
        author_id="author:test",
        change_description="setup",
    )

    # 2-level: organization/political_party
    await pub.create_entity(
        entity_type=EntityType.ORGANIZATION,
        entity_subtype=EntitySubType.POLITICAL_PARTY,
        entity_data={
            "slug": "nepali-congress",
            "names": [{"kind": "PRIMARY", "en": {"full": "Nepali Congress"}}],
        },
        author_id="author:test",
        change_description="setup",
    )

    # 3-level: organization/nepal_govt/moha
    await pub.create_entity(
        entity_prefix="organization/nepal_govt/moha",
        entity_data={
            "slug": "department-of-immigration",
            "names": [
                {"kind": "PRIMARY", "en": {"full": "Department of Immigration"}}
            ],
        },
        author_id="author:test",
        change_description="setup",
    )

    # 3-level: organization/nepal_govt/mol
    await pub.create_entity(
        entity_prefix="organization/nepal_govt/mol",
        entity_data={
            "slug": "legal-aid-section",
            "names": [{"kind": "PRIMARY", "en": {"full": "Legal Aid Section"}}],
        },
        author_id="author:test",
        change_description="setup",
    )

    yield db

    ALLOWED_ENTITY_PREFIXES.discard("organization/nepal_govt")
    ALLOWED_ENTITY_PREFIXES.discard("organization/nepal_govt/moha")
    ALLOWED_ENTITY_PREFIXES.discard("organization/nepal_govt/mol")


@pytest_asyncio.fixture
async def client(test_db_with_prefix_entities):
    """HTTP test client with prefix-entity database injected."""
    original_db = Config._database
    original_search_service = Config._search_service
    Config._database = test_db_with_prefix_entities
    Config._search_service = None  # force recreation with the new DB
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    Config._database = original_db
    Config._search_service = original_search_service


# ---------------------------------------------------------------------------
# Tests: entity_prefix filtering via API
# ---------------------------------------------------------------------------


class TestApiEntityPrefixFilter:
    """GET /api/entities?entity_prefix=... must filter by prefix."""

    @pytest.mark.asyncio
    async def test_exact_prefix_returns_matching_entities(self, client):
        """entity_prefix=organization/nepal_govt/moha returns only moha entities."""
        response = await client.get(
            "/api/entities",
            params={"entity_prefix": "organization/nepal_govt/moha"},
        )

        assert response.status_code == 200
        data = response.json()
        ids = [e["id"] for e in data["entities"]]
        assert "entity:organization/nepal_govt/moha/department-of-immigration" in ids
        assert "entity:organization/nepal_govt/mol/legal-aid-section" not in ids
        assert "entity:person/rabi-lamichhane" not in ids

    @pytest.mark.asyncio
    async def test_partial_prefix_returns_all_children(self, client):
        """entity_prefix=organization/nepal_govt returns all children (startswith)."""
        response = await client.get(
            "/api/entities",
            params={"entity_prefix": "organization/nepal_govt"},
        )

        assert response.status_code == 200
        data = response.json()
        ids = {e["id"] for e in data["entities"]}
        assert "entity:organization/nepal_govt/moha/department-of-immigration" in ids
        assert "entity:organization/nepal_govt/mol/legal-aid-section" in ids
        assert "entity:person/rabi-lamichhane" not in ids
        assert "entity:organization/political_party/nepali-congress" not in ids

    @pytest.mark.asyncio
    async def test_entity_prefix_combined_with_query(self, client):
        """entity_prefix combined with text query applies AND logic."""
        response = await client.get(
            "/api/entities",
            params={
                "entity_prefix": "organization/nepal_govt",
                "query": "immigration",
            },
        )

        assert response.status_code == 200
        data = response.json()
        ids = [e["id"] for e in data["entities"]]
        assert "entity:organization/nepal_govt/moha/department-of-immigration" in ids
        assert "entity:organization/nepal_govt/mol/legal-aid-section" not in ids
        # Prefix filter must exclude person entities even when query would match none of them
        assert "entity:person/rabi-lamichhane" not in ids
        # Only 1 entity should match (prefix=nepal_govt AND query=immigration)
        assert len(data["entities"]) == 1

    @pytest.mark.asyncio
    async def test_entity_prefix_response_has_entity_prefix_field(self, client):
        """Entities returned via entity_prefix filter include entity_prefix in their data."""
        response = await client.get(
            "/api/entities",
            params={"entity_prefix": "organization/nepal_govt/moha"},
        )

        assert response.status_code == 200
        data = response.json()
        # Exactly 1 entity should match this exact prefix
        assert len(data["entities"]) == 1
        entity = data["entities"][0]
        assert entity["id"] == "entity:organization/nepal_govt/moha/department-of-immigration"
        assert entity["entity_prefix"] == "organization/nepal_govt/moha"


# ---------------------------------------------------------------------------
# Tests: invalid entity_prefix → HTTP 400
# ---------------------------------------------------------------------------


class TestApiEntityPrefixValidation:
    """An entity_prefix not in ALLOWED_ENTITY_PREFIXES must return HTTP 400."""

    @pytest.mark.asyncio
    async def test_invalid_prefix_returns_400(self, client):
        """entity_prefix not in ALLOWED_ENTITY_PREFIXES returns HTTP 400."""
        response = await client.get(
            "/api/entities",
            params={"entity_prefix": "organization/unknown_ministry/xyz"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_prefix_error_body(self, client):
        """400 response includes a meaningful error code."""
        response = await client.get(
            "/api/entities",
            params={"entity_prefix": "totally/invalid/prefix"},
        )

        assert response.status_code == 400
        body = response.json()
        assert body["detail"]["error"]["code"] == "INVALID_ENTITY_PREFIX"

    @pytest.mark.asyncio
    async def test_valid_prefix_not_in_db_returns_200_empty(self, client):
        """A valid (known) prefix with no matching entities returns 200 with empty list."""
        # "organization" is in ALLOWED_ENTITY_PREFIXES but no exact-match entities
        # (the moha/mol entities have "organization/nepal_govt/..." prefixes, not bare "organization")
        ALLOWED_ENTITY_PREFIXES.add("organization/nepal_govt/moe")
        try:
            response = await client.get(
                "/api/entities",
                params={"entity_prefix": "organization/nepal_govt/moe"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["entities"] == []
        finally:
            ALLOWED_ENTITY_PREFIXES.discard("organization/nepal_govt/moe")


# ---------------------------------------------------------------------------
# Tests: backward compatibility
# ---------------------------------------------------------------------------


class TestApiEntityPrefixBackwardCompat:
    """Old entity_type/sub_type query params must still work."""

    @pytest.mark.asyncio
    async def test_entity_type_filter_still_works(self, client):
        """GET /api/entities?entity_type=person still returns person entities."""
        response = await client.get(
            "/api/entities", params={"entity_type": "person"}
        )

        assert response.status_code == 200
        data = response.json()
        ids = [e["id"] for e in data["entities"]]
        assert "entity:person/rabi-lamichhane" in ids
        assert "entity:organization/nepal_govt/moha/department-of-immigration" not in ids

    @pytest.mark.asyncio
    async def test_sub_type_filter_still_works(self, client):
        """GET /api/entities?entity_type=organization&sub_type=political_party still works."""
        response = await client.get(
            "/api/entities",
            params={"entity_type": "organization", "sub_type": "political_party"},
        )

        assert response.status_code == 200
        data = response.json()
        ids = [e["id"] for e in data["entities"]]
        assert "entity:organization/political_party/nepali-congress" in ids
        assert "entity:organization/nepal_govt/moha/department-of-immigration" not in ids
