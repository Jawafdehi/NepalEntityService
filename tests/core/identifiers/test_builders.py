"""Tests for identifier builders in nes."""

import pytest


# ===========================================================================
# Backward compat: existing build_entity_id / break_entity_id behaviour
# ===========================================================================


def test_build_entity_id_with_subtype():
    """Test building entity ID with subtype (deprecated wrapper — must keep working)."""
    from nes.core.identifiers.builders import build_entity_id

    entity_id = build_entity_id("person", "politician", "ram-chandra-poudel")
    assert entity_id == "entity:person/politician/ram-chandra-poudel"


def test_build_entity_id_without_subtype():
    """Test building entity ID without subtype (deprecated wrapper — must keep working)."""
    from nes.core.identifiers.builders import build_entity_id

    entity_id = build_entity_id("person", None, "ram-chandra-poudel")
    assert entity_id == "entity:person/ram-chandra-poudel"


def test_break_entity_id_with_subtype():
    """Test breaking entity ID with subtype — backward compat regression."""
    from nes.core.identifiers.builders import break_entity_id

    components = break_entity_id("entity:person/politician/ram-chandra-poudel")
    assert components.type == "person"
    assert components.subtype == "politician"
    assert components.slug == "ram-chandra-poudel"


def test_break_entity_id_without_subtype():
    """Test breaking entity ID without subtype — backward compat regression."""
    from nes.core.identifiers.builders import break_entity_id

    components = break_entity_id("entity:person/ram-chandra-poudel")
    assert components.type == "person"
    assert components.subtype is None
    assert components.slug == "ram-chandra-poudel"


# ===========================================================================
# New: EntityIdComponents.prefix field
# ===========================================================================


def test_entity_id_components_prefix_1_segment():
    """EntityIdComponents.prefix returns the full prefix — 1 segment."""
    from nes.core.identifiers.builders import break_entity_id

    components = break_entity_id("entity:person/rabi-lamichhane")
    assert components.prefix == "person"
    assert components.slug == "rabi-lamichhane"


def test_entity_id_components_prefix_2_segment():
    """EntityIdComponents.prefix returns the full prefix — 2 segments."""
    from nes.core.identifiers.builders import break_entity_id

    components = break_entity_id(
        "entity:organization/political_party/national-independent-party"
    )
    assert components.prefix == "organization/political_party"
    assert components.slug == "national-independent-party"


def test_entity_id_components_type_property_1_segment():
    """EntityIdComponents.type (compat property) returns first prefix segment."""
    from nes.core.identifiers.builders import break_entity_id

    components = break_entity_id("entity:person/rabi-lamichhane")
    assert components.type == "person"


def test_entity_id_components_type_property_2_segment():
    """EntityIdComponents.type (compat property) returns first prefix segment for 2-segment prefix."""
    from nes.core.identifiers.builders import break_entity_id

    components = break_entity_id(
        "entity:organization/political_party/national-independent-party"
    )
    assert components.type == "organization"


def test_entity_id_components_subtype_property_none():
    """EntityIdComponents.subtype (compat property) returns None for 1-segment prefix."""
    from nes.core.identifiers.builders import break_entity_id

    components = break_entity_id("entity:person/rabi-lamichhane")
    assert components.subtype is None


def test_entity_id_components_subtype_property_2_segment():
    """EntityIdComponents.subtype (compat property) returns second segment for 2-segment prefix."""
    from nes.core.identifiers.builders import break_entity_id

    components = break_entity_id(
        "entity:organization/political_party/national-independent-party"
    )
    assert components.subtype == "political_party"


# ===========================================================================
# New: 3-segment prefix support
# ===========================================================================


def test_break_entity_id_3_segment_prefix():
    """break_entity_id supports 3-segment entity_prefix (new capability)."""
    from nes.core.identifiers.builders import break_entity_id

    # RSP-like deep hierarchy: organization/nepal_govt/moha
    components = break_entity_id(
        "entity:organization/nepal_govt/moha/department-of-immigration"
    )
    assert components.prefix == "organization/nepal_govt/moha"
    assert components.slug == "department-of-immigration"
    assert components.type == "organization"
    assert components.subtype == "nepal_govt"


def test_break_entity_id_3_segment_prefix_location():
    """break_entity_id supports 3-segment prefix for location hierarchy."""
    from nes.core.identifiers.builders import break_entity_id

    components = break_entity_id(
        "entity:location/bagmati/district/kathmandu"
    )
    assert components.prefix == "location/bagmati/district"
    assert components.slug == "kathmandu"
    assert components.type == "location"


def test_break_entity_id_exceeds_max_depth_raises():
    """break_entity_id raises ValueError when prefix depth exceeds MAX_PREFIX_DEPTH."""
    from nes.core.identifiers.builders import break_entity_id

    # 4-segment prefix exceeds MAX_PREFIX_DEPTH=3 → must raise
    with pytest.raises(ValueError):
        break_entity_id("entity:a/b/c/d/some-slug")


def test_break_entity_id_invalid_prefix_raises():
    """break_entity_id raises ValueError for missing entity: prefix."""
    from nes.core.identifiers.builders import break_entity_id

    with pytest.raises(ValueError):
        break_entity_id("organization/nepal_govt/moha/slug")


# ===========================================================================
# New: build_entity_id_from_prefix
# ===========================================================================


def test_build_entity_id_from_prefix_1_segment():
    """build_entity_id_from_prefix works with 1-segment prefix."""
    from nes.core.identifiers.builders import build_entity_id_from_prefix

    assert (
        build_entity_id_from_prefix("person", "rabi-lamichhane")
        == "entity:person/rabi-lamichhane"
    )


def test_build_entity_id_from_prefix_2_segment():
    """build_entity_id_from_prefix works with 2-segment prefix."""
    from nes.core.identifiers.builders import build_entity_id_from_prefix

    assert (
        build_entity_id_from_prefix(
            "organization/political_party", "national-independent-party"
        )
        == "entity:organization/political_party/national-independent-party"
    )


def test_build_entity_id_from_prefix_3_segment():
    """build_entity_id_from_prefix works with 3-segment prefix."""
    from nes.core.identifiers.builders import build_entity_id_from_prefix

    assert (
        build_entity_id_from_prefix(
            "organization/nepal_govt/moha", "department-of-immigration"
        )
        == "entity:organization/nepal_govt/moha/department-of-immigration"
    )


def test_build_relationship_id():
    """Test building relationship ID."""
    from nes.core.identifiers.builders import build_relationship_id

    rel_id = build_relationship_id(
        "entity:person/ram-chandra-poudel",
        "entity:organization/political_party/nepali-congress",
        "MEMBER_OF",
    )
    assert (
        rel_id
        == "relationship:person/ram-chandra-poudel:organization/political_party/nepali-congress:MEMBER_OF"
    )


def test_break_relationship_id():
    """Test breaking relationship ID."""
    from nes.core.identifiers.builders import break_relationship_id

    components = break_relationship_id(
        "relationship:person/ram-chandra-poudel:organization/political_party/nepali-congress:MEMBER_OF"
    )
    assert components.source == "entity:person/ram-chandra-poudel"
    assert components.target == "entity:organization/political_party/nepali-congress"
    assert components.type == "MEMBER_OF"


def test_build_version_id():
    """Test building version ID."""
    from nes.core.identifiers.builders import build_version_id

    version_id = build_version_id("entity:person/ram-chandra-poudel", 1)
    assert version_id == "version:entity:person/ram-chandra-poudel:1"


def test_break_version_id():
    """Test breaking version ID."""
    from nes.core.identifiers.builders import break_version_id

    components = break_version_id("version:entity:person/ram-chandra-poudel:2")
    assert components.entity_or_relationship_id == "entity:person/ram-chandra-poudel"
    assert components.version_number == 2


def test_build_author_id():
    """Test building author ID."""
    from nes.core.identifiers.builders import build_author_id

    author_id = build_author_id("csv-importer")
    assert author_id == "author:csv-importer"


def test_break_author_id():
    """Test breaking author ID."""
    from nes.core.identifiers.builders import break_author_id

    components = break_author_id("author:csv-importer")
    assert components.slug == "csv-importer"
