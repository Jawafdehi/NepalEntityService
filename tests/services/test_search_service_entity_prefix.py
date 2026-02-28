"""Tests for SearchService entity_prefix filtering — Task 14.14 (Red phase).

Requirement 21.10: search_entities must accept an entity_prefix parameter and
return entities whose entity_prefix matches using startswith logic.

Test Coverage:
- search_entities(entity_prefix=exact_3_level) returns only entities with that exact prefix
- search_entities(entity_prefix=partial_2_level) returns all children (startswith match)
- entity_prefix filter combined with text query
- entity_prefix filter combined with pagination
- old-style entity_type/sub_type params still work (backward compat regression)
- unknown entity_prefix returns empty list
"""

from datetime import UTC, datetime

import pytest

from nes.core.models.base import Name, NameKind
from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES
from nes.core.models.organization import Organization, PoliticalParty
from nes.core.models.person import Person
from nes.core.models.version import Author, VersionSummary, VersionType
from nes.database.file_database import FileDatabase
from nes.services.search import SearchService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _version_summary(entity_id: str) -> VersionSummary:
    return VersionSummary(
        entity_or_relationship_id=entity_id,
        type=VersionType.ENTITY,
        version_number=1,
        author=Author(slug="system"),
        change_description="Test",
        created_at=datetime.now(UTC),
    )


def _name(en_full: str, ne_full: str) -> Name:
    return Name(kind=NameKind.PRIMARY, en={"full": en_full}, ne={"full": ne_full})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def register_test_prefixes():
    """Register 3-level prefixes used in these tests and clean up after."""
    test_prefixes = {
        "organization/nepal_govt/moha",
        "organization/nepal_govt/mol",
    }
    ALLOWED_ENTITY_PREFIXES.update(test_prefixes)
    yield
    for p in test_prefixes:
        ALLOWED_ENTITY_PREFIXES.discard(p)


@pytest.fixture
def db(temp_db_path):
    return FileDatabase(base_path=str(temp_db_path))


@pytest.fixture
def service(db):
    return SearchService(database=db)


@pytest.fixture
def moha_department(db):
    """organization/nepal_govt/moha — Department of Immigration."""
    entity = Organization(
        slug="department-of-immigration",
        entity_prefix="organization/nepal_govt/moha",
        names=[_name("Department of Immigration", "आप्रवासन विभाग")],
        version_summary=_version_summary(
            "entity:organization/nepal_govt/moha/department-of-immigration"
        ),
        created_at=datetime.now(UTC),
    )
    import asyncio

    asyncio.run(db.put_entity(entity))
    return entity


@pytest.fixture
def mol_section(db):
    """organization/nepal_govt/mol — Legal Aid Section."""
    entity = Organization(
        slug="legal-aid-section",
        entity_prefix="organization/nepal_govt/mol",
        names=[_name("Legal Aid Section", "कानुनी सहायता शाखा")],
        version_summary=_version_summary(
            "entity:organization/nepal_govt/mol/legal-aid-section"
        ),
        created_at=datetime.now(UTC),
    )
    import asyncio

    asyncio.run(db.put_entity(entity))
    return entity


@pytest.fixture
def political_party(db):
    """organization/political_party — Nepali Congress."""
    entity = PoliticalParty(
        slug="nepali-congress",
        names=[_name("Nepali Congress", "नेपाली कांग्रेस")],
        version_summary=_version_summary(
            "entity:organization/political_party/nepali-congress"
        ),
        created_at=datetime.now(UTC),
    )
    import asyncio

    asyncio.run(db.put_entity(entity))
    return entity


@pytest.fixture
def politician(db):
    """person — Rabi Lamichhane."""
    entity = Person(
        slug="rabi-lamichhane",
        names=[_name("Rabi Lamichhane", "रबी लामिछाने")],
        version_summary=_version_summary("entity:person/rabi-lamichhane"),
        created_at=datetime.now(UTC),
    )
    import asyncio

    asyncio.run(db.put_entity(entity))
    return entity


# ---------------------------------------------------------------------------
# Tests: entity_prefix filtering
# ---------------------------------------------------------------------------


class TestSearchEntitiesEntityPrefix:
    """search_entities must filter by entity_prefix using startswith logic."""

    @pytest.mark.asyncio
    async def test_exact_three_level_prefix_returns_matching_entity(
        self, service, moha_department, mol_section
    ):
        """search_entities(entity_prefix='org/nepal_govt/moha') returns only moha entities."""
        results = await service.search_entities(
            entity_prefix="organization/nepal_govt/moha"
        )

        ids = [e.id for e in results]
        assert "entity:organization/nepal_govt/moha/department-of-immigration" in ids
        assert "entity:organization/nepal_govt/mol/legal-aid-section" not in ids

    @pytest.mark.asyncio
    async def test_exact_three_level_prefix_excludes_other_prefix(
        self, service, moha_department, mol_section
    ):
        """Exact prefix match does not return entities with a different 3-level prefix."""
        results = await service.search_entities(
            entity_prefix="organization/nepal_govt/mol"
        )

        ids = [e.id for e in results]
        assert "entity:organization/nepal_govt/mol/legal-aid-section" in ids
        assert (
            "entity:organization/nepal_govt/moha/department-of-immigration" not in ids
        )

    @pytest.mark.asyncio
    async def test_partial_prefix_returns_all_children(
        self, service, moha_department, mol_section
    ):
        """search_entities(entity_prefix='org/nepal_govt') returns all children (startswith)."""
        results = await service.search_entities(entity_prefix="organization/nepal_govt")

        ids = {e.id for e in results}
        assert "entity:organization/nepal_govt/moha/department-of-immigration" in ids
        assert "entity:organization/nepal_govt/mol/legal-aid-section" in ids

    @pytest.mark.asyncio
    async def test_partial_prefix_excludes_unrelated_entities(
        self, service, moha_department, political_party, politician
    ):
        """entity_prefix filter excludes entities outside the prefix subtree."""
        results = await service.search_entities(entity_prefix="organization/nepal_govt")

        ids = [e.id for e in results]
        assert "entity:organization/political_party/nepali-congress" not in ids
        assert "entity:person/rabi-lamichhane" not in ids

    @pytest.mark.asyncio
    async def test_entity_prefix_combined_with_text_query(
        self, service, moha_department, mol_section
    ):
        """entity_prefix and text query can be combined (AND logic)."""
        results = await service.search_entities(
            entity_prefix="organization/nepal_govt",
            query="immigration",
        )

        ids = [e.id for e in results]
        assert "entity:organization/nepal_govt/moha/department-of-immigration" in ids
        assert "entity:organization/nepal_govt/mol/legal-aid-section" not in ids

    @pytest.mark.asyncio
    async def test_entity_prefix_combined_with_pagination(
        self, service, moha_department, mol_section
    ):
        """entity_prefix filter respects limit/offset pagination."""
        all_results = await service.search_entities(
            entity_prefix="organization/nepal_govt"
        )
        first_page = await service.search_entities(
            entity_prefix="organization/nepal_govt", limit=1, offset=0
        )
        second_page = await service.search_entities(
            entity_prefix="organization/nepal_govt", limit=1, offset=1
        )

        assert len(all_results) == 2
        assert len(first_page) == 1
        assert len(second_page) == 1
        # No overlap between pages
        assert first_page[0].id != second_page[0].id

    @pytest.mark.asyncio
    async def test_nonexistent_entity_prefix_returns_empty_list(
        self, service, moha_department
    ):
        """A valid prefix with no matching entities returns an empty list."""
        results = await service.search_entities(
            entity_prefix="organization/nepal_govt/moe"  # Ministry of Education — not in DB
        )

        assert results == []


# ---------------------------------------------------------------------------
# Tests: backward compatibility — old-style entity_type/sub_type still works
# ---------------------------------------------------------------------------


class TestSearchEntitiesBackwardCompat:
    """Old-style entity_type and sub_type filtering must still work."""

    @pytest.mark.asyncio
    async def test_entity_type_filter_still_works(
        self, service, politician, moha_department
    ):
        """search_entities(entity_type='person') still filters by type correctly."""
        results = await service.search_entities(entity_type="person")

        ids = [e.id for e in results]
        assert "entity:person/rabi-lamichhane" in ids
        assert (
            "entity:organization/nepal_govt/moha/department-of-immigration" not in ids
        )

    @pytest.mark.asyncio
    async def test_sub_type_filter_still_works(
        self, service, political_party, moha_department
    ):
        """search_entities(entity_type='organization', sub_type='political_party') still works."""
        results = await service.search_entities(
            entity_type="organization", sub_type="political_party"
        )

        ids = [e.id for e in results]
        assert "entity:organization/political_party/nepali-congress" in ids
        assert (
            "entity:organization/nepal_govt/moha/department-of-immigration" not in ids
        )

    @pytest.mark.asyncio
    async def test_no_filters_returns_all_entities(
        self, service, politician, political_party, moha_department
    ):
        """search_entities() with no filters returns all entities (regression)."""
        results = await service.search_entities()

        ids = {e.id for e in results}
        assert "entity:person/rabi-lamichhane" in ids
        assert "entity:organization/political_party/nepali-congress" in ids
        assert "entity:organization/nepal_govt/moha/department-of-immigration" in ids
