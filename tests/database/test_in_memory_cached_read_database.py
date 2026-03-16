"""Tests for InMemoryCachedReadDatabase in nes.

Following TDD approach: Write failing tests first (Red phase).
These tests define the expected behavior of the in-memory cached read database.

Expected Behavior:
- Cache is automatically warmed with ALL entities and relationships at initialization
- All read operations (get, list, search) use the in-memory cache
- Cache never accesses underlying database after warming
- Write operations are rejected with clear error messages
- Version/Author operations delegate to underlying database (not cached)
"""

from datetime import UTC, date, datetime

import pytest

from nes.core.identifiers.builders import build_relationship_id
from nes.core.models.base import Name, NameKind
from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES
from nes.core.models.organization import Organization, PoliticalParty
from nes.core.models.person import Person
from nes.core.models.relationship import Relationship
from nes.core.models.version import Author, Version, VersionSummary, VersionType
from nes.database.file_database import FileDatabase
from nes.database.in_memory_cached_read_database import InMemoryCachedReadDatabase


def create_person(slug: str, full_name: str) -> Person:
    """Helper to create a Person entity with minimal boilerplate."""
    entity_id = f"entity:person/{slug}"
    return Person(
        slug=slug,
        names=[Name(kind=NameKind.PRIMARY, en={"full": full_name})],
        version_summary=create_version_summary(entity_id, VersionType.ENTITY),
        created_at=datetime.now(UTC),
    )


def create_political_party(slug: str, full_name: str) -> PoliticalParty:
    """Helper to create a PoliticalParty entity with minimal boilerplate."""
    entity_id = f"entity:organization/political_party/{slug}"
    return PoliticalParty(
        slug=slug,
        names=[Name(kind=NameKind.PRIMARY, en={"full": full_name})],
        version_summary=create_version_summary(entity_id, VersionType.ENTITY),
        created_at=datetime.now(UTC),
    )


def create_relationship(
    source_id: str, target_id: str, rel_type: str, start_date: date
) -> Relationship:
    """Helper to create a Relationship with minimal boilerplate."""
    relationship_id = build_relationship_id(source_id, target_id, rel_type)
    return Relationship(
        source_entity_id=source_id,
        target_entity_id=target_id,
        type=rel_type,
        start_date=start_date,
        version_summary=create_version_summary(
            relationship_id, VersionType.RELATIONSHIP
        ),
        created_at=datetime.now(UTC),
    )


def create_version_summary(
    entity_or_relationship_id: str, version_type: VersionType
) -> VersionSummary:
    """Helper to create a VersionSummary with minimal boilerplate."""
    return VersionSummary(
        entity_or_relationship_id=entity_or_relationship_id,
        type=version_type,
        version_number=1,
        author=Author(slug="system"),
        change_description="Initial",
        created_at=datetime.now(UTC),
    )


def create_version(
    entity_or_relationship_id: str,
    change_description: str,
    version_type: VersionType = VersionType.ENTITY,
) -> Version:
    """Helper to create a Version with minimal boilerplate."""
    return Version(
        entity_or_relationship_id=entity_or_relationship_id,
        type=version_type,
        version_number=1,
        author=Author(slug="system"),
        change_description=change_description,
        created_at=datetime.now(UTC),
    )


def create_author(slug: str, name: str | None = None) -> Author:
    """Helper to create an Author with minimal boilerplate."""
    return Author(slug=slug, name=name)


class TestCacheWarming:
    """Test automatic cache warming at initialization."""

    @pytest.mark.asyncio
    async def test_all_entities_loaded_into_cache_on_init(self, temp_db_path):
        """Cache should contain all entities from underlying database after initialization."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        # Create test entities
        person = create_person("harka-sampang", "Harka Sampang")
        party = create_political_party(
            "rastriya-swatantra-party", "Rastriya Swatantra Party"
        )

        await underlying_db.put_entity(person)
        await underlying_db.put_entity(party)

        # Initialize cached database - should load all entities
        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # Should be able to retrieve both entities
        result1 = await cached_db.get_entity("entity:person/harka-sampang")
        result2 = await cached_db.get_entity(
            "entity:organization/political_party/rastriya-swatantra-party"
        )

        assert result1 is not None
        assert result1.slug == "harka-sampang"
        assert result2 is not None
        assert result2.slug == "rastriya-swatantra-party"

    @pytest.mark.asyncio
    async def test_all_relationships_loaded_into_cache_on_init(self, temp_db_path):
        """Cache should contain all relationships from underlying database after initialization."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        # Create entities
        person = create_person("harka-sampang", "Harka Sampang")
        party = create_political_party(
            "rastriya-swatantra-party", "Rastriya Swatantra Party"
        )

        await underlying_db.put_entity(person)
        await underlying_db.put_entity(party)

        # Create relationship
        relationship = create_relationship(
            "entity:person/harka-sampang",
            "entity:organization/political_party/rastriya-swatantra-party",
            "MEMBER_OF",
            date(2022, 6, 1),
        )
        await underlying_db.put_relationship(relationship)

        # Initialize cached database - should load all relationships
        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # Should be able to retrieve relationship
        result = await cached_db.get_relationship(relationship.id)
        assert result is not None
        assert result.type == "MEMBER_OF"

    @pytest.mark.asyncio
    async def test_empty_database_results_in_empty_cache(self, temp_db_path):
        """Empty underlying database should result in empty cache."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))
        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # Should return None for non-existent entities
        result = await cached_db.get_entity("entity:person/nonexistent")
        assert result is None

        # Should return empty list
        entities = await cached_db.list_entities()
        assert len(entities) == 0

    @pytest.mark.asyncio
    async def test_large_database_fully_cached(self, temp_db_path):
        """All entities should be cached regardless of database size."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        # Create 100 entities
        for i in range(100):
            person = create_person(f"person-{i}", f"Person {i}")
            await underlying_db.put_entity(person)

        # Initialize cached database
        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # All 100 entities should be retrievable
        entities = await cached_db.list_entities(limit=200)
        assert len(entities) == 100


class TestReadOperations:
    """Test read operations from cache."""

    @pytest.mark.asyncio
    async def test_get_entity_from_cache(self, temp_db_path):
        """Test retrieving entity from cache."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        person = create_person("rabindra-mishra", "Rabindra Mishra")
        await underlying_db.put_entity(person)

        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # Get entity from cache
        result = await cached_db.get_entity("entity:person/rabindra-mishra")

        assert result is not None
        assert result.slug == "rabindra-mishra"
        assert result.names[0].en.full == "Rabindra Mishra"

    @pytest.mark.asyncio
    async def test_get_nonexistent_entity(self, temp_db_path):
        """Test retrieving nonexistent entity returns None."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))
        cached_db = InMemoryCachedReadDatabase(underlying_db)

        result = await cached_db.get_entity("entity:person/nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_relationship_from_cache(self, temp_db_path):
        """Test retrieving relationship from cache."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        # Create entities
        person = create_person("miraj-dhungana", "Miraj Dhungana")
        party = create_political_party("shram-sanskriti-party", "Shram Sanskriti Party")

        await underlying_db.put_entity(person)
        await underlying_db.put_entity(party)

        relationship = create_relationship(
            "entity:person/miraj-dhungana",
            "entity:organization/political_party/shram-sanskriti-party",
            "MEMBER_OF",
            date(2023, 1, 1),
        )
        await underlying_db.put_relationship(relationship)

        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # Get relationship from cache
        result = await cached_db.get_relationship(relationship.id)

        assert result is not None
        assert result.type == "MEMBER_OF"
        assert result.source_entity_id == "entity:person/miraj-dhungana"

    @pytest.mark.asyncio
    async def test_list_entities_respects_pagination(self, temp_db_path):
        """list_entities should respect limit and offset parameters."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        # Create 10 entities
        for i in range(10):
            person = create_person(f"person-{i}", f"Person {i}")
            await underlying_db.put_entity(person)

        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # Test limit
        results = await cached_db.list_entities(limit=5)
        assert len(results) == 5

        # Test offset
        results = await cached_db.list_entities(limit=5, offset=5)
        assert len(results) == 5

        # Test limit beyond available
        results = await cached_db.list_entities(limit=20)
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_list_entities_filters_by_type(self, temp_db_path):
        """list_entities should filter by entity_type parameter."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        # Create person
        person = create_person("person-1", "Person 1")

        # Create party
        party = create_political_party("nepali-congress", "Nepali Congress")

        await underlying_db.put_entity(person)
        await underlying_db.put_entity(party)

        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # Filter by person type
        results = await cached_db.list_entities(entity_type="person")
        assert len(results) == 1
        assert results[0].slug == "person-1"

        # Filter by organization type
        results = await cached_db.list_entities(entity_type="organization")
        assert len(results) == 1
        assert results[0].slug == "nepali-congress"

    @pytest.mark.asyncio
    async def test_list_relationships_returns_all_cached_relationships(
        self, temp_db_path
    ):
        """list_relationships should return relationships from cache."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        # Create entities
        person = create_person("person-1", "Person 1")
        party = create_political_party("party-1", "Party 1")

        await underlying_db.put_entity(person)
        await underlying_db.put_entity(party)

        # Create 3 relationships with valid types
        rel_types = ["MEMBER_OF", "EMPLOYED_BY", "AFFILIATED_WITH"]
        for i in range(3):
            relationship = create_relationship(
                "entity:person/person-1",
                "entity:organization/political_party/party-1",
                rel_types[i],
                date(2020 + i, 1, 1),
            )
            await underlying_db.put_relationship(relationship)

        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # Should return all 3 relationships
        results = await cached_db.list_relationships()
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_entities_finds_matching_names(self, temp_db_path):
        """search_entities should find entities by name query."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        # Create entities with searchable names
        person1 = create_person("ram-kumar-sharma", "Ram Kumar Sharma")
        person2 = create_person("shyam-prasad-sharma", "Shyam Prasad Sharma")
        person3 = create_person("pushpa-kamal-dahal", "Pushpa Kamal Dahal")

        await underlying_db.put_entity(person1)
        await underlying_db.put_entity(person2)
        await underlying_db.put_entity(person3)

        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # Search for "Sharma" - should find 2
        results = await cached_db.search_entities(query="Sharma")
        assert len(results) == 2

        # Search for "Pushpa" - should find 1
        results = await cached_db.search_entities(query="Pushpa")
        assert len(results) == 1


class TestWriteOperationsRejection:
    """Test that write operations are properly rejected."""

    @pytest.mark.asyncio
    async def test_put_entity_raises_error(self, temp_db_path):
        """Test that put_entity raises ValueError with clear message."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))
        cached_db = InMemoryCachedReadDatabase(underlying_db)

        person = create_person("test-person", "Test Person")

        with pytest.raises(
            ValueError, match="Read-only database does not support write operations"
        ):
            await cached_db.put_entity(person)

    @pytest.mark.asyncio
    async def test_delete_entity_raises_error(self, temp_db_path):
        """Test that delete_entity raises ValueError with clear message."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))
        cached_db = InMemoryCachedReadDatabase(underlying_db)

        with pytest.raises(
            ValueError, match="Read-only database does not support write operations"
        ):
            await cached_db.delete_entity("entity:person/test-person")

    @pytest.mark.asyncio
    async def test_put_relationship_raises_error(self, temp_db_path):
        """Test that put_relationship raises ValueError with clear message."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))
        cached_db = InMemoryCachedReadDatabase(underlying_db)

        relationship = create_relationship(
            "entity:person/person-1",
            "entity:organization/political_party/party-1",
            "MEMBER_OF",
            date(2020, 1, 1),
        )

        with pytest.raises(
            ValueError, match="Read-only database does not support write operations"
        ):
            await cached_db.put_relationship(relationship)

    @pytest.mark.asyncio
    async def test_delete_relationship_raises_error(self, temp_db_path):
        """Test that delete_relationship raises ValueError with clear message."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))
        cached_db = InMemoryCachedReadDatabase(underlying_db)

        with pytest.raises(
            ValueError, match="Read-only database does not support write operations"
        ):
            await cached_db.delete_relationship("relationship:test")


class TestVersionOperations:
    """Test that version operations delegate to underlying database."""

    @pytest.mark.asyncio
    async def test_version_write_operations_raise_error(self, temp_db_path):
        """Test that version write operations raise ValueError."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))
        cached_db = InMemoryCachedReadDatabase(underlying_db)

        version = create_version("entity:person/test", "Test")

        with pytest.raises(
            ValueError, match="Read-only database does not support write operations"
        ):
            await cached_db.put_version(version)

        with pytest.raises(
            ValueError, match="Read-only database does not support write operations"
        ):
            await cached_db.delete_version("version:entity:person/test/1")

    @pytest.mark.asyncio
    async def test_version_read_operations_delegate(self, temp_db_path):
        """Test that version read operations delegate to underlying database."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        # Create entity and version
        person = create_person("test-person", "Test Person")
        await underlying_db.put_entity(person)

        version = create_version("entity:person/test-person", "Initial version")
        await underlying_db.put_version(version)

        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # Test get_version
        result = await cached_db.get_version(version.id)
        assert result is not None
        assert result.version_number == 1

        # Test list_versions
        versions = await cached_db.list_versions()
        assert len(versions) >= 1


class TestAuthorOperations:
    """Test that author operations delegate to underlying database."""

    @pytest.mark.asyncio
    async def test_author_write_operations_raise_error(self, temp_db_path):
        """Test that author write operations raise ValueError."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))
        cached_db = InMemoryCachedReadDatabase(underlying_db)

        author = create_author("test-author")

        with pytest.raises(
            ValueError, match="Read-only database does not support write operations"
        ):
            await cached_db.put_author(author)

        with pytest.raises(
            ValueError, match="Read-only database does not support write operations"
        ):
            await cached_db.delete_author("author:test-author")

    @pytest.mark.asyncio
    async def test_author_read_operations_delegate(self, temp_db_path):
        """Test that author read operations delegate to underlying database."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        # Create author
        author = create_author("test-author", "Test Author")
        await underlying_db.put_author(author)

        cached_db = InMemoryCachedReadDatabase(underlying_db)

        # Test get_author
        result = await cached_db.get_author("author:test-author")
        assert result is not None
        assert result.slug == "test-author"

        # Test list_authors
        authors = await cached_db.list_authors()
        assert len(authors) >= 1


def create_org_with_prefix(
    slug: str, full_name: str, entity_prefix: str
) -> Organization:
    """Helper to create an Organization entity with a given entity_prefix."""
    from nes.core.models.entity import EntitySubType
    from nes.core.models.organization import GovernmentBody, Hospital

    entity_id = f"entity:{entity_prefix}/{slug}"

    # Determine the correct class and sub_type based on entity_prefix
    if entity_prefix.startswith("organization/government"):
        return GovernmentBody(
            slug=slug,
            entity_prefix=entity_prefix,
            sub_type=EntitySubType.GOVERNMENT_BODY,
            names=[Name(kind=NameKind.PRIMARY, en={"full": full_name})],
            version_summary=create_version_summary(entity_id, VersionType.ENTITY),
            created_at=datetime.now(UTC),
        )
    elif entity_prefix == "organization/hospital":
        return Hospital(
            slug=slug,
            entity_prefix=entity_prefix,
            sub_type=EntitySubType.HOSPITAL,
            names=[Name(kind=NameKind.PRIMARY, en={"full": full_name})],
            version_summary=create_version_summary(entity_id, VersionType.ENTITY),
            created_at=datetime.now(UTC),
        )
    else:
        return Organization(
            slug=slug,
            entity_prefix=entity_prefix,
            names=[Name(kind=NameKind.PRIMARY, en={"full": full_name})],
            version_summary=create_version_summary(entity_id, VersionType.ENTITY),
            created_at=datetime.now(UTC),
        )


class TestSearchEntitiesEntityPrefix:
    """InMemoryCachedReadDatabase.search_entities must filter by entity_prefix — GAP 2."""

    @pytest.mark.asyncio
    async def test_exact_three_level_prefix_returns_matching_entity(self, temp_db_path):
        """search_entities(entity_prefix=exact) returns only entities with that prefix."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        federal_dept = create_org_with_prefix(
            "department-of-immigration",
            "Department of Immigration",
            "organization/government/federal",
        )
        hospital = create_org_with_prefix(
            "bir-hospital",
            "Bir Hospital",
            "organization/hospital",
        )
        await underlying_db.put_entity(federal_dept)
        await underlying_db.put_entity(hospital)

        cached_db = InMemoryCachedReadDatabase(underlying_db)
        results = await cached_db.search_entities(
            entity_prefix="organization/government/federal"
        )

        ids = [e.id for e in results]
        assert "entity:organization/government/federal/department-of-immigration" in ids
        assert "entity:organization/hospital/bir-hospital" not in ids

    @pytest.mark.asyncio
    async def test_partial_prefix_returns_all_children(self, temp_db_path):
        """search_entities(entity_prefix=partial) returns all children via startswith match."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        federal_dept = create_org_with_prefix(
            "department-of-immigration",
            "Department of Immigration",
            "organization/government/federal",
        )
        hospital = create_org_with_prefix(
            "bir-hospital",
            "Bir Hospital",
            "organization/hospital",
        )
        politician = create_person("rabi-lamichhane", "Rabi Lamichhane")

        await underlying_db.put_entity(federal_dept)
        await underlying_db.put_entity(hospital)
        await underlying_db.put_entity(politician)

        cached_db = InMemoryCachedReadDatabase(underlying_db)
        results = await cached_db.search_entities(
            entity_prefix="organization/government"
        )

        ids = {e.id for e in results}
        assert "entity:organization/government/federal/department-of-immigration" in ids
        assert "entity:organization/hospital/bir-hospital" not in ids
        assert "entity:person/rabi-lamichhane" not in ids

    @pytest.mark.asyncio
    async def test_entity_prefix_excludes_unrelated_entities(self, temp_db_path):
        """entity_prefix filter does not return entities outside the prefix subtree."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        federal_dept = create_org_with_prefix(
            "department-of-immigration",
            "Department of Immigration",
            "organization/government/federal",
        )
        party = create_political_party("nepali-congress", "Nepali Congress")
        politician = create_person("rabi-lamichhane", "Rabi Lamichhane")

        await underlying_db.put_entity(federal_dept)
        await underlying_db.put_entity(party)
        await underlying_db.put_entity(politician)

        cached_db = InMemoryCachedReadDatabase(underlying_db)
        results = await cached_db.search_entities(
            entity_prefix="organization/government/federal"
        )

        ids = [e.id for e in results]
        assert "entity:organization/government/federal/department-of-immigration" in ids
        assert "entity:organization/political_party/nepali-congress" not in ids
        assert "entity:person/rabi-lamichhane" not in ids

    @pytest.mark.asyncio
    async def test_entity_prefix_no_match_returns_empty_list(self, temp_db_path):
        """entity_prefix with no matching entities returns an empty list."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        federal_dept = create_org_with_prefix(
            "department-of-immigration",
            "Department of Immigration",
            "organization/government/federal",
        )
        await underlying_db.put_entity(federal_dept)

        cached_db = InMemoryCachedReadDatabase(underlying_db)
        # organization/ngo exists in registry but no entities in DB
        results = await cached_db.search_entities(entity_prefix="organization/ngo")

        assert results == []

    @pytest.mark.asyncio
    async def test_entity_prefix_combined_with_text_query(self, temp_db_path):
        """entity_prefix and text query apply AND logic in the cached database."""
        underlying_db = FileDatabase(base_path=str(temp_db_path))

        federal_dept = create_org_with_prefix(
            "department-of-immigration",
            "Department of Immigration",
            "organization/government/federal",
        )
        hospital = create_org_with_prefix(
            "bir-hospital",
            "Bir Hospital",
            "organization/hospital",
        )
        await underlying_db.put_entity(federal_dept)
        await underlying_db.put_entity(hospital)

        cached_db = InMemoryCachedReadDatabase(underlying_db)
        results = await cached_db.search_entities(
            entity_prefix="organization/government",
            query="immigration",
        )

        ids = [e.id for e in results]
        assert "entity:organization/government/federal/department-of-immigration" in ids
        assert "entity:organization/hospital/bir-hospital" not in ids
