"""Tests for FileDatabase N-level entity_prefix traversal — Task 14.12 (Red phase).

Requirement 21.12: list_entities must discover entities stored at 1-, 2-, and
3-level directory depths. _entity_from_dict must load both old-style entities
(no entity_prefix) and new-style entities (entity_prefix set).

Test Coverage:
- list_entities discovers entities at 1-level depth (entity/person/)
- list_entities discovers entities at 2-level depth (entity/organization/political_party/)
- list_entities discovers entities at 3-level depth (entity/organization/nepal_govt/moha/)
- list_entities discovers mixed-depth entities in a single call
- list_entities entity_type filter still works with 3-level entities
- _entity_from_dict loads old-style entity (no entity_prefix)
- _entity_from_dict loads new-style entity (entity_prefix set)
- _entity_from_dict assigns correct Python class from first prefix segment
"""

from datetime import UTC, datetime

import pytest

from nes.core.models.base import Name, NameKind
from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES
from nes.core.models.organization import Organization, PoliticalParty
from nes.core.models.person import Person
from nes.core.models.version import Author, VersionSummary, VersionType
from nes.database.file_database import FileDatabase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _version_summary(entity_id: str) -> VersionSummary:
    return VersionSummary(
        entity_or_relationship_id=entity_id,
        type=VersionType.ENTITY,
        version_number=1,
        author=Author(slug="system"),
        change_description="Test entity",
        created_at=datetime.now(UTC),
    )


def _name(en_full: str, ne_full: str) -> Name:
    return Name(
        kind=NameKind.PRIMARY,
        en={"full": en_full},
        ne={"full": ne_full},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(temp_db_path):
    return FileDatabase(base_path=str(temp_db_path))


@pytest.fixture
def person_entity():
    """1-level path: entity/person/rabi-lamichhane.json"""
    return Person(
        slug="rabi-lamichhane",
        names=[_name("Rabi Lamichhane", "रबी लामिछाने")],
        version_summary=_version_summary("entity:person/rabi-lamichhane"),
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def political_party_entity():
    """2-level path: entity/organization/political_party/rastriya-swatantra-party.json"""
    return PoliticalParty(
        slug="rastriya-swatantra-party",
        names=[_name("Rastriya Swatantra Party", "राष्ट्रिय स्वतन्त्र पार्टी")],
        version_summary=_version_summary(
            "entity:organization/political_party/rastriya-swatantra-party"
        ),
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def three_level_org_entity():
    """3-level path: entity/organization/nepal_govt/moha/department-of-immigration.json"""
    ALLOWED_ENTITY_PREFIXES.add("organization/nepal_govt/moha")
    entity = Organization(
        slug="department-of-immigration",
        entity_prefix="organization/nepal_govt/moha",
        names=[_name("Department of Immigration", "आप्रवासन विभाग")],
        version_summary=_version_summary(
            "entity:organization/nepal_govt/moha/department-of-immigration"
        ),
        created_at=datetime.now(UTC),
    )
    yield entity
    ALLOWED_ENTITY_PREFIXES.discard("organization/nepal_govt/moha")


# ---------------------------------------------------------------------------
# Tests: list_entities depth traversal
# ---------------------------------------------------------------------------


class TestListEntitiesDepthTraversal:
    """list_entities must discover entities at all valid directory depths."""

    @pytest.mark.asyncio
    async def test_discovers_one_level_deep_entities(self, db, person_entity):
        """list_entities finds entities stored at entity/{type}/{slug}.json."""
        await db.put_entity(person_entity)

        results = await db.list_entities()

        ids = [e.id for e in results]
        assert "entity:person/rabi-lamichhane" in ids

    @pytest.mark.asyncio
    async def test_discovers_two_level_deep_entities(self, db, political_party_entity):
        """list_entities finds entities stored at entity/{type}/{subtype}/{slug}.json."""
        await db.put_entity(political_party_entity)

        results = await db.list_entities()

        ids = [e.id for e in results]
        assert "entity:organization/political_party/rastriya-swatantra-party" in ids

    @pytest.mark.asyncio
    async def test_discovers_three_level_deep_entities(
        self, db, three_level_org_entity
    ):
        """list_entities finds entities stored at entity/{s1}/{s2}/{s3}/{slug}.json."""
        await db.put_entity(three_level_org_entity)

        results = await db.list_entities()

        ids = [e.id for e in results]
        assert "entity:organization/nepal_govt/moha/department-of-immigration" in ids

    @pytest.mark.asyncio
    async def test_discovers_mixed_depth_entities_in_single_call(
        self, db, person_entity, political_party_entity, three_level_org_entity
    ):
        """list_entities finds entities at all depths in one call."""
        await db.put_entity(person_entity)
        await db.put_entity(political_party_entity)
        await db.put_entity(three_level_org_entity)

        results = await db.list_entities()

        ids = {e.id for e in results}
        assert "entity:person/rabi-lamichhane" in ids
        assert "entity:organization/political_party/rastriya-swatantra-party" in ids
        assert "entity:organization/nepal_govt/moha/department-of-immigration" in ids

    @pytest.mark.asyncio
    async def test_entity_type_filter_includes_three_level_org_entities(
        self, db, three_level_org_entity
    ):
        """list_entities(entity_type='organization') includes 3-level org entities."""
        await db.put_entity(three_level_org_entity)

        results = await db.list_entities(entity_type="organization")

        ids = [e.id for e in results]
        assert "entity:organization/nepal_govt/moha/department-of-immigration" in ids

    @pytest.mark.asyncio
    async def test_entity_type_filter_excludes_other_types(
        self, db, person_entity, three_level_org_entity
    ):
        """list_entities(entity_type='person') does not return organization entities."""
        await db.put_entity(person_entity)
        await db.put_entity(three_level_org_entity)

        results = await db.list_entities(entity_type="person")

        ids = [e.id for e in results]
        assert "entity:person/rabi-lamichhane" in ids
        assert (
            "entity:organization/nepal_govt/moha/department-of-immigration" not in ids
        )

    @pytest.mark.asyncio
    async def test_three_level_entity_has_entity_prefix_after_load(
        self, db, three_level_org_entity
    ):
        """An entity retrieved via list_entities retains its entity_prefix value."""
        await db.put_entity(three_level_org_entity)

        results = await db.list_entities()

        moha_entities = [
            e
            for e in results
            if e.id == "entity:organization/nepal_govt/moha/department-of-immigration"
        ]
        assert len(moha_entities) == 1
        assert moha_entities[0].entity_prefix == "organization/nepal_govt/moha"


# ---------------------------------------------------------------------------
# Tests: _entity_from_dict with and without entity_prefix
# ---------------------------------------------------------------------------


class TestEntityFromDictWithEntityPrefix:
    """_entity_from_dict must load both old-style and new-style entities correctly."""

    def _base_version_summary_dict(self, entity_id: str) -> dict:
        return {
            "entity_or_relationship_id": entity_id,
            "type": "ENTITY",
            "version_number": 1,
            "author": {"slug": "system"},
            "change_description": "Initial",
            "created_at": datetime.now(UTC).isoformat(),
        }

    def test_loads_old_style_person_entity(self, db):
        """_entity_from_dict loads a person without entity_prefix (backward compat)."""
        data = {
            "type": "person",
            "sub_type": None,
            "slug": "rabi-lamichhane",
            "entity_prefix": None,
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {"full": "Rabi Lamichhane"},
                    "ne": {"full": "रबी लामिछाने"},
                }
            ],
            "created_at": datetime.now(UTC).isoformat(),
            "version_summary": self._base_version_summary_dict(
                "entity:person/rabi-lamichhane"
            ),
        }

        entity = db._entity_from_dict(data)

        assert entity.slug == "rabi-lamichhane"
        assert entity.id == "entity:person/rabi-lamichhane"
        assert entity.entity_prefix is None

    def test_loads_old_style_org_with_subtype(self, db):
        """_entity_from_dict loads org/political_party without entity_prefix (backward compat)."""
        data = {
            "type": "organization",
            "sub_type": "political_party",
            "slug": "rastriya-swatantra-party",
            "entity_prefix": None,
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {"full": "Rastriya Swatantra Party"},
                    "ne": {"full": "राष्ट्रिय स्वतन्त्र पार्टी"},
                }
            ],
            "created_at": datetime.now(UTC).isoformat(),
            "version_summary": self._base_version_summary_dict(
                "entity:organization/political_party/rastriya-swatantra-party"
            ),
        }

        entity = db._entity_from_dict(data)

        assert entity.slug == "rastriya-swatantra-party"
        assert (
            entity.id == "entity:organization/political_party/rastriya-swatantra-party"
        )
        assert entity.entity_prefix is None

    def test_loads_new_style_entity_with_three_level_prefix(self, db):
        """_entity_from_dict loads an entity that has a 3-level entity_prefix."""
        data = {
            "type": "organization",
            "sub_type": None,
            "slug": "department-of-immigration",
            "entity_prefix": "organization/nepal_govt/moha",
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {"full": "Department of Immigration"},
                    "ne": {"full": "आप्रवासन विभाग"},
                }
            ],
            "created_at": datetime.now(UTC).isoformat(),
            "version_summary": self._base_version_summary_dict(
                "entity:organization/nepal_govt/moha/department-of-immigration"
            ),
        }

        entity = db._entity_from_dict(data)

        assert entity.slug == "department-of-immigration"
        assert entity.entity_prefix == "organization/nepal_govt/moha"
        assert (
            entity.id == "entity:organization/nepal_govt/moha/department-of-immigration"
        )

    def test_three_level_entity_instantiated_as_organization(self, db):
        """An entity with 3-level org prefix is returned as an Organization instance."""
        data = {
            "type": "organization",
            "sub_type": None,
            "slug": "department-of-immigration",
            "entity_prefix": "organization/nepal_govt/moha",
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {"full": "Department of Immigration"},
                    "ne": {"full": "आप्रवासन विभाग"},
                }
            ],
            "created_at": datetime.now(UTC).isoformat(),
            "version_summary": self._base_version_summary_dict(
                "entity:organization/nepal_govt/moha/department-of-immigration"
            ),
        }

        entity = db._entity_from_dict(data)

        assert isinstance(entity, Organization)

    def test_entity_from_dict_missing_type_raises_value_error(self, db):
        """_entity_from_dict raises ValueError when 'type' field is absent."""
        data = {
            "entity_prefix": "organization/nepal_govt/moha",
            "slug": "department-of-immigration",
        }

        with pytest.raises(ValueError, match="type"):
            db._entity_from_dict(data)
