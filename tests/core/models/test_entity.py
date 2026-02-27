"""Tests for Entity model in nes."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from nes.core.models.base import Name, NameKind
from nes.core.models.entity import Entity, ExternalIdentifier, IdentifierScheme
from nes.core.models.organization import PoliticalParty
from nes.core.models.person import Person
from nes.core.models.version import Author, VersionSummary, VersionType


def test_entity_requires_primary_name():
    """Test that Entity requires at least one PRIMARY name."""
    # Should fail without PRIMARY name
    with pytest.raises(ValidationError, match="PRIMARY"):
        Person(
            slug="test-entity",
            names=[Name(kind=NameKind.ALIAS, en={"full": "Alias Name"})],
            version_summary=VersionSummary(
                entity_or_relationship_id="entity:person/test-entity",
                type=VersionType.ENTITY,
                version_number=1,
                author=Author(slug="system"),
                change_description="Initial",
                created_at=datetime.now(UTC),
            ),
            created_at=datetime.now(UTC),
        )


def test_entity_with_multilingual_names():
    """Test Entity with both English and Nepali names."""
    entity = Person(
        slug="test-entity",
        names=[
            Name(
                kind=NameKind.PRIMARY,
                en={"full": "Test Person", "given": "Test", "family": "Person"},
                ne={"full": "परीक्षण व्यक्ति"},
            )
        ],
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:person/test-entity",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert entity.slug == "test-entity"
    assert entity.type == "person"
    assert entity.sub_type is None
    assert entity.names[0].en.full == "Test Person"
    assert entity.names[0].ne.full == "परीक्षण व्यक्ति"
    assert entity.id == "entity:person/test-entity"


def test_entity_computed_id():
    """Test that Entity.id is computed correctly for organizations."""
    entity = PoliticalParty(
        slug="nepali-congress",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Nepali Congress"})],
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:organization/political_party/nepali-congress",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert entity.id == "entity:organization/political_party/nepali-congress"


def test_entity_slug_validation():
    """Test Entity slug validation."""
    # Invalid slug (too short)
    with pytest.raises(ValidationError):
        Person(
            slug="ab",
            names=[Name(kind=NameKind.PRIMARY, en={"full": "Test"})],
            version_summary=VersionSummary(
                entity_or_relationship_id="entity:person/ab",
                type=VersionType.ENTITY,
                version_number=1,
                author=Author(slug="system"),
                change_description="Initial",
                created_at=datetime.now(UTC),
            ),
            created_at=datetime.now(UTC),
        )

    # Invalid slug (uppercase)
    with pytest.raises(ValidationError):
        Person(
            slug="Test-Entity",
            names=[Name(kind=NameKind.PRIMARY, en={"full": "Test"})],
            version_summary=VersionSummary(
                entity_or_relationship_id="entity:person/Test-Entity",
                type=VersionType.ENTITY,
                version_number=1,
                author=Author(slug="system"),
                change_description="Initial",
                created_at=datetime.now(UTC),
            ),
            created_at=datetime.now(UTC),
        )


def test_entity_with_multiple_names():
    """Test Entity with multiple name variations."""
    entity = Person(
        slug="test-entity",
        names=[
            Name(kind=NameKind.PRIMARY, en={"full": "Primary Name"}),
            Name(kind=NameKind.ALIAS, en={"full": "Alias Name"}),
            Name(kind=NameKind.ALTERNATE, en={"full": "Alternate Name"}),
        ],
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:person/test-entity",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert len(entity.names) == 3
    assert entity.names[0].kind == NameKind.PRIMARY
    assert entity.names[1].kind == NameKind.ALIAS
    assert entity.names[2].kind == NameKind.ALTERNATE


def test_entity_with_external_identifiers():
    """Test Entity with external identifiers."""
    entity = Person(
        slug="test-entity",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Test Person"})],
        identifiers=[
            ExternalIdentifier(
                scheme=IdentifierScheme.WIKIPEDIA,
                value="Test_Person",
                url="https://en.wikipedia.org/wiki/Test_Person",
            ),
            ExternalIdentifier(scheme=IdentifierScheme.WIKIDATA, value="Q12345"),
        ],
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:person/test-entity",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert len(entity.identifiers) == 2
    assert entity.identifiers[0].scheme == IdentifierScheme.WIKIPEDIA
    assert entity.identifiers[1].scheme == IdentifierScheme.WIKIDATA


def test_entity_with_tags_and_attributes():
    """Test Entity with tags and custom attributes."""
    entity = Person(
        slug="test-entity",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Test Person"})],
        tags=["politician", "activist", "writer"],
        attributes={
            "role": "politician",
            "party": "test-party",
            "active": True,
            "years_active": 10,
        },
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:person/test-entity",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert len(entity.tags) == 3
    assert "politician" in entity.tags
    assert entity.attributes["role"] == "politician"
    assert entity.attributes["active"] is True


# ===========================================================================
# New: entity_prefix field and id computation
# ===========================================================================


def _make_version_summary(entity_id: str):
    """Helper to build a VersionSummary for tests."""
    return VersionSummary(
        entity_or_relationship_id=entity_id,
        type=VersionType.ENTITY,
        version_number=1,
        author=Author(slug="system"),
        change_description="Initial",
        created_at=datetime.now(UTC),
    )


def test_entity_prefix_field_exists_on_organization():
    """Organization (and all entities) accept an entity_prefix field."""
    from nes.core.models.organization import Organization

    org = Organization(
        slug="department-of-immigration",
        entity_prefix="organization/nepal_govt/moha",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Department of Immigration"})],
        version_summary=_make_version_summary(
            "entity:organization/nepal_govt/moha/department-of-immigration"
        ),
        created_at=datetime.now(UTC),
    )
    assert org.entity_prefix == "organization/nepal_govt/moha"


def test_entity_prefix_overrides_id():
    """When entity_prefix is set, id uses it instead of type/sub_type."""
    from nes.core.models.organization import Organization

    org = Organization(
        slug="department-of-immigration",
        entity_prefix="organization/nepal_govt/moha",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Department of Immigration"})],
        version_summary=_make_version_summary(
            "entity:organization/nepal_govt/moha/department-of-immigration"
        ),
        created_at=datetime.now(UTC),
    )
    assert org.id == "entity:organization/nepal_govt/moha/department-of-immigration"


def test_entity_prefix_fallback_when_not_set():
    """When entity_prefix is not set, id falls back to type/sub_type — backward compat."""
    from nes.core.models.organization import PoliticalParty

    party = PoliticalParty(
        slug="nepali-congress",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Nepali Congress"})],
        version_summary=_make_version_summary(
            "entity:organization/political_party/nepali-congress"
        ),
        created_at=datetime.now(UTC),
    )
    assert party.entity_prefix is None
    assert party.id == "entity:organization/political_party/nepali-congress"


def test_entity_prefix_person_fallback():
    """Person without entity_prefix still produces correct id — backward compat."""
    person = Person(
        slug="rabi-lamichhane",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Rabi Lamichhane"})],
        version_summary=_make_version_summary("entity:person/rabi-lamichhane"),
        created_at=datetime.now(UTC),
    )
    assert person.entity_prefix is None
    assert person.id == "entity:person/rabi-lamichhane"


def test_entity_prefix_depth_too_deep_raises():
    """entity_prefix with more than MAX_PREFIX_DEPTH segments raises ValidationError."""
    from pydantic import ValidationError

    from nes.core.models.organization import Organization

    with pytest.raises(ValidationError):
        Organization(
            slug="some-org",
            entity_prefix="organization/a/b/c",  # 4 segments — exceeds MAX_PREFIX_DEPTH=3
            names=[Name(kind=NameKind.PRIMARY, en={"full": "Some Org"})],
            version_summary=_make_version_summary("entity:organization/a/b/c/some-org"),
            created_at=datetime.now(UTC),
        )


def test_entity_prefix_class_determined_by_first_segment():
    """An Organization instance with a 3-level prefix still IS an Organization."""
    from nes.core.models.organization import Organization

    org = Organization(
        slug="department-of-immigration",
        entity_prefix="organization/nepal_govt/moha",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Department of Immigration"})],
        version_summary=_make_version_summary(
            "entity:organization/nepal_govt/moha/department-of-immigration"
        ),
        created_at=datetime.now(UTC),
    )
    assert isinstance(org, Organization)
    assert org.type == "organization"


def test_entity_cannot_be_instantiated_directly():
    """Test that Entity class cannot be instantiated directly."""
    # Should fail when trying to instantiate Entity directly
    with pytest.raises(ValidationError, match="Cannot instantiate Entity directly"):
        Entity(
            slug="test-person",
            type="person",
            names=[Name(kind=NameKind.PRIMARY, en={"full": "Test Person"})],
            version_summary=VersionSummary(
                entity_or_relationship_id="entity:person/test-person",
                type=VersionType.ENTITY,
                version_number=1,
                author=Author(slug="system"),
                change_description="Initial",
                created_at=datetime.now(UTC),
            ),
            created_at=datetime.now(UTC),
        )
